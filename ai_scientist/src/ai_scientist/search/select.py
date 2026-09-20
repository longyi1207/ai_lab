"""Parent selection: coverage pressure, quality pressure, and novelty escape.

Weights come from `SearchConfig`; the uniform-cell strategy additionally biases toward
cells with empty neighbors so the frontier of the map gets pushed.
"""

from __future__ import annotations

import random
from collections.abc import Callable

from ..schema import Candidate, SearchConfig
from .map_elites import MapElites
from .novelty import NoveltyArchive

Lookup = Callable[[str], Candidate]


class ParentSelector:
    def __init__(
        self,
        archive: MapElites,
        novelty: NoveltyArchive,
        lookup: Lookup,
        config: SearchConfig,
    ) -> None:
        self.archive = archive
        self.novelty = novelty
        self.lookup = lookup
        self.config = config

    # ---- strategies ----
    def _uniform_cell(self, rng: random.Random) -> Candidate | None:
        if not self.archive.cells:
            return None
        cells = list(self.archive.cells)
        weights = [1.0 + self.archive.empty_neighbor_count(c) for c in cells]
        cell = rng.choices(cells, weights=weights, k=1)[0]
        return self.archive.cells[cell].candidate

    def _fitness_weighted(self, rng: random.Random) -> Candidate | None:
        elites = self.archive.elites()
        if not elites:
            return None
        floor = min(e.fitness for e in elites)
        weights = [e.fitness - floor + 1e-6 for e in elites]
        return rng.choices(elites, weights=weights, k=1)[0].candidate

    def _from_novelty(self, rng: random.Random) -> Candidate | None:
        if not len(self.novelty):
            return None
        entries = self.novelty.most_novel(max(5, self.config.novelty_k))
        for entry in rng.sample(entries, k=len(entries)):
            try:
                return self.lookup(entry.candidate_id)
            except Exception:  # noqa: BLE001 - candidate file may be gone; try the next
                continue
        return None

    # ---- api ----
    def select(self, rng: random.Random, n_parents: int = 1) -> list[Candidate]:
        cfg = self.config
        strategies = [
            (self._uniform_cell, cfg.select_uniform_cell),
            (self._fitness_weighted, cfg.select_fitness_weighted),
            (self._from_novelty, cfg.select_novelty),
        ]
        chosen: list[Candidate] = []
        seen: set[str] = set()
        attempts = 0
        while len(chosen) < n_parents and attempts < 12:
            attempts += 1
            pool = [(fn, w) for fn, w in strategies if w > 0] or [(self._uniform_cell, 1.0)]
            fn = rng.choices([f for f, _ in pool], weights=[w for _, w in pool], k=1)[0]
            parent = fn(rng) or self._uniform_cell(rng) or self._fitness_weighted(rng)
            if parent is None:
                break
            if parent.candidate_id in seen and len(self.archive.cells) > 1:
                continue
            seen.add(parent.candidate_id)
            chosen.append(parent)
        return chosen
