"""Harness protocol: prompt -> HarnessResult. Two implementations ship in v1
(BatchChatHarness, AgentHarness); see harness/registry.py for kind -> class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class HarnessResult:
    completion: str
    transcript: list[dict] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    cost_usd_est: float = 0.0


class TransientHarnessError(Exception):
    """Retryable failure (429 / timeout / connection). The engine's circuit
    breaker counts consecutive occurrences of this across rollouts."""


class Harness(Protocol):
    def run(self, prompt: str, *, sample_id: str, arm: str) -> HarnessResult: ...


def is_transient_error(exc: Exception) -> bool:
    """True for 429 / connection / timeout errors the OpenAI SDK raises —
    safe to retry with backoff rather than failing the rollout outright."""
    name = type(exc).__name__
    return "RateLimit" in name or "APIConnection" in name or "Timeout" in name
