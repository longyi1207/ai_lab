from __future__ import annotations

from research_dojo.alerts import rules


def test_budget_threshold_none_below_80pct():
    assert rules.budget_threshold("r1", 1.0, 10.0) is None


def test_budget_threshold_warning_at_80pct():
    trigger = rules.budget_threshold("r1", 8.0, 10.0)
    assert trigger is not None
    assert trigger.rule == "budget_threshold"
    assert trigger.severity == "warning"


def test_budget_threshold_exceeded_at_100pct():
    trigger = rules.budget_threshold("r1", 10.0, 10.0)
    assert trigger.rule == "budget_exceeded"
    assert trigger.severity == "critical"


def test_run_stale_below_threshold_is_none():
    assert rules.run_stale("r1", 5.0, 600) is None


def test_run_stale_above_threshold():
    trigger = rules.run_stale("r1", 700.0, 600)
    assert trigger.rule == "run_stale"


def test_consecutive_failures_below_k_is_none():
    assert rules.consecutive_failures("r1", 2, k=5) is None


def test_consecutive_failures_at_k():
    trigger = rules.consecutive_failures("r1", 5, k=5)
    assert trigger.severity == "critical"


def test_sanity_spike_threshold():
    assert rules.sanity_spike("r1", 1, 10, threshold_pct=0.2) is None
    trigger = rules.sanity_spike("r1", 3, 10, threshold_pct=0.2)
    assert trigger.rule == "sanity_spike"


def test_dlq_non_empty():
    assert rules.dlq_non_empty("r1", 0) is None
    trigger = rules.dlq_non_empty("r1", 3)
    assert trigger.rule == "dlq_non_empty"
