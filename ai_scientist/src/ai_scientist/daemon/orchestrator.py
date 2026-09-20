"""Orchestrator: epistemic state + the only writer of the archive.

Each tick ingests finished trials, then tops the queue up from search. Budget and
generation caps are enforced here, so a runaway loop stops spending instead of the human
noticing later.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any

from ..domain import load_domain
from ..fs_layout import Workspace
from ..llm import get_llm
from ..ops.state import StateStore
from ..schema import Candidate, Job, Metrics
from ..search import FakeMutator, LLMMutator, SearchEngine
from ..skills_loader import SkillRegistry


@dataclass
class OrchestratorTick:
    ingested: list[str] = field(default_factory=list)
    inserted: list[str] = field(default_factory=list)
    enqueued: list[str] = field(default_factory=list)
    skipped_reason: str | None = None

    @property
    def acted(self) -> bool:
        return bool(self.ingested or self.enqueued)


class Orchestrator:
    def __init__(
        self,
        workspace: Workspace,
        store: StateStore,
        *,
        seed: int | None = None,
        engine: SearchEngine | None = None,
    ) -> None:
        self.ws = workspace
        self.store = store
        self.config = workspace.read_config()
        self.metadata = workspace.read_metadata()
        self.domain = load_domain(self.config.domain)
        self.engine = engine or SearchEngine(
            workspace,
            self.domain,
            self.config.search,
            mutator=self._build_mutator(),
            rng=random.Random(seed if seed is not None else 0),
        )

    def _build_mutator(self):
        if self.config.search.mutator == "llm":
            return LLMMutator(get_llm(), SkillRegistry().load())
        return FakeMutator()

    # ---- lifecycle ----
    def bootstrap(self) -> list[str]:
        """Enqueue the Phase-1 spec (if any) plus domain seed candidates, once."""
        if self.store.get_runtime("bootstrapped", False):
            return []
        job_ids: list[str] = []
        spec_candidate = self._phase1_candidate()
        if spec_candidate is not None:
            self.ws.write_candidate(spec_candidate)
            self.engine.register(spec_candidate)
            job_ids.append(self._enqueue(spec_candidate, priority=2.0))
        job_ids += [self._enqueue(c, priority=1.0) for c in self.engine.seed()]
        self.store.set_runtime("bootstrapped", True)
        self.store.add_event(
            "bootstrapped", {"jobs": job_ids, "from_phase1_spec": spec_candidate is not None}
        )
        return job_ids

    def _phase1_candidate(self) -> Candidate | None:
        """The Phase-1 `experiment_spec.yaml`, if it exists and the domain accepts it."""
        from ..phase1 import read_spec_candidate

        try:
            return read_spec_candidate(self.ws, self.domain)
        except Exception as exc:  # noqa: BLE001 - a bad spec must not block seeds
            self.store.add_event("phase1_spec_rejected", {"error": f"{type(exc).__name__}: {exc}"})
            return None

    def _enqueue(self, candidate: Candidate, *, priority: float = 0.0) -> str:
        job = Job(
            candidate_id=candidate.candidate_id,
            priority=priority,
            resources=candidate.plan.resources,
        )
        self.store.enqueue(job)
        self.ws.append_audit(
            "enqueue",
            {
                "job_id": job.job_id,
                "candidate_id": candidate.candidate_id,
                "origin": candidate.origin,
            },
        )
        return job.job_id

    # ---- budget / caps ----
    def budget_exceeded(self) -> bool:
        cap = self.metadata.budget.max_usd
        if cap is None:
            return False
        return self.store.total_spend()["usd"] >= cap

    def generation_cap_reached(self) -> bool:
        cap = self.config.search.max_generations
        return cap is not None and self.engine.generation >= cap

    # ---- tick ----
    def ingest_pending(self) -> OrchestratorTick:
        """Fold finished trials into the archive without proposing new work."""
        result = OrchestratorTick()
        for job in self.store.pending_ingest():
            self._ingest_job(job, result)
        return result

    def tick(self) -> OrchestratorTick:
        result = self.ingest_pending()

        if self.budget_exceeded():
            result.skipped_reason = "budget_exceeded"
            if not self.store.get_runtime("budget_alerted", False):
                self.store.set_runtime("budget_alerted", True)
                self.store.set_runtime("paused", True)
                self.store.add_event("budget_exceeded", self.store.total_spend())
            return result
        if self.generation_cap_reached():
            result.skipped_reason = "generation_cap"
            return result

        counts = self.store.counts_by_status()
        job_budget = self.store.get_runtime("job_budget", None)
        if job_budget is not None and sum(counts.values()) >= int(job_budget):
            result.skipped_reason = "job_budget"
            return result

        inflight = counts.get("queued", 0) + counts.get("running", 0)
        room = self.config.search.target_inflight - inflight
        if room <= 0:
            result.skipped_reason = "queue_full"
            return result

        want = min(room, self.config.search.offspring_per_tick)
        children, stats = self.engine.propose(want)
        for child in children:
            result.enqueued.append(self._enqueue(child))
        if stats.produced == 0 and stats.requested > 0:
            self.store.add_event(
                "proposal_empty",
                {"duplicates": stats.duplicates, "failures": stats.failures},
            )
        return result

    def _ingest_job(self, job: Job, result: OrchestratorTick) -> None:
        payload_path = self.ws.job_dir(job.job_id) / "result.json"
        try:
            if job.status == "failed" or not payload_path.exists():
                self.store.mark_ingested(job.job_id)
                result.ingested.append(job.job_id)
                return
            payload: dict[str, Any] = json.loads(payload_path.read_text())
            metrics_payload = payload.get("metrics")
            if not metrics_payload:
                self.store.mark_ingested(job.job_id)
                result.ingested.append(job.job_id)
                return
            candidate = self.ws.read_candidate(job.candidate_id)
            metrics = Metrics.model_validate(metrics_payload)
            outcome = self.engine.ingest(
                candidate,
                metrics,
                job_id=job.job_id,
                results_ref=f"jobs/{job.job_id}/result.json",
                writeup_ref=payload.get("writeup_ref"),
            )
            self.store.mark_ingested(job.job_id)
            result.ingested.append(job.job_id)
            if outcome.inserted:
                result.inserted.append(outcome.elite.elite_id)
            self.store.add_event(
                "ingested",
                {
                    "job_id": job.job_id,
                    "cell": list(outcome.cell),
                    "fitness": metrics.fitness,
                    "inserted": outcome.inserted,
                    "novel": outcome.novel,
                    "flags": metrics.verification_flags,
                },
            )
        except Exception as exc:  # noqa: BLE001 - never let one bad payload stall ingest
            self.store.mark_ingested(job.job_id)
            self.store.add_event(
                "ingest_failed", {"job_id": job.job_id, "error": f"{type(exc).__name__}: {exc}"}
            )

    # ---- views ----
    def status(self) -> dict[str, Any]:
        counts = self.store.counts_by_status()
        return {
            "project": str(self.ws.root),
            "domain": self.config.domain,
            "paused": bool(self.store.get_runtime("paused", False)),
            "concurrency": int(self.store.get_runtime("concurrency", self.config.ops.concurrency)),
            "jobs": counts,
            "locks": self.store.held_locks(),
            "spend": self.store.total_spend(),
            "budget_usd": self.metadata.budget.max_usd,
            "search": self.engine.summary(),
            "top_elites": self.engine.top_elites(5),
        }
