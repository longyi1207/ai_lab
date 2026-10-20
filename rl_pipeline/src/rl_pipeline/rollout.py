"""Stages 4 and 7: sample continuations from a branch point and grade them.

A rollout is one continuation of one episode from one branch point:

1. start a fresh container and replay the recorded prefix (``replay.py``);
2. run the agent loop from the branch step with the policy being sampled;
3. grade the whole episode (replayed prefix + continuation) with the task's own grader;
4. score it with ``reward.py``.

The agent loop mirrors the original task runners: the policy may call ``bash`` (run in the
container as the agent user, output truncated the same way) or the task's final tool, which ends
the episode. A reply with no tool call gets the runner's nudge. The episode also ends when the
step budget runs out, exactly as the runner's ``--max-steps`` would.

A *fresh* rollout (evaluation from step 0) is the same thing with an empty prefix.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from .budget import BudgetExceeded
from .judge import judge_intent
from .llm import AzureChat, ProviderError
from .replay import replay_prefix
from .reward import score
from .sandbox import SandboxError
from .tasks.base import Cell, Task
from .transcript import Entry, invalid_call_reply, prefix_before

log = logging.getLogger(__name__)


@dataclass
class Continuation:
    entries: list[Entry] = field(default_factory=list)
    final_answer: str = ""
    end: str = "max_steps"           # final_tool | max_steps
    steps: int = 0
    usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0


def continue_episode(task: Task, sb, cell: Cell, messages: list[dict[str, Any]], chat: AzureChat,
                     model: str, *, start_step: int, max_new_steps: int, temperature: float,
                     max_tokens: int, purpose: str) -> Continuation:
    """Run the agent loop from ``messages`` until the final tool or the step budget."""
    out = Continuation()
    for step in range(start_step, start_step + max_new_steps):
        res = chat.chat(model, messages, tools=task.tools, temperature=temperature,
                        max_tokens=max_tokens, purpose=purpose)
        out.usd += res.usd
        out.input_tokens += res.usage.input_tokens
        out.output_tokens += res.usage.output_tokens
        out.steps += 1
        msg = res.message
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        out.entries.append({"step": step, "role": "assistant", "content": msg.get("content"),
                            "reasoning": None,
                            "tool_calls": [{"cmd": f"{c['function']['name']} {c['function']['arguments']}"}
                                           for c in calls]})
        if not calls:
            messages.append({"role": "user", "content": task.nudge(cell)})
            continue
        for c in calls:
            name = c["function"]["name"]
            try:
                args = json.loads(c["function"]["arguments"] or "{}")
            except ValueError:
                args = None
            if name == "bash" and isinstance(args, dict):
                cmd = str(args.get("cmd", ""))
                result = task.run_bash(sb, cmd)
                out.entries.append({"step": step, "role": "tool", "tool_calls": [{"cmd": cmd}],
                                    "tool_output": result})
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": result or "(no output)"})
            elif name == task.final_tool:
                out.final_answer = str((args or {}).get(task.final_arg, "")).strip()
                out.end = "final_tool"
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": task.final_tool_reply()})
                return out
            else:
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": invalid_call_reply(name)})
    return out


def rollout_key(branch_id: str, policy_label: str, sample_idx: int) -> str:
    return f"{branch_id}|{policy_label}|{sample_idx}"


def run_rollout(task: Task, episode: dict[str, Any] | None, bp: dict[str, Any], *, chat: AzureChat,
                model: str, policy_label: str, sample_idx: int, max_new_steps: int, temperature: float,
                max_tokens: int, label_source: str, intent_policy: str, judge_model: str | None,
                phase: str) -> dict[str, Any]:
    """One continuation from a branch point (or from step 0 when ``episode`` is None)."""
    t0 = time.time()
    cell = bp["cell"]
    branch_step = bp["branch_step"]
    prefix = prefix_before(episode["transcript"], branch_step) if episode else []
    record: dict[str, Any] = {
        "key": rollout_key(bp["branch_id"], policy_label, sample_idx),
        "branch_id": bp["branch_id"], "task": task.name, "split": bp.get("split"), "phase": phase,
        "policy": policy_label, "model": model, "sample_idx": sample_idx, "branch_step": branch_step,
        "cell": cell,
    }
    budget_steps = max(1, min(max_new_steps, task.default_max_steps - (branch_step - 1)))
    try:
        with task.sandbox() as sb:
            replay = replay_prefix(task, sb, cell, prefix)
            record["replay"] = replay.stats()
            if not replay.ok:
                record.update(status="replay_mismatch", wall_seconds=round(time.time() - t0, 1))
                return record
            messages = [dict(m) for m in replay.messages]
            cont = continue_episode(task, sb, cell, messages, chat, model, start_step=branch_step,
                                    max_new_steps=budget_steps, temperature=temperature,
                                    max_tokens=max_tokens, purpose=f"{phase}:{policy_label}")
            full = replay.walk.entries + cont.entries
            verdict = task.grade(sb, cont.final_answer, full, cell)
    except ProviderError as e:
        record.update(status=f"provider_error:{e.kind}", error=str(e)[:300],
                      wall_seconds=round(time.time() - t0, 1))
        return record
    except SandboxError as e:
        record.update(status="sandbox_error", error=str(e)[:300], wall_seconds=round(time.time() - t0, 1))
        return record
    except BudgetExceeded:
        raise
    except Exception as e:  # one broken rollout must not stop a long run; it is recorded and excluded
        log.exception("rollout %s failed", record["key"])
        record.update(status=f"error:{type(e).__name__}", error=str(e)[:300],
                      wall_seconds=round(time.time() - t0, 1))
        return record

    judgement = None
    if judge_model:
        try:
            judgement = judge_intent(chat, judge_model, task, cell, full, verdict)
        except ProviderError as e:
            judgement = {"judge_error": True, "error": str(e)[:200]}
    rec = score(verdict, judgement, label_source=label_source, intent_policy=intent_policy)
    record.update(
        status="ok",
        prefix_entries=replay.walk.entries,
        entries=cont.entries,
        end=cont.end,
        final_answer=cont.final_answer,
        verdict={"label": verdict.get("label"), "channel": verdict.get("channel"),
                 "signals": verdict.get("signals") or {}},
        intent_judge=judgement,
        reward=rec.to_dict(),
        steps=cont.steps,
        usd=round(cont.usd, 5),
        input_tokens=cont.input_tokens,
        output_tokens=cont.output_tokens,
        wall_seconds=round(time.time() - t0, 1),
    )
    return record
