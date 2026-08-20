"""Alert rule evaluators (pillar 5.1). Pure functions: given state, return a
trigger or None. The engine/supervisor call these at the right point in the
state machine and pass any trigger to alerts.dispatcher.dispatch().
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AlertTrigger:
    rule: str
    severity: str
    message: str


def run_failed(run_id: str, error_summary: str | None) -> AlertTrigger:
    return AlertTrigger("run_failed", "critical", f"run {run_id} FAILED: {error_summary or 'unknown error'}")


def budget_threshold(run_id: str, cost_usd: float, max_usd: float) -> AlertTrigger | None:
    if max_usd <= 0:
        return None
    ratio = cost_usd / max_usd
    if ratio >= 1.0:
        return AlertTrigger(
            "budget_exceeded", "critical", f"run {run_id} cost ${cost_usd:.2f} >= cap ${max_usd:.2f}"
        )
    if ratio >= 0.8:
        return AlertTrigger(
            "budget_threshold", "warning",
            f"run {run_id} cost ${cost_usd:.2f} is {ratio:.0%} of cap ${max_usd:.2f}",
        )
    return None


def run_stale(run_id: str, seconds_since_heartbeat: float, threshold_seconds: int) -> AlertTrigger | None:
    if seconds_since_heartbeat > threshold_seconds:
        return AlertTrigger(
            "run_stale", "warning",
            f"run {run_id} heartbeat stale for {seconds_since_heartbeat:.0f}s (threshold {threshold_seconds}s)",
        )
    return None


def consecutive_failures(run_id: str, count: int, k: int = 3) -> AlertTrigger | None:
    if count >= k:
        return AlertTrigger(
            "consecutive_failures", "critical", f"run {run_id} has {count} consecutive rollout failures"
        )
    return None


def sanity_spike(run_id: str, flagged: int, total: int, threshold_pct: float = 0.2) -> AlertTrigger | None:
    if total == 0:
        return None
    pct = flagged / total
    if pct >= threshold_pct:
        return AlertTrigger(
            "sanity_spike", "critical",
            f"run {run_id}: {flagged}/{total} ({pct:.0%}) recent rollouts flagged by sanity checks",
        )
    return None


def dlq_non_empty(run_id: str, count: int) -> AlertTrigger | None:
    if count > 0:
        return AlertTrigger("dlq_non_empty", "warning", f"run {run_id} finished with {count} unresolved DLQ entries")
    return None
