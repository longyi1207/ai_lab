"""Run engine: orchestrates one experiment run end to end.

State machine: PENDING -> RUNNING -> VERIFYING -> COMPLETE | FAILED |
BUDGET_STOP | CANCELLED (engine/state_machine.py).

Crash safety: every rollout write commits before moving to the next work
item, so a hard kill loses at most one in-flight rollout — `dojo resume`
picks up exactly where it left off via RolloutRepo.get_or_create_pending's
unique-constraint idempotency (no duplicate rows).

Graceful stop: SIGINT/SIGTERM set a flag instead of raising; the loop
finishes the rollout in flight, commits, then exits without marking any
terminal status — the run stays RESUMABLE (`dojo resume <run_id>`).
"""

from __future__ import annotations

import json
import logging
import platform
import signal
import subprocess
import time
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from research_dojo import __version__ as PACKAGE_VERSION
from research_dojo.alerts import dispatcher, rules
from research_dojo.analysis.report import generate_report
from research_dojo.artifacts.store import append_audit_jsonl, write_artifact
from research_dojo.config.settings import get_settings
from research_dojo.config.spec import ExperimentSpec, load_spec
from research_dojo.db.models import ArtifactKind, RolloutStatus, RunStatus
from research_dojo.db.repositories import (
    DLQRepo,
    ExperimentRepo,
    JudgmentRepo,
    MetricRepo,
    RolloutRepo,
    RunRepo,
    SampleRepo,
)
from research_dojo.db.session import new_session
from research_dojo.engine.dataset import load_dataset
from research_dojo.harness.registry import build_harness
from research_dojo.metrics import collector as metrics
from research_dojo.verify.pipeline import Verifier

logger = logging.getLogger("research_dojo.engine")

MAX_CIRCUIT_OPENS = 3
SANITY_WINDOW = 20


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, check=False,
        )
        return out.stdout.strip() or None
    except Exception:  # noqa: BLE001 — git metadata is best-effort
        return None


class _GracefulStop:
    """Installs SIGINT/SIGTERM handlers that set a flag instead of raising,
    so the engine loop can finish its current rollout before exiting."""

    def __init__(self):
        self.requested = False
        self._orig: dict[int, object] = {}

    def _handle(self, signum, frame):  # noqa: ARG002
        logger.warning("received signal %s — will stop after the current rollout", signum)
        self.requested = True

    def __enter__(self) -> _GracefulStop:
        try:
            self._orig[signal.SIGINT] = signal.signal(signal.SIGINT, self._handle)
            self._orig[signal.SIGTERM] = signal.signal(signal.SIGTERM, self._handle)
        except ValueError:
            pass  # not main thread — signals unavailable, e.g. inside tests/threads
        return self

    def __exit__(self, *exc) -> None:
        for sig, handler in self._orig.items():
            signal.signal(sig, handler)


def _default_run_id(spec: ExperimentSpec) -> str:
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{spec.experiment_id}_{ts}"


class RunEngine:
    def __init__(self, session: Session | None = None):
        self._owns_session = session is None
        self.session: Session = session or new_session()
        self.settings = get_settings()

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def run(self, spec_path: str | Path, run_id: str | None = None, resume: bool = False) -> str:
        session = self.session
        spec = load_spec(spec_path)
        frozen = spec.freeze()
        # not a spec field — stashed so the supervisor can auto-resume this
        # run without the caller having to remember which file it came from
        frozen["_spec_path"] = str(Path(spec_path).resolve())

        ExperimentRepo.get_or_create(session, spec.experiment_id, spec.hypothesis)

        run = None
        if resume:
            if run_id:
                run = RunRepo.get(session, run_id)
            else:
                candidates = [
                    r for r in RunRepo.list(session, spec.experiment_id)
                    if r.status in (RunStatus.RUNNING.value, RunStatus.STALE.value, RunStatus.PENDING.value)
                ]
                run = candidates[0] if candidates else None

        if run is None:
            run_id = run_id or _default_run_id(spec)
            run = RunRepo.create(
                session, run_id=run_id, experiment_id=spec.experiment_id,
                spec_frozen_json=frozen, spec_hash=frozen["spec_hash"],
                git_commit=_git_commit(), python_version=platform.python_version(),
                package_version=PACKAGE_VERSION,
            )
            RunRepo.set_arms(session, run.run_id, {arm: {} for arm in spec.arms})
            session.commit()
        run_id = run.run_id

        write_artifact(
            session, run_id, "spec_frozen.json",
            json.dumps(frozen, indent=2).encode("utf-8"), ArtifactKind.SPEC,
        )
        session.commit()

        # dataset/rubric paths in the spec are relative to the CWD `dojo` was
        # invoked from (project root), matching specs/tom_smoke.yaml's
        # `dataset: data/...` and the README quickstart's `cd research_dojo`
        sample_ids = load_dataset(session, spec.dataset)
        if spec.budget.max_samples is not None:
            sample_ids = sample_ids[: spec.budget.max_samples]
        session.commit()

        work_items: list[tuple[str, str, int]] = [
            (sample_id, arm, idx)
            for arm in spec.arms
            for sample_id in sample_ids
            for idx in range(spec.rollouts_per_sample)
        ]
        done = RolloutRepo.completed_keys(session, run_id)
        work_items = [item for item in work_items if item not in done]
        logger.info(
            "run %s: %d work items pending (%d already complete)", run_id, len(work_items), len(done)
        )

        harness = build_harness(spec)
        verifier = Verifier(spec)

        RunRepo.mark_started(session, run_id)
        session.commit()

        circuit_open_events = 0
        recent_flags: deque[bool] = deque(maxlen=SANITY_WINDOW)
        last_heartbeat = time.monotonic()
        stopped_gracefully = False

        with _GracefulStop() as stopper:
            for sample_id, arm, rollout_idx in work_items:
                session.expire_all()
                current = RunRepo.get(session, run_id)
                if current is not None and current.status == RunStatus.CANCELLED.value:
                    logger.info("run %s cancelled externally — stopping", run_id)
                    return run_id
                if stopper.requested:
                    stopped_gracefully = True
                    break

                self._wait_for_circuit(run_id)

                sample = SampleRepo.get(session, sample_id)
                rollout = RolloutRepo.get_or_create_pending(session, run_id, sample_id, arm, rollout_idx)
                if rollout.status == RolloutStatus.COMPLETE.value:
                    continue

                RolloutRepo.mark_running(session, rollout.id)
                session.commit()

                try:
                    result = harness.run(sample.prompt, sample_id=sample_id, arm=arm)
                except Exception as e:  # noqa: BLE001 — any harness failure fails this rollout, not the run
                    self._handle_rollout_failure(run_id, rollout, sample_id, arm, rollout_idx, e)
                    circuit_open_events_delta, hard_fail = self._maybe_open_circuit(run_id, circuit_open_events)
                    circuit_open_events = circuit_open_events_delta
                    if hard_fail:
                        return run_id
                    continue

                RolloutRepo.complete(
                    session, rollout.id, result.completion,
                    {"transcript": result.transcript}, result.latency_ms,
                    result.tokens_in, result.tokens_out, result.cost_usd_est,
                )
                metrics.record_rollout_success(
                    session, run_id, arm, result.latency_ms, result.tokens_in, result.tokens_out, result.cost_usd_est
                )
                RunRepo.reset_consecutive_failures(session, run_id)
                RunRepo.close_circuit(session, run_id)
                append_audit_jsonl(run_id, "rollouts.jsonl", {
                    "sample_id": sample_id, "arm": arm, "rollout_idx": rollout_idx,
                    "completion": result.completion, "latency_ms": result.latency_ms,
                    "cost_usd_est": result.cost_usd_est,
                })
                session.commit()

                self._verify_and_record(verifier, sample, result, rollout.id, run_id, recent_flags)
                session.commit()

                if self._budget_check(spec, run_id):
                    return run_id

                if time.monotonic() - last_heartbeat > self.settings.heartbeat_interval_seconds:
                    RunRepo.heartbeat(session, run_id)
                    session.commit()
                    last_heartbeat = time.monotonic()

        if stopped_gracefully:
            logger.info("run %s: graceful stop requested; leaving RUNNING for `dojo resume`", run_id)
            return run_id

        self._finalize(spec, run_id)
        return run_id

    def _wait_for_circuit(self, run_id: str) -> None:
        session = self.session
        waited = False
        while RunRepo.circuit_is_open(session, run_id):
            if not waited:
                logger.warning("run %s: circuit breaker open, pausing", run_id)
                waited = True
            time.sleep(1)
            session.expire_all()

    def _handle_rollout_failure(
        self, run_id: str, rollout, sample_id: str, arm: str, rollout_idx: int, exc: Exception,
    ) -> None:
        session = self.session
        error_text = f"{type(exc).__name__}: {exc}"
        RolloutRepo.fail(session, rollout.id, error_text)
        metrics.record_rollout_failure(session, run_id, arm)
        session.commit()
        session.refresh(rollout)
        if rollout.attempts >= self.settings.max_dlq_attempts:
            DLQRepo.add(session, run_id, sample_id, arm, rollout_idx, error_text, rollout.attempts)
            session.commit()
        logger.warning("run %s: rollout failed sample=%s arm=%s: %s", run_id, sample_id, arm, error_text)

    def _maybe_open_circuit(self, run_id: str, circuit_open_events: int) -> tuple[int, bool]:
        session = self.session
        n_fail = RunRepo.increment_consecutive_failures(session, run_id)
        session.commit()
        if n_fail < self.settings.circuit_breaker_threshold:
            return circuit_open_events, False

        RunRepo.open_circuit(session, run_id, self.settings.circuit_breaker_cooldown_seconds)
        circuit_open_events += 1
        trigger = rules.consecutive_failures(run_id, n_fail, k=self.settings.circuit_breaker_threshold)
        if trigger:
            dispatcher.dispatch(session, trigger, run_id)
        session.commit()

        if circuit_open_events > MAX_CIRCUIT_OPENS:
            RunRepo.mark_finished(
                session, run_id, RunStatus.FAILED,
                f"circuit breaker opened {circuit_open_events} times — giving up",
            )
            trigger = rules.run_failed(run_id, "circuit breaker opened too many times")
            dispatcher.dispatch(session, trigger, run_id)
            session.commit()
            return circuit_open_events, True
        return circuit_open_events, False

    def _verify_and_record(self, verifier: Verifier, sample, result, rollout_id: int, run_id: str,
                            recent_flags: deque) -> None:
        session = self.session
        ver = verifier.verify(sample.prompt, result.completion, sample.expected)
        JudgmentRepo.create(
            session, rollout_id, ver.judge_version or "", ver.judge_score, ver.judge_label,
            ver.judge_rationale,
            {"deterministic_passed": ver.deterministic_passed, "deterministic_reason": ver.deterministic_reason,
             "flags": ver.flags},
            ver.judge_raw_response,
        )
        if ver.judge_score is not None:
            metrics.record_judge_score(session, run_id, ver.judge_score)
        for flag in ver.flags:
            metrics.record_verification_flag(session, run_id, flag["kind"])
        append_audit_jsonl(run_id, "judgments.jsonl", {
            "rollout_id": rollout_id, "deterministic_passed": ver.deterministic_passed,
            "judge_score": ver.judge_score, "flags": ver.flags,
        })

        recent_flags.append(bool(ver.flags))
        trigger = rules.sanity_spike(run_id, sum(recent_flags), len(recent_flags))
        if trigger:
            dispatcher.dispatch(session, trigger, run_id)

    def _budget_check(self, spec: ExperimentSpec, run_id: str) -> bool:
        """Returns True if the run was stopped due to budget_exceeded."""
        session = self.session
        agg = MetricRepo.aggregate(session, run_id)
        total_cost = agg.get("cost_usd_est_total", {}).get("sum", 0.0)
        trigger = rules.budget_threshold(run_id, total_cost, spec.budget.max_usd)
        if trigger is None:
            return False
        dispatcher.dispatch(session, trigger, run_id)
        if trigger.rule == "budget_exceeded":
            RunRepo.mark_finished(
                session, run_id, RunStatus.BUDGET_STOP,
                f"cost ${total_cost:.2f} exceeded cap ${spec.budget.max_usd:.2f}",
            )
            session.commit()
            return True
        session.commit()
        return False

    def _finalize(self, spec: ExperimentSpec, run_id: str) -> None:
        session = self.session
        RunRepo.set_status(session, run_id, RunStatus.VERIFYING)
        session.commit()

        dlq_count = DLQRepo.count_unresolved(session, run_id)
        metrics.record_dlq_depth(session, run_id, dlq_count)
        trigger = rules.dlq_non_empty(run_id, dlq_count)
        if trigger:
            dispatcher.dispatch(session, trigger, run_id)
        session.commit()

        RunRepo.mark_finished(session, run_id, RunStatus.COMPLETE)
        session.commit()

        report_text = generate_report(session, run_id)
        write_artifact(session, run_id, "REPORT.md", report_text.encode("utf-8"), ArtifactKind.REPORT)
        session.commit()

        try:
            from research_dojo.inspect_tasks.bridge import export_run_to_inspect_log

            export_run_to_inspect_log(session, run_id)
            session.commit()
        except Exception as e:  # noqa: BLE001 — Inspect export is best-effort, never fails the run
            logger.debug("inspect export skipped: %s", e)

        logger.info("run %s COMPLETE", run_id)


def run_experiment(spec_path: str | Path, run_id: str | None = None, resume: bool = False) -> str:
    engine = RunEngine()
    try:
        return engine.run(spec_path, run_id=run_id, resume=resume)
    finally:
        engine.close()
