"""Phase 1 driver: brief + docs → hypothesis, experiment spec, metadata.

The `phase1_intake` and `design_debate` skills hold the *policy*; this module holds the
mechanics: gather context, call the model, run the design-time adversary, check the exit
condition, and write artifacts.

Two properties worth preserving:

- **Questions are gated.** Only genuinely under-determined, shape-changing items are asked;
  everything else becomes a recorded assumption. `ready` is false while blocking questions
  remain, so a caller cannot skip the conversation by accident.
- **Credentials stay as names.** Nothing here ever writes a secret into an artifact.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from .domain import DomainPack, PlanInvalid, load_domain
from .fs_layout import Workspace
from .llm import LLMClient, get_llm
from .research import ResearchBundle, gather as gather_research
from .schema import Candidate, ExperimentPlan, Hypothesis
from .skills_loader import SkillRegistry

# Metadata the intake wants settled before Phase 2 (DESIGN §5.3).
METADATA_DIMENSIONS = (
    "budget",
    "time",
    "credentials",
    "audience",
    "style",
    "topic_fidelity",
    "extensibility",
    "knowledge_sources",
    "tools",
)


@dataclass
class IntakeDraft:
    hypothesis: Hypothesis
    plan: ExperimentPlan
    questions: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    metadata_updates: dict[str, Any] = field(default_factory=dict)
    critique: str = ""
    verdict: str = "unknown"
    model_used: str = "unavailable"
    notes: list[str] = field(default_factory=list)
    research: ResearchBundle | None = None

    @property
    def ready(self) -> bool:
        """Exit condition: nothing load-bearing is still open."""
        return not self.questions and self.verdict != "revise"

    def candidate(self) -> Candidate:
        return Candidate(hypothesis=self.hypothesis, plan=self.plan, origin="phase1")


class IntakeSession:
    def __init__(
        self,
        workspace: Workspace,
        *,
        llm: LLMClient | None = None,
        skills: SkillRegistry | None = None,
        domain: DomainPack | None = None,
        research: bool = True,
    ) -> None:
        self.ws = workspace
        self.config = workspace.read_config()
        self.metadata = workspace.read_metadata()
        self.domain = domain or load_domain(self.config.domain)
        self.llm = llm or get_llm()
        self.skills = skills or SkillRegistry().load()
        self.research_enabled = research

    # ---- context ----
    def read_documents(self, paths: list[str | Path]) -> str:
        chunks: list[str] = []
        for raw in paths:
            path = Path(raw)
            if not path.exists():
                chunks.append(f"### {path} (missing)")
                continue
            chunks.append(f"### {path.name}\n{path.read_text(errors='replace')[:6000]}")
        return "\n\n".join(chunks) if chunks else "_no documents supplied_"

    def _domain_summary(self) -> str:
        return json.dumps(
            {
                "domain": self.domain.domain_id,
                "axes": [a.name for a in self.domain.axes()],
                "param_space": [s.model_dump() for s in self.domain.param_space()],
            },
            indent=2,
        )

    def _auto_research(self, brief: str, documents_text: str) -> ResearchBundle:
        if not self.research_enabled:
            return ResearchBundle(skipped="research disabled by caller")
        return gather_research(
            brief,
            documents_text=documents_text,
            knowledge_sources=list(self.metadata.knowledge_sources),
        )

    # ---- drafting ----
    def draft(
        self,
        brief: str,
        *,
        documents: list[str | Path] | None = None,
        answers: dict[str, str] | None = None,
    ) -> IntakeDraft:
        seed = self.domain.seed_candidates()[0]
        known = json.loads(self.metadata.model_dump_json())
        known["answers_from_human"] = answers or {}
        documents_text = self.read_documents(documents or [])
        research = self._auto_research(brief, documents_text)
        # Persist research so Phase 2 / humans can audit what intake knew.
        research_path = self.ws.root / "intake" / "research_notes.md"
        self.ws.write_text(research_path, research.to_markdown())
        research_context = documents_text
        if research.notes or research.skipped:
            research_context = (
                f"{documents_text}\n\n## Auto-research\n\n{research.to_markdown()}"
            )

        draft = IntakeDraft(
            hypothesis=seed.hypothesis.model_copy(
                update={
                    "statement": brief.strip() or seed.hypothesis.statement,
                    "tags": ["phase1"],
                    "parent_ids": [],
                }
            ),
            plan=seed.plan.model_copy(update={"parent_ids": [], "generation": 0}),
            research=research,
        )
        if research.skipped:
            draft.notes.append(f"research: {research.skipped}")
        elif research.notes:
            draft.notes.append(f"research: fetched {len(research.notes)} source(s)")

        payload: dict[str, Any] | None = None
        try:
            from .agent import context_block, run_skilled

            out = run_skilled(
                "phase1_intake",
                "\n\n".join(
                    [
                        "Draft hypothesis, plan params, questions, assumptions, and metadata.",
                        context_block("brief", brief),
                        context_block("documents", research_context),
                        context_block("research_notes", research.to_dict()),
                        context_block("known_metadata", known),
                        context_block("domain_summary", json.loads(self._domain_summary())),
                    ]
                ),
                role=(
                    "You are the Phase-1 intake agent for ai_scientist. "
                    "Ask only shape-changing questions; never write secrets."
                ),
                llm=self.llm,
                skills=self.skills,
                expect_json=True,
                temperature=0.4,
            )
            candidate_payload = out.parsed
            if isinstance(candidate_payload, dict) and candidate_payload.get("claim"):
                payload = candidate_payload
                draft.model_used = out.model_used
        except Exception as exc:  # noqa: BLE001 - intake must still produce a usable draft
            draft.notes.append(f"intake model unavailable: {type(exc).__name__}: {exc}")

        if payload is None:
            draft.notes.append(
                "No usable model reply: drafted from the domain seed and the brief verbatim. "
                "Review the claim before running Phase 2."
            )
            draft.questions = self._default_questions(answers or {})
            draft.assumptions = [
                f"{dim}: inherited from metadata.yaml / defaults"
                for dim in METADATA_DIMENSIONS
                if dim not in (answers or {})
            ]
            return draft

        draft.hypothesis = draft.hypothesis.model_copy(
            update={
                "statement": str(payload.get("statement") or draft.hypothesis.statement),
                "claim": str(payload.get("claim")),
                "rationale": str(payload.get("rationale") or "") or None,
            }
        )
        params = payload.get("params")
        if isinstance(params, dict) and params:
            merged = {**draft.plan.params, **params}
            trial = draft.plan.model_copy(update={"params": merged})
            try:
                self.domain.validate_plan(trial)
                draft.plan = trial
            except PlanInvalid as exc:
                draft.notes.append(f"model params rejected by domain, kept seed plan: {exc}")
        draft.questions = [str(q) for q in (payload.get("questions") or []) if str(q).strip()]
        draft.assumptions = [str(a) for a in (payload.get("assumptions") or [])]
        meta_updates = payload.get("metadata")
        if isinstance(meta_updates, dict):
            draft.metadata_updates = _safe_metadata_updates(meta_updates)
        return draft

    def _default_questions(self, answers: dict[str, str]) -> list[str]:
        """Shape-changing items only — the rest can be assumed and recorded."""
        blocking = {
            "budget": "What dollar budget may this study spend?",
            "topic_fidelity": (
                "Must this stay exactly on the stated question, or is discovery welcome?"
            ),
            "audience": "Who reads the final report?",
        }
        return [text for key, text in blocking.items() if key not in answers]

    # ---- design-time adversary ----
    def critique(self, draft: IntakeDraft) -> IntakeDraft:
        try:
            from .agent import context_block, run_skilled

            out = run_skilled(
                "design_debate",
                "\n\n".join(
                    [
                        "Attack this draft study design before any compute is spent.",
                        context_block(
                            "hypothesis",
                            {
                                "statement": draft.hypothesis.statement,
                                "claim": draft.hypothesis.claim,
                            },
                        ),
                        context_block(
                            "plan",
                            {
                                "domain": draft.plan.domain,
                                "params": draft.plan.params,
                                "baselines": draft.plan.baselines,
                            },
                        ),
                        context_block("constraints", draft.metadata_updates or {}),
                    ]
                ),
                role=(
                    "You are the design-time debater for ai_scientist. "
                    "You are not the author's assistant. End with VERDICT: ready or VERDICT: revise."
                ),
                llm=self.llm,
                skills=self.skills,
                expect_json=False,
                temperature=0.5,
            )
            text = (out.text or "").strip()
            draft.critique = text
            lowered = text.lower()
            if "verdict: ready" in lowered:
                draft.verdict = "ready"
            elif "verdict: revise" in lowered:
                draft.verdict = "revise"
            else:
                draft.verdict = "unknown"
                draft.notes.append("design debate returned no explicit verdict")
        except Exception as exc:  # noqa: BLE001
            draft.critique = ""
            draft.verdict = "unknown"
            draft.notes.append(f"design debate unavailable: {type(exc).__name__}: {exc}")
        return draft

    # ---- artifacts ----
    def commit(
        self, draft: IntakeDraft, *, brief: str, answers: dict[str, str] | None = None
    ) -> dict[str, Path]:
        candidate = draft.candidate()
        self.domain.validate_plan(candidate.plan)

        hypothesis_md = (
            f"# Hypothesis — {self.metadata.project_id}\n\n"
            f"**Statement:** {candidate.hypothesis.statement}\n\n"
            f"**Claim (falsifiable):** {candidate.hypothesis.claim}\n\n"
            f"**Rationale:** {candidate.hypothesis.rationale or '_none recorded_'}\n\n"
            f"**Domain:** `{candidate.plan.domain}`\n\n"
            f"**Falsified if:** {candidate.plan.notes or '_not stated_'}\n"
        )
        self.ws.write_text(self.ws.hypothesis_path, hypothesis_md)

        spec = {
            "hypothesis": {
                "statement": candidate.hypothesis.statement,
                "claim": candidate.hypothesis.claim,
                "rationale": candidate.hypothesis.rationale,
                "tags": candidate.hypothesis.tags,
            },
            "plan": {
                "domain": candidate.plan.domain,
                "params": candidate.plan.params,
                "metrics": candidate.plan.metrics,
                "baselines": candidate.plan.baselines,
                "seed": candidate.plan.seed,
                "notes": candidate.plan.notes,
            },
        }
        self.ws.write_text(self.ws.spec_path, yaml.safe_dump(spec, sort_keys=False))

        metadata = self.metadata.model_copy(
            update={
                **draft.metadata_updates,
                "question": brief.strip() or self.metadata.question,
                "assumptions": sorted({*self.metadata.assumptions, *draft.assumptions}),
                "updated_at": datetime.now(UTC),
            }
        )
        self.ws.write_metadata(metadata)
        self.metadata = metadata

        log = [
            f"# Intake log — {datetime.now(UTC).isoformat()}",
            "",
            f"- model: `{draft.model_used}`",
            f"- ready: **{draft.ready}**  (verdict: {draft.verdict})",
            "",
            "## Brief",
            brief or "_empty_",
            "",
            "## Auto-research",
            (
                draft.research.to_markdown()
                if draft.research is not None
                else "_not run_"
            ),
            "",
            "## Answers supplied by human",
            json.dumps(answers or {}, indent=2),
            "",
            "## Open questions",
            *(f"- {q}" for q in draft.questions or ["_none_"]),
            "",
            "## Assumptions recorded (inferred, not asked)",
            *(f"- {a}" for a in draft.assumptions or ["_none_"]),
            "",
            "## Design-debate critique",
            draft.critique or "_unavailable_",
            "",
            "## Harness notes",
            *(f"- {n}" for n in draft.notes or ["_none_"]),
            "",
        ]
        existing = self.ws.intake_log_path.read_text() if self.ws.intake_log_path.exists() else ""
        self.ws.write_text(self.ws.intake_log_path, existing + "\n".join(log) + "\n")

        return {
            "hypothesis": self.ws.hypothesis_path,
            "spec": self.ws.spec_path,
            "metadata": self.ws.metadata_path,
            "intake_log": self.ws.intake_log_path,
        }


def _safe_metadata_updates(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept only known, non-secret metadata fields from a model reply."""
    allowed = {"audience", "style", "topic_fidelity", "extensible", "knowledge_sources", "tools"}
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key not in allowed:
            continue
        if key == "style" and value not in {"rigorous", "casual"}:
            continue
        if key == "topic_fidelity" and value not in {"stuck", "discovery", "mixed"}:
            continue
        out[key] = value
    return out


def read_spec_candidate(workspace: Workspace, domain: DomainPack) -> Candidate | None:
    """Load `experiment_spec.yaml` as a seed candidate for Phase 2, if present and valid."""
    if not workspace.spec_path.exists():
        return None
    payload = yaml.safe_load(workspace.spec_path.read_text()) or {}
    hypothesis_payload = payload.get("hypothesis") or {}
    plan_payload = payload.get("plan") or {}
    if not hypothesis_payload.get("claim") or not plan_payload.get("params"):
        return None
    hypothesis = Hypothesis(
        statement=str(hypothesis_payload.get("statement") or hypothesis_payload["claim"]),
        claim=str(hypothesis_payload["claim"]),
        rationale=hypothesis_payload.get("rationale"),
        tags=[str(t) for t in hypothesis_payload.get("tags", [])] + ["phase1_spec"],
    )
    plan = ExperimentPlan(
        hypothesis_id=hypothesis.hypothesis_id,
        domain=str(plan_payload.get("domain") or domain.domain_id),
        params=dict(plan_payload["params"]),
        metrics=[str(m) for m in plan_payload.get("metrics", [])],
        baselines=[str(b) for b in plan_payload.get("baselines", [])],
        seed=int(plan_payload.get("seed", 0) or 0),
        notes=plan_payload.get("notes"),
    )
    domain.validate_plan(plan)
    return Candidate(hypothesis=hypothesis, plan=plan, origin="phase1")


__all__ = ["METADATA_DIMENSIONS", "IntakeDraft", "IntakeSession", "read_spec_candidate"]
