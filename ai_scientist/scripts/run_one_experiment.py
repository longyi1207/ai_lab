#!/usr/bin/env python3
"""Lightweight mode: run exactly one experiment, no daemon.

The host agent (Cursor, Claude Code, a shell loop) is the supervisor here. Use this when
portability matters more than unattended reliability; see scripts/README.md for the caveats.

By default it **drains the queue**: it runs the highest-priority job that search already
proposed. Pass `--params` or `--seed-index` to force a fresh candidate instead — otherwise a
host loop would pile up new work while the queued work never ran.

    python scripts/run_one_experiment.py --project runs/demo
    python scripts/run_one_experiment.py --project runs/demo --params '{"protocol":"debate"}'
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_scientist.daemon.orchestrator import Orchestrator  # noqa: E402
from ai_scientist.domain import load_domain  # noqa: E402
from ai_scientist.fs_layout import Workspace  # noqa: E402
from ai_scientist.ops.state import StateStore  # noqa: E402
from ai_scientist.ops.worker import run_job  # noqa: E402
from ai_scientist.schema import Job  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--candidate", default=None, help="Candidate id already on disk")
    parser.add_argument("--params", default=None, help="JSON params override (forces a new plan)")
    parser.add_argument(
        "--seed-index", type=int, default=None, help="Base a new plan on this domain seed"
    )
    args = parser.parse_args(argv)

    ws = Workspace(args.project)
    if not ws.initialized:
        print(f"not an ai_scientist project: {ws.root}", file=sys.stderr)
        return 2
    domain = load_domain(ws.read_config().domain)
    store = StateStore(ws.db_path)
    try:
        forcing_new = bool(args.candidate or args.params or args.seed_index is not None)
        queued = store.list_jobs("queued", limit=1)
        job: Job | None = None

        if not forcing_new and queued:
            job = queued[0]  # drain what search already proposed
        else:
            if args.candidate:
                candidate = ws.read_candidate(args.candidate)
            else:
                candidate = domain.seed_candidates()[args.seed_index or 0]
                if args.params:
                    candidate.plan.params.update(json.loads(args.params))
                domain.validate_plan(candidate.plan)
                ws.write_candidate(candidate)
            job = store.enqueue(
                Job(candidate_id=candidate.candidate_id, resources=candidate.plan.resources)
            )

        if not store.try_start(job.job_id, ["api:0"], "lightweight"):
            print(
                "could not take the api:0 lock or claim the job — is a daemon running?",
                file=sys.stderr,
            )
            return 1
        code = run_job(ws.root, job.job_id, worker_id="lightweight", store=store)
        store.release_locks(job.job_id)

        # fold the result into the archive so lightweight runs still accumulate
        ingested = Orchestrator(ws, store).ingest_pending()
        payload = json.loads((ws.job_dir(job.job_id) / "result.json").read_text())
        print(
            json.dumps(
                {
                    "job_id": job.job_id,
                    "source": "new_candidate" if forcing_new or not queued else "queue",
                    "exit_code": code,
                    "metrics": payload.get("metrics"),
                    "writeup": payload.get("writeup_ref"),
                    "ingested": ingested.ingested,
                    "inserted_elites": ingested.inserted,
                },
                indent=2,
            )
        )
        return code
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
