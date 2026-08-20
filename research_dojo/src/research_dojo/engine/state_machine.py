"""Run state machine (pillar 3.1):

    PENDING -> RUNNING -> VERIFYING -> COMPLETE | FAILED | BUDGET_STOP | CANCELLED
    RUNNING can also short-circuit to FAILED / BUDGET_STOP / CANCELLED / STALE
    STALE (supervisor-assigned on a dead heartbeat) resumes back to RUNNING
"""

from __future__ import annotations

from research_dojo.db.models import RunStatus

_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.PENDING: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.RUNNING: {
        RunStatus.VERIFYING, RunStatus.FAILED, RunStatus.BUDGET_STOP,
        RunStatus.CANCELLED, RunStatus.STALE,
    },
    RunStatus.VERIFYING: {RunStatus.COMPLETE, RunStatus.FAILED, RunStatus.BUDGET_STOP, RunStatus.CANCELLED},
    RunStatus.STALE: {RunStatus.RUNNING, RunStatus.FAILED, RunStatus.CANCELLED},
    RunStatus.COMPLETE: set(),
    RunStatus.FAILED: set(),
    RunStatus.BUDGET_STOP: set(),
    RunStatus.CANCELLED: set(),
}


def is_valid_transition(current: str, target: str) -> bool:
    try:
        cur, tgt = RunStatus(current), RunStatus(target)
    except ValueError:
        return False
    return tgt in _TRANSITIONS.get(cur, set())


def is_terminal(status: str) -> bool:
    try:
        return not _TRANSITIONS.get(RunStatus(status), set())
    except ValueError:
        return False
