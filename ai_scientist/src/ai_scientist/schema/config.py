"""Phase-1 metadata (human/agent contract) and engine config (ops knobs)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Budget(_Model):
    max_usd: float | None = 30.0
    max_tokens: int | None = None


class TimeBudget(_Model):
    deadline: datetime | None = None
    overnight_ok: bool = True


class Metadata(_Model):
    """`metadata.yaml` — Phase-1 expectations. Credentials are *names*, never values."""

    project_id: str
    question: str = ""
    budget: Budget = Field(default_factory=Budget)
    time: TimeBudget = Field(default_factory=TimeBudget)
    credentials_refs: list[str] = Field(default_factory=list)
    audience: str = "self"
    style: Literal["rigorous", "casual"] = "rigorous"
    topic_fidelity: Literal["stuck", "discovery", "mixed"] = "mixed"
    extensible: bool = True
    knowledge_sources: list[str] = Field(default_factory=lambda: ["web_default"])
    tools: list[str] = Field(default_factory=lambda: ["web", "fs", "basic"])
    assumptions: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ResourcePool(_Model):
    gpus: list[int] = Field(default_factory=list)
    api_slots: int = 4


class SearchConfig(_Model):
    offspring_per_tick: int = 2
    target_inflight: int = 4
    max_generations: int | None = None
    novelty_k: int = 15
    novelty_max_size: int = 200
    select_uniform_cell: float = 0.5
    select_fitness_weighted: float = 0.3
    select_novelty: float = 0.2
    mutator: Literal["fake", "llm"] = "fake"
    mutation_ops: dict[str, float] = Field(
        default_factory=lambda: {
            "sharpen_claim": 0.25,
            "vary_params": 0.35,
            "change_seed": 0.1,
            "broaden_scope": 0.15,
            "crossover": 0.15,
        }
    )


class VerifyConfig(_Model):
    """Run-time adversarial truth seeking (DESIGN §6): debate a result, then judge it."""

    enabled: bool = True
    temperature: float = 0.3
    # When a model is unavailable/unparseable we flag it rather than silently trusting.
    unavailable_flag: str = "verification_unavailable"


class OpsConfig(_Model):
    concurrency: int = 2
    heartbeat_interval_s: float = 1.0
    heartbeat_timeout_s: float = 15.0
    scheduler_tick_s: float = 0.2
    health_tick_s: float = 1.0
    # Phase-2 ops agent (LLM soft brain) — slower than scheduler; emits intents only.
    ops_triage_enabled: bool = True
    ops_triage_tick_s: float = 5.0
    max_attempts: int = 2
    job_timeout_s: float | None = 900.0
    control_host: str = "127.0.0.1"
    control_port: int = 0  # 0 = ephemeral, written to state/daemon.json


class EngineConfig(_Model):
    """`config.yaml` — engine knobs, distinct from Phase-1 semantics."""

    domain: str = "fake_toy"
    resources: ResourcePool = Field(default_factory=ResourcePool)
    search: SearchConfig = Field(default_factory=SearchConfig)
    ops: OpsConfig = Field(default_factory=OpsConfig)
    verify: VerifyConfig = Field(default_factory=VerifyConfig)
