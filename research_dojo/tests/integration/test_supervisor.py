"""Supervisor: stale RUNNING run -> marked STALE + alert fired (mock file
notifier, no real network)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_check_once_marks_stale_and_alerts(dojo_env):
    from research_dojo.db.models import Run, RunStatus
    from research_dojo.db.repositories import AlertRepo, ExperimentRepo
    from research_dojo.db.session import new_session
    from research_dojo.supervisor.daemon import check_once

    session = new_session()
    ExperimentRepo.get_or_create(session, "exp", "h")
    run = Run(
        run_id="stale1", experiment_id="exp", status=RunStatus.RUNNING.value,
        spec_frozen_json={"supervisor": {"stale_after_seconds": 1}},
        spec_hash="x",
        heartbeat_at=datetime.now(UTC) - timedelta(seconds=30),
    )
    session.add(run)
    session.commit()
    session.close()

    summary = check_once(auto_resume=False)
    assert "stale1" in summary["stale_marked"]

    session = new_session()
    from research_dojo.db.repositories import RunRepo

    updated = RunRepo.get(session, "stale1")
    assert updated.status == RunStatus.STALE.value

    events = AlertRepo.list(session, run_id="stale1")
    assert any(e.rule == "run_stale" for e in events)
    session.close()


def test_check_once_ignores_fresh_heartbeat(dojo_env):
    from research_dojo.db.models import Run, RunStatus
    from research_dojo.db.repositories import ExperimentRepo
    from research_dojo.db.session import new_session
    from research_dojo.supervisor.daemon import check_once

    session = new_session()
    ExperimentRepo.get_or_create(session, "exp", "h")
    run = Run(
        run_id="fresh1", experiment_id="exp", status=RunStatus.RUNNING.value,
        spec_frozen_json={"supervisor": {"stale_after_seconds": 600}},
        spec_hash="x", heartbeat_at=datetime.now(UTC),
    )
    session.add(run)
    session.commit()
    session.close()

    summary = check_once(auto_resume=False)
    assert "fresh1" not in summary["stale_marked"]
