from __future__ import annotations

from research_dojo.config.spec import ExperimentSpec
from research_dojo.harness.agent import AgentHarness
from research_dojo.harness.base import Harness
from research_dojo.harness.batch_chat import BatchChatHarness

_REGISTRY: dict[str, type] = {
    "batch_chat": BatchChatHarness,
    "agent": AgentHarness,
}


def build_harness(spec: ExperimentSpec) -> Harness:
    cls = _REGISTRY.get(spec.harness.kind)
    if cls is None:
        raise ValueError(f"unknown harness kind: {spec.harness.kind!r} (known: {sorted(_REGISTRY)})")
    return cls(spec)
