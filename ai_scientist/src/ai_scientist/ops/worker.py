"""Experiment worker process entry: own fault domain, one job via ExperimentAgent."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .heartbeat import Heartbeat
from .state import StateStore

__all__ = ["Heartbeat", "main", "run_job"]


def run_job(
    project: str | Path,
    job_id: str,
    *,
    worker_id: str | None = None,
    heartbeat: bool = True,
    store: StateStore | None = None,
) -> int:
    """Execute one job via the experiment agent. Returns process-style exit code."""
    from .experiment_agent import ExperimentAgent

    return ExperimentAgent(
        project,
        job_id,
        worker_id=worker_id,
        heartbeat=heartbeat,
        store=store,
    ).run()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ai_scientist experiment worker")
    parser.add_argument("--project", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--worker-id", default=None)
    args = parser.parse_args(argv)
    return run_job(args.project, args.job_id, worker_id=args.worker_id)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
