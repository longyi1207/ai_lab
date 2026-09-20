"""Production path: real worker subprocesses and a real detached daemon.

The other suites inject an in-process spawn hook; these exercise the code that actually
runs when a human types `sci serve`.
"""

from __future__ import annotations

import time

import pytest

from ai_scientist.daemon import Daemon, DaemonClient
from ai_scientist.ops.state import StateStore

pytestmark = pytest.mark.slow


def test_scheduler_spawns_real_worker_processes(project):
    daemon = Daemon(project.root, seed=8)  # default spawn = subprocess
    try:
        daemon.store.set_runtime("job_budget", 4)
        outcome = daemon.run_until_idle(timeout_s=120, tick_s=0.2)
        status = daemon.c_status()
    finally:
        daemon.stop()

    assert not outcome["timed_out"]
    assert status["jobs"].get("done", 0) >= 3
    assert status["jobs"].get("running", 0) == 0
    assert status["locks"] == {}
    assert status["search"]["cells_filled"] >= 1

    # a real subprocess wrote its own worker log and artifacts
    store = StateStore(project.db_path)
    try:
        done = store.list_jobs("done", limit=10)
        events = store.recent_events(100)
    finally:
        store.close()
    job_dir = project.job_dir(done[0].job_id)
    assert (job_dir / "logs" / "worker.log").exists()
    assert (job_dir / "result.json").exists()
    assert done[0].pid is None  # cleared on completion; the child is gone

    # the pid was real while the trial ran, and each start took distinct locks
    starts = [e["payload"] for e in events if e["kind"] == "job_started"]
    assert starts and all(s["pid"] for s in starts)
    assert all(s["locks"] for s in starts)


def test_detached_daemon_serves_control_plane(project):
    client = DaemonClient(project.root)
    info = client.ensure(timeout_s=30)
    try:
        assert info["pid"] and client.running
        client.call("set_job_budget", n=3)

        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            status = client.call("status")
            if status["jobs"].get("done", 0) >= 3 and not status["jobs"].get("running"):
                break
            time.sleep(0.5)

        status = client.call("status")
        assert status["jobs"].get("done", 0) >= 3
        assert status["daemon"]["pid"] == info["pid"]
        assert set(status["daemon"]["loops"]) >= {"sci-scheduler", "sci-health"}
        assert client.call("pause")["paused"] is True
    finally:
        assert client.stop() is True
    assert not client.running
