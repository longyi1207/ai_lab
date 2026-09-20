"""Search engine: the single writer of the archive.

Only the daemon orchestrator drives this, so MAP/novelty updates never race. Workers
produce results on the filesystem; the engine ingests them.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any

from ..domain import DomainPack, validate_metrics
from ..fs_layout import Workspace
from ..schema import Candidate, EliteRecord, Metrics, SearchConfig
from .map_elites import MapElites
from .mutate import FakeMutator, MutationFailed, Mutator, pick_op
from .novelty import NoveltyArchive
from .select import ParentSelector


@dataclass
class IngestOutcome:
    elite: EliteRecord
    inserted: bool
    novel: bool
    cell: tuple[int, ...]


@dataclass
class ProposalStats:
    requested: int = 0
    produced: int = 0
    duplicates: int = 0
    failures: int = 0
    ops: dict[str, int] = field(default_factory=dict)


class SearchEngine:
    def __init__(
        self,
        workspace: Workspace,
        domain: DomainPack,
        config: SearchConfig,
        *,
        mutator: Mutator | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.ws = workspace
        self.domain = domain
        self.config = config
        self.mutator: Mutator = mutator or FakeMutator()
        self.rng = rng or random.Random()
        self.archive = MapElites.load(self.ws.map_path, domain.axes())
        self.novelty = NoveltyArchive.load(
            self.ws.novelty_path, k=config.novelty_k, max_size=config.novelty_max_size
        )
        self._fingerprints: set[str] = set()
        self._load_fingerprints()

    # ---- state ----
    def _load_fingerprints(self) -> None:
        for path in self.ws.candidates_dir.glob("*.json"):
            try:
                cand = Candidate.model_validate_json(path.read_text())
            except Exception:  # noqa: BLE001 - ignore partial/foreign files
                continue
            self._fingerprints.add(cand.fingerprint())

    def save(self) -> None:
        self.archive.save(self.ws.map_path)
        self.novelty.save(self.ws.novelty_path)

    def register(self, candidate: Candidate) -> None:
        """Record an externally authored candidate (Phase-1 spec, human pin) for dedupe."""
        self._fingerprints.add(candidate.fingerprint())

    @property
    def generation(self) -> int:
        return max((r.generation for r in self.archive.cells.values()), default=0)

    # ---- population ----
    def seed(self) -> list[Candidate]:
        """Write the domain's baseline candidates (idempotent by fingerprint)."""
        out: list[Candidate] = []
        for candidate in self.domain.seed_candidates():
            self.domain.validate_plan(candidate.plan)
            fp = candidate.fingerprint()
            if fp in self._fingerprints:
                continue
            self._fingerprints.add(fp)
            self.ws.write_candidate(candidate)
            out.append(candidate)
        return out

    def propose(self, n: int) -> tuple[list[Candidate], ProposalStats]:
        stats = ProposalStats(requested=n)
        selector = ParentSelector(self.archive, self.novelty, self.ws.read_candidate, self.config)
        produced: list[Candidate] = []
        # Bounded attempts: duplicates and rejected mutations must not spin the loop.
        for _ in range(max(n * 6, n + 4)):
            if len(produced) >= n:
                break
            want_two = self.rng.random() < self.config.mutation_ops.get("crossover", 0.0)
            parents = selector.select(self.rng, 2 if want_two else 1)
            if not parents:
                break
            op = pick_op(self.rng, self.config.mutation_ops, n_parents=len(parents))
            try:
                child = self.mutator.mutate(
                    op,
                    parents,
                    domain=self.domain,
                    rng=self.rng,
                    context={"archive_summary": self.summary(), "constraints": {}},
                )
            except (MutationFailed, ValueError):
                stats.failures += 1
                continue
            fp = child.fingerprint()
            if fp in self._fingerprints:
                stats.duplicates += 1
                continue
            self._fingerprints.add(fp)
            self.ws.write_candidate(child)
            produced.append(child)
            stats.ops[op] = stats.ops.get(op, 0) + 1
        stats.produced = len(produced)
        return produced, stats

    # ---- evaluation feedback ----
    def ingest(
        self,
        candidate: Candidate,
        metrics: Metrics,
        *,
        job_id: str | None = None,
        results_ref: str | None = None,
        writeup_ref: str | None = None,
    ) -> IngestOutcome:
        validate_metrics(self.domain, metrics)
        cell = self.archive.cell_for(metrics.descriptor)
        record = EliteRecord(
            candidate=candidate,
            metrics=metrics,
            cell=cell,
            fitness=metrics.fitness,
            job_id=job_id,
            generation=candidate.generation,
            results_ref=results_ref,
            writeup_ref=writeup_ref,
            lineage=list(candidate.hypothesis.parent_ids),
        )
        inserted = self.archive.insert(record)
        novel = (
            self.novelty.consider(
                candidate.candidate_id,
                metrics.behavior,
                fitness=metrics.fitness,
                generation=candidate.generation,
            )
            is not None
        )
        if inserted:
            self._write_elite(record)
        self.save()
        return IngestOutcome(elite=record, inserted=inserted, novel=novel, cell=cell)

    def _write_elite(self, record: EliteRecord) -> None:
        elite_dir = self.ws.elites_dir / record.elite_id
        self.ws.write_json(elite_dir / "elite.json", json.loads(record.model_dump_json()))

    # ---- views ----
    def summary(self) -> dict[str, Any]:
        best = self.archive.best()
        return {
            "domain": self.domain.domain_id,
            "cells_filled": len(self.archive.cells),
            "cells_total": self.archive.total_cells,
            "occupancy": round(self.archive.occupancy, 4),
            "generation": self.generation,
            "novelty_size": len(self.novelty),
            "novelty_mean_distance": round(self.novelty.mean_pairwise_distance(), 4),
            "best": None
            if best is None
            else {
                "elite_id": best.elite_id,
                "fitness": best.fitness,
                "cell": list(best.cell),
                "claim": best.candidate.hypothesis.claim,
                "params": best.candidate.plan.params,
                "flags": best.metrics.verification_flags,
            },
        }

    def top_elites(self, n: int = 5) -> list[dict[str, Any]]:
        return [
            {
                "elite_id": r.elite_id,
                "cell": list(r.cell),
                "fitness": r.fitness,
                "generation": r.generation,
                "pinned": r.pinned,
                "statement": r.candidate.hypothesis.statement,
                "params": r.candidate.plan.params,
                "values": r.metrics.values,
                "flags": r.metrics.verification_flags,
                "writeup_ref": r.writeup_ref,
            }
            for r in self.archive.elites()[:n]
        ]
