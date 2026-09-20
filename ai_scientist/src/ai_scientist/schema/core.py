"""Core science objects.

Phenotype split (DESIGN §0): search mutates `Hypothesis + ExperimentPlan` (a `Candidate`);
`Results`/`Metrics` are written by evaluation and cached on the archived `EliteRecord`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .ids import content_hash, new_id


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Hypothesis(Strict):
    hypothesis_id: str = Field(default_factory=lambda: new_id("hyp"))
    statement: str = Field(min_length=1)
    claim: str = Field(min_length=1, description="Falsifiable form of the statement")
    rationale: str | None = None
    parent_ids: list[str] = Field(default_factory=list)
    generation: int = 0
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class ResourceRequest(Strict):
    gpu: int = 0
    api_slots: int = 1

    @field_validator("gpu", "api_slots")
    @classmethod
    def _non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("resource counts must be >= 0")
        return v

    def lock_count(self) -> dict[str, int]:
        return {"gpu": self.gpu, "api": self.api_slots}


class ExperimentPlan(Strict):
    plan_id: str = Field(default_factory=lambda: new_id("plan"))
    hypothesis_id: str
    domain: str = Field(min_length=1, description="Domain pack id")
    params: dict[str, Any] = Field(default_factory=dict)
    metrics: list[str] = Field(
        default_factory=list, description="Metric names the domain must emit"
    )
    baselines: list[str] = Field(default_factory=list)
    resources: ResourceRequest = Field(default_factory=ResourceRequest)
    seed: int = 0
    splits: dict[str, str] = Field(default_factory=dict)
    parent_ids: list[str] = Field(default_factory=list)
    generation: int = 0
    notes: str | None = None


class Candidate(Strict):
    """One searchable individual: hypothesis + how to test it."""

    candidate_id: str = Field(default_factory=lambda: new_id("cand"))
    hypothesis: Hypothesis
    plan: ExperimentPlan
    origin: str = "seed"
    created_at: datetime = Field(default_factory=_utcnow)

    def model_post_init(self, _ctx: Any) -> None:
        if self.plan.hypothesis_id != self.hypothesis.hypothesis_id:
            raise ValueError("plan.hypothesis_id must match hypothesis.hypothesis_id")

    @property
    def generation(self) -> int:
        return max(self.hypothesis.generation, self.plan.generation)

    def fingerprint(self) -> str:
        """Hash of the searchable content only (ids/timestamps excluded)."""
        return content_hash(
            {
                "statement": self.hypothesis.statement,
                "claim": self.hypothesis.claim,
                "domain": self.plan.domain,
                "params": self.plan.params,
                "seed": self.plan.seed,
                "splits": self.plan.splits,
            }
        )


class Results(Strict):
    """Raw output of one trial, as returned by a domain pack."""

    ok: bool = True
    payload: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list)
    usage: dict[str, float] = Field(default_factory=dict, description="e.g. usd, tokens")
    error: str | None = None


class Metrics(Strict):
    fitness: float
    descriptor: dict[str, float] = Field(default_factory=dict)
    values: dict[str, float] = Field(default_factory=dict)
    behavior: list[float] = Field(default_factory=list, description="Novelty behavior vector")
    verification_flags: list[str] = Field(default_factory=list)


class EliteRecord(Strict):
    elite_id: str = Field(default_factory=lambda: new_id("elite"))
    candidate: Candidate
    metrics: Metrics
    cell: tuple[int, ...]
    fitness: float
    job_id: str | None = None
    generation: int = 0
    pinned: bool = False
    results_ref: str | None = None
    writeup_ref: str | None = None
    lineage: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


JobStatus = Literal["queued", "running", "done", "failed", "stale", "cancelled"]
TERMINAL_STATUSES: frozenset[str] = frozenset({"done", "failed", "cancelled"})


class Job(Strict):
    job_id: str = Field(default_factory=lambda: new_id("job"))
    candidate_id: str
    priority: float = 0.0
    resources: ResourceRequest = Field(default_factory=ResourceRequest)
    status: JobStatus = "queued"
    worker_id: str | None = None
    pid: int | None = None
    attempts: int = 0
    ingested: bool = False
    error: str | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    heartbeat_at: datetime | None = None


class Axis(Strict):
    """One MAP-Elites descriptor axis; `edges` has bins+1 monotonically rising values."""

    name: str
    edges: list[float] = Field(min_length=2)

    @field_validator("edges")
    @classmethod
    def _monotonic(cls, v: list[float]) -> list[float]:
        if any(b <= a for a, b in zip(v, v[1:], strict=False)):
            raise ValueError("axis edges must be strictly increasing")
        return v

    @property
    def bins(self) -> int:
        return len(self.edges) - 1

    def bin_for(self, value: float) -> int:
        for i in range(self.bins):
            if value < self.edges[i + 1]:
                return max(i, 0) if value >= self.edges[0] else 0
        return self.bins - 1
