"""Variation operators over `(hypothesis, plan)`.

Two implementations share one interface: `FakeMutator` is deterministic and offline (used
by tests and the lightweight default), `LLMMutator` renders the `hypothesize` /
`plan_experiment` skills and falls back to the fake operator when a model returns
something unusable — a bad mutation must never stall the loop.
"""

from __future__ import annotations

import json
import random
from typing import Any, Protocol, runtime_checkable

from ..domain import DomainPack, ParamSpec, PlanInvalid
from ..llm import LLMClient
from ..schema import Candidate, ExperimentPlan, Hypothesis

OPS = ("sharpen_claim", "vary_params", "change_seed", "broaden_scope", "crossover")


class MutationFailed(RuntimeError):
    pass


@runtime_checkable
class Mutator(Protocol):
    name: str

    def mutate(
        self,
        op: str,
        parents: list[Candidate],
        *,
        domain: DomainPack,
        rng: random.Random,
        context: dict[str, Any] | None = None,
    ) -> Candidate: ...


def pick_op(rng: random.Random, weights: dict[str, float], *, n_parents: int) -> str:
    """Sample an operator, excluding crossover when only one parent is available."""
    items = [(op, w) for op, w in weights.items() if w > 0 and op in OPS]
    if n_parents < 2:
        items = [(op, w) for op, w in items if op != "crossover"]
    if not items:
        return "vary_params"
    total = sum(w for _, w in items)
    draw = rng.random() * total
    upto = 0.0
    for op, w in items:
        upto += w
        if draw <= upto:
            return op
    return items[-1][0]


def _jitter(spec: ParamSpec, value: Any, rng: random.Random) -> Any:
    if spec.kind == "float":
        span = (spec.high - spec.low) or 1.0  # type: ignore[operator]
        current = float(value) if isinstance(value, (int, float)) else (spec.low + spec.high) / 2
        proposed = current + rng.gauss(0, span * 0.2)
        return round(min(spec.high, max(spec.low, proposed)), 4)  # type: ignore[arg-type]
    if spec.kind == "int":
        current = int(value) if isinstance(value, (int, float)) else int(spec.low)  # type: ignore[arg-type]
        proposed = current + rng.choice([-2, -1, 1, 2])
        return int(min(spec.high, max(spec.low, proposed)))  # type: ignore[arg-type]
    if spec.kind == "choice":
        options = [c for c in (spec.choices or []) if c != value] or list(spec.choices or [])
        return rng.choice(options)
    return not bool(value)


def _child(
    parents: list[Candidate],
    *,
    statement: str,
    claim: str,
    rationale: str | None,
    tags: list[str],
    domain: DomainPack,
    params: dict[str, Any],
    seed: int,
    metrics: list[str],
    baselines: list[str],
    notes: str | None,
    origin: str,
) -> Candidate:
    generation = max((p.generation for p in parents), default=0) + 1
    hypothesis = Hypothesis(
        statement=statement,
        claim=claim,
        rationale=rationale,
        parent_ids=[p.hypothesis.hypothesis_id for p in parents],
        generation=generation,
        tags=tags,
    )
    plan = ExperimentPlan(
        hypothesis_id=hypothesis.hypothesis_id,
        domain=domain.domain_id,
        params=params,
        metrics=metrics,
        baselines=baselines,
        resources=parents[0].plan.resources.model_copy() if parents else None,  # type: ignore[arg-type]
        seed=seed,
        splits=dict(parents[0].plan.splits) if parents else {},
        parent_ids=[p.plan.plan_id for p in parents],
        generation=generation,
        notes=notes,
    )
    domain.validate_plan(plan)
    return Candidate(hypothesis=hypothesis, plan=plan, origin=origin)


class FakeMutator:
    """Deterministic structural variation — no model calls."""

    name = "fake"

    def mutate(
        self,
        op: str,
        parents: list[Candidate],
        *,
        domain: DomainPack,
        rng: random.Random,
        context: dict[str, Any] | None = None,
    ) -> Candidate:
        if not parents:
            raise MutationFailed("no parents supplied")
        primary = parents[0]
        specs = {s.name: s for s in domain.param_space()}
        params = dict(primary.plan.params)
        seed = primary.plan.seed
        statement = primary.hypothesis.statement
        claim = primary.hypothesis.claim
        rationale = f"{op} of {primary.hypothesis.hypothesis_id}"
        tags = [t for t in primary.hypothesis.tags if t != "seed"] + [op]

        if op == "sharpen_claim":
            fixed = {k: v for k, v in params.items() if k in specs and specs[k].kind != "float"}
            claim = f"{claim} Holding {sorted(fixed)} fixed."
        elif op == "change_seed":
            seed = rng.randrange(1, 10_000)
            claim = f"{claim} Replicated at seed {seed}."
        elif op == "broaden_scope":
            statement = f"Across settings: {statement}"
            for name, spec in specs.items():
                if spec.kind == "float":
                    params[name] = _jitter(spec, params.get(name), rng)
        elif op == "crossover" and len(parents) > 1:
            donor = parents[1]
            for name in list(params):
                if name in donor.plan.params and rng.random() < 0.5:
                    params[name] = donor.plan.params[name]
            statement = f"{statement} (crossed with {donor.hypothesis.hypothesis_id})"
        else:  # vary_params (and crossover fallback with a single parent)
            mutable = [n for n in params if n in specs] or list(specs)
            for name in rng.sample(mutable, k=max(1, len(mutable) // 2)):
                params[name] = _jitter(specs[name], params.get(name), rng)

        for name, spec in specs.items():
            if name not in params:
                params[name] = _jitter(spec, None, rng)

        return _child(
            parents,
            statement=statement,
            claim=claim,
            rationale=rationale,
            tags=tags,
            domain=domain,
            params=params,
            seed=seed,
            metrics=list(primary.plan.metrics),
            baselines=list(primary.plan.baselines),
            notes=primary.plan.notes,
            origin=f"mutation:{op}",
        )


class LLMMutator:
    """Skill-driven variation with a deterministic fallback."""

    name = "llm"

    def __init__(self, llm: LLMClient, skills: Any, *, temperature: float = 0.9) -> None:
        self.llm = llm
        self.skills = skills
        self.temperature = temperature
        self.fallback = FakeMutator()
        self.fallbacks_used = 0
        self.last_error: str | None = None

    def mutate(
        self,
        op: str,
        parents: list[Candidate],
        *,
        domain: DomainPack,
        rng: random.Random,
        context: dict[str, Any] | None = None,
    ) -> Candidate:
        if not parents:
            raise MutationFailed("no parents supplied")
        context = context or {}
        try:
            return self._mutate_via_skills(op, parents, domain=domain, context=context)
        except Exception as exc:  # noqa: BLE001 - any model/parse failure degrades to fake
            self.fallbacks_used += 1
            self.last_error = f"{type(exc).__name__}: {exc}"
            return self.fallback.mutate(op, parents, domain=domain, rng=rng, context=context)

    def _mutate_via_skills(
        self,
        op: str,
        parents: list[Candidate],
        *,
        domain: DomainPack,
        context: dict[str, Any],
    ) -> Candidate:
        from ..agent import context_block, run_skilled

        parents_payload = [
            {
                "hypothesis_id": p.hypothesis.hypothesis_id,
                "statement": p.hypothesis.statement,
                "claim": p.hypothesis.claim,
                "params": p.plan.params,
            }
            for p in parents
        ]
        hyp_out = run_skilled(
            "hypothesize",
            "\n\n".join(
                [
                    "Propose a mutated hypothesis for the evolutionary search.",
                    context_block("mutation_op", op),
                    context_block("parents", parents_payload),
                    context_block("archive_summary", context.get("archive_summary", {})),
                    context_block("domain_notes", context.get("domain_notes", domain.domain_id)),
                ]
            ),
            role=(
                "You are the hypothesize agent in ai_scientist evolutionary search. "
                "Propose a falsifiable claim; do not invent measured results."
            ),
            llm=self.llm,
            skills=self.skills,
            expect_json=True,
            temperature=self.temperature,
        )
        hyp_payload = hyp_out.parsed
        if not isinstance(hyp_payload, dict):
            raise MutationFailed("model returned no hypothesis JSON")
        statement = str(hyp_payload.get("statement") or "").strip()
        claim = str(hyp_payload.get("claim") or "").strip()
        if not statement or not claim:
            raise MutationFailed("model returned an empty hypothesis")

        plan_out = run_skilled(
            "plan_experiment",
            "\n\n".join(
                [
                    "Turn the hypothesis into a runnable plan.",
                    context_block("domain", domain.domain_id),
                    context_block("hypothesis", {"statement": statement, "claim": claim}),
                    context_block("parent_plan", parents[0].plan.params),
                    context_block(
                        "param_space", [s.model_dump() for s in domain.param_space()]
                    ),
                    context_block("constraints", context.get("constraints", {})),
                ]
            ),
            role=(
                "You are the plan_experiment agent for ai_scientist. "
                "Emit params only inside the domain parameter space."
            ),
            llm=self.llm,
            skills=self.skills,
            expect_json=True,
            temperature=self.temperature,
        )
        plan_payload = plan_out.parsed
        if not isinstance(plan_payload, dict):
            raise MutationFailed("model returned no plan JSON")
        params = plan_payload.get("params") or {}
        if not isinstance(params, dict) or not params:
            raise MutationFailed("model returned no params")

        try:
            return _child(
                parents,
                statement=statement,
                claim=claim,
                rationale=str(hyp_payload.get("rationale") or "") or None,
                tags=[str(t) for t in (hyp_payload.get("tags") or [])] + [op],
                domain=domain,
                params=params,
                seed=int(plan_payload.get("seed", parents[0].plan.seed)),
                metrics=[str(m) for m in (plan_payload.get("metrics") or parents[0].plan.metrics)],
                baselines=[
                    str(b) for b in (plan_payload.get("baselines") or parents[0].plan.baselines)
                ],
                notes=str(plan_payload.get("notes") or "") or None,
                origin=f"mutation:{op}",
            )
        except PlanInvalid as exc:
            raise MutationFailed(f"model plan rejected by domain: {exc}") from exc
