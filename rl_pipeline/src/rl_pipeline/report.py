"""Stage 8: a readable REPORT.md for one run, built only from the run directory's files."""
from __future__ import annotations

from collections import Counter
from typing import Any

from .budget import Budget
from .config import Config
from .store import RunStore


def _table(header: list[str], rows: list[list[Any]]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    return out + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def _rate(block: dict[str, Any], name: str) -> str:
    x = block.get(name) or {}
    if not block.get("n"):
        return "-"
    lo, hi = x.get("ci95", (0, 0))
    return f"{x['k']}/{block['n']} ({x['rate']:.2f}, {lo:.2f}-{hi:.2f})"


def build_report(cfg: Config, store: RunStore, budget: Budget) -> str:
    L: list[str] = [f"# Run report: `{cfg.run_name}`", "",
                    f"Config: `{cfg.source_path.name if cfg.source_path else '?'}` · policy "
                    f"`{cfg.azure.policy_deployment}` · label source `{cfg.reward.label_source}` · "
                    f"budget ${budget.spent:.2f} of ${budget.max_usd:.2f} spent.", ""]

    imp = store.read_json(store.root / "import_summary.json", {})
    sel = store.read_json(store.root / "select_summary.json", {})
    replay = store.read(store.replay_check)
    rollouts = store.read(store.rollouts)
    pairs = store.read_json(store.pairs_dir / "summary.json", {})
    ft = store.read_json(store.finetune_state, {}) or {}
    ev = store.read_json(store.eval_summary, {})

    L += ["## 1. Data funnel", ""]
    sample = [r for r in rollouts if r.get("phase") == "sample"]
    sample_ok = [r for r in sample if r["status"] == "ok"]
    rows = [
        ["recorded episodes imported", imp.get("episodes", "-"), ", ".join(f"{k} {v}" for k, v in sorted((imp.get("skipped") or {}).items()))],
        ["branch points selected", sel.get("branch_points", "-"), ", ".join(f"{k} {v}" for k, v in sorted((sel.get("not_used") or {}).items()))],
        ["branch points whose prefix replays faithfully", f"{sum(r['ok'] for r in replay)}/{len(replay)}", ""],
        ["training rollouts (base policy)", f"{len(sample_ok)} ok / {len(sample)}", ", ".join(f"{k} {v}" for k, v in Counter(r["status"] for r in sample).items())],
        ["preference pairs (train / val)", f"{pairs.get('train_pairs', '-')} / {pairs.get('val_pairs', '-')}",
         f"{pairs.get('branches_with_pairs', 0)} of {pairs.get('branches', 0)} branch points had both a 0 and a 1"],
    ]
    L += _table(["stage", "count", "notes"], rows) + [""]

    if sample_ok:
        L += ["## 2. What the base policy did from the training branch points", ""]
        c = Counter((r["task"], r["reward"]["reason"]) for r in sample_ok)
        tasks = sorted({t for t, _ in c})
        reasons = ["clean_completion", "action_cheat", "not_completed"]
        L += _table(["task"] + reasons, [[t] + [c.get((t, x), 0) for x in reasons] for t in tasks]) + [""]

    if pairs:
        L += ["## 3. Preference pairs", "",
              f"- Rejected side, by reason: {pairs.get('rejected_reason')}",
              f"- Turn of the continuation where the pair diverges (5 = 5 or later): {pairs.get('divergence_turn')}",
              f"- Pairs whose two contexts are byte-identical: {pairs.get('context_exact')} of "
              f"{pairs.get('train_pairs', 0) + pairs.get('val_pairs', 0)} (the rest differ only in masked values)", ""]

    if ft:
        L += ["## 4. Fine-tuning job", ""]
        rows = [[k, ft.get(k)] for k in ("job_id", "status", "fine_tuned_model", "trained_tokens",
                                         "training_charged", "deployment", "error") if ft.get(k) is not None]
        L += _table(["field", "value"], rows) + [""]

    if ev:
        L += ["## 5. Evaluation: base vs tuned", "",
              "Rates are k/n (rate, Wilson 95% interval). Branch-point evaluation uses held-out branch points; "
              "the paired delta is tuned minus base mean reward per branch point, with a bootstrap 95% interval.", ""]
        for kind, title in (("branch", "Held-out branch points"), ("fresh", "Fresh episodes from step 0")):
            sec = ev.get(kind)
            if not sec:
                continue
            L += [f"### {title}", ""]
            rows = []
            for task, block in sec.items():
                for pol in ("base", "tuned"):
                    b = block.get(pol) or {}
                    j = b.get("judge") or {}
                    rows.append([task, pol, b.get("n", 0), _rate(b, "clean_completion"), _rate(b, "action_cheat"),
                                 _rate(b, "not_completed"),
                                 f"{j.get('intent_dirty', '-')}/{j.get('n', '-')}" if j else "-"])
            L += _table(["task", "policy", "n", "clean completion (reward 1)", "action cheat", "not completed",
                         "judge: intent flagged"], rows) + [""]
            if kind == "branch":
                for task, block in sec.items():
                    p = block.get("paired") or {}
                    if p.get("branch_points"):
                        L.append(f"- **{task}**: paired delta {p['mean_delta_reward']:+.3f} (95% CI {p['ci95'][0]:+.3f} to "
                                 f"{p['ci95'][1]:+.3f}) over {p['branch_points']} branch points; improved "
                                 f"{p['improved']}, worse {p['worse']}, same {p['same']}.")
                L.append("")

    L += ["## 6. Spend", ""]
    L += _table(["item", "USD"], [[k, v] for k, v in budget.summary().items()]) + [""]
    return "\n".join(L)
