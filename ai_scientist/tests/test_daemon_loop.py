"""End-to-end loop, resume behavior, and control plane — all offline."""

from __future__ import annotations

import json

import pytest

from ai_scientist.daemon import ControlError, Daemon, DaemonClient, DaemonUnavailable
from ai_scientist.ops import run_job
from ai_scientist.ops.state import StateStore
from ai_scientist.report import build_report


def inprocess_daemon(project, **kwargs) -> Daemon:
    """Daemon whose 'workers' run synchronously in this process (no subprocess spawn)."""
    daemon = Daemon.__new__(Daemon)  # configured below to inject the spawn hook

    def spawn(job, worker_id):
        run_job(project.root, job.job_id, worker_id=worker_id, store=daemon.store)
        return None

    Daemon.__init__(daemon, project.root, spawn=spawn, **kwargs)
    return daemon


def test_full_loop_fills_archive_and_reports(project):
    daemon = inprocess_daemon(project, seed=3)
    try:
        daemon.store.set_runtime("job_budget", 9)
        outcome = daemon.run_until_idle(timeout_s=90)
        status = daemon.c_status()
    finally:
        daemon.stop()

    assert not outcome["timed_out"]
    assert status["jobs"].get("done", 0) >= 3
    assert status["search"]["cells_filled"] >= 1
    assert status["search"]["best"]["fitness"] > 0
    assert status["spend"]["usd"] > 0

    # every done job produced an ingestable payload and a writeup
    store = StateStore(project.db_path)
    try:
        done = store.list_jobs("done", limit=50)
        assert done and all(job.ingested for job in done)
    finally:
        store.close()
    for job in done:
        assert (project.job_dir(job.job_id) / "results_writeup.md").exists()

    report_path = build_report(project.root, narrative=False)
    text = report_path.read_text()
    assert "Archive coverage" in text and "Top elites" in text
    assert "Scope caveat" in text


def test_generation_beyond_seeds_is_reached(project):
    daemon = inprocess_daemon(project, seed=11)
    try:
        daemon.store.set_runtime("job_budget", 10)
        daemon.run_until_idle(timeout_s=90)
        summary = daemon.orchestrator.engine.summary()
    finally:
        daemon.stop()
    assert summary["generation"] >= 1  # mutated children, not only seeds
    assert summary["novelty_size"] >= 1


def test_budget_stop_pauses_scheduling(project):
    metadata = project.read_metadata()
    metadata.budget.max_usd = 0.0001  # smaller than one toy trial
    project.write_metadata(metadata)

    daemon = inprocess_daemon(project, seed=1)
    try:
        daemon.store.set_runtime("job_budget", 20)
        daemon.run_until_idle(timeout_s=60)
        status = daemon.c_status()
        events = [e["kind"] for e in daemon.store.recent_events(200)]
    finally:
        daemon.stop()
    assert "budget_exceeded" in events
    assert status["paused"] is True


def test_resume_after_crash_keeps_archive_consistent(project):
    first = inprocess_daemon(project, seed=2)
    try:
        first.store.set_runtime("job_budget", 5)
        first.run_until_idle(timeout_s=60)
        cells_before = len(first.orchestrator.engine.archive.cells)
        map_before = json.loads(project.map_path.read_text())
    finally:
        first.stop()

    # simulate a hard kill: a running job left behind with a dead pid
    store = StateStore(project.db_path)
    try:
        candidate_id = store.list_jobs("done", limit=1)[0].candidate_id
        from ai_scientist.schema import Job

        orphan = store.enqueue(Job(candidate_id=candidate_id))
        store.try_start(orphan.job_id, ["api:0"], "ghost")
        store.set_pid(orphan.job_id, 2**30)
    finally:
        store.close()

    second = inprocess_daemon(project, seed=2)
    try:
        second.store.set_runtime("job_budget", 8)
        second.run_until_idle(timeout_s=60)
        status = second.c_status()
    finally:
        second.stop()

    assert status["locks"] == {}
    assert len(second.orchestrator.engine.archive.cells) >= cells_before
    assert json.loads(project.map_path.read_text())["axes"] == map_before["axes"]
    assert status["jobs"].get("running", 0) == 0


def test_control_plane_over_http(project):
    daemon = inprocess_daemon(project, seed=4)
    client = DaemonClient(project.root)
    try:
        info = daemon.start()
        assert info["port"] and client.running

        status = client.call("status")
        assert status["domain"] == "fake_toy"

        assert client.call("pause")["paused"] is True
        assert client.call("resume")["paused"] is False
        assert client.call("set_concurrency", n=3)["concurrency"] == 3

        # drive a step through the control plane, then inspect elites
        for _ in range(6):
            client.call("step")
        elites = client.call("elites", n=3)
        assert isinstance(elites, list)

        with pytest.raises(DaemonUnavailable, match="no such elite"):
            client.call("pin", elite_id="elite_nope")
    finally:
        daemon.stop()
    assert not client.running
    assert not project.daemon_info_path.exists()


def test_control_rejects_unknown_method_and_bad_args(project):
    daemon = inprocess_daemon(project)
    try:
        with pytest.raises(ControlError):
            daemon.call("definitely_not_a_method")
        with pytest.raises(ControlError):
            daemon.call("set_concurrency", {"n": -1})
    finally:
        daemon.stop()


def test_pin_and_ban_via_control(project):
    daemon = inprocess_daemon(project, seed=6)
    try:
        daemon.store.set_runtime("job_budget", 4)
        daemon.run_until_idle(timeout_s=60)
        elites = daemon.c_elites(n=1)
        assert elites, "expected at least one elite"
        elite_id = elites[0]["elite_id"]

        assert daemon.c_pin(elite_id)["pinned"] is True
        assert daemon.orchestrator.engine.archive.cells and any(
            r.pinned for r in daemon.orchestrator.engine.archive.cells.values()
        )
        assert daemon.c_ban(elite_id)["removed"] is True
        assert all(
            r.elite_id != elite_id for r in daemon.orchestrator.engine.archive.cells.values()
        )
    finally:
        daemon.stop()
