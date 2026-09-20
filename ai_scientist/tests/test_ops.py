from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest

from ai_scientist.domain import load_domain
from ai_scientist.ops import (
    HealthMonitor,
    InsufficientResources,
    ResourceBroker,
    Scheduler,
    run_job,
)
from ai_scientist.ops.health import pid_alive
from ai_scientist.schema import Job, ResourcePool, ResourceRequest


def _seed_job(project, store, **plan_params) -> Job:
    candidate = load_domain("fake_toy").seed_candidates()[0]
    candidate.plan.params.update(plan_params)
    project.write_candidate(candidate)
    return store.enqueue(
        Job(candidate_id=candidate.candidate_id, resources=candidate.plan.resources)
    )


# --------------------------------------------------------------------- locks
def test_broker_allocates_distinct_names_and_reports_busy():
    broker = ResourceBroker(ResourcePool(gpus=[0, 1], api_slots=2))
    first = broker.plan_locks(ResourceRequest(gpu=1, api_slots=1), set())
    assert first == ["gpu:0", "api:0"]
    # a second job must get the *other* gpu and the *other* api slot
    assert broker.plan_locks(ResourceRequest(gpu=1), set(first)) == ["gpu:1", "api:1"]
    assert broker.plan_locks(ResourceRequest(gpu=2), {"gpu:0"}) is None
    assert broker.plan_locks(ResourceRequest(api_slots=1), {"api:0", "api:1"}) is None


def test_broker_rejects_unsatisfiable_requests():
    broker = ResourceBroker(ResourcePool(gpus=[], api_slots=1))
    with pytest.raises(InsufficientResources):
        broker.plan_locks(ResourceRequest(gpu=1), set())


# --------------------------------------------------------------------- state
def test_try_start_is_atomic_and_prevents_double_kickoff(project, store):
    job = _seed_job(project, store)
    assert store.try_start(job.job_id, ["api:0"], "w1") is True
    # same job again, and a different job contending for the same lock
    assert store.try_start(job.job_id, ["api:0"], "w2") is False
    other = _seed_job(project, store)
    assert store.try_start(other.job_id, ["api:0"], "w3") is False
    assert store.held_locks() == {"api:0": job.job_id}
    assert store.get_job(job.job_id).status == "running"
    assert store.get_job(other.job_id).status == "queued"


def test_failed_lock_attempt_leaves_no_partial_locks(project, store):
    job = _seed_job(project, store)
    store.try_start(job.job_id, ["api:0"], "w1")
    other = _seed_job(project, store)
    assert store.try_start(other.job_id, ["api:1", "api:0"], "w2") is False
    assert "api:1" not in store.held_locks()


def test_spend_and_runtime_kv(store):
    store.record_spend("j1", 0.5, 100)
    store.record_spend("j2", 0.25, 50)
    assert store.total_spend() == {"usd": 0.75, "tokens": 150.0}
    store.set_runtime("concurrency", 7)
    assert store.get_runtime("concurrency") == 7
    assert store.get_runtime("missing", "fallback") == "fallback"


# --------------------------------------------------------------------- scheduler
def test_scheduler_respects_concurrency_and_pause(project, store):
    for _ in range(4):
        _seed_job(project, store)
    spawned: list[str] = []
    scheduler = Scheduler(
        project, store, project.read_config(), spawn=lambda job, wid: spawned.append(job.job_id)
    )
    started = scheduler.tick().started
    assert len(started) == 2  # concurrency=2 in the fixture
    assert len(spawned) == 2
    assert len(scheduler.tick().started) == 0  # no free slots

    store.set_runtime("paused", True)
    store.mark_terminal(started[0], "done")
    store.release_locks(started[0])
    assert scheduler.tick().started == []


def test_scheduler_fails_unschedulable_jobs_instead_of_spinning(project, store):
    job = _seed_job(project, store)
    store.release_locks(job.job_id)
    gpu_job = Job(candidate_id=job.candidate_id, resources=ResourceRequest(gpu=2, api_slots=1))
    store.enqueue(gpu_job)
    scheduler = Scheduler(project, store, project.read_config(), spawn=lambda j, w: 1)
    result = scheduler.tick()
    assert gpu_job.job_id in result.rejected
    assert store.get_job(gpu_job.job_id).status == "failed"
    assert "unschedulable" in store.get_job(gpu_job.job_id).error


def test_spawn_failure_requeues_and_releases_locks(project, store):
    job = _seed_job(project, store)

    def boom(job, worker_id):
        raise RuntimeError("no fork today")

    Scheduler(project, store, project.read_config(), spawn=boom).tick()
    refreshed = store.get_job(job.job_id)
    assert refreshed.status == "queued"
    assert "spawn failed" in refreshed.error
    assert store.held_locks() == {}


# --------------------------------------------------------------------- worker
def test_worker_runs_grades_and_writes_artifacts(project, store):
    job = _seed_job(project, store)
    assert store.try_start(job.job_id, ["api:0"], "w1")
    assert run_job(project.root, job.job_id, worker_id="w1", store=store) == 0

    refreshed = store.get_job(job.job_id)
    assert refreshed.status == "done"
    job_dir = project.job_dir(job.job_id)
    payload = (job_dir / "result.json").read_text()
    assert '"metrics"' in payload
    assert (job_dir / "results_writeup.md").exists()
    assert (job_dir / "verification.json").exists()
    assert (job_dir / "artifacts" / "trial.json").exists()
    assert store.total_spend()["tokens"] > 0
    # verification could not run against a fake model: that is flagged, not assumed ok
    assert "verification_unavailable" in (job_dir / "result.json").read_text()


def test_worker_failure_marks_job_failed_with_error(project, store):
    job = _seed_job(project, store, fail=True)
    store.try_start(job.job_id, ["api:0"], "w1")
    assert run_job(project.root, job.job_id, store=store) == 1
    refreshed = store.get_job(job.job_id)
    assert refreshed.status == "failed"
    assert "deliberate failure" in refreshed.error
    assert '"error"' in (project.job_dir(job.job_id) / "result.json").read_text()


def test_worker_heartbeats_while_running(project, store):
    job = _seed_job(project, store, sleep_s=0.5)
    store.try_start(job.job_id, ["api:0"], "w1")
    before = store.get_job(job.job_id).heartbeat_at
    run_job(project.root, job.job_id, store=store)
    after = store.get_job(job.job_id).heartbeat_at
    assert after >= before


# --------------------------------------------------------------------- health
def test_health_requeues_stale_worker_then_fails_after_max_attempts(project, store):
    job = _seed_job(project, store)
    config = project.read_config()
    monitor = HealthMonitor(store, config)

    store.try_start(job.job_id, ["api:0"], "w1")
    # simulate a wedged worker: heartbeat far in the past, pid we know is alive (this process)
    store.set_pid(job.job_id, None)
    stale = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
    store._conn.execute(  # noqa: SLF001 - deliberately forcing a stale row
        "UPDATE jobs SET heartbeat_at=? WHERE job_id=?", (stale, job.job_id)
    )
    store._conn.commit()  # noqa: SLF001

    report = monitor.tick()
    assert job.job_id in report.stale
    assert job.job_id in report.requeued
    assert store.get_job(job.job_id).status == "queued"
    assert store.held_locks() == {}

    # second strike hits max_attempts (2) and fails the job for good
    store.try_start(job.job_id, ["api:0"], "w2")
    store._conn.execute(  # noqa: SLF001
        "UPDATE jobs SET heartbeat_at=? WHERE job_id=?", (stale, job.job_id)
    )
    store._conn.commit()  # noqa: SLF001
    report = monitor.tick()
    assert job.job_id in report.failed
    assert store.get_job(job.job_id).status == "failed"


def test_health_detects_dead_pid_immediately(project, store):
    job = _seed_job(project, store)
    store.try_start(job.job_id, ["api:0"], "w1")
    store.set_pid(job.job_id, 2**30)  # certainly not a live pid
    report = HealthMonitor(store, project.read_config()).tick()
    assert job.job_id in report.crashed
    assert store.get_job(job.job_id).status == "queued"


def test_health_enforces_job_timeout(project, store):
    job = _seed_job(project, store)
    config = project.read_config()
    config.ops.job_timeout_s = 0.01
    store.try_start(job.job_id, ["api:0"], "w1")
    time.sleep(0.05)
    report = HealthMonitor(store, config).tick()
    assert job.job_id in report.timed_out


def test_reconcile_on_start_recovers_orphans(project, store):
    job = _seed_job(project, store)
    store.try_start(job.job_id, ["api:0"], "w1")
    store.set_pid(job.job_id, 2**30)
    report = HealthMonitor(store, project.read_config()).reconcile_on_start()
    assert job.job_id in report.crashed
    assert store.get_job(job.job_id).status == "queued"
    assert store.held_locks() == {}


def test_pid_alive_on_self():
    import os

    assert pid_alive(os.getpid()) is True
    assert pid_alive(None) is False
