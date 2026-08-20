"""SQLAlchemy 2.x ORM models — the relational schema is the source of truth.

JSONL under artifacts/<run_id>/audit/*.jsonl is a write-through audit export
only; it is never read back as state. See docs/architecture.md.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class RunStatus(enum.StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    BUDGET_STOP = "BUDGET_STOP"
    CANCELLED = "CANCELLED"
    STALE = "STALE"


class RolloutStatus(enum.StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ArtifactKind(enum.StrEnum):
    SPEC = "SPEC"
    TRANSCRIPT = "TRANSCRIPT"
    REPORT = "REPORT"
    BUNDLE = "BUNDLE"
    INSPECT_LOG = "INSPECT_LOG"
    OTHER = "OTHER"


class AlertSeverity(enum.StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


_SEVERITY_ORDER = {AlertSeverity.INFO: 0, AlertSeverity.WARNING: 1, AlertSeverity.CRITICAL: 2}


class Experiment(Base):
    __tablename__ = "experiments"

    experiment_id: Mapped[str] = mapped_column(String, primary_key=True)
    hypothesis: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    runs: Mapped[list[Run]] = relationship(back_populates="experiment", cascade="all, delete-orphan")


class Run(Base):
    __tablename__ = "runs"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey("experiments.experiment_id"), index=True)
    status: Mapped[str] = mapped_column(String, default=RunStatus.PENDING.value, index=True)
    spec_frozen_json: Mapped[dict] = mapped_column(JSON, default=dict)
    spec_hash: Mapped[str] = mapped_column(String, default="")
    git_commit: Mapped[str | None] = mapped_column(String, nullable=True)
    python_version: Mapped[str | None] = mapped_column(String, nullable=True)
    package_version: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(nullable=True)
    error_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    circuit_open_until: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    experiment: Mapped[Experiment] = relationship(back_populates="runs")
    arms: Mapped[list[RunArm]] = relationship(back_populates="run", cascade="all, delete-orphan")
    rollouts: Mapped[list[Rollout]] = relationship(back_populates="run", cascade="all, delete-orphan")


class RunArm(Base):
    __tablename__ = "run_arms"
    __table_args__ = (UniqueConstraint("run_id", "arm_name", name="uq_run_arms_run_arm"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), index=True)
    arm_name: Mapped[str] = mapped_column(String)
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)

    run: Mapped[Run] = relationship(back_populates="arms")


class Sample(Base):
    __tablename__ = "samples"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    dataset_name: Mapped[str] = mapped_column(String, index=True)
    prompt: Mapped[str] = mapped_column(String)
    expected: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Rollout(Base):
    __tablename__ = "rollouts"
    __table_args__ = (
        UniqueConstraint("run_id", "sample_id", "arm", "rollout_idx", name="uq_rollouts_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), index=True)
    sample_id: Mapped[str] = mapped_column(ForeignKey("samples.id"), index=True)
    arm: Mapped[str] = mapped_column(String)
    rollout_idx: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String, default=RolloutStatus.PENDING.value, index=True)
    completion: Mapped[str | None] = mapped_column(String, nullable=True)
    transcript_json: Mapped[dict] = mapped_column(JSON, default=dict)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cost_usd_est: Mapped[float] = mapped_column(Float, default=0.0)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    run: Mapped[Run] = relationship(back_populates="rollouts")
    sample: Mapped[Sample] = relationship()
    judgments: Mapped[list[Judgment]] = relationship(back_populates="rollout", cascade="all, delete-orphan")


class Judgment(Base):
    __tablename__ = "judgments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rollout_id: Mapped[int] = mapped_column(ForeignKey("rollouts.id"), index=True)
    judge_version: Mapped[str] = mapped_column(String, default="")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    rationale: Mapped[str | None] = mapped_column(String, nullable=True)
    flags_json: Mapped[dict] = mapped_column(JSON, default=dict)
    raw_response: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    rollout: Mapped[Rollout] = relationship(back_populates="judgments")


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), index=True)
    name: Mapped[str] = mapped_column(String, index=True)
    value: Mapped[float] = mapped_column(Float)
    labels_json: Mapped[dict] = mapped_column(JSON, default=dict)
    ts: Mapped[datetime] = mapped_column(default=utcnow, index=True)


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), index=True)
    path: Mapped[str] = mapped_column(String)
    sha256: Mapped[str] = mapped_column(String, index=True)
    kind: Mapped[str] = mapped_column(String, default=ArtifactKind.OTHER.value)
    bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("runs.run_id"), nullable=True, index=True)
    rule: Mapped[str] = mapped_column(String, index=True)
    severity: Mapped[str] = mapped_column(String, default=AlertSeverity.INFO.value)
    message: Mapped[str] = mapped_column(String)
    delivered_to: Mapped[dict] = mapped_column(JSON, default=dict)
    ts: Mapped[datetime] = mapped_column(default=utcnow, index=True)


class DLQEntry(Base):
    __tablename__ = "dlq_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), index=True)
    sample_id: Mapped[str] = mapped_column(String)
    arm: Mapped[str] = mapped_column(String)
    rollout_idx: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(String)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    resolved: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
