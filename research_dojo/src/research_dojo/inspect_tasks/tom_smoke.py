"""Inspect AI task for the tom_smoke experiment (pillar 6.2). Reads the same
data/tom_smoke.jsonl the batch engine uses, so `dojo run --spec
specs/tom_smoke.yaml` and `dojo inspect run tom_smoke` are two lenses on one
dataset — batch harness for throughput, Inspect for transcript debugging.

    inspect eval src/research_dojo/inspect_tasks/tom_smoke.py --model openai/azure/<deployment>
    dojo inspect run tom_smoke --model azure/<deployment>   # thin wrapper, cli/main.py

Debugging: `inspect view --log-dir outputs/inspect_logs` opens the transcript
viewer — Model Call -> API tab shows exactly what was sent, same muscle as
industry_application/METR/inspect_practice/SAMPLE_EVAL_DEBUG.md walks through.
"""

from __future__ import annotations

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, json_dataset
from inspect_ai.scorer import includes, model_graded_qa
from inspect_ai.solver import generate

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "tom_smoke.jsonl"


def record_to_sample(record: dict) -> Sample:
    return Sample(
        id=record["id"],
        input=record["prompt"],
        target=record.get("expected") or "",
        metadata=record.get("metadata", {}),
    )


@task
def tom_smoke() -> Task:
    return Task(
        dataset=json_dataset(str(DATA_PATH), sample_fields=record_to_sample),
        solver=generate(),
        # deterministic substring check + model-graded judgment — mirrors
        # verify/pipeline.py's deterministic-then-judge combination.
        scorer=[includes(), model_graded_qa()],
    )
