"""Where each stage reads and writes its files, plus resumable JSONL helpers.

A run directory looks like this (``outputs/<run_name>/``)::

    episodes.jsonl        stage 1  recorded episodes, scored
    branch_points.jsonl   stage 2  where to branch, with a train/test split
    replay_check.jsonl    stage 3  can we rebuild the environment state at each branch point?
    rollouts.jsonl        stage 4+ every sampled continuation (base and tuned policies)
    pairs/train.jsonl     stage 5  preference pairs in the Azure DPO format
    pairs/val.jsonl
    finetune/state.json   stage 6  file ids, job id, fine-tuned model, deployment
    eval/summary.json     stage 7  base vs tuned on held-out branch points
    spend.jsonl           every billed API call (the budget reads this on start-up)
    REPORT.md             stage 8  human-readable summary of the whole run

Stages that call a model append one JSON line per finished unit of work, keyed by a stable id.
Re-running a stage skips keys that are already on disk, so an interrupted run resumes where it
stopped and never pays twice for the same rollout.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator


class RunStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    # file locations
    @property
    def episodes(self) -> Path:
        return self.root / "episodes.jsonl"

    @property
    def branch_points(self) -> Path:
        return self.root / "branch_points.jsonl"

    @property
    def replay_check(self) -> Path:
        return self.root / "replay_check.jsonl"

    @property
    def rollouts(self) -> Path:
        return self.root / "rollouts.jsonl"

    @property
    def pairs_dir(self) -> Path:
        return self.root / "pairs"

    @property
    def finetune_state(self) -> Path:
        return self.root / "finetune" / "state.json"

    @property
    def eval_summary(self) -> Path:
        return self.root / "eval" / "summary.json"

    @property
    def spend(self) -> Path:
        return self.root / "spend.jsonl"

    @property
    def report(self) -> Path:
        return self.root / "REPORT.md"

    # JSONL helpers
    def append(self, path: Path, record: dict[str, Any]) -> None:
        """Append one record; safe to call from several threads."""
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a") as f:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())

    @staticmethod
    def read(path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            return []
        out = []
        for line in path.read_text().splitlines():
            if line.strip():
                out.append(json.loads(line))
        return out

    @staticmethod
    def iter(path: Path) -> Iterator[dict[str, Any]]:
        if path.is_file():
            with path.open() as f:
                for line in f:
                    if line.strip():
                        yield json.loads(line)

    def done_keys(self, path: Path, key: Callable[[dict[str, Any]], str] = lambda r: r["key"]) -> set[str]:
        return {key(r) for r in self.iter(path)}

    def write_jsonl(self, path: Path, records: Iterable[dict[str, Any]]) -> int:
        """Replace a file atomically (write to a temp file, then rename)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        n = 0
        with tmp.open("w") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
                n += 1
        os.replace(tmp, path)
        return n

    def write_json(self, path: Path, obj: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
        os.replace(tmp, path)

    @staticmethod
    def read_json(path: Path, default: Any = None) -> Any:
        return json.loads(path.read_text()) if path.is_file() else default
