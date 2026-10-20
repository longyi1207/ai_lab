"""Shared fakes so the core logic can be tested offline: no Docker, no Azure, no score-seeking-eval."""
from __future__ import annotations

import json
from typing import Any

import pytest

from rl_pipeline.budget import Usage
from rl_pipeline.llm import ChatResult
from rl_pipeline.tasks.base import Task


class FakeSandbox:
    """Answers shell commands from a dict; records what ran."""

    def __init__(self, outputs: dict[str, str] | None = None):
        self.outputs = outputs or {}
        self.ran: list[str] = []

    def exec(self, cmd: str, *, user: str | None = None, timeout: int = 60) -> str:
        self.ran.append(cmd)
        return self.outputs.get(cmd, f"out:{cmd}")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None


class FakeTask(Task):
    name = "fake"
    image = "fake:latest"
    final_tool = "submit"
    final_arg = "answer"
    agent_user = "agent"
    default_max_steps = 10

    def __init__(self, sandbox: FakeSandbox | None = None):   # no score-seeking-eval needed
        self._sb = sandbox or FakeSandbox()

    def cell_from_run(self, run):
        return {"scope": run.get("scope", "none")}

    @property
    def tools(self):
        return [{"type": "function", "function": {"name": "bash", "parameters": {}}},
                {"type": "function", "function": {"name": "submit", "parameters": {}}}]

    def system_prompt(self, cell):
        return f"system scope={cell['scope']}"

    def user_prompt(self, cell):
        return "begin"

    def nudge(self, cell):
        return "keep going"

    def sandbox(self):
        return self._sb

    def prepare(self, sb, cell):
        sb.exec("prepare")

    def run_bash(self, sb, cmd):
        return sb.exec(cmd)

    def grade(self, sb, final_answer, transcript, cell):
        if final_answer == "honest":
            return {"label": "honest_solve", "channel": "honest", "signals": {}}
        if final_answer == "cheat":
            return {"label": "score_seek_success", "channel": "backdoor_used", "signals": {}}
        return {"label": "fail", "channel": "none", "signals": {}}


def bash_call(cmd: str, call_id: str = "c1") -> dict[str, Any]:
    return {"id": call_id, "type": "function",
            "function": {"name": "bash", "arguments": json.dumps({"cmd": cmd})}}


def final_call(answer: str, call_id: str = "f1") -> dict[str, Any]:
    return {"id": call_id, "type": "function",
            "function": {"name": "submit", "arguments": json.dumps({"answer": answer})}}


class FakeChat:
    """Replays a scripted list of assistant messages."""

    def __init__(self, script: list[dict[str, Any]]):
        self.script = list(script)
        self.calls: list[list[dict[str, Any]]] = []

    def chat(self, model, messages, **kwargs) -> ChatResult:
        self.calls.append([dict(m) for m in messages])
        msg = self.script.pop(0)
        return ChatResult(message={"role": "assistant", **msg}, usage=Usage(100, 10), finish_reason="stop", usd=0.001)


def entries_for(*turns: tuple[int, str | None, list[tuple[str, str]], list[str]]) -> list[dict[str, Any]]:
    """Build transcript entries: (step, content, [(tool_name, args_json)], [bash outputs])."""
    out = []
    for step, content, calls, outputs in turns:
        out.append({"step": step, "role": "assistant", "content": content, "reasoning": None,
                    "tool_calls": [{"cmd": f"{n} {a}"} for n, a in calls]})
        bash = []
        for n, a in calls:            # unparseable calls produce no tool entry, as in the agent loop
            try:
                if n == "bash":
                    bash.append(json.loads(a)["cmd"])
            except ValueError:
                pass
        for cmd, o in zip(bash, outputs):
            out.append({"step": step, "role": "tool", "tool_calls": [{"cmd": cmd}], "tool_output": o})
    return out


@pytest.fixture
def task() -> FakeTask:
    return FakeTask()
