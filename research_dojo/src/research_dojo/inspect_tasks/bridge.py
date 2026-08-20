"""Bidirectional Dojo <-> Inspect sync (pillar 6.3).

`export_run_to_inspect_log`: after a dojo run completes, materialize its
rollouts + judgments as a real inspect_ai EvalLog (.eval file) so
`inspect view` opens it exactly like a native `inspect eval` run — same
transcript-debugging muscle as industry_application/METR/inspect_practice/.
Best-effort by design: called from engine/run_engine.py._finalize inside a
try/except, since a logging-export bug must never fail the underlying run.

`import_inspect_scores`: pull scores from an `inspect eval` run of the
tom_smoke task back into dojo's `judgments` table, keyed by sample id, for a
single dashboard that doesn't care which path produced a rollout.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from research_dojo.artifacts.store import write_artifact
from research_dojo.config.settings import get_settings
from research_dojo.db.models import ArtifactKind
from research_dojo.db.repositories import JudgmentRepo, RolloutRepo, RunRepo, SampleRepo

logger = logging.getLogger("research_dojo.inspect_bridge")


def inspect_logs_dir() -> Path:
    d = get_settings().resolve_data_dir() / "inspect_logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def export_run_to_inspect_log(session: Session, run_id: str) -> Path | None:
    from inspect_ai.log import write_eval_log
    from inspect_ai.log._log import (
        EvalConfig,
        EvalDataset,
        EvalLog,
        EvalPlan,
        EvalResults,
        EvalSample,
        EvalSpec,
        EvalStats,
    )
    from inspect_ai.model import ModelOutput
    from inspect_ai.scorer import Score

    run = RunRepo.get(session, run_id)
    if run is None:
        return None
    rollouts = RolloutRepo.list_by_run(session, run_id)
    spec = run.spec_frozen_json or {}
    model_name = (spec.get("model") or {}).get("deployment", "unknown")

    samples = []
    for r in rollouts:
        sample = SampleRepo.get(session, r.sample_id)
        judgments = JudgmentRepo.list_for_rollout(session, r.id)
        scores = {}
        for j in judgments:
            scores[f"judge_v{j.judge_version or 'na'}"] = Score(
                value=j.score if j.score is not None else "NA",
                explanation=j.rationale,
                metadata={"label": j.label, **(j.flags_json or {})},
            )
        output = ModelOutput.from_content(model=model_name, content=r.completion or "")
        samples.append(EvalSample(
            id=r.sample_id,
            epoch=r.rollout_idx + 1,
            input=sample.prompt if sample else "",
            target=(sample.expected or "") if sample else "",
            output=output,
            scores=scores or None,
            metadata={"arm": r.arm, "dojo_rollout_id": r.id, "dojo_run_id": run_id, "status": r.status},
        ))

    status = "success" if run.status == "COMPLETE" else "started"
    eval_spec = EvalSpec(
        created=datetime.now(UTC).isoformat(),
        task=run.experiment_id,
        dataset=EvalDataset(name=spec.get("dataset")),
        model=f"openai/azure/{model_name}",
        config=EvalConfig(),
    )
    log = EvalLog(
        eval=eval_spec,
        plan=EvalPlan(name="dojo_export"),
        results=EvalResults(scores=[], total_samples=len(samples), completed_samples=len(samples)),
        stats=EvalStats(),
        samples=samples,
        status=status,
    )

    out_path = inspect_logs_dir() / f"{run_id}.eval"
    try:
        write_eval_log(log, str(out_path))
    except Exception:
        logger.exception("failed writing inspect .eval export for run %s (non-fatal)", run_id)
        return None

    write_artifact(session, run_id, f"inspect/{run_id}.eval", out_path.read_bytes(), ArtifactKind.INSPECT_LOG)
    logger.info("exported inspect log for run %s -> %s", run_id, out_path)
    return out_path


def import_inspect_scores(session: Session, run_id: str, eval_log_path: str | Path) -> int:
    """Read an `inspect eval` .eval log and write its scores into dojo's
    `judgments` table for rollouts sharing the same sample id + run_id.
    Returns the number of judgments imported."""
    from inspect_ai.log import read_eval_log

    log = read_eval_log(str(eval_log_path))
    rollouts_by_sample = {r.sample_id: r for r in RolloutRepo.list_by_run(session, run_id)}
    imported = 0
    for sample in log.samples or []:
        rollout = rollouts_by_sample.get(str(sample.id))
        if rollout is None or not sample.scores:
            continue
        for scorer_name, score in sample.scores.items():
            JudgmentRepo.create(
                session, rollout.id, judge_version=f"inspect:{scorer_name}",
                score=score.as_float() if hasattr(score, "as_float") else None,
                label=str(score.value), rationale=score.explanation,
                flags_json={"source": "inspect_import"}, raw_response=None,
            )
            imported += 1
    return imported
