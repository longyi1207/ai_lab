"""Apparent-vs-real progress guards (pillar 7.3). A rollout that "looks done"
(high judge score, deterministic pass) but has no real content is worse than
an honest failure — it hides broken harnesses behind a green dashboard.
"""

from __future__ import annotations

SANITY_HIGH_SCORE_THRESHOLD = 0.7


def check_sanity(completion: str, judge_score: float | None, deterministic_passed: bool | None) -> list[dict]:
    flags: list[dict] = []
    empty = not (completion or "").strip()

    if empty and judge_score is not None and judge_score >= SANITY_HIGH_SCORE_THRESHOLD:
        flags.append({
            "kind": "empty_completion_high_score",
            "severity": "critical",
            "detail": f"completion is empty but judge score={judge_score:.2f} — apparent progress without real output",
        })

    if empty and deterministic_passed:
        flags.append({
            "kind": "empty_completion_deterministic_pass",
            "severity": "critical",
            "detail": "completion is empty but deterministic check reported pass",
        })

    return flags
