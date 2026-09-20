"""Workspace layout (SPEC §2).

`fs` is the shared agent workspace: specs, candidates, job dirs, archive, report.
The sqlite state db under `state/` is the ops source of truth for jobs/locks;
everything here is either agent-authored or a durable artifact.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ..schema import Candidate, EngineConfig, Metadata


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


class Workspace:
    """Paths + typed artifact IO for one project root."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

    # ---- paths ----
    @property
    def metadata_path(self) -> Path:
        return self.root / "metadata.yaml"

    @property
    def config_path(self) -> Path:
        return self.root / "config.yaml"

    @property
    def hypothesis_path(self) -> Path:
        return self.root / "hypothesis.md"

    @property
    def spec_path(self) -> Path:
        return self.root / "experiment_spec.yaml"

    @property
    def intake_log_path(self) -> Path:
        return self.root / "intake_log.md"

    @property
    def state_dir(self) -> Path:
        return self.root / "state"

    @property
    def db_path(self) -> Path:
        return self.state_dir / "daemon.sqlite"

    @property
    def daemon_info_path(self) -> Path:
        return self.state_dir / "daemon.json"

    @property
    def candidates_dir(self) -> Path:
        return self.root / "candidates"

    @property
    def jobs_dir(self) -> Path:
        return self.root / "jobs"

    @property
    def archive_dir(self) -> Path:
        return self.root / "archive"

    @property
    def map_path(self) -> Path:
        return self.archive_dir / "map.json"

    @property
    def novelty_path(self) -> Path:
        return self.archive_dir / "novelty.jsonl"

    @property
    def elites_dir(self) -> Path:
        return self.archive_dir / "elites"

    @property
    def report_path(self) -> Path:
        return self.root / "report" / "final_report.md"

    @property
    def audit_path(self) -> Path:
        return self.root / "audit" / "events.jsonl"

    def job_dir(self, job_id: str) -> Path:
        return self.jobs_dir / job_id

    def candidate_path(self, candidate_id: str) -> Path:
        return self.candidates_dir / f"{candidate_id}.json"

    # ---- lifecycle ----
    def init(self, *, metadata: Metadata, config: EngineConfig, exist_ok: bool = True) -> None:
        if self.metadata_path.exists() and not exist_ok:
            raise FileExistsError(f"workspace already initialized: {self.root}")
        for d in (
            self.state_dir,
            self.candidates_dir,
            self.jobs_dir,
            self.elites_dir,
            self.report_path.parent,
            self.audit_path.parent,
        ):
            d.mkdir(parents=True, exist_ok=True)
        if not self.metadata_path.exists():
            self.write_metadata(metadata)
        if not self.config_path.exists():
            self.write_config(config)

    @property
    def initialized(self) -> bool:
        return self.metadata_path.exists() and self.config_path.exists()

    # ---- typed artifacts ----
    def write_metadata(self, metadata: Metadata) -> None:
        _atomic_write(self.metadata_path, yaml.safe_dump(_jsonable(metadata), sort_keys=False))

    def read_metadata(self) -> Metadata:
        return Metadata.model_validate(yaml.safe_load(self.metadata_path.read_text()))

    def write_config(self, config: EngineConfig) -> None:
        _atomic_write(self.config_path, yaml.safe_dump(_jsonable(config), sort_keys=False))

    def read_config(self) -> EngineConfig:
        return EngineConfig.model_validate(yaml.safe_load(self.config_path.read_text()))

    def write_candidate(self, candidate: Candidate) -> Path:
        path = self.candidate_path(candidate.candidate_id)
        _atomic_write(path, candidate.model_dump_json(indent=2))
        return path

    def read_candidate(self, candidate_id: str) -> Candidate:
        return Candidate.model_validate_json(self.candidate_path(candidate_id).read_text())

    def write_json(self, path: Path, payload: Any) -> None:
        _atomic_write(path, json.dumps(payload, indent=2, default=str))

    def write_text(self, path: Path, text: str) -> None:
        _atomic_write(path, text)

    def append_audit(self, kind: str, payload: dict[str, Any]) -> None:
        line = json.dumps(
            {"ts": datetime.now(UTC).isoformat(), "kind": kind, **payload}, default=str
        )
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def _jsonable(model: Any) -> Any:
    return json.loads(model.model_dump_json())


__all__ = ["Workspace"]
