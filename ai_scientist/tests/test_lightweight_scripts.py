"""Lightweight (portable) mode: the scripts a host agent drives without a daemon."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ai_scientist.ops.scheduler import worker_env

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

pytestmark = pytest.mark.slow


def _run(script: str, *args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True,
        text=True,
        env=worker_env(),
        timeout=180,
        check=False,
    )
    assert proc.returncode == 0, f"{script} failed:\n{proc.stdout}\n{proc.stderr}"
    return json.loads(proc.stdout)


def test_host_driven_loop_accumulates_an_archive(project):
    root = str(project.root)

    first = _run("propose_next.py", "--project", root, "--bootstrap")
    assert first["bootstrapped"], "bootstrap should seed the population"
    assert first["archive"]["cells_filled"] == 0

    trial = _run("run_one_experiment.py", "--project", root)
    assert trial["exit_code"] == 0
    assert trial["source"] == "queue", "it must drain proposed work, not invent new work"
    assert trial["metrics"]["fitness"] is not None
    assert trial["ingested"], "the script should fold its own result into the archive"
    assert trial["inserted_elites"]

    second = _run("propose_next.py", "--project", root)
    assert second["archive"]["cells_filled"] >= 1
    assert second["enqueued"], "with an archive in place, search should propose more work"

    health = _run("check_workers.py", "--project", root)
    assert health["locks_held"] == {}
    assert health["jobs"].get("done", 0) >= 1


def test_run_one_experiment_accepts_param_overrides(project):
    root = str(project.root)
    _run("propose_next.py", "--project", root, "--bootstrap")
    trial = _run(
        "run_one_experiment.py", "--project", root, "--params", '{"alpha": 0.75, "rounds": 4}'
    )
    assert trial["exit_code"] == 0
    snapshot = json.loads((project.job_dir(trial["job_id"]) / "spec_snapshot.json").read_text())
    assert snapshot["plan"]["params"]["alpha"] == 0.75
    assert snapshot["plan"]["params"]["rounds"] == 4


def test_check_workers_recovers_an_orphan(project):
    from ai_scientist.ops.state import StateStore
    from ai_scientist.schema import Job

    root = str(project.root)
    _run("propose_next.py", "--project", root, "--bootstrap")

    store = StateStore(project.db_path)
    try:
        job = store.list_jobs("queued", limit=1)[0]
        store.try_start(job.job_id, ["api:0"], "ghost")
        store.set_pid(job.job_id, 2**30)
        assert isinstance(job, Job)
    finally:
        store.close()

    report = _run("check_workers.py", "--project", root, "--reconcile")
    assert report["crashed"], "a dead pid must be detected"
    assert report["locks_held"] == {}


def test_scripts_reject_an_uninitialized_project(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / "propose_next.py"), "--project", str(tmp_path / "nope")],
        capture_output=True,
        text=True,
        env=worker_env(),
        check=False,
    )
    assert proc.returncode == 2
    assert "not an ai_scientist project" in proc.stderr
