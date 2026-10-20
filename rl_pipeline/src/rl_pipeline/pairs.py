"""Stage 5: turn graded continuations into preference pairs at the step where they diverge.

For each training branch point we have K continuations, each graded 0 or 1. A pair is
(one continuation that earned 1, one that earned 0) from the same branch point.

Where does the preference apply? Two continuations from the same state often start identically
(both read the same file first) and only later go different ways. While their turns and tool
outputs are identical, they are in the same state, so we extend the shared context through those
turns and put the preference on the **first turn where they differ**. That is the decision the
outcome reward is about, and it is the only turn the DPO loss touches:

    input               = system + task + replayed prefix + shared continuation turns
    preferred_output    = the next assistant turn of the continuation that earned 1
    non_preferred_output= the next assistant turn of the continuation that earned 0

This matches the Azure OpenAI DPO format, which trains on one final assistant turn per example.
The label comes from rolling each continuation out to the end; the gradient lands on the turn
where they split (a Monte Carlo estimate of which first move leads to a clean completion).
"""
from __future__ import annotations

import hashlib
import itertools
import json
import random
from collections import defaultdict
from typing import Any

from .replay import normalize_output
from .tasks.base import Task
from .transcript import dpo_output_message, finetune_messages, is_tool_entry, parse_call, prefix_before, walk


def recorded_rollout(bp: dict[str, Any], episode: dict[str, Any]) -> dict[str, Any]:
    """The recorded episode's own continuation from the branch point, as a pseudo-rollout.

    Replay fidelity guarantees the recorded prefix and a replayed prefix describe the same state,
    so the original agent's continuation is one more graded sample from that state. Its turns
    were written by a different model (off-policy), which DPO tolerates on the preferred side.
    """
    step = bp["branch_step"]
    return {"key": f"{bp['branch_id']}|recorded|0", "branch_id": bp["branch_id"], "task": bp["task"],
            "split": bp["split"], "phase": "sample", "policy": "recorded", "status": "ok",
            "cell": bp["cell"], "prefix_entries": prefix_before(episode["transcript"], step),
            "entries": [e for e in episode["transcript"] if (e.get("step") or 0) >= step],
            "reward": episode["reward"]}


def _turns(entries: list[dict[str, Any]]) -> list[tuple[dict[str, Any], list[str]]]:
    """Group continuation entries into (assistant entry, [tool outputs]) turns."""
    turns: list[tuple[dict[str, Any], list[str]]] = []
    for e in entries:
        if is_tool_entry(e):
            if turns:
                turns[-1][1].append(normalize_output(e.get("tool_output") or ""))
        else:
            turns.append((e, []))
    return turns


def _canonical_calls(entry: dict) -> list[tuple[str, str]]:
    """Tool calls as (name, canonical JSON arguments), so formatting differences do not count.

    Two models can emit the same command with different JSON spacing (`{"cmd": "ls"}` vs
    `{"cmd":"ls"}`). Comparing raw strings would call those a divergence and put the preference
    on a turn where nothing was actually decided (the pilot's first version did exactly this).
    """
    out = []
    for tc in entry.get("tool_calls") or []:
        name, raw, args = parse_call(tc.get("cmd", ""))
        out.append((name, json.dumps(args, sort_keys=True) if args is not None else raw.strip()))
    return out


def _same_turn(a: tuple[dict, list[str]], b: tuple[dict, list[str]]) -> bool:
    """Same decision: the same tool calls (canonical) leading to the same (masked) outputs.

    Visible wording is ignored: it does not change the environment, and two models phrase things
    differently even when they do the same thing. A turn with no tool call matches only another
    turn with no tool call.
    """
    return _canonical_calls(a[0]) == _canonical_calls(b[0]) and a[1] == b[1]


def divergence(chosen: dict[str, Any], rejected: dict[str, Any]) -> int | None:
    """Index (within the continuation) of the first assistant turn that differs, or None."""
    tc, tr = _turns(chosen["entries"]), _turns(rejected["entries"])
    for i in range(min(len(tc), len(tr))):
        if not _same_turn(tc[i], tr[i]):
            return i
    return None


def build_pair(task: Task, chosen: dict[str, Any], rejected: dict[str, Any]) -> dict[str, Any] | None:
    d = divergence(chosen, rejected)
    if d is None:
        return None
    cell = chosen["cell"]
    wc = walk(task, cell, chosen["prefix_entries"] + chosen["entries"])
    wr = walk(task, cell, rejected["prefix_entries"] + rejected["entries"])
    n_prefix = len([e for e in chosen["prefix_entries"] if not is_tool_entry(e)])
    g = n_prefix + d
    if g >= len(wc.turn_starts) or g >= len(wr.turn_starts):
        return None
    context = wc.messages[: wc.turn_starts[g]]
    preferred = dpo_output_message(wc.messages[wc.turn_starts[g]])
    non_preferred = dpo_output_message(wr.messages[wr.turn_starts[g]])
    if json.dumps(preferred, sort_keys=True) == json.dumps(non_preferred, sort_keys=True):
        return None
    # Contexts can differ in masked values (e.g. a nonce in a token both containers issued).
    exact = context == wr.messages[: wr.turn_starts[g]]
    example = {
        "input": {"messages": finetune_messages(context), "tools": task.tools, "parallel_tool_calls": True},
        "preferred_output": [preferred],
        "non_preferred_output": [non_preferred],
    }
    meta = {
        "pair_id": hashlib.sha256((chosen["key"] + "||" + rejected["key"]).encode()).hexdigest()[:16],
        "branch_id": chosen["branch_id"], "task": task.name,
        "chosen": chosen["key"], "rejected": rejected["key"],
        "chosen_policy": chosen.get("policy"), "rejected_policy": rejected.get("policy"),
        "rejected_reason": rejected["reward"]["reason"], "divergence_turn": d,
        "context_exact": exact, "context_messages": len(context),
    }
    return {"example": example, "meta": meta}


def build_pairs(tasks: dict[str, Task], rollouts: list[dict[str, Any]], *, max_pairs_per_branch: int,
                val_fraction: float, seed: int = 0, recorded: list[dict[str, Any]] | None = None,
                ) -> dict[str, Any]:
    """Pairs from training rollouts (plus, optionally, the recorded continuations).

    Returns train/val examples, per-pair metadata, and counts. A pair always has a policy sample on
    at least one side: two recorded continuations never form a pair.
    """
    by_branch: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rollouts:
        if r.get("status") == "ok" and r.get("phase") == "sample" and r.get("split") == "train":
            by_branch[r["branch_id"]].append(r)
    for r in recorded or []:
        if r["split"] == "train" and r["branch_id"] in by_branch:
            by_branch[r["branch_id"]].append(r)

    rng = random.Random(seed)
    counts = defaultdict(int)
    train, val, meta = [], [], []
    for branch_id in sorted(by_branch):
        recs = sorted(by_branch[branch_id], key=lambda r: r["key"])
        ones = [r for r in recs if r["reward"]["reward"] == 1]
        zeros = [r for r in recs if r["reward"]["reward"] == 0]
        counts["branches"] += 1
        if not ones or not zeros:
            counts["branches_without_contrast"] += 1
            continue
        combos = [(c, z) for c, z in itertools.product(ones, zeros)
                  if not (c.get("policy") == "recorded" and z.get("policy") == "recorded")]
        if not combos:
            counts["branches_without_contrast"] += 1
            continue
        rng.shuffle(combos)
        made = 0
        bucket = "val" if (int(hashlib.sha256(branch_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF) < val_fraction else "train"
        for c, z in combos:
            if made >= max_pairs_per_branch:
                break
            p = build_pair(tasks[c["task"]], c, z)
            if p is None:
                counts["pairs_identical_or_unusable"] += 1
                continue
            p["meta"]["bucket"] = bucket
            (val if bucket == "val" else train).append(p["example"])
            meta.append(p["meta"])
            made += 1
        counts["branches_with_pairs"] += bool(made)
    counts["train_pairs"] = len(train)
    counts["val_pairs"] = len(val)
    return {"train": train, "val": val, "meta": meta, "counts": dict(counts)}


def validate_example(ex: dict[str, Any]) -> list[str]:
    """Structural checks mirroring what the fine-tuning service rejects."""
    problems = []
    msgs = ex.get("input", {}).get("messages") or []
    if not msgs or msgs[0].get("role") != "system":
        problems.append("input must start with a system message")
    for m in msgs + (ex.get("preferred_output") or []) + (ex.get("non_preferred_output") or []):
        if "content" in m and m["content"] is None:
            problems.append("null content (the fine-tuning validator rejects it)")
            break
    pending: set[str] = set()
    for m in msgs:
        if m.get("role") == "assistant":
            if pending:
                problems.append("assistant turn before all tool calls were answered")
            pending = {c["id"] for c in m.get("tool_calls") or []}
        elif m.get("role") == "tool":
            pending.discard(m.get("tool_call_id"))
    if pending:
        problems.append("context ends with unanswered tool calls")
    for side in ("preferred_output", "non_preferred_output"):
        out = ex.get(side) or []
        if len(out) != 1 or out[0].get("role") != "assistant":
            problems.append(f"{side} must be exactly one assistant message")
    return problems
