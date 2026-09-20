"""Novelty archive — exploration memory that does not require high fitness.

Behavior vectors come from the domain pack (`Metrics.behavior`), not prompt embeddings
(DESIGN §8).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NoveltyEntry:
    candidate_id: str
    behavior: list[float]
    fitness: float = 0.0
    novelty: float = 0.0
    generation: int = 0
    meta: dict = field(default_factory=dict)


def cosine_distance(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("behavior vectors must have equal length")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        # Zero vector has no direction; treat identical zeros as distance 0, else max.
        return 0.0 if na == nb else 1.0
    return 1.0 - max(-1.0, min(1.0, dot / (na * nb)))


class NoveltyArchive:
    def __init__(self, k: int = 15, max_size: int = 200) -> None:
        self.k = max(1, k)
        self.max_size = max_size
        self.entries: list[NoveltyEntry] = []

    def __len__(self) -> int:
        return len(self.entries)

    def novelty(self, behavior: list[float]) -> float:
        """Mean distance to k nearest neighbors; 1.0 (maximal) for an empty archive."""
        if not self.entries:
            return 1.0
        dists = sorted(cosine_distance(behavior, e.behavior) for e in self.entries)
        near = dists[: self.k]
        return sum(near) / len(near)

    def consider(
        self, candidate_id: str, behavior: list[float], *, fitness: float = 0.0, generation: int = 0
    ) -> NoveltyEntry | None:
        """Admit while under capacity; afterwards replace the least novel incumbent."""
        if not behavior:
            return None
        score = self.novelty(behavior)
        entry = NoveltyEntry(
            candidate_id=candidate_id,
            behavior=list(behavior),
            fitness=fitness,
            novelty=score,
            generation=generation,
        )
        if len(self.entries) < self.max_size:
            self.entries.append(entry)
            return entry
        self._rescore()
        weakest = min(self.entries, key=lambda e: e.novelty)
        if score <= weakest.novelty:
            return None
        self.entries.remove(weakest)
        self.entries.append(entry)
        return entry

    def _rescore(self) -> None:
        for e in self.entries:
            others = [o for o in self.entries if o is not e]
            if not others:
                e.novelty = 1.0
                continue
            dists = sorted(cosine_distance(e.behavior, o.behavior) for o in others)
            near = dists[: self.k]
            e.novelty = sum(near) / len(near)

    def most_novel(self, n: int = 5) -> list[NoveltyEntry]:
        self._rescore()
        return sorted(self.entries, key=lambda e: e.novelty, reverse=True)[:n]

    def mean_pairwise_distance(self) -> float:
        if len(self.entries) < 2:
            return 0.0
        total = 0.0
        pairs = 0
        for i, a in enumerate(self.entries):
            for b in self.entries[i + 1 :]:
                total += cosine_distance(a.behavior, b.behavior)
                pairs += 1
        return total / pairs

    # ---- persistence ----
    def save(self, path: Path) -> None:
        from ..fs_layout import _atomic_write

        lines = [
            json.dumps(
                {
                    "candidate_id": e.candidate_id,
                    "behavior": e.behavior,
                    "fitness": e.fitness,
                    "novelty": e.novelty,
                    "generation": e.generation,
                    "meta": e.meta,
                }
            )
            for e in self.entries
        ]
        _atomic_write(path, "\n".join(lines) + ("\n" if lines else ""))

    @classmethod
    def load(cls, path: Path, k: int = 15, max_size: int = 200) -> NoveltyArchive:
        archive = cls(k=k, max_size=max_size)
        if path.exists():
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                archive.entries.append(
                    NoveltyEntry(
                        candidate_id=payload["candidate_id"],
                        behavior=payload["behavior"],
                        fitness=payload.get("fitness", 0.0),
                        novelty=payload.get("novelty", 0.0),
                        generation=payload.get("generation", 0),
                        meta=payload.get("meta", {}),
                    )
                )
        return archive
