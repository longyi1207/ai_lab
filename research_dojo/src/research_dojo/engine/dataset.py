"""Load a dataset JSONL file into `samples` rows. Each line:
{"id": ..., "prompt": ..., "expected": <optional>, "metadata": {...}}
"""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from research_dojo.db.repositories import SampleRepo


def load_dataset(session: Session, dataset_path: str | Path, dataset_name: str | None = None) -> list[str]:
    path = Path(dataset_path)
    name = dataset_name or path.stem
    rows = []
    sample_ids = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rows.append({
                "id": obj["id"],
                "dataset_name": name,
                "prompt": obj["prompt"],
                "expected": obj.get("expected"),
                "metadata_json": obj.get("metadata", {}),
            })
            sample_ids.append(obj["id"])
    SampleRepo.bulk_upsert(session, rows)
    return sample_ids
