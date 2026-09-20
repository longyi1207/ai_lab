"""Domain pack interface (SPEC §8).

A domain pack owns the science: what a plan means, how to run it, how to grade it,
and which behavior descriptors define the MAP axes. The harness owns search, ops,
persistence, and verification plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..schema import Axis, Candidate, ExperimentPlan, Metrics, Results


class PlanInvalid(ValueError):
    """Raised by `validate_plan` when a plan cannot be run by this domain."""


class ParamSpec(BaseModel):
    """Mutable knob in a plan's `params`, so mutators can vary plans meaningfully."""

    model_config = ConfigDict(extra="forbid")

    name: str
    kind: Literal["int", "float", "choice", "bool"]
    low: float | None = None
    high: float | None = None
    choices: list[Any] | None = None

    @model_validator(mode="after")
    def _check(self) -> ParamSpec:
        if self.kind in {"int", "float"} and (self.low is None or self.high is None):
            raise ValueError(f"{self.name}: numeric ParamSpec needs low and high")
        if self.kind == "choice" and not self.choices:
            raise ValueError(f"{self.name}: choice ParamSpec needs choices")
        return self


@dataclass
class RunContext:
    """Everything a trial may use, injected by the worker."""

    job_id: str
    seed: int
    llm: Any = None
    heartbeat: Any = None  # callable() -> None
    log: Any = None  # callable(str) -> None
    extra: dict[str, Any] = field(default_factory=dict)

    def beat(self) -> None:
        if self.heartbeat is not None:
            self.heartbeat()

    def info(self, message: str) -> None:
        if self.log is not None:
            self.log(message)


@runtime_checkable
class DomainPack(Protocol):
    domain_id: str

    def axes(self) -> list[Axis]:
        """MAP descriptor axes; `Metrics.descriptor` must supply each axis name."""

    def param_space(self) -> list[ParamSpec]:
        """Knobs mutators may vary."""

    def validate_plan(self, plan: ExperimentPlan) -> None:
        """Raise `PlanInvalid` if the plan is not runnable."""

    def run(self, plan: ExperimentPlan, job_dir: Path, ctx: RunContext) -> Results:
        """Execute one trial. Long work must call `ctx.beat()` periodically."""

    def grade(self, plan: ExperimentPlan, results: Results) -> Metrics:
        """Fitness + descriptor + behavior vector."""

    def seed_candidates(self) -> list[Candidate]:
        """Baselines the archive should always contain."""


class DomainMetricsError(ValueError):
    pass


def validate_metrics(domain: DomainPack, metrics: Metrics) -> None:
    missing = [axis.name for axis in domain.axes() if axis.name not in metrics.descriptor]
    if missing:
        raise DomainMetricsError(
            f"{domain.domain_id}: metrics.descriptor missing axis values {missing}"
        )


class PlanParams(BaseModel):
    """Helper for packs that want a typed view over `plan.params`."""

    model_config = ConfigDict(extra="allow")

    values: dict[str, Any] = Field(default_factory=dict)
