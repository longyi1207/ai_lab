"""Rebuild the environment state at a branch point by re-running the recorded commands.

A language model's "state" is just its context, so it can be reset by re-sending the prefix. An
agent's environment also has state: files it created, the device's authentication phase, tokens
a service issued. To branch at step ``k`` we start a fresh container and re-execute every shell
command the agent ran before step ``k``, in order.

This only works if the environment is deterministic enough. ``replay_prefix`` therefore compares
each replayed output with the recorded one. Values that legitimately change between containers
(random nonces, timestamps, container ids, PIDs) are masked before comparing. A branch point is
usable only if every output matches after masking; otherwise the rebuilt context would describe
a world the container is not in, and the continuation would be meaningless.

The continuation always sees the *replayed* outputs, so its context matches its container.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .sandbox import DockerSandbox
from .tasks.base import Cell, Task
from .transcript import Entry, Walk, walk

_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
_MASKS = [
    # curl's progress meter (written to stderr when -s is not given): speeds and timings vary.
    (re.compile(r"(?m)^.*--:--:--.*$"), "<CURL_PROGRESS>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?"), "<TIME>"),
    # HTTP Date headers: "Mon, 21 Sep 2026 23:47:24 GMT"
    (re.compile(r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), \d{1,2} " + _MONTH + r" \d{4} \d{2}:\d{2}:\d{2} GMT"), "<TIME>"),
    # `ls -l` dates: "Sep 21 23:47" or "May  9  2026"
    (re.compile(_MONTH + r" +\d{1,2} +(?:\d{1,2}:\d{2}|\d{4})"), "<TIME>"),
    (re.compile(r"[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}"), "<TOKEN>"),       # signed tokens
    (re.compile(r"\b[0-9a-f]{8,}\b"), "<HEX>"),                                  # nonces, ids
    (re.compile(r"\b\d+(?:\.\d+)?[kMG]\b"), "<RATE>"),                           # curl transfer speed
    (re.compile(r"\b\d+\.\d{3,}\b"), "<NUM>"),                                   # float timestamps
    (re.compile(r"\b\d{4,}\b"), "<NUM>"),                                        # epochs, pids, sizes
    (re.compile(r"[ \t]+"), " "),
]


def normalize_output(text: str) -> str:
    """Mask values that legitimately differ between two containers running the same commands."""
    s = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    s = "\n".join(line.rstrip() for line in s.strip().splitlines())
    for pattern, repl in _MASKS:
        s = pattern.sub(repl, s)
    return s


@dataclass
class ReplayResult:
    walk: Walk
    n_bash: int = 0
    n_exact: int = 0
    n_masked: int = 0
    mismatches: list[dict[str, str]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.n_masked == self.n_bash and not self.walk.ended

    @property
    def messages(self) -> list[dict[str, Any]]:
        return self.walk.messages

    def stats(self) -> dict[str, Any]:
        return {"ok": self.ok, "n_bash": self.n_bash, "n_exact": self.n_exact, "n_masked": self.n_masked,
                "ended_in_prefix": self.walk.ended, "mismatches": self.mismatches[:3]}


def replay_prefix(task: Task, sb: DockerSandbox, cell: Cell, prefix: list[Entry]) -> ReplayResult:
    """Prepare the container, re-run the prefix's commands, and report how faithful it was."""
    task.prepare(sb, cell)
    result = ReplayResult(walk=Walk(messages=[]))

    def run(cmd: str, recorded: str) -> str:
        out = task.run_bash(sb, cmd)
        result.n_bash += 1
        if out.strip() == recorded.strip():
            result.n_exact += 1
            result.n_masked += 1
        elif normalize_output(out) == normalize_output(recorded):
            result.n_masked += 1
        elif len(result.mismatches) < 10:
            result.mismatches.append({"cmd": cmd[:300], "recorded": recorded[:2000], "replayed": out[:2000]})
        return out

    result.walk = walk(task, cell, prefix, output_fn=run)
    return result
