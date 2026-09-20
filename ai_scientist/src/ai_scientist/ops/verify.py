"""Run-time adversarial truth seeking (`truth_debate` → `truth_judge`).

Uses the Agent runtime (skill playbook + tools/context), not prompt stuffing.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..agent import context_block, run_skilled
from ..llm import LLMClient
from ..schema import Candidate, Metrics, VerifyConfig
from ..skills_loader import SkillRegistry

ALLOWED_FLAGS = {
    "overfit_risk",
    "cost_confound",
    "baseline_missing",
    "metric_gaming",
    "seed_luck",
    "effect_too_small",
    "unreproducible",
}
RULINGS = {"supports", "undermines", "unclear"}

DEBATE_ROLE = (
    "You are the runtime truth-debate agent for ai_scientist. "
    "Argue both sides of a finished trial using only measured metrics."
)
JUDGE_ROLE = (
    "You are the runtime truth-judge for ai_scientist. "
    "Rule on a debated trial; prefer unclear over a confident wrong ruling."
)


@dataclass
class Verification:
    ruling: str = "unavailable"
    confidence: float = 0.0
    flags: list[str] = field(default_factory=list)
    reason: str = ""
    debate: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ruling": self.ruling,
            "confidence": self.confidence,
            "flags": self.flags,
            "reason": self.reason,
            "debate": self.debate,
        }


def verify_result(
    candidate: Candidate,
    metrics: Metrics,
    *,
    llm: LLMClient,
    skills: SkillRegistry,
    config: VerifyConfig,
) -> Verification:
    if not config.enabled:
        return Verification(ruling="skipped", reason="verification disabled in config")

    metrics_payload = {
        "fitness": metrics.fitness,
        "values": metrics.values,
        "flags": metrics.verification_flags,
    }
    plan_payload = {
        "params": candidate.plan.params,
        "baselines": candidate.plan.baselines,
        "seed": candidate.plan.seed,
    }

    debate: dict[str, Any] = {}
    try:
        out = run_skilled(
            "truth_debate",
            "\n\n".join(
                [
                    "Debate whether this trial supports the claim.",
                    context_block("claim", candidate.hypothesis.claim),
                    context_block("plan", plan_payload),
                    context_block("metrics", metrics_payload),
                ]
            ),
            role=DEBATE_ROLE,
            llm=llm,
            skills=skills,
            expect_json=True,
            temperature=config.temperature,
        )
        payload = out.parsed
        if not isinstance(payload, dict) or "supports" not in payload:
            raise ValueError("debate payload missing 'supports'")
        debate = payload
    except Exception as exc:  # noqa: BLE001
        return Verification(
            ruling="unavailable",
            flags=[config.unavailable_flag],
            reason=f"debate unavailable: {type(exc).__name__}: {exc}",
        )

    try:
        out = run_skilled(
            "truth_judge",
            "\n\n".join(
                [
                    "Judge the debate and emit flags.",
                    context_block("claim", candidate.hypothesis.claim),
                    context_block("debate", debate),
                    context_block("metrics", metrics_payload),
                ]
            ),
            role=JUDGE_ROLE,
            llm=llm,
            skills=skills,
            expect_json=True,
            temperature=config.temperature,
        )
        payload = out.parsed
        if not isinstance(payload, dict):
            raise ValueError("judge returned no JSON")
        ruling = str(payload.get("ruling", "")).strip().lower()
        if ruling not in RULINGS:
            raise ValueError(f"bad ruling {ruling!r}")
        flags = [str(f) for f in payload.get("flags", []) if str(f) in ALLOWED_FLAGS]
        return Verification(
            ruling=ruling,
            confidence=float(payload.get("confidence", 0.0) or 0.0),
            flags=flags,
            reason=str(payload.get("reason", "")),
            debate=debate,
        )
    except Exception as exc:  # noqa: BLE001
        return Verification(
            ruling="unavailable",
            flags=[config.unavailable_flag],
            reason=f"judge unavailable: {type(exc).__name__}: {exc}",
            debate=debate,
        )
