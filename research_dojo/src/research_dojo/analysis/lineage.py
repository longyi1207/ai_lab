"""`dojo lineage <run_id>` — text summary of spec_hash -> model deployment ->
dataset -> judge rubric version for one run.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from research_dojo.db.repositories import RunRepo


def lineage_summary(session: Session, run_id: str) -> str:
    run = RunRepo.get(session, run_id)
    if run is None:
        raise ValueError(f"run {run_id} not found")
    spec = run.spec_frozen_json
    model = spec.get("model", {})
    verification = spec.get("verification", {})
    judge = verification.get("judge") or {}
    lines = [
        f"lineage for run {run_id}",
        f"  spec_hash        = {spec.get('spec_hash')}",
        f"  experiment_id    = {spec.get('experiment_id')}",
        f"  git_commit       = {run.git_commit}",
        f"  python_version   = {run.python_version}",
        f"  package_version  = {run.package_version}",
        f"  model.provider   = {model.get('provider')}",
        f"  model.deployment = {model.get('deployment')}",
        f"  dataset          = {spec.get('dataset')}",
        f"  arms             = {spec.get('arms')}",
        f"  judge.rubric     = {judge.get('rubric', 'n/a (deterministic-only)')}",
        f"  judge.version    = {judge.get('version', 'n/a')}",
    ]
    return "\n".join(lines)
