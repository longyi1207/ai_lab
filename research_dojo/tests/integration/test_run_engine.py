"""Full-pipeline integration tests, offline (mocked LLM). Covers acceptance
criteria: a full run completes with judgments + REPORT.md, resume after
partial completion produces no duplicate rows, graceful SIGINT stop leaves a
resumable run, and the circuit breaker hard-fails after repeated opens.
"""

from __future__ import annotations

import os
import signal
from pathlib import Path

from research_dojo.config import settings as settings_module

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_full_run_completes_with_judgments_and_report(dojo_env, mock_llm):
    from research_dojo.artifacts.store import run_dir
    from research_dojo.db.repositories import JudgmentRepo, RolloutRepo, RunRepo
    from research_dojo.db.session import new_session
    from research_dojo.engine.run_engine import run_experiment

    run_id = run_experiment(str(FIXTURES / "mini_spec.yaml"), run_id="mini_full")

    session = new_session()
    run = RunRepo.get(session, run_id)
    assert run.status == "COMPLETE"
    rollouts = RolloutRepo.list_by_run(session, run_id)
    assert len(rollouts) == 3
    assert all(r.status == "COMPLETE" for r in rollouts)
    judgments = JudgmentRepo.list_for_run(session, run_id)
    assert len(judgments) == 3
    session.close()

    report_path = run_dir(run_id) / "REPORT.md"
    assert report_path.exists()
    assert "Run Report" in report_path.read_text()


def test_resume_after_partial_completion_has_no_duplicates(dojo_env, mock_llm):
    from research_dojo.config.spec import load_spec
    from research_dojo.db.repositories import ExperimentRepo, RolloutRepo, RunRepo
    from research_dojo.db.session import new_session
    from research_dojo.engine.dataset import load_dataset
    from research_dojo.engine.run_engine import run_experiment

    run_id = "mini_resume"
    spec_path = FIXTURES / "mini_spec.yaml"
    spec = load_spec(spec_path)

    # simulate "crashed after 1 of 3 rollouts": pre-create the run + dataset
    # and mark exactly one rollout COMPLETE before the engine ever runs.
    session = new_session()
    ExperimentRepo.get_or_create(session, spec.experiment_id, spec.hypothesis)
    frozen = spec.freeze()
    frozen["_spec_path"] = str(spec_path.resolve())
    RunRepo.create(session, run_id, spec.experiment_id, frozen, frozen["spec_hash"])
    load_dataset(session, FIXTURES / "mini_dataset.jsonl")
    session.commit()
    pre_existing = RolloutRepo.get_or_create_pending(session, run_id, "s1", "baseline", 0)
    RolloutRepo.mark_running(session, pre_existing.id)
    RolloutRepo.complete(session, pre_existing.id, "paprika (pre-existing)", {"transcript": []}, 1.0, 1, 1, 0.0)
    session.commit()
    session.close()

    calls_before = len(mock_llm.client.chat.completions.calls)
    run_experiment(str(spec_path), run_id=run_id, resume=True)
    calls_after = len(mock_llm.client.chat.completions.calls)

    session = new_session()
    rollouts = RolloutRepo.list_by_run(session, run_id)
    assert len(rollouts) == 3  # no duplicate row for s1
    assert all(r.status == "COMPLETE" for r in rollouts)
    s1 = [r for r in rollouts if r.sample_id == "s1"][0]
    assert s1.completion == "paprika (pre-existing)"  # untouched, not re-run
    session.close()

    # only s2 + s3 should have triggered a harness call (2 non-judge chat
    # calls); judge calls also happen but the point is s1 wasn't re-run
    assert calls_after > calls_before


def test_graceful_sigint_stops_after_current_rollout_and_stays_resumable(dojo_env, mock_llm):
    from research_dojo.db.repositories import RolloutRepo, RunRepo
    from research_dojo.db.session import new_session
    from research_dojo.engine.run_engine import run_experiment

    call_count = {"n": 0}
    real_responder = mock_llm.responder

    def responder_with_signal(messages):
        call_count["n"] += 1
        if call_count["n"] == 1:
            os.kill(os.getpid(), signal.SIGINT)
        return real_responder(messages)

    mock_llm.responder = responder_with_signal

    run_id = run_experiment(str(FIXTURES / "mini_spec.yaml"), run_id="mini_sigint")

    session = new_session()
    run = RunRepo.get(session, run_id)
    assert run.status == "RUNNING"  # not COMPLETE — left resumable
    rollouts = RolloutRepo.list_by_run(session, run_id)
    assert len(rollouts) < 3  # stopped before finishing all work items
    session.close()


def test_circuit_breaker_hard_fails_after_repeated_opens(dojo_env, tmp_path, monkeypatch):
    monkeypatch.setenv("DOJO_CIRCUIT_BREAKER_THRESHOLD", "2")
    monkeypatch.setenv("DOJO_CIRCUIT_BREAKER_COOLDOWN_SECONDS", "1")
    settings_module.get_settings.cache_clear()

    dataset_path = tmp_path / "fail_dataset.jsonl"
    dataset_path.write_text("\n".join(
        f'{{"id": "s{i}", "prompt": "p{i}", "expected": null, "metadata": {{}}}}' for i in range(10)
    ) + "\n")
    spec_path = tmp_path / "fail_spec.yaml"
    spec_path.write_text(
        "experiment_id: fail_test\nhypothesis: h\n"
        "model:\n  deployment: mock\n"
        f"dataset: {dataset_path}\n"
        "arms: [baseline]\nrollouts_per_sample: 1\n"
        "harness:\n  kind: batch_chat\n"
        "verification:\n  deterministic: true\n"
        "budget:\n  max_usd: 100.0\n"
    )

    class AlwaysFailsHarness:
        def __init__(self, spec):
            pass

        def run(self, prompt, *, sample_id, arm):
            raise RuntimeError("simulated harness failure")

    import research_dojo.engine.run_engine as run_engine_mod
    monkeypatch.setattr(run_engine_mod, "build_harness", lambda spec: AlwaysFailsHarness(spec))

    from research_dojo.db.repositories import RunRepo
    from research_dojo.db.session import new_session
    from research_dojo.engine.run_engine import run_experiment

    run_id = run_experiment(str(spec_path), run_id="fail_run")

    session = new_session()
    run = RunRepo.get(session, run_id)
    assert run.status == "FAILED"
    assert "circuit breaker" in (run.error_summary or "")
    session.close()


def test_dlq_entry_added_after_max_attempts(dojo_env, monkeypatch):
    monkeypatch.setenv("DOJO_MAX_DLQ_ATTEMPTS", "2")
    settings_module.get_settings.cache_clear()

    from research_dojo.db.repositories import DLQRepo, ExperimentRepo, RolloutRepo, RunRepo, SampleRepo
    from research_dojo.db.session import new_session
    from research_dojo.engine.run_engine import RunEngine

    session = new_session()
    ExperimentRepo.get_or_create(session, "exp", "h")
    RunRepo.create(session, "r1", "exp", {"spec_hash": "x"}, "x")
    SampleRepo.upsert(session, "s1", "ds", "p")
    session.commit()
    rollout = RolloutRepo.get_or_create_pending(session, "r1", "s1", "baseline", 0)
    RolloutRepo.mark_running(session, rollout.id)
    RolloutRepo.mark_running(session, rollout.id)  # attempts=2 == DOJO_MAX_DLQ_ATTEMPTS
    session.commit()

    engine = RunEngine(session=session)
    engine.settings = settings_module.get_settings()
    engine._handle_rollout_failure("r1", rollout, "s1", "baseline", 0, RuntimeError("boom"))
    session.commit()

    entries = DLQRepo.list_for_run(session, "r1")
    assert len(entries) == 1
    session.close()
