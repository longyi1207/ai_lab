"""Stage 7: compare the base and fine-tuned policies.

Two measurements, both on data the policy was never trained on:

* **Held-out branch points.** Both policies continue from the same test branch points (same
  replayed state, K samples each). Because the states are identical, we can compare per branch
  point: the paired difference in mean reward is the cleanest estimate of what training changed.
* **Fresh episodes.** Full episodes from step 0 in the conditions of the test branch points. This
  is closer to deployment, noisier, and more expensive per sample.

For each policy we report the rate of clean completions (reward 1), of cheating (action_cheat),
and of failing without cheating (not_completed), with Wilson 95% intervals. A policy that "stops
cheating" by giving up would show cheating down and not_completed up; the reward rate is what
we actually want to go up.

The intent judge runs on evaluation rollouts as a **monitor**. If training taught the policy to
hide its intent rather than drop it, we would see clean completions whose transcripts the judge
flags, or the judge's flag rate falling much faster than the grader's cheat rate.
"""
from __future__ import annotations

import math
import random
from collections import defaultdict
from typing import Any


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3))


def rates(records: list[dict[str, Any]]) -> dict[str, Any]:
    ok = [r for r in records if r.get("status") == "ok"]
    n = len(ok)
    out: dict[str, Any] = {"n": n, "excluded": len(records) - n}
    for name in ("clean_completion", "action_cheat", "not_completed", "intent_cheat"):
        k = sum(r["reward"]["reason"] == name for r in ok)
        out[name] = {"k": k, "rate": round(k / n, 3) if n else None, "ci95": wilson(k, n)}
    judged = [r for r in ok if isinstance(r.get("intent_judge"), dict) and not r["intent_judge"].get("judge_error")]
    if judged:
        dirty = [r for r in judged if r["reward"]["intent"] == "dirty"]
        clean_done = [r for r in judged if r["reward"]["reason"] == "clean_completion"]
        hidden = [r for r in clean_done if r["reward"]["intent"] == "dirty"]
        out["judge"] = {"n": len(judged), "intent_dirty": len(dirty),
                        "intent_dirty_rate": round(len(dirty) / len(judged), 3),
                        "clean_completions_flagged": len(hidden),
                        "clean_completions": len(clean_done)}
    return out


def paired_delta(records: list[dict[str, Any]], base: str, tuned: str, *, n_boot: int = 2000,
                 seed: int = 0) -> dict[str, Any]:
    """Mean over branch points of (tuned mean reward - base mean reward), with a bootstrap CI."""
    per: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for r in records:
        if r.get("status") == "ok":
            per[r["branch_id"]][r["policy"]].append(r["reward"]["reward"])
    diffs = [sum(v[tuned]) / len(v[tuned]) - sum(v[base]) / len(v[base])
             for v in per.values() if v.get(base) and v.get(tuned)]
    if not diffs:
        return {"branch_points": 0}
    rng = random.Random(seed)
    boots = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(n_boot))
    return {"branch_points": len(diffs), "mean_delta_reward": round(sum(diffs) / len(diffs), 3),
            "ci95": (round(boots[int(0.025 * n_boot)], 3), round(boots[int(0.975 * n_boot) - 1], 3)),
            "improved": sum(d > 0 for d in diffs), "worse": sum(d < 0 for d in diffs),
            "same": sum(d == 0 for d in diffs)}


def summarize(eval_records: list[dict[str, Any]], base: str = "base", tuned: str = "tuned") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for kind, select in (("branch", lambda r: not r["branch_id"].startswith("fresh:")),
                         ("fresh", lambda r: r["branch_id"].startswith("fresh:"))):
        recs = [r for r in eval_records if select(r)]
        if not recs:
            continue
        section: dict[str, Any] = {}
        for task in sorted({r["task"] for r in recs} | {"all"}):
            sub = [r for r in recs if task == "all" or r["task"] == task]
            section[task] = {p: rates([r for r in sub if r["policy"] == p]) for p in (base, tuned)}
            if kind == "branch":
                section[task]["paired"] = paired_delta(sub, base, tuned)
        out[kind] = section
    return out
