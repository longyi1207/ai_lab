"""Verification pipeline: deterministic -> (optional) judge -> sanity flags.
The engine calls `Verifier.verify()` once per completed rollout and persists
every field via JudgmentRepo + the audit JSONL writer — never DB-only, never
JSONL-only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from research_dojo.config.spec import ExperimentSpec
from research_dojo.verify.deterministic import check_deterministic
from research_dojo.verify.judge import judge_rollout
from research_dojo.verify.sanity import check_sanity


@dataclass
class VerificationResult:
    deterministic_passed: bool | None = None
    deterministic_reason: str | None = None
    judge_score: float | None = None
    judge_label: str | None = None
    judge_rationale: str | None = None
    judge_raw_response: str | None = None
    judge_version: str | None = None
    flags: list[dict] = field(default_factory=list)


class Verifier:
    def __init__(self, spec: ExperimentSpec):
        self.spec = spec
        self._rubric_text: str | None = None

    def _load_rubric(self) -> str:
        if self._rubric_text is None:
            cfg = self.spec.verification.judge
            # relative to the CWD `dojo` was invoked from (project root),
            # matching specs/tom_smoke.yaml's `rubric: prompts/...`
            self._rubric_text = Path(cfg.rubric).read_text()
        return self._rubric_text

    def verify(self, prompt: str, completion: str, expected: str | None) -> VerificationResult:
        result = VerificationResult()

        if self.spec.verification.deterministic:
            det = check_deterministic(completion, expected)
            result.deterministic_passed = det["passed"]
            result.deterministic_reason = det["reason"]

        if self.spec.verification.judge is not None:
            rubric = self._load_rubric()
            j = judge_rollout(rubric, prompt, completion, self.spec.verification.judge.version)
            result.judge_score = j["score"]
            result.judge_label = j["label"]
            result.judge_rationale = j["rationale"]
            result.judge_raw_response = j["raw_response"]
            result.judge_version = j["judge_version"]

        result.flags = check_sanity(completion, result.judge_score, result.deterministic_passed)
        return result
