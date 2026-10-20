"""Command-line entry point: ``python -m rl_pipeline <stage> --config configs/pilot.yaml``.

Run the stages in order, or ``run-all`` to do everything. Every stage prints a short JSON summary
and writes its files under ``outputs/<run_name>/``.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys

from .budget import BudgetExceeded
from .config import load_config
from .report import build_report
from .stages import Pipeline

STAGES = ["import", "select", "replay", "sample", "pairs", "finetune", "deploy", "evaluate",
          "teardown", "report", "run-all", "local-dpo", "local-grpo", "serve-env"]


def _local_policy(cfg):
    from .local.model import LocalPolicy
    lc = cfg.local
    return LocalPolicy(lc.model, device=lc.device, lora_r=lc.lora_r, lora_alpha=lc.lora_alpha,
                       max_prompt_tokens=lc.max_prompt_tokens, seed=lc.seed)


def _run_local_dpo(p: "Pipeline", trainer: str = "hand") -> dict:
    lc = p.cfg.local
    examples = p.store.read(p.store.pairs_dir / "train.jsonl") + p.store.read(p.store.pairs_dir / "val.jsonl")
    if lc.dpo_max_pairs:
        examples = examples[: lc.dpo_max_pairs]
    kw = dict(beta=lc.dpo_beta, epochs=lc.dpo_epochs, lr=lc.dpo_lr, seed=lc.seed)
    if trainer == "trl":
        from .local.trl_dpo import train_trl_dpo
        return train_trl_dpo(_local_policy(p.cfg), examples, p.store.root / "local" / "dpo_trl", **kw)
    from .local.dpo import train_dpo
    return train_dpo(_local_policy(p.cfg), examples, p.store.root / "local" / "dpo", **kw)


def _run_local_grpo(p: "Pipeline") -> dict:
    from .local.grpo import train_grpo
    from .local.toy_env import ToyShortcutTask
    lc = p.cfg.local
    if lc.grpo_env == "toy":
        starts = [(ToyShortcutTask(), None, {"branch_id": "toy", "task": "toy_shortcut", "cell": {},
                                              "branch_step": 1, "split": "train"})]
    else:
        ok = p._replay_ok()
        bps = [b for b in p.store.read(p.store.branch_points) if b["split"] == "train" and b["branch_id"] in ok]
        bps = bps[: lc.grpo_branch_points]
        eps = p.episodes_by_id({b["episode_id"] for b in bps})
        starts = [(p.tasks[b["task"]], eps[b["episode_id"]], b) for b in bps]
    out = p.store.root / "local" / f"grpo_{lc.grpo_env}"
    return train_grpo(_local_policy(p.cfg), starts, out, iterations=lc.grpo_iterations,
                      groups_per_iter=lc.grpo_groups_per_iter, k=lc.grpo_k, lr=lc.grpo_lr,
                      kl_coef=lc.grpo_kl_coef, clip_eps=lc.grpo_clip_eps, ppo_epochs=lc.grpo_ppo_epochs,
                      max_new_steps=lc.grpo_max_new_steps, temperature=lc.temperature,
                      max_new_tokens=lc.max_new_tokens, label_source=p.cfg.reward.label_source,
                      intent_policy=p.cfg.reward.intent_policy, eval_rollouts=lc.grpo_eval_rollouts,
                      seed=lc.seed)


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def apply_overrides(cfg, items: list[str]) -> None:
    """``--set section.key=value`` overrides, typed like the field they replace."""
    for item in items or []:
        path, _, raw = item.partition("=")
        *parents, leaf = path.strip().split(".")
        obj = cfg
        for name in parents:
            obj = getattr(obj, name)
        if not hasattr(obj, leaf):
            raise SystemExit(f"--set: unknown config key {path!r}")
        current = getattr(obj, leaf)
        if isinstance(current, bool):
            value = raw.lower() in ("1", "true", "yes", "on")
        elif isinstance(current, (int, float)) and current is not None:
            value = type(current)(raw)
        else:
            value = raw
        setattr(obj, leaf, value)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rl_pipeline", description=__doc__.split("\n")[0])
    ap.add_argument("stage", choices=STAGES)
    ap.add_argument("--config", default="configs/pilot.yaml")
    ap.add_argument("--env-file", default=None, help="overrides azure.env_file")
    ap.add_argument("--limit", type=int, default=None, help="only the first N branch points (smoke tests)")
    ap.add_argument("--no-wait", action="store_true", help="finetune: submit and return without waiting")
    ap.add_argument("--policies", default="base,tuned", help="evaluate: comma-separated policy labels")
    ap.add_argument("--retry-failed", action="store_true",
                    help="sample/evaluate: drop crashed or provider-failed rollouts first, so they rerun")
    ap.add_argument("--grpo-env", choices=["toy", "branch"], default=None,
                    help="local-grpo: train in the toy task or from Docker branch points")
    ap.add_argument("--trainer", choices=["hand", "trl"], default="hand",
                    help="local-dpo: the hand-written trainer or TRL's DPOTrainer (cross-check)")
    ap.add_argument("--host", default="127.0.0.1", help="serve-env: bind address")
    ap.add_argument("--port", type=int, default=8000, help="serve-env: port")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE",
                    help="override a config value, e.g. --set local.grpo_iterations=2 (repeatable)")
    ap.add_argument("--log-level", default="INFO")
    a = ap.parse_args(argv)

    logging.basicConfig(level=a.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for noisy in ("httpx", "httpx2", "openai", "transformers", "torch"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    cfg = load_config(a.config, env_file=a.env_file)
    apply_overrides(cfg, a.set)
    p = Pipeline(cfg)

    def report() -> None:
        p.store.report.write_text(build_report(cfg, p.store, p.budget))
        print(f"wrote {p.store.report}")

    try:
        if a.stage == "import":
            _print(p.import_())
        elif a.stage == "select":
            _print(p.select())
        elif a.stage == "replay":
            _print(p.replay_check(a.limit))
        elif a.stage == "sample":
            if a.retry_failed:
                logging.info("dropped %d failed sample rollouts for retry", p.drop_failed("sample"))
            _print(p.sample(a.limit))
        elif a.stage == "pairs":
            _print(p.pairs())
        elif a.stage == "finetune":
            _print(p.finetune(wait_for_job=not a.no_wait))
        elif a.stage == "deploy":
            print(p.deploy())
        elif a.stage == "evaluate":
            if a.retry_failed:
                logging.info("dropped %d failed eval rollouts for retry", p.drop_failed("eval"))
            _print(p.evaluate(a.limit, tuple(x.strip() for x in a.policies.split(",") if x.strip())))
        elif a.stage == "teardown":
            p.teardown()
        elif a.stage == "report":
            report()
        elif a.stage == "local-dpo":
            _print(_run_local_dpo(p, a.trainer))
        elif a.stage == "local-grpo":
            if a.grpo_env:
                cfg.local.grpo_env = a.grpo_env
            _print(_run_local_grpo(p))
        elif a.stage == "serve-env":
            import uvicorn
            from .openenv_env import make_app
            uvicorn.run(make_app(cfg), host=a.host, port=a.port)
        elif a.stage == "run-all":
            for name, fn in (("import", p.import_), ("select", p.select), ("replay", p.replay_check),
                             ("sample", p.sample), ("pairs", p.pairs), ("finetune", p.finetune),
                             ("deploy", p.deploy), ("evaluate", p.evaluate)):
                logging.info("=== %s ===", name)
                _print(fn())
            p.teardown()
            report()
    except BudgetExceeded as e:
        logging.error("stopped: %s (finished work is saved; raise budget.max_usd to continue)", e)
        report()
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
