"""The pipeline stages, wired together. ``cli.py`` exposes each one as a subcommand.

Each stage reads the previous stage's files from the run directory and writes its own, so stages
can be run one at a time, inspected, and rerun. Stages that call a model are resumable: finished
rollouts are skipped on a rerun.
"""
from __future__ import annotations

import logging
import threading
from collections import Counter
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from typing import Any, Callable

from tqdm import tqdm

from .budget import Budget, BudgetExceeded
from .config import Config
from .decision_points import select_branch_points
from .episodes import import_episodes
from .evaluate import summarize
from .finetune import FineTuner
from .llm import AzureChat, make_openai_client
from .pairs import build_pairs, recorded_rollout, validate_example
from .replay import replay_prefix
from .rollout import rollout_key, run_rollout
from .store import RunStore
from .tasks import Task, get_task
from .transcript import prefix_before

log = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.store = RunStore(cfg.run_dir)
        self.budget = Budget(cfg.budget.max_usd, cfg.budget.prices, self.store.spend)
        self._tasks: dict[str, Task] | None = None
        self._chat: AzureChat | None = None

    # lazily built so offline stages never need credentials
    @property
    def tasks(self) -> dict[str, Task]:
        if self._tasks is None:
            self._tasks = {n: get_task(n, self.cfg.paths.score_seeking_eval) for n in self.cfg.select.tasks}
        return self._tasks

    @property
    def chat(self) -> AzureChat:
        if self._chat is None:
            self._chat = AzureChat(self.budget)
        return self._chat

    def episodes_by_id(self, ids: set[str] | None = None) -> dict[str, dict[str, Any]]:
        return {e["episode_id"]: e for e in self.store.iter(self.store.episodes)
                if ids is None or e["episode_id"] in ids}

    # stage 1 ---------------------------------------------------------------------------------
    def import_(self) -> dict[str, Any]:
        eps, skipped = import_episodes(self.cfg.runs_dir, self.tasks, label_source=self.cfg.reward.label_source,
                                       intent_policy=self.cfg.reward.intent_policy)
        self.store.write_jsonl(self.store.episodes, eps)
        summary = {"episodes": len(eps), "skipped": dict(skipped),
                   "by_task_reason": dict(Counter(f"{e['task']}:{e['reward']['reason']}" for e in eps))}
        self.store.write_json(self.store.root / "import_summary.json", summary)
        return summary

    # stage 2 ---------------------------------------------------------------------------------
    def select(self) -> dict[str, Any]:
        s = self.cfg.select
        eps = list(self.store.iter(self.store.episodes))
        bps, skipped = select_branch_points(eps, margin=s.margin, max_per_task=s.max_branch_points_per_task,
                                            include_temptation=s.include_temptation_points,
                                            test_fraction=s.test_fraction, seed=s.seed)
        self.store.write_jsonl(self.store.branch_points, bps)
        summary = {"branch_points": len(bps), "not_used": skipped,
                   "by_task_kind_split": dict(Counter(f"{b['task']}:{b['kind']}:{b['split']}" for b in bps))}
        self.store.write_json(self.store.root / "select_summary.json", summary)
        return summary

    # stage 3 ---------------------------------------------------------------------------------
    def replay_check(self, limit: int | None = None) -> dict[str, Any]:
        bps = self.store.read(self.store.branch_points)[:limit]
        done = self.store.done_keys(self.store.replay_check, key=lambda r: r["branch_id"])
        todo = [b for b in bps if b["branch_id"] not in done]
        eps = self.episodes_by_id({b["episode_id"] for b in todo})

        def one(bp: dict[str, Any]) -> None:
            task = self.tasks[bp["task"]]
            with task.sandbox() as sb:
                r = replay_prefix(task, sb, bp["cell"], prefix_before(eps[bp["episode_id"]]["transcript"],
                                                                      bp["branch_step"]))
            self.store.append(self.store.replay_check, {"branch_id": bp["branch_id"], "task": bp["task"],
                                                        **r.stats()})

        self._parallel(todo, one, desc="replay", workers=self.cfg.sample.workers)
        rows = self.store.read(self.store.replay_check)
        return {"checked": len(rows), "ok": sum(r["ok"] for r in rows),
                "by_task": dict(Counter(f"{r['task']}:{'ok' if r['ok'] else 'mismatch'}" for r in rows))}

    def drop_failed(self, phase: str) -> int:
        """Remove crashed or provider-failed rollouts of a phase so a rerun retries them.

        ``replay_mismatch`` is kept: it is a property of the branch point, not a transient failure.
        Never call this while a stage is writing to the same run directory.
        """
        keep, dropped = [], 0
        for r in self.store.iter(self.store.rollouts):
            transient = r.get("phase") == phase and r["status"] not in ("ok", "replay_mismatch")
            dropped += transient
            if not transient:
                keep.append(r)
        if dropped:
            self.store.write_jsonl(self.store.rollouts, keep)
        return dropped

    def _replay_ok(self) -> set[str]:
        return {r["branch_id"] for r in self.store.iter(self.store.replay_check) if r["ok"]}

    # stages 4 and 7 --------------------------------------------------------------------------
    def _rollouts(self, jobs: list[tuple[dict[str, Any], str, str, int]], *, phase: str, k_desc: str,
                  judge: bool) -> None:
        done = self.store.done_keys(self.store.rollouts)
        todo = [j for j in jobs if rollout_key(j[0]["branch_id"], j[1], j[3]) not in done]
        ids = {j[0]["episode_id"] for j in todo if j[0].get("episode_id")}
        eps = self.episodes_by_id(ids)
        s, r = self.cfg.sample, self.cfg.reward
        judge_model = self.cfg.azure.judge_deployment if judge else None
        log.info("%s: %d rollouts to run (%d already on disk)", phase, len(todo), len(jobs) - len(todo))

        def one(job: tuple[dict[str, Any], str, str, int]) -> None:
            bp, label, model, idx = job
            rec = run_rollout(self.tasks[bp["task"]], eps.get(bp.get("episode_id")), bp, chat=self.chat,
                              model=model, policy_label=label, sample_idx=idx, max_new_steps=s.max_new_steps,
                              temperature=s.temperature, max_tokens=s.max_tokens, label_source=r.label_source,
                              intent_policy=r.intent_policy, judge_model=judge_model, phase=phase)
            self.store.append(self.store.rollouts, rec)

        self._parallel(todo, one, desc=k_desc, workers=s.workers)

    def sample(self, limit: int | None = None) -> dict[str, Any]:
        """K base-policy continuations per training branch point (the training data)."""
        ok = self._replay_ok()
        bps = [b for b in self.store.read(self.store.branch_points) if b["split"] == "train" and b["branch_id"] in ok]
        bps = bps[:limit]
        jobs = [(bp, "base", self.cfg.azure.policy_deployment, i) for bp in bps for i in range(self.cfg.sample.k)]
        self._rollouts(jobs, phase="sample", k_desc="sample", judge=self.cfg.judge.enabled and self.cfg.judge.scope == "all")
        return self.rollout_summary("sample")

    def rollout_summary(self, phase: str) -> dict[str, Any]:
        recs = [r for r in self.store.iter(self.store.rollouts) if r.get("phase") == phase]
        return {"rollouts": len(recs),
                "status": dict(Counter(r["status"] for r in recs)),
                "reward": dict(Counter(f"{r['task']}:{r['policy']}:{r['reward']['reason']}"
                                       for r in recs if r["status"] == "ok")),
                "spent_usd": round(self.budget.spent, 2)}

    # stage 5 ---------------------------------------------------------------------------------
    def pairs(self) -> dict[str, Any]:
        rollouts = list(self.store.iter(self.store.rollouts))
        recorded = None
        if self.cfg.pairs.include_recorded:
            ok = self._replay_ok()
            bps = [b for b in self.store.read(self.store.branch_points) if b["split"] == "train" and b["branch_id"] in ok]
            eps = self.episodes_by_id({b["episode_id"] for b in bps})
            recorded = [recorded_rollout(b, eps[b["episode_id"]]) for b in bps]
        built = build_pairs(self.tasks, rollouts, max_pairs_per_branch=self.cfg.pairs.max_pairs_per_branch,
                            val_fraction=self.cfg.pairs.val_fraction, seed=self.cfg.select.seed,
                            recorded=recorded)
        bad = [p for ex in built["train"] + built["val"] for p in validate_example(ex)]
        if bad:
            raise RuntimeError(f"{len(bad)} invalid pair(s), e.g. {bad[0]}")
        self.store.write_jsonl(self.store.pairs_dir / "train.jsonl", built["train"])
        self.store.write_jsonl(self.store.pairs_dir / "val.jsonl", built["val"])
        self.store.write_jsonl(self.store.pairs_dir / "meta.jsonl", built["meta"])
        counts = built["counts"] | {
            "rejected_reason": dict(Counter(m["rejected_reason"] for m in built["meta"])),
            "divergence_turn": dict(Counter(min(m["divergence_turn"], 5) for m in built["meta"])),
            "context_exact": sum(m["context_exact"] for m in built["meta"]),
            "by_task": dict(Counter(m["task"] for m in built["meta"])),
            "chosen_policy": dict(Counter(m["chosen_policy"] for m in built["meta"])),
            "rejected_policy": dict(Counter(m["rejected_policy"] for m in built["meta"])),
        }
        self.store.write_json(self.store.pairs_dir / "summary.json", counts)
        if counts["train_pairs"] < self.cfg.pairs.min_pairs:
            log.warning("only %d training pairs (min_pairs=%d): fine-tuning will be skipped",
                        counts["train_pairs"], self.cfg.pairs.min_pairs)
        return counts

    # stage 6 ---------------------------------------------------------------------------------
    def finetuner(self) -> FineTuner:
        return FineTuner(self.cfg, self.store, make_openai_client(max_retries=5), self.budget)

    def finetune(self, wait_for_job: bool = True) -> dict[str, Any]:
        counts = self.store.read_json(self.store.pairs_dir / "summary.json", {})
        if counts.get("train_pairs", 0) < self.cfg.pairs.min_pairs:
            raise RuntimeError(f"not enough training pairs ({counts.get('train_pairs', 0)}); "
                               "sample more branch points first")
        ft = self.finetuner()
        ft.upload()
        ft.submit()
        return ft.wait() if wait_for_job else ft.state

    def deploy(self) -> str:
        return self.finetuner().deploy()

    def teardown(self) -> None:
        self.finetuner().teardown()

    # stage 7 ---------------------------------------------------------------------------------
    def evaluate(self, limit: int | None = None, policies: tuple[str, ...] = ("base", "tuned")) -> dict[str, Any]:
        ok = self._replay_ok()
        test = [b for b in self.store.read(self.store.branch_points) if b["split"] == "test" and b["branch_id"] in ok]
        test = test[:limit]
        state = self.store.read_json(self.store.finetune_state, {}) or {}
        models = {"base": self.cfg.azure.policy_deployment, "tuned": state.get("deployment")}
        if "tuned" in policies and not models["tuned"]:
            raise RuntimeError("no tuned deployment; run `finetune` and `deploy` first")
        jobs = [(bp, p, models[p], i) for p in policies for bp in test for i in range(self.cfg.evaluate.k)]
        # fresh episodes from step 0, in the conditions of the test branch points
        n_fresh = self.cfg.evaluate.fresh_episodes
        if n_fresh:
            for task in self.cfg.select.tasks:
                cells = []
                for b in test:
                    if b["task"] == task and b["cell"] not in cells:
                        cells.append(b["cell"])
                for i in range(n_fresh):
                    if not cells:
                        break
                    fresh = {"branch_id": f"fresh:{task}:{i}", "task": task, "cell": cells[i % len(cells)],
                             "branch_step": 1, "split": "test"}
                    jobs += [(fresh, p, models[p], 0) for p in policies]
        self._rollouts(jobs, phase="eval", k_desc="evaluate", judge=self.cfg.judge.enabled)
        recs = [r for r in self.store.iter(self.store.rollouts) if r.get("phase") == "eval"]
        summary = summarize(recs)
        self.store.write_json(self.store.eval_summary, summary)
        return summary

    # helpers ---------------------------------------------------------------------------------
    def _parallel(self, items: list[Any], fn: Callable[[Any], None], *, desc: str, workers: int) -> None:
        """Run ``fn`` over ``items`` with a thread pool; stop everything on the first budget stop."""
        if not items:
            return
        stop = threading.Event()

        def guarded(item: Any) -> None:
            if stop.is_set():
                return
            try:
                fn(item)
            except BudgetExceeded:
                stop.set()
                raise

        with ThreadPoolExecutor(max_workers=workers) as ex, tqdm(total=len(items), desc=desc) as bar:
            futures = [ex.submit(guarded, it) for it in items]
            for f in futures:
                f.add_done_callback(lambda _f: bar.update(1))
            done, _ = wait(futures, return_when=FIRST_EXCEPTION)
            errors = [f.exception() for f in done if f.exception()]
            if errors:
                stop.set()
                for f in futures:
                    f.cancel()
                raise errors[0]
