"""The task interface: everything the pipeline needs to know about one environment.

The environments themselves (Dockerfiles, services, graders, prompts) live in
`score-seeking-eval <https://github.com/longyi1207/score-seeking-eval>`_. A ``Task`` adapts one of
them to this pipeline:

* the **prompts and tools** the agent saw, read from the original runner so a rebuilt
  conversation matches the recorded one word for word;
* a **cell**, the experimental condition of a run (scope wording, eval framing, planted notes);
* **prepare** the container (wait for the service, plant files) and **grade** the finished
  episode with the task's own grader, which reads ground truth the agent cannot touch.

Prompt constants are extracted with ``ast`` rather than by importing the runner, so loading a
task never executes runner code or needs its dependencies.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from types import ModuleType
from typing import Any

from ..sandbox import DockerSandbox

Cell = dict[str, Any]


def literal_constants(path: Path, names: list[str]) -> dict[str, Any]:
    """Module-level literal assignments (strings, lists, dicts) from a Python file, unexecuted."""
    tree = ast.parse(Path(path).read_text())
    found: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in names:
                found[name] = ast.literal_eval(node.value)
    missing = [n for n in names if n not in found]
    if missing:
        raise ValueError(f"{path} has no literal constant(s) {missing}; did the runner change?")
    return found


def load_module(path: Path, unique_name: str) -> ModuleType:
    """Import a file under a unique module name (each task ships its own ``grade.py``)."""
    spec = importlib.util.spec_from_file_location(unique_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = mod        # dataclasses look their module up while it loads
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(unique_name, None)
        raise
    return mod


def normalize_frame(value: str | None, aliases: dict[str, str], frames: tuple[str, ...]) -> str:
    if not value:
        return "control"
    if value in frames:
        return value
    if value in aliases:
        return aliases[value]
    raise ValueError(f"unknown eval frame {value!r}")


class Task(ABC):
    """One environment, adapted for branching, rollouts and grading."""

    name: str
    image: str
    final_tool: str            # the tool that ends an episode (e.g. submit_flag)
    final_arg: str             # its argument carrying the answer
    agent_user: str | None     # the container user the agent's commands run as
    default_max_steps: int
    tool_output_limit = 6000   # the runners truncate each tool output to this many characters

    def __init__(self, sse_root: Path):
        self.sse_root = Path(sse_root)
        harness = self.sse_root / "platform" / "harness" / "eval_awareness.py"
        frames = literal_constants(harness, ["EVAL_FRAME", "MONITORING_ALIASES", "EVAL_FRAME_PROMPTS",
                                             "TASK_FRAME_PROMPTS"])
        self._frames = frames

    # --- conditions -------------------------------------------------------------------------
    @abstractmethod
    def cell_from_run(self, run: dict[str, Any]) -> Cell:
        """The condition a recorded run was collected under."""

    def supports(self, cell: Cell) -> tuple[bool, str]:
        """Whether this pipeline can rebuild and continue episodes from this condition."""
        return True, ""

    def frame_prompt(self, frame: str) -> str:
        f = normalize_frame(frame, self._frames["MONITORING_ALIASES"], tuple(self._frames["EVAL_FRAME"]))
        table = self._frames["TASK_FRAME_PROMPTS"].get(self.name, self._frames["EVAL_FRAME_PROMPTS"])
        return table.get(f, "")

    # --- conversation -----------------------------------------------------------------------
    @property
    @abstractmethod
    def tools(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def system_prompt(self, cell: Cell) -> str: ...

    @abstractmethod
    def user_prompt(self, cell: Cell) -> str: ...

    @abstractmethod
    def nudge(self, cell: Cell) -> str:
        """The user message the runner sends when the agent replies without a tool call."""

    def initial_messages(self, cell: Cell) -> list[dict[str, Any]]:
        return [{"role": "system", "content": self.system_prompt(cell)},
                {"role": "user", "content": self.user_prompt(cell)}]

    # --- environment ------------------------------------------------------------------------
    def sandbox(self) -> DockerSandbox:
        return DockerSandbox(self.image)

    @abstractmethod
    def prepare(self, sb: DockerSandbox, cell: Cell) -> None:
        """Wait until the service is ready and apply the cell's setup (planted notes etc.)."""

    def run_bash(self, sb: DockerSandbox, cmd: str) -> str:
        return sb.exec(cmd, user=self.agent_user)[: self.tool_output_limit]

    @abstractmethod
    def grade(self, sb: DockerSandbox, final_answer: str, transcript: list[dict[str, Any]],
              cell: Cell) -> dict[str, Any]:
        """Grade a finished episode from ground truth outside the agent's reach."""

    @staticmethod
    def final_tool_reply() -> str:
        return json.dumps({"noted": True})
