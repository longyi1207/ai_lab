"""Repository pattern: all state transitions go through these classes.

No raw SQL in engine/harness/verify/supervisor business logic — everything
touches the DB through a repo method, so idempotency and locking rules live
in one place (rollout upsert, resume-skip, stale detection, DLQ retry).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from research_dojo.db.models import (
    AlertEvent,
    Artifact,
    DLQEntry,
    Experiment,
    Judgment,
    Metric,
    Rollout,
    RolloutStatus,
    Run,
    RunArm,
    RunStatus,
    Sample,
    utcnow,
)


class ExperimentRepo:
    @staticmethod
    def get_or_create(session: Session, experiment_id: str, hypothesis: str = "") -> Experiment:
        exp = session.get(Experiment, experiment_id)
        if exp is None:
            exp = Experiment(experiment_id=experiment_id, hypothesis=hypothesis)
            session.add(exp)
            session.flush()
        return exp

    @staticmethod
    def get(session: Session, experiment_id: str) -> Experiment | None:
        return session.get(Experiment, experiment_id)

    @staticmethod
    def list(session: Session) -> list[Experiment]:
        return list(session.scalars(select(Experiment).order_by(Experiment.created_at)))


class RunRepo:
    @staticmethod
    def create(
        session: Session,
        run_id: str,
        experiment_id: str,
        spec_frozen_json: dict,
        spec_hash: str,
        git_commit: str | None = None,
        python_version: str | None = None,
        package_version: str | None = None,
    ) -> Run:
        run = Run(
            run_id=run_id,
            experiment_id=experiment_id,
            status=RunStatus.PENDING.value,
            spec_frozen_json=spec_frozen_json,
            spec_hash=spec_hash,
            git_commit=git_commit,
            python_version=python_version,
            package_version=package_version,
        )
        session.add(run)
        session.flush()
        return run

    @staticmethod
    def get(session: Session, run_id: str) -> Run | None:
        return session.get(Run, run_id)

    @staticmethod
    def list(session: Session, experiment_id: str | None = None) -> list[Run]:
        stmt = select(Run).order_by(Run.created_at.desc())
        if experiment_id:
            stmt = stmt.where(Run.experiment_id == experiment_id)
        return list(session.scalars(stmt))

    @staticmethod
    def set_arms(session: Session, run_id: str, arms: dict[str, dict]) -> None:
        for name, config in arms.items():
            session.add(RunArm(run_id=run_id, arm_name=name, config_json=config))
        session.flush()

    @staticmethod
    def set_status(session: Session, run_id: str, status: RunStatus, error_summary: str | None = None) -> None:
        run = session.get(Run, run_id)
        if run is None:
            return
        run.status = status.value
        if error_summary is not None:
            run.error_summary = error_summary
        session.flush()

    @staticmethod
    def mark_started(session: Session, run_id: str) -> None:
        run = session.get(Run, run_id)
        if run is None:
            return
        run.status = RunStatus.RUNNING.value
        run.started_at = utcnow()
        run.heartbeat_at = utcnow()
        session.flush()

    @staticmethod
    def mark_finished(session: Session, run_id: str, status: RunStatus, error_summary: str | None = None) -> None:
        run = session.get(Run, run_id)
        if run is None:
            return
        run.status = status.value
        run.finished_at = utcnow()
        if error_summary is not None:
            run.error_summary = error_summary
        session.flush()

    @staticmethod
    def heartbeat(session: Session, run_id: str) -> None:
        run = session.get(Run, run_id)
        if run is None:
            return
        run.heartbeat_at = utcnow()
        session.flush()

    @staticmethod
    def stale_running(session: Session, threshold_seconds: int) -> list[Run]:
        cutoff = utcnow() - timedelta(seconds=threshold_seconds)
        stmt = select(Run).where(
            Run.status == RunStatus.RUNNING.value,
            Run.heartbeat_at.is_not(None),
            Run.heartbeat_at < cutoff,
        )
        return list(session.scalars(stmt))

    @staticmethod
    def increment_consecutive_failures(session: Session, run_id: str) -> int:
        run = session.get(Run, run_id)
        if run is None:
            return 0
        run.consecutive_failures += 1
        session.flush()
        return run.consecutive_failures

    @staticmethod
    def reset_consecutive_failures(session: Session, run_id: str) -> None:
        run = session.get(Run, run_id)
        if run is None:
            return
        run.consecutive_failures = 0
        session.flush()

    @staticmethod
    def open_circuit(session: Session, run_id: str, cooldown_seconds: int) -> datetime:
        run = session.get(Run, run_id)
        until = utcnow() + timedelta(seconds=cooldown_seconds)
        if run is not None:
            run.circuit_open_until = until
            session.flush()
        return until

    @staticmethod
    def circuit_is_open(session: Session, run_id: str) -> bool:
        run = session.get(Run, run_id)
        if run is None or run.circuit_open_until is None:
            return False
        until = run.circuit_open_until
        if until.tzinfo is None:
            until = until.replace(tzinfo=UTC)
        return until > utcnow()

    @staticmethod
    def close_circuit(session: Session, run_id: str) -> None:
        run = session.get(Run, run_id)
        if run is not None:
            run.circuit_open_until = None
            session.flush()


class SampleRepo:
    @staticmethod
    def upsert(session: Session, id: str, dataset_name: str, prompt: str,
               expected: str | None = None, metadata_json: dict | None = None) -> Sample:
        sample = session.get(Sample, id)
        if sample is None:
            sample = Sample(
                id=id, dataset_name=dataset_name, prompt=prompt,
                expected=expected, metadata_json=metadata_json or {},
            )
            session.add(sample)
        else:
            sample.dataset_name = dataset_name
            sample.prompt = prompt
            sample.expected = expected
            sample.metadata_json = metadata_json or {}
        session.flush()
        return sample

    @staticmethod
    def bulk_upsert(session: Session, samples: list[dict]) -> None:
        for s in samples:
            SampleRepo.upsert(
                session, id=s["id"], dataset_name=s["dataset_name"], prompt=s["prompt"],
                expected=s.get("expected"), metadata_json=s.get("metadata_json") or {},
            )

    @staticmethod
    def get(session: Session, id: str) -> Sample | None:
        return session.get(Sample, id)

    @staticmethod
    def list_for_dataset(session: Session, dataset_name: str) -> list[Sample]:
        stmt = select(Sample).where(Sample.dataset_name == dataset_name).order_by(Sample.id)
        return list(session.scalars(stmt))


class RolloutRepo:
    @staticmethod
    def get_or_create_pending(
        session: Session, run_id: str, sample_id: str, arm: str, rollout_idx: int
    ) -> Rollout:
        """Idempotent: returns the existing row if one already exists for this
        (run_id, sample_id, arm, rollout_idx) identity, otherwise inserts a new
        PENDING row. Safe to call twice (resume / re-launch after crash).
        """
        stmt = select(Rollout).where(
            Rollout.run_id == run_id,
            Rollout.sample_id == sample_id,
            Rollout.arm == arm,
            Rollout.rollout_idx == rollout_idx,
        )
        existing = session.scalars(stmt).first()
        if existing is not None:
            return existing
        rollout = Rollout(
            run_id=run_id, sample_id=sample_id, arm=arm, rollout_idx=rollout_idx,
            status=RolloutStatus.PENDING.value,
        )
        session.add(rollout)
        try:
            session.flush()
        except IntegrityError:
            session.rollback()
            existing = session.scalars(stmt).first()
            if existing is None:
                raise
            return existing
        return rollout

    @staticmethod
    def mark_running(session: Session, rollout_id: int) -> None:
        rollout = session.get(Rollout, rollout_id)
        if rollout is None:
            return
        rollout.status = RolloutStatus.RUNNING.value
        rollout.attempts += 1
        session.flush()

    @staticmethod
    def complete(
        session: Session, rollout_id: int, completion: str, transcript_json: dict,
        latency_ms: float, tokens_in: int, tokens_out: int, cost_usd_est: float,
    ) -> Rollout:
        rollout = session.get(Rollout, rollout_id)
        if rollout is None:
            raise ValueError(f"rollout {rollout_id} not found")
        rollout.status = RolloutStatus.COMPLETE.value
        rollout.completion = completion
        rollout.transcript_json = transcript_json
        rollout.latency_ms = latency_ms
        rollout.tokens_in = tokens_in
        rollout.tokens_out = tokens_out
        rollout.cost_usd_est = cost_usd_est
        rollout.error = None
        session.flush()
        return rollout

    @staticmethod
    def fail(session: Session, rollout_id: int, error: str) -> Rollout:
        rollout = session.get(Rollout, rollout_id)
        if rollout is None:
            raise ValueError(f"rollout {rollout_id} not found")
        rollout.status = RolloutStatus.FAILED.value
        rollout.error = error
        session.flush()
        return rollout

    @staticmethod
    def get(session: Session, rollout_id: int) -> Rollout | None:
        return session.get(Rollout, rollout_id)

    @staticmethod
    def list_by_run(session: Session, run_id: str) -> list[Rollout]:
        stmt = select(Rollout).where(Rollout.run_id == run_id).order_by(Rollout.id)
        return list(session.scalars(stmt))

    @staticmethod
    def completed_keys(session: Session, run_id: str) -> set[tuple[str, str, int]]:
        stmt = select(Rollout.sample_id, Rollout.arm, Rollout.rollout_idx).where(
            Rollout.run_id == run_id, Rollout.status == RolloutStatus.COMPLETE.value,
        )
        return {(s, a, i) for s, a, i in session.execute(stmt).all()}

    @staticmethod
    def count_by_status(session: Session, run_id: str) -> dict[str, int]:
        stmt = (
            select(Rollout.status, func.count(Rollout.id))
            .where(Rollout.run_id == run_id)
            .group_by(Rollout.status)
        )
        return dict(session.execute(stmt).all())

    @staticmethod
    def recent(session: Session, run_id: str, limit: int = 20) -> list[Rollout]:
        stmt = (
            select(Rollout)
            .where(Rollout.run_id == run_id)
            .order_by(Rollout.id.desc())
            .limit(limit)
        )
        return list(session.scalars(stmt))


class JudgmentRepo:
    @staticmethod
    def create(
        session: Session, rollout_id: int, judge_version: str, score: float | None,
        label: str | None, rationale: str | None, flags_json: dict, raw_response: str | None,
    ) -> Judgment:
        j = Judgment(
            rollout_id=rollout_id, judge_version=judge_version, score=score, label=label,
            rationale=rationale, flags_json=flags_json, raw_response=raw_response,
        )
        session.add(j)
        session.flush()
        return j

    @staticmethod
    def list_for_rollout(session: Session, rollout_id: int) -> list[Judgment]:
        stmt = select(Judgment).where(Judgment.rollout_id == rollout_id).order_by(Judgment.id)
        return list(session.scalars(stmt))

    @staticmethod
    def list_for_run(session: Session, run_id: str) -> list[Judgment]:
        stmt = (
            select(Judgment)
            .join(Rollout, Judgment.rollout_id == Rollout.id)
            .where(Rollout.run_id == run_id)
            .order_by(Judgment.id)
        )
        return list(session.scalars(stmt))


class MetricRepo:
    @staticmethod
    def record(session: Session, run_id: str, name: str, value: float, labels_json: dict | None = None) -> Metric:
        m = Metric(run_id=run_id, name=name, value=value, labels_json=labels_json or {})
        session.add(m)
        session.flush()
        return m

    @staticmethod
    def list_for_run(session: Session, run_id: str, name: str | None = None) -> list[Metric]:
        stmt = select(Metric).where(Metric.run_id == run_id)
        if name:
            stmt = stmt.where(Metric.name == name)
        return list(session.scalars(stmt.order_by(Metric.ts)))

    @staticmethod
    def aggregate(session: Session, run_id: str) -> dict[str, dict[str, float]]:
        stmt = select(
            Metric.name, func.count(Metric.id), func.sum(Metric.value),
            func.avg(Metric.value), func.max(Metric.value),
        ).where(Metric.run_id == run_id).group_by(Metric.name)
        out: dict[str, dict[str, float]] = {}
        for name, count, total, avg, mx in session.execute(stmt).all():
            out[name] = {"count": count, "sum": total or 0.0, "avg": avg or 0.0, "max": mx or 0.0}
        return out


class ArtifactRepo:
    @staticmethod
    def record(session: Session, run_id: str, path: str, sha256: str, kind: str, bytes_: int) -> Artifact:
        a = Artifact(run_id=run_id, path=path, sha256=sha256, kind=kind, bytes=bytes_)
        session.add(a)
        session.flush()
        return a

    @staticmethod
    def list_for_run(session: Session, run_id: str) -> list[Artifact]:
        stmt = select(Artifact).where(Artifact.run_id == run_id).order_by(Artifact.created_at)
        return list(session.scalars(stmt))


class AlertRepo:
    @staticmethod
    def record(
        session: Session, run_id: str | None, rule: str, severity: str, message: str,
        delivered_to: dict | None = None,
    ) -> AlertEvent:
        e = AlertEvent(
            run_id=run_id, rule=rule, severity=severity, message=message,
            delivered_to=delivered_to or {},
        )
        session.add(e)
        session.flush()
        return e

    @staticmethod
    def list(session: Session, run_id: str | None = None, limit: int = 100) -> list[AlertEvent]:
        stmt = select(AlertEvent).order_by(AlertEvent.ts.desc()).limit(limit)
        if run_id:
            stmt = select(AlertEvent).where(AlertEvent.run_id == run_id).order_by(AlertEvent.ts.desc()).limit(limit)
        return list(session.scalars(stmt))


class DLQRepo:
    @staticmethod
    def add(
        session: Session, run_id: str, sample_id: str, arm: str, rollout_idx: int,
        error: str, attempts: int, retry_delay_seconds: int = 60,
    ) -> DLQEntry:
        entry = DLQEntry(
            run_id=run_id, sample_id=sample_id, arm=arm, rollout_idx=rollout_idx,
            error=error, attempts=attempts,
            next_retry_at=utcnow() + timedelta(seconds=retry_delay_seconds),
        )
        session.add(entry)
        session.flush()
        return entry

    @staticmethod
    def list_for_run(session: Session, run_id: str, unresolved_only: bool = True) -> list[DLQEntry]:
        stmt = select(DLQEntry).where(DLQEntry.run_id == run_id)
        if unresolved_only:
            stmt = stmt.where(DLQEntry.resolved.is_(False))
        return list(session.scalars(stmt.order_by(DLQEntry.created_at)))

    @staticmethod
    def due_for_retry(session: Session, max_attempts: int) -> list[DLQEntry]:
        stmt = select(DLQEntry).where(
            DLQEntry.resolved.is_(False),
            DLQEntry.next_retry_at <= utcnow(),
            DLQEntry.attempts < max_attempts,
        )
        return list(session.scalars(stmt))

    @staticmethod
    def resolve(session: Session, entry_id: int) -> None:
        entry = session.get(DLQEntry, entry_id)
        if entry is not None:
            entry.resolved = True
            session.flush()

    @staticmethod
    def bump_attempt(session: Session, entry_id: int, retry_delay_seconds: int) -> None:
        entry = session.get(DLQEntry, entry_id)
        if entry is not None:
            entry.attempts += 1
            entry.next_retry_at = utcnow() + timedelta(seconds=retry_delay_seconds)
            session.flush()

    @staticmethod
    def count_unresolved(session: Session, run_id: str) -> int:
        stmt = select(func.count(DLQEntry.id)).where(
            DLQEntry.run_id == run_id, DLQEntry.resolved.is_(False),
        )
        return session.scalar(stmt) or 0
