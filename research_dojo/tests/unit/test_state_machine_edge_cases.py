from __future__ import annotations

from research_dojo.engine.state_machine import is_terminal, is_valid_transition


def test_invalid_status_strings_are_not_valid_transitions():
    assert not is_valid_transition("NOT_A_STATUS", "RUNNING")
    assert not is_valid_transition("PENDING", "NOT_A_STATUS")


def test_invalid_status_string_is_not_terminal():
    assert not is_terminal("NOT_A_STATUS")


def test_running_can_go_directly_to_failed_or_cancelled():
    assert is_valid_transition("RUNNING", "FAILED")
    assert is_valid_transition("RUNNING", "BUDGET_STOP")
    assert is_valid_transition("RUNNING", "CANCELLED")
    assert is_valid_transition("RUNNING", "STALE")
