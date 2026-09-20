#!/usr/bin/env python3
"""Lightweight mode: best-effort health check.

    python scripts/check_workers.py --project runs/demo

**This is not a watchdog.** It only acts while something is calling it. Unattended runs need
`sci serve` (V1), whose health loop runs on a timer in its own process and keeps working when
the model provider is down. See scripts/README.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_scientist.fs_layout import Workspace  # noqa: E402
from ai_scientist.ops.health import HealthMonitor  # noqa: E402
from ai_scientist.ops.state import StateStore  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True)
    parser.add_argument("--reconcile", action="store_true", help="Adopt/recover after a crash")
    args = parser.parse_args(argv)

    ws = Workspace(args.project)
    if not ws.initialized:
        print(f"not an ai_scientist project: {ws.root}", file=sys.stderr)
        return 2
    store = StateStore(ws.db_path)
    try:
        monitor = HealthMonitor(store, ws.read_config())
        report = monitor.reconcile_on_start() if args.reconcile else monitor.tick()
        print(
            json.dumps(
                {
                    "stale": report.stale,
                    "crashed": report.crashed,
                    "timed_out": report.timed_out,
                    "requeued": report.requeued,
                    "failed": report.failed,
                    "locks_released": report.locks_released,
                    "jobs": store.counts_by_status(),
                    "locks_held": store.held_locks(),
                },
                indent=2,
            )
        )
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
