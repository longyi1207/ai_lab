from __future__ import annotations

from research_dojo.engine.state_machine import is_terminal, is_valid_transition


def test_pending_to_running_valid():
    assert is_valid_transition("PENDING", "RUNNING")


def test_running_to_verifying_valid():
    assert is_valid_transition("RUNNING", "VERIFYING")


def test_verifying_to_complete_valid():
    assert is_valid_transition("VERIFYING", "COMPLETE")


def test_complete_to_anything_invalid():
    assert not is_valid_transition("COMPLETE", "RUNNING")
    assert not is_valid_transition("COMPLETE", "FAILED")


def test_pending_to_complete_invalid_skip():
    assert not is_valid_transition("PENDING", "COMPLETE")


def test_stale_resumes_to_running():
    assert is_valid_transition("STALE", "RUNNING")


def test_terminal_statuses():
    for s in ("COMPLETE", "FAILED", "BUDGET_STOP", "CANCELLED"):
        assert is_terminal(s)
    for s in ("PENDING", "RUNNING", "VERIFYING", "STALE"):
        assert not is_terminal(s)
