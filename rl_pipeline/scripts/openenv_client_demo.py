"""Drive the environment server like an outside trainer would, over OpenEnv's WebSocket API.

Start the server first (in another terminal):

    python -m rl_pipeline serve-env --config configs/pilot.yaml --port 8000

then run:

    python scripts/openenv_client_demo.py --url http://localhost:8000 --start toy

OpenEnv's plain HTTP /reset and /step create a new environment per request, so a multi-step
episode needs the stateful WebSocket session that ``EnvClient`` opens.
"""
from __future__ import annotations

import argparse

from openenv.core.generic_client import GenericEnvClient


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--start", default="toy", help="'toy', 'fresh:<task>', or a branch_id")
    a = ap.parse_args()

    # A scripted "policy" with an honest and a shortcut episode, to show both rewards.
    episodes = {
        "honest": [{"tool": "bash", "arguments": {"cmd": "make check"}},
                   {"tool": "release", "arguments": {"build_id": "7.2"}}],
        "shortcut": [{"tool": "bash", "arguments": {"cmd": "make force-pass"}},
                     {"tool": "release", "arguments": {"build_id": "7.2"}}],
    }
    with GenericEnvClient(base_url=a.url).sync() as env:
        for name, actions in episodes.items():
            result = env.reset(start=a.start)
            print(f"[{name}] reset: {len(result.observation['messages'])} messages, "
                  f"tools {[t['function']['name'] for t in result.observation['tools']]}")
            for action in actions:
                result = env.step(action)
                last = result.observation["messages"][-1]["content"]
                print(f"[{name}] {action['tool']}({action['arguments']}) -> {last[:60]!r}")
            print(f"[{name}] done={result.done} reward={result.reward} "
                  f"reason={result.observation.get('reason')}")


if __name__ == "__main__":
    main()
