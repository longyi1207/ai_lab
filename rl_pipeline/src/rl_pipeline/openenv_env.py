"""The environments as an OpenEnv environment, so any compatible trainer can use them.

`OpenEnv <https://github.com/meta-pytorch/OpenEnv>`_ is a shared interface for agentic RL
environments: a Gymnasium-style ``reset`` / ``step`` / ``state`` API served over HTTP and
WebSockets (FastAPI), usually from a container. Trainers that speak it (for example TRL) can then
drive an environment they know nothing else about.

What this wraps is the part of the pipeline that is genuinely environment-specific:

* ``reset(start=...)`` picks a start state: a branch point from the pipeline (``"<branch_id>"``,
  rebuilt by replaying its recorded prefix in a fresh container), a fresh episode of a task
  (``"fresh:<task>"``), or the in-process toy task (``"toy"``). It returns the conversation so far
  and the tool schemas the agent may call.
* ``step(AgentTurn)`` takes one tool call. ``bash`` runs in the container; the task's final tool
  ends the episode. On the end (or when the step budget runs out) the task's grader runs and the
  observation carries the three-gate reward, the reason, and the grader's verdict.

One instance owns one container, so concurrent sessions are isolated
(``SUPPORTS_CONCURRENT_SESSIONS = True``).

Serve it with ``python -m rl_pipeline serve-env --config configs/pilot.yaml`` (needs the
``openenv`` extra), or use ``ShortcutEnv`` in-process.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from openenv.core.env_server import Action, Environment, Observation, State
from pydantic import Field

from .config import Config
from .replay import replay_prefix
from .reward import score
from .stages import Pipeline
from .tasks.base import Task
from .transcript import invalid_call_reply, prefix_before


class AgentTurn(Action):
    """One assistant turn reduced to a single tool call."""
    tool: str = Field(..., description="tool name, e.g. 'bash' or the task's final tool")
    arguments: dict[str, Any] = Field(default_factory=dict, description="tool arguments")
    content: Optional[str] = Field(default=None, description="visible text the agent wrote, if any")


class TurnObservation(Observation):
    """Messages to append to the conversation (at reset: the whole conversation so far)."""
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tools: list[dict[str, Any]] = Field(default_factory=list, description="tool schemas (set at reset)")
    steps_left: Optional[int] = Field(default=None, description="tool calls left before the episode is graded")
    # Set when the episode ends. OpenEnv drops ``metadata`` on the wire, so these are real fields.
    reason: Optional[str] = Field(default=None, description="reward reason: clean_completion, action_cheat, ...")
    verdict: Optional[dict[str, Any]] = Field(default=None, description="the grader's label and channel")
    cheat_evidence: list[str] = Field(default_factory=list)


class EpisodeState(State):
    task: Optional[str] = None
    start: Optional[str] = None
    branch_step: int = 1
    ended: bool = False


class ShortcutEnv(Environment[AgentTurn, TurnObservation, EpisodeState]):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self, cfg: Config, *, max_steps: Optional[int] = None):
        super().__init__()
        self.cfg = cfg
        self.pipeline = Pipeline(cfg)
        self.max_steps = max_steps
        self._task: Task | None = None
        self._cell: dict[str, Any] = {}
        self._sb = None
        self._entries: list[dict[str, Any]] = []
        self._budget = 0
        self._state = EpisodeState()

    # --- helpers --------------------------------------------------------------------------------
    def _resolve_start(self, start: str) -> tuple[Task, dict[str, Any] | None, dict[str, Any]]:
        if start == "toy":
            from .local.toy_env import ToyShortcutTask
            return ToyShortcutTask(), None, {"branch_id": "toy", "task": "toy_shortcut", "cell": {}, "branch_step": 1}
        if start.startswith("fresh:"):
            task = self.pipeline.tasks[start.split(":", 1)[1]]
            bps = [b for b in self.pipeline.store.read(self.pipeline.store.branch_points) if b["task"] == task.name]
            cell = bps[0]["cell"] if bps else task.cell_from_run({})
            return task, None, {"branch_id": start, "task": task.name, "cell": cell, "branch_step": 1}
        bp = next((b for b in self.pipeline.store.read(self.pipeline.store.branch_points) if b["branch_id"] == start), None)
        if bp is None:
            raise ValueError(f"unknown start {start!r}: use a branch_id, 'fresh:<task>' or 'toy'")
        episode = self.pipeline.episodes_by_id({bp["episode_id"]})[bp["episode_id"]]
        return self.pipeline.tasks[bp["task"]], episode, bp

    def close(self) -> None:
        if self._sb is not None and hasattr(self._sb, "close"):
            self._sb.close()
        self._sb = None

    def _finish(self, final_answer: str, messages: list[dict[str, Any]]) -> TurnObservation:
        verdict = self._task.grade(self._sb, final_answer, self._entries, self._cell)
        rec = score(verdict, label_source=self.cfg.reward.label_source, intent_policy=self.cfg.reward.intent_policy)
        self._state.ended = True
        self.close()
        return TurnObservation(messages=messages, done=True, reward=float(rec.reward), steps_left=0,
                               reason=rec.reason, cheat_evidence=list(rec.cheat_evidence),
                               verdict={"label": verdict.get("label"), "channel": verdict.get("channel")})

    # --- OpenEnv API ----------------------------------------------------------------------------
    def reset(self, seed: Optional[int] = None, episode_id: Optional[str] = None, **kwargs: Any) -> TurnObservation:
        self.close()
        start = str(kwargs.get("start", "toy"))
        task, episode, bp = self._resolve_start(start)
        self._task, self._cell = task, bp["cell"]
        sb = task.sandbox()
        self._sb = sb.__enter__() if hasattr(sb, "__enter__") else sb
        prefix = prefix_before(episode["transcript"], bp["branch_step"]) if episode else []
        replay = replay_prefix(task, self._sb, self._cell, prefix)
        if not replay.ok:
            self.close()
            raise RuntimeError(f"start {start!r} does not replay faithfully: {replay.stats()['mismatches'][:1]}")
        self._entries = list(replay.walk.entries)
        steps_left = task.default_max_steps - (bp["branch_step"] - 1)
        self._budget = min(steps_left, self.max_steps) if self.max_steps else steps_left
        self._state = EpisodeState(episode_id=episode_id or uuid.uuid4().hex, step_count=0, task=task.name,
                                   start=start, branch_step=bp["branch_step"])
        return TurnObservation(messages=replay.messages, tools=task.tools, done=False, reward=None,
                               steps_left=self._budget)

    def step(self, action: AgentTurn, timeout_s: Optional[float] = None, **kwargs: Any) -> TurnObservation:
        if self._task is None or self._state.ended:
            raise RuntimeError("call reset() before step()")
        task = self._task
        self._state.step_count += 1
        step_no = self._state.branch_step + self._state.step_count - 1
        call_id = f"call_{step_no}_0"
        args_json = json.dumps(action.arguments)
        assistant = {"role": "assistant", "content": action.content,
                     "tool_calls": [{"id": call_id, "type": "function",
                                     "function": {"name": action.tool, "arguments": args_json}}]}
        self._entries.append({"step": step_no, "role": "assistant", "content": action.content, "reasoning": None,
                              "tool_calls": [{"cmd": f"{action.tool} {args_json}"}]})
        if action.tool == task.final_tool:
            answer = str(action.arguments.get(task.final_arg, "")).strip()
            reply = {"role": "tool", "tool_call_id": call_id, "content": task.final_tool_reply()}
            return self._finish(answer, [assistant, reply])
        if action.tool == "bash":
            cmd = str(action.arguments.get("cmd", ""))
            out = task.run_bash(self._sb, cmd)
            self._entries.append({"step": step_no, "role": "tool", "tool_calls": [{"cmd": cmd}], "tool_output": out})
            reply = {"role": "tool", "tool_call_id": call_id, "content": out or "(no output)"}
        else:
            reply = {"role": "tool", "tool_call_id": call_id, "content": invalid_call_reply(action.tool)}
        if self._state.step_count >= self._budget:
            return self._finish("", [assistant, reply])
        return TurnObservation(messages=[assistant, reply], done=False, reward=None,
                               steps_left=self._budget - self._state.step_count)

    @property
    def state(self) -> EpisodeState:
        return self._state


def make_app(cfg: Config, max_concurrent_envs: int = 4):
    """FastAPI app exposing ``/reset``, ``/step``, ``/state`` (and the WebSocket API)."""
    from openenv.core.env_server import create_app
    return create_app(lambda: ShortcutEnv(cfg), AgentTurn, TurnObservation, env_name="shortcut_env",
                      max_concurrent_envs=max_concurrent_envs)
