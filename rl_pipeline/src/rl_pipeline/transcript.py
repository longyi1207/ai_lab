"""Convert between recorded transcripts and the chat messages a model sees.

The task runners record an episode as a flat list of entries:

    {"step": 3, "role": "assistant", "content": "...", "reasoning": "...",
     "tool_calls": [{"cmd": "bash {\"cmd\": \"cat /app/spec.md\"}"}]}
    {"step": 3, "role": "tool", "tool_calls": [{"cmd": "cat /app/spec.md"}], "tool_output": "..."}

To continue an episode from step ``k`` we must rebuild the exact conversation the agent had at
that point. The transcript leaves out three things the runner did send, which we restore:

* tool-call ids (synthesised as ``call_<step>_<i>``; the model never sees them as content);
* the nudge the runner sends when the agent answers without calling a tool;
* the ``{"noted": true}`` reply to the final tool (``submit_flag`` / ``done``).

Private reasoning is kept in the transcript for analysis but is not sent back to the model:
chat APIs do not accept another model's reasoning as input.

``walk`` is the single source of truth for this reconstruction. Replay passes it a function that
re-executes each shell command; plain conversion passes one that returns the recorded output.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from .tasks.base import Cell, Task

Entry = dict[str, Any]


def is_tool_entry(e: Entry) -> bool:
    return e.get("role") == "tool" or "tool_output" in e


def parse_call(cmd: str) -> tuple[str, str, dict[str, Any] | None]:
    """'bash {"cmd": "ls"}' -> ('bash', '{"cmd": "ls"}', {'cmd': 'ls'})."""
    name, _, raw = (cmd or "").strip().partition(" ")
    raw = raw.strip()
    try:
        args = json.loads(raw) if raw else {}
    except ValueError:
        args = None
    return name, raw or "{}", args if isinstance(args, dict) else None


def assistant_steps(entries: list[Entry]) -> list[int]:
    return [e.get("step") for e in entries if not is_tool_entry(e)]


def prefix_before(entries: list[Entry], step: int) -> list[Entry]:
    """Entries the agent had produced before it took step ``step`` (1-based)."""
    return [e for e in entries if (e.get("step") or 0) < step]


@dataclass
class Walk:
    messages: list[dict[str, Any]]
    turn_starts: list[int] = field(default_factory=list)   # message index of each assistant turn
    entries: list[Entry] = field(default_factory=list)      # entries with the outputs actually used
    bash_calls: int = 0
    ended: bool = False                                     # a final tool was called


OutputFn = Callable[[str, str], str]     # (command, recorded_output) -> output to use


def recorded_output(cmd: str, recorded: str) -> str:
    return recorded


def invalid_call_reply(name: str) -> str:
    """Tool reply for an unknown tool or unparseable arguments (shared with the agent loop)."""
    return json.dumps({"error": f"unknown tool or invalid arguments: {name}"})


def walk(task: Task, cell: Cell, entries: list[Entry], output_fn: OutputFn = recorded_output) -> Walk:
    """Rebuild the conversation for ``entries``, taking each tool output from ``output_fn``."""
    w = Walk(messages=task.initial_messages(cell))
    tool_queue = [e for e in entries if is_tool_entry(e)]
    qi = 0
    for e in entries:
        if is_tool_entry(e):
            continue
        step = e.get("step")
        calls = [parse_call(tc.get("cmd", "")) for tc in (e.get("tool_calls") or []) if isinstance(tc, dict)]
        msg: dict[str, Any] = {"role": "assistant", "content": e.get("content")}
        if calls:
            msg["tool_calls"] = [{"id": f"call_{step}_{i}", "type": "function",
                                  "function": {"name": name, "arguments": raw}}
                                 for i, (name, raw, _) in enumerate(calls)]
        w.turn_starts.append(len(w.messages))
        w.messages.append(msg)
        w.entries.append(dict(e))
        if not calls:
            w.messages.append({"role": "user", "content": task.nudge(cell)})
            continue
        for i, (name, _, args) in enumerate(calls):
            call_id = f"call_{step}_{i}"
            if name == "bash" and args is not None:
                rec = tool_queue[qi] if qi < len(tool_queue) else {}
                qi += 1
                cmd = str(args.get("cmd", ""))
                out = output_fn(cmd, rec.get("tool_output") or "")
                w.bash_calls += 1
                w.entries.append({"step": step, "role": "tool", "tool_calls": [{"cmd": cmd}], "tool_output": out})
                w.messages.append({"role": "tool", "tool_call_id": call_id, "content": out or "(no output)"})
            elif name == task.final_tool:
                w.messages.append({"role": "tool", "tool_call_id": call_id, "content": task.final_tool_reply()})
                w.ended = True
                break
            else:
                w.messages.append({"role": "tool", "tool_call_id": call_id, "content": invalid_call_reply(name)})
        if w.ended:
            break
    return w


def to_messages(task: Task, cell: Cell, entries: list[Entry]) -> list[dict[str, Any]]:
    return walk(task, cell, entries).messages


def dpo_output_message(msg: dict[str, Any]) -> dict[str, Any]:
    """An assistant message in the fine-tuning data format.

    The fine-tuning validator rejects ``"content": null``, which chat APIs return for turns that
    only call tools, so empty content is left out instead.
    """
    out: dict[str, Any] = {"role": "assistant"}
    if msg.get("content"):
        out["content"] = msg["content"]
    if msg.get("tool_calls"):
        out["tool_calls"] = msg["tool_calls"]
    if "content" not in out and "tool_calls" not in out:
        out["content"] = ""
    return out


def finetune_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Context messages in the fine-tuning format (assistant turns cleaned as above)."""
    return [dpo_output_message(m) if m.get("role") == "assistant" else dict(m) for m in messages]
