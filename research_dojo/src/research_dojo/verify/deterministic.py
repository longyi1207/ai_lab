"""Deterministic verification: non-empty check, exact/substring match against
`expected` when the sample sets one. No LLM call — this always runs first,
cheaply, before the (optional) judge call.
"""

from __future__ import annotations


def check_deterministic(completion: str, expected: str | None) -> dict:
    text = (completion or "").strip()
    if not text:
        return {"passed": False, "reason": "empty completion"}
    if expected is None:
        return {"passed": True, "reason": "non-empty; no expected value to match"}
    if text.lower() == expected.strip().lower():
        return {"passed": True, "reason": "exact match (case-insensitive)"}
    if expected.strip().lower() in text.lower():
        return {"passed": True, "reason": "expected substring found in completion"}
    return {"passed": False, "reason": f"completion did not match or contain expected={expected!r}"}
