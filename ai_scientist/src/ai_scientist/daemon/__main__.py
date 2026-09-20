"""`python -m ai_scientist.daemon --project <dir>` — detached daemon entry point."""

from __future__ import annotations

import argparse
import sys

from .server import Daemon


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ai_scientist daemon")
    parser.add_argument("--project", required=True)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args(argv)

    daemon = Daemon(args.project, seed=args.seed)
    info = daemon.start()
    print(f"daemon up pid={info['pid']} control={info['host']}:{info['port']}", flush=True)
    daemon.serve_forever()
    return 0


if __name__ == "__main__":  # pragma: no cover - process entry point
    sys.exit(main())
