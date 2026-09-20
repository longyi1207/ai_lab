"""MAP-Elites archive over `(hypothesis, plan)` elites.

Descriptor axes come from the domain pack; binning lives here so it is testable and
uniform across domains. Pinned elites are immortal (human taste injection, DESIGN §0/12).
"""

from __future__ import annotations

import json
from pathlib import Path

from ..schema import Axis, EliteRecord


class MapElites:
    def __init__(self, axes: list[Axis]) -> None:
        if not axes:
            raise ValueError("MAP-Elites needs at least one axis")
        self.axes = axes
        self.cells: dict[tuple[int, ...], EliteRecord] = {}
        self.history: list[dict] = []

    # ---- geometry ----
    @property
    def total_cells(self) -> int:
        n = 1
        for axis in self.axes:
            n *= axis.bins
        return n

    @property
    def occupancy(self) -> float:
        return len(self.cells) / self.total_cells

    def cell_for(self, descriptor: dict[str, float]) -> tuple[int, ...]:
        missing = [a.name for a in self.axes if a.name not in descriptor]
        if missing:
            raise KeyError(f"descriptor missing axes: {missing}")
        return tuple(axis.bin_for(float(descriptor[axis.name])) for axis in self.axes)

    def neighbors(self, cell: tuple[int, ...]) -> list[tuple[int, ...]]:
        """Axis-aligned neighbors inside bounds (used for curiosity bias)."""
        out: list[tuple[int, ...]] = []
        for i, axis in enumerate(self.axes):
            for delta in (-1, 1):
                idx = cell[i] + delta
                if 0 <= idx < axis.bins:
                    out.append(cell[:i] + (idx,) + cell[i + 1 :])
        return out

    def empty_neighbor_count(self, cell: tuple[int, ...]) -> int:
        return sum(1 for n in self.neighbors(cell) if n not in self.cells)

    # ---- updates ----
    def insert(self, record: EliteRecord) -> bool:
        """Standard MAP-Elites replacement: occupy empty cell, or beat the incumbent."""
        cell = record.cell
        incumbent = self.cells.get(cell)
        if incumbent is not None:
            if incumbent.pinned or record.fitness <= incumbent.fitness:
                return False
        self.cells[cell] = record
        self.history.append(
            {
                "cell": list(cell),
                "elite_id": record.elite_id,
                "candidate_id": record.candidate.candidate_id,
                "fitness": record.fitness,
                "generation": record.generation,
                "replaced": incumbent.elite_id if incumbent else None,
            }
        )
        return True

    def pin(self, elite_id: str, pinned: bool = True) -> bool:
        for cell, record in self.cells.items():
            if record.elite_id == elite_id:
                self.cells[cell] = record.model_copy(update={"pinned": pinned})
                return True
        return False

    def remove(self, elite_id: str) -> bool:
        for cell, record in list(self.cells.items()):
            if record.elite_id == elite_id:
                del self.cells[cell]
                return True
        return False

    # ---- views ----
    def elites(self) -> list[EliteRecord]:
        return sorted(self.cells.values(), key=lambda r: r.fitness, reverse=True)

    def best(self) -> EliteRecord | None:
        elites = self.elites()
        return elites[0] if elites else None

    # ---- persistence ----
    def to_dict(self) -> dict:
        return {
            "axes": [a.model_dump() for a in self.axes],
            "cells": [
                {"cell": list(cell), "record": json.loads(rec.model_dump_json())}
                for cell, rec in sorted(self.cells.items())
            ],
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> MapElites:
        archive = cls([Axis.model_validate(a) for a in payload["axes"]])
        for entry in payload.get("cells", []):
            archive.cells[tuple(entry["cell"])] = EliteRecord.model_validate(entry["record"])
        archive.history = payload.get("history", [])
        return archive

    def save(self, path: Path) -> None:
        from ..fs_layout import _atomic_write

        _atomic_write(path, json.dumps(self.to_dict(), indent=2, default=str))

    @classmethod
    def load(cls, path: Path, axes: list[Axis]) -> MapElites:
        if not path.exists():
            return cls(axes)
        archive = cls.from_dict(json.loads(path.read_text()))
        if [a.model_dump() for a in archive.axes] != [a.model_dump() for a in axes]:
            raise ValueError(
                "archive axes differ from domain axes; start a new project or migrate the archive"
            )
        return archive
