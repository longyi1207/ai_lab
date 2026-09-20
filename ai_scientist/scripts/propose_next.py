#!/usr/bin/env python3
"""Lightweight mode: one orchestrator tick — ingest finished trials, propose new ones.

    python scripts/propose_next.py --project runs/demo

Pair with run_one_experiment.py in a host-driven loop. In V1 the daemon does this
continuously; here the host decides when to step.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_scientist.daemon.orchestrator import Orchestrator  # noqa: E402
from ai_scientist.fs_layout import Workspace  # noqa: E402
from ai_scientist.ops.state import StateStore  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--bootstrap", action="store_true", help="Seed the population first")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    ws = Workspace(args.project)
    if not ws.initialized:
        print(f"not an ai_scientist project: {ws.root}", file=sys.stderr)
        return 2
    store = StateStore(ws.db_path)
    try:
        orchestrator = Orchestrator(ws, store, seed=args.seed)
        bootstrapped = orchestrator.bootstrap() if args.bootstrap else []
        tick = orchestrator.tick()
        print(
            json.dumps(
                {
                    "bootstrapped": bootstrapped,
                    "ingested": tick.ingested,
                    "inserted_elites": tick.inserted,
                    "enqueued": tick.enqueued,
                    "skipped": tick.skipped_reason,
                    "archive": orchestrator.engine.summary(),
                },
                indent=2,
                default=str,
            )
        )
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
