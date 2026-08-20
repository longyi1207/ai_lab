from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from research_dojo.supervisor import daemon


def test_pidfile_lifecycle(dojo_env):
    assert daemon.running_pid() is None
    daemon.write_pidfile()
    assert daemon.running_pid() == os.getpid()
    daemon.remove_pidfile()
    assert daemon.running_pid() is None
    daemon.remove_pidfile()  # idempotent, no error if already gone


def test_running_pid_handles_garbage_file(dojo_env):
    daemon.pidfile_path().write_text("not-a-pid")
    assert daemon.running_pid() is None


def test_running_pid_handles_dead_pid(dojo_env):
    # PID 1 exists on this machine but we're unlikely to own it; use a PID
    # that is very unlikely to exist instead, to exercise the OSError path.
    daemon.pidfile_path().write_text("999999")
    assert daemon.running_pid() is None


def test_seconds_since_none_is_zero():
    assert daemon._seconds_since(None) == 0.0


def test_launch_resume_success(monkeypatch):
    monkeypatch.setattr(daemon.subprocess, "Popen", MagicMock())
    assert daemon._launch_resume("r1", "/tmp/spec.yaml") is True


def test_launch_resume_failure(monkeypatch):
    def boom(*a, **k):
        raise OSError("no such file")

    monkeypatch.setattr(daemon.subprocess, "Popen", boom)
    assert daemon._launch_resume("r1", "/tmp/spec.yaml") is False


def test_loop_once_writes_and_removes_pidfile(dojo_env):
    daemon.loop(poll_interval=1, once=True, auto_resume=False)
    assert daemon.running_pid() is None  # pidfile removed after one tick


def test_check_once_reenqueues_due_dlq_entries(dojo_env, monkeypatch, tmp_path):
    from research_dojo.db.repositories import DLQRepo, ExperimentRepo, RunRepo
    from research_dojo.db.session import new_session

    spec_path = tmp_path / "spec.yaml"
    spec_path.write_text("experiment_id: x\n")

    session = new_session()
    ExperimentRepo.get_or_create(session, "exp", "h")
    RunRepo.create(session, "r1", "exp", {"_spec_path": str(spec_path)}, "x")
    RunRepo.mark_started(session, "r1")
    session.commit()
    DLQRepo.add(session, "r1", "s1", "baseline", 0, "boom", attempts=1, retry_delay_seconds=0)
    session.commit()
    session.close()

    monkeypatch.setattr(daemon, "_launch_resume", MagicMock(return_value=True))
    summary = daemon.check_once(auto_resume=True)
    assert len(summary["dlq_retried"]) == 1
    daemon._launch_resume.assert_called_once()


def test_check_once_stale_without_spec_path_stays_stale(dojo_env):
    from research_dojo.db.models import Run, RunStatus
    from research_dojo.db.repositories import ExperimentRepo, RunRepo
    from research_dojo.db.session import new_session

    session = new_session()
    ExperimentRepo.get_or_create(session, "exp", "h")
    run = Run(
        run_id="r_nospec", experiment_id="exp", status=RunStatus.RUNNING.value,
        spec_frozen_json={}, spec_hash="x",
        heartbeat_at=datetime.now(UTC) - timedelta(seconds=9999),
    )
    session.add(run)
    session.commit()
    session.close()

    summary = daemon.check_once(auto_resume=True)
    assert "r_nospec" in summary["stale_marked"]
    assert "r_nospec" not in summary["resumed"]

    session = new_session()
    assert RunRepo.get(session, "r_nospec").status == RunStatus.STALE.value
    session.close()
