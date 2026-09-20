"""`fake_toy` — deterministic offline domain pack.

Purpose: exercise the whole harness (search → schedule → run → grade → archive → report)
with no network and no real science. It is the reference implementation of the
`DomainPack` protocol and the fixture used by the test suite.

The "experiment" is a closed-form scoring function with a couple of local optima, so
MAP-Elites has something to fill and novelty has something to spread over.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from pathlib import Path

from ..schema import Axis, Candidate, ExperimentPlan, Hypothesis, Metrics, Results
from .base import ParamSpec, PlanInvalid, RunContext

PROBE_COUNT = 12
MODES = ["direct", "critique", "debate"]


def _unit_hash(*parts: object) -> float:
    blob = "|".join(str(p) for p in parts).encode()
    return int.from_bytes(hashlib.sha256(blob).digest()[:8], "big") / 2**64


class FakeToyDomain:
    domain_id = "fake_toy"

    def axes(self) -> list[Axis]:
        return [
            Axis(name="quality", edges=[0.0, 0.25, 0.5, 0.75, 1.0001]),
            Axis(name="cost", edges=[0.0, 0.33, 0.66, 1.0001]),
        ]

    def param_space(self) -> list[ParamSpec]:
        return [
            ParamSpec(name="alpha", kind="float", low=0.0, high=1.0),
            ParamSpec(name="rounds", kind="int", low=1, high=6),
            ParamSpec(name="mode", kind="choice", choices=list(MODES)),
            ParamSpec(name="verbose", kind="bool"),
        ]

    def validate_plan(self, plan: ExperimentPlan) -> None:
        if plan.domain != self.domain_id:
            raise PlanInvalid(f"plan.domain {plan.domain!r} != {self.domain_id!r}")
        params = plan.params
        for required in ("alpha", "rounds", "mode"):
            if required not in params:
                raise PlanInvalid(f"missing param {required!r}")
        if not 0.0 <= float(params["alpha"]) <= 1.0:
            raise PlanInvalid("alpha must be within [0, 1]")
        rounds = params["rounds"]
        if not isinstance(rounds, int) or not 1 <= rounds <= 6:
            raise PlanInvalid("rounds must be an int within [1, 6]")
        if params["mode"] not in MODES:
            raise PlanInvalid(f"mode must be one of {MODES}")
        if plan.resources.gpu > 0:
            raise PlanInvalid("fake_toy never needs a GPU")

    def run(self, plan: ExperimentPlan, job_dir: Path, ctx: RunContext) -> Results:
        params = plan.params
        alpha = float(params["alpha"])
        rounds = int(params["rounds"])
        mode = str(params["mode"])
        if params.get("fail"):
            raise RuntimeError("fake_toy: deliberate failure (params.fail)")

        # Two humps in alpha plus a mode bonus: enough structure for QD to explore.
        base = 0.55 * math.exp(-((alpha - 0.25) ** 2) / 0.02)
        base += 0.85 * math.exp(-((alpha - 0.75) ** 2) / 0.02)
        base += {"direct": 0.0, "critique": 0.08, "debate": 0.14}[mode]
        base += 0.05 * math.log1p(rounds)
        noise = 0.04 * (_unit_hash(plan.plan_id, plan.seed, "noise") - 0.5)
        quality = max(0.0, min(1.0, base + noise))

        probes: list[int] = []
        for i in range(PROBE_COUNT):
            draw = _unit_hash(mode, round(alpha, 3), rounds, plan.seed, i)
            probes.append(1 if draw < quality else 0)

        sleep_s = float(params.get("sleep_s", 0.0) or 0.0)
        waited = 0.0
        while waited < sleep_s:
            step = min(0.2, sleep_s - waited)
            time.sleep(step)
            waited += step
            ctx.beat()

        tokens = 120.0 * rounds * (1.4 if mode == "debate" else 1.0)
        ctx.info(f"fake_toy: alpha={alpha:.3f} rounds={rounds} mode={mode} quality={quality:.3f}")
        payload = {
            "quality": quality,
            "probes": probes,
            "rounds": rounds,
            "mode": mode,
            "alpha": alpha,
        }
        (job_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        (job_dir / "artifacts" / "trial.json").write_text(json.dumps(payload, indent=2))
        return Results(
            ok=True,
            payload=payload,
            artifacts=["artifacts/trial.json"],
            usage={"usd": round(tokens * 1e-5, 6), "tokens": tokens},
        )

    def grade(self, plan: ExperimentPlan, results: Results) -> Metrics:
        quality = float(results.payload["quality"])
        probes: list[int] = list(results.payload["probes"])
        tokens = float(results.usage.get("tokens", 0.0))
        cost = min(1.0, tokens / 1200.0)
        accuracy = sum(probes) / len(probes) if probes else 0.0
        fitness = round(quality - 0.15 * cost, 6)
        flags: list[str] = []
        if abs(accuracy - quality) > 0.35:
            flags.append("probe_quality_mismatch")
        return Metrics(
            fitness=fitness,
            descriptor={"quality": quality, "cost": cost},
            values={"quality": quality, "cost": cost, "probe_accuracy": accuracy, "tokens": tokens},
            behavior=[float(b) for b in probes] + [cost],
            verification_flags=flags,
        )

    def seed_candidates(self) -> list[Candidate]:
        seeds: list[Candidate] = []
        for mode in MODES:
            if mode == "direct":
                statement = "The direct mode sets the quality baseline for this toy task."
                claim = "mode=direct establishes the reference graded quality at alpha=0.5."
            else:
                statement = f"A {mode} protocol improves toy task quality over the default."
                claim = f"mode={mode} yields higher graded quality than mode=direct at alpha=0.5."
            hyp = Hypothesis(
                statement=statement,
                claim=claim,
                rationale="Seed baseline.",
                tags=["seed", mode],
            )
            plan = ExperimentPlan(
                hypothesis_id=hyp.hypothesis_id,
                domain=self.domain_id,
                params={"alpha": 0.5, "rounds": 2, "mode": mode, "verbose": False},
                metrics=["quality", "cost", "probe_accuracy"],
                baselines=["mode=direct"],
                seed=7,
            )
            seeds.append(Candidate(hypothesis=hyp, plan=plan, origin="seed"))
        return seeds


def build() -> FakeToyDomain:
    return FakeToyDomain()
