"""Experiment spec: YAML -> validated Pydantic model -> frozen JSON.

No silent defaults for safety-critical fields (budget.max_usd, judge.version) —
they must be explicit in the spec (Pydantic raises if missing since these
fields carry no default). See docs/spec_schema.md for the published schema.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(:-([^}]*))?\}")


def _expand_env(value: object) -> object:
    """Expand ${VAR} / ${VAR:-default} in strings, recursively for dict/list."""
    if isinstance(value, str):
        def repl(m: re.Match) -> str:
            var, _, default = m.group(1), m.group(2), m.group(3)
            return os.environ.get(var, default if default is not None else "")
        return _ENV_VAR_PATTERN.sub(repl, value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


class ModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: Literal["azure_openai", "openai"] = "azure_openai"
    deployment: str
    temperature: float = 0.0
    max_tokens: int = 512


class JudgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rubric: str
    version: str  # required — no silent default, judge results must be traceable


class VerificationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deterministic: bool = True
    judge: JudgeSpec | None = None


class BudgetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_usd: float  # required — safety-critical, no silent default
    max_samples: int | None = None


class AlertsSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    webhook_url: str = ""
    on: list[str] = Field(default_factory=list)


class SupervisorSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    stale_after_seconds: int = 600


class HarnessSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["batch_chat", "agent"] = "batch_chat"
    max_steps: int = 10
    timeout_seconds: int = 120


class ExperimentSpec(BaseModel):
    """Top-level experiment spec, validated from specs/*.yaml."""

    model_config = ConfigDict(extra="forbid")

    experiment_id: str
    hypothesis: str

    model: ModelSpec
    dataset: str
    arms: list[str] = Field(default_factory=lambda: ["baseline"])
    rollouts_per_sample: int = 1

    verification: VerificationSpec = Field(default_factory=VerificationSpec)
    budget: BudgetSpec
    alerts: AlertsSpec = Field(default_factory=AlertsSpec)
    supervisor: SupervisorSpec = Field(default_factory=SupervisorSpec)
    harness: HarnessSpec = Field(default_factory=HarnessSpec)

    @field_validator("arms")
    @classmethod
    def _nonempty_arms(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("arms must be non-empty")
        return v

    @model_validator(mode="after")
    def _judge_required_if_verification_judge_configured(self) -> ExperimentSpec:
        # deterministic-only mode is valid; judge is opt-in via verification.judge
        return self

    def spec_hash(self) -> str:
        payload = self.model_dump(mode="json")
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]

    def freeze(self) -> dict:
        """Frozen JSON representation stored in DB + artifact."""
        return {
            "spec_hash": self.spec_hash(),
            **self.model_dump(mode="json"),
        }


def load_spec(path: str | Path) -> ExperimentSpec:
    path = Path(path)
    raw = yaml.safe_load(path.read_text())
    raw = _expand_env(raw)
    return ExperimentSpec.model_validate(raw)
