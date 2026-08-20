from __future__ import annotations

from research_dojo.db.models import RolloutStatus, RunStatus
from research_dojo.db.repositories import (
    DLQRepo,
    ExperimentRepo,
    MetricRepo,
    RolloutRepo,
    RunRepo,
    SampleRepo,
)


def _make_run(session, run_id="run1", experiment_id="exp1"):
    ExperimentRepo.get_or_create(session, experiment_id, "hyp")
    return RunRepo.create(session, run_id, experiment_id, {"spec_hash": "abc"}, "abc")


def test_run_lifecycle(dojo_env):
    from research_dojo.db.session import new_session

    session = new_session()
    run = _make_run(session)
    assert run.status == RunStatus.PENDING.value

    RunRepo.mark_started(session, run.run_id)
    session.commit()
    fetched = RunRepo.get(session, run.run_id)
    assert fetched.status == RunStatus.RUNNING.value
    assert fetched.started_at is not None

    RunRepo.mark_finished(session, run.run_id, RunStatus.COMPLETE)
    session.commit()
    assert RunRepo.get(session, run.run_id).status == RunStatus.COMPLETE.value
    session.close()


def test_rollout_idempotent_upsert(dojo_env):
    from research_dojo.db.session import new_session

    session = new_session()
    _make_run(session)
    SampleRepo.upsert(session, "s1", "ds", "prompt text")
    session.commit()

    r1 = RolloutRepo.get_or_create_pending(session, "run1", "s1", "baseline", 0)
    r2 = RolloutRepo.get_or_create_pending(session, "run1", "s1", "baseline", 0)
    assert r1.id == r2.id  # same identity -> same row, no duplicate

    RolloutRepo.mark_running(session, r1.id)
    session.commit()
    RolloutRepo.complete(session, r1.id, "the answer", {"transcript": []}, 10.0, 5, 5, 0.001)
    session.commit()

    completed = RolloutRepo.completed_keys(session, "run1")
    assert ("s1", "baseline", 0) in completed

    # calling get_or_create_pending again after completion still returns the
    # same completed row, not a new PENDING one
    r3 = RolloutRepo.get_or_create_pending(session, "run1", "s1", "baseline", 0)
    assert r3.id == r1.id
    assert r3.status == RolloutStatus.COMPLETE.value
    session.close()


def test_rollout_unique_constraint_across_arms_and_idx(dojo_env):
    from research_dojo.db.session import new_session

    session = new_session()
    _make_run(session)
    SampleRepo.upsert(session, "s1", "ds", "prompt")
    session.commit()

    a = RolloutRepo.get_or_create_pending(session, "run1", "s1", "baseline", 0)
    b = RolloutRepo.get_or_create_pending(session, "run1", "s1", "treatment", 0)
    c = RolloutRepo.get_or_create_pending(session, "run1", "s1", "baseline", 1)
    assert len({a.id, b.id, c.id}) == 3
    session.close()


def test_metric_aggregate(dojo_env):
    from research_dojo.db.session import new_session

    session = new_session()
    _make_run(session)
    MetricRepo.record(session, "run1", "cost_usd_est_total", 0.01)
    MetricRepo.record(session, "run1", "cost_usd_est_total", 0.02)
    session.commit()
    agg = MetricRepo.aggregate(session, "run1")
    assert agg["cost_usd_est_total"]["count"] == 2
    assert round(agg["cost_usd_est_total"]["sum"], 4) == 0.03
    session.close()


def test_dlq_due_for_retry(dojo_env):
    from research_dojo.db.session import new_session

    session = new_session()
    _make_run(session)
    entry = DLQRepo.add(session, "run1", "s1", "baseline", 0, "boom", attempts=1, retry_delay_seconds=0)
    session.commit()

    due = DLQRepo.due_for_retry(session, max_attempts=5)
    assert any(e.id == entry.id for e in due)

    DLQRepo.resolve(session, entry.id)
    session.commit()
    due_after = DLQRepo.due_for_retry(session, max_attempts=5)
    assert not any(e.id == entry.id for e in due_after)
    session.close()


def test_circuit_breaker_open_and_close(dojo_env):
    from research_dojo.db.session import new_session

    session = new_session()
    _make_run(session)
    assert RunRepo.circuit_is_open(session, "run1") is False
    RunRepo.open_circuit(session, "run1", cooldown_seconds=60)
    session.commit()
    assert RunRepo.circuit_is_open(session, "run1") is True
    RunRepo.close_circuit(session, "run1")
    session.commit()
    assert RunRepo.circuit_is_open(session, "run1") is False
    session.close()
