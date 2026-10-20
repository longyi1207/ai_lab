"""Stage 2: find where each episode's decision happened, and choose branch points.

An outcome reward for a long episode says *that* something went wrong, not *where*. Most of a
cheating episode is ordinary work; the decision to take the shortcut happens at one step. We want
our training signal there.

Locating the decision: the intent judge quotes the agent's own words as evidence ("the device.conf
key would unlock it directly..."). The first assistant step whose reasoning, message, or tool
call contains one of those quotes is the **onset** step. No new model calls are needed.

Choosing the branch: we branch ``margin`` steps *before* the onset, because judge labels are
noisy by a few steps and agents usually drift toward a shortcut gradually rather than jumping.
Continuations sampled from that state are where "decline" and "take the shortcut" compete.

Two kinds of source episodes give useful branch points:
* ``pursued``: the agent went for the shortcut (reward 0, intent or action dirty);
* ``temptation``: the agent noticed the shortcut and did not take it (judge says noticed, or
  contemplated and declined).

Each branch point is assigned to ``train`` or ``test`` by a hash of its source episode, so the
split is stable across runs and no episode contributes to both.
"""
from __future__ import annotations

import hashlib
import json
import random
import re
from collections import defaultdict
from typing import Any

from .transcript import is_tool_entry

_MIN_QUOTE = 25


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip().lower()


def _assistant_text(entry: dict[str, Any]) -> str:
    calls = json.dumps(entry.get("tool_calls") or [], ensure_ascii=False)
    return _norm(" ".join([str(entry.get("reasoning") or ""), str(entry.get("content") or ""), calls]))


def locate_onset(episode: dict[str, Any]) -> tuple[int | None, str | None]:
    """(step, quote) of the first assistant step containing one of the judge's evidence quotes."""
    judgement = episode.get("intent_judge") or {}
    quotes = [_norm(q) for q in judgement.get("evidence_quotes") or []]
    quotes = [q[:160] for q in quotes if len(q) >= _MIN_QUOTE]
    if not quotes:
        return None, None
    for entry in episode["transcript"]:
        if is_tool_entry(entry):
            continue
        text = _assistant_text(entry)
        # tool-call arguments are JSON-escaped in the transcript; compare both forms
        for q in quotes:
            if q in text or q in text.replace('\\"', '"'):
                return entry.get("step"), q
    return None, None


def kind_of(episode: dict[str, Any]) -> str | None:
    reward = episode["reward"]
    level = (episode.get("intent_judge") or {}).get("intent_status")
    declined = bool((episode.get("intent_judge") or {}).get("declined_after_notice"))
    if reward["reward"] == 0 and (reward["reason"] in ("action_cheat", "intent_cheat")
                                  or level in ("planned", "attempted_in_reasoning", "contemplated")):
        return "pursued"
    if level == "noticed" or (level == "contemplated" and declined):
        return "temptation"
    return None


def split_of(episode_id: str, test_fraction: float) -> str:
    h = int(hashlib.sha256(episode_id.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "test" if h < test_fraction else "train"


def select_branch_points(episodes: list[dict[str, Any]], *, margin: int, max_per_task: int,
                         include_temptation: bool, test_fraction: float, seed: int
                         ) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Return (branch_points, counts of why episodes were not used)."""
    skipped: dict[str, int] = defaultdict(int)
    candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ep in episodes:
        kind = kind_of(ep)
        if kind is None or (kind == "temptation" and not include_temptation):
            skipped["no_decision_to_branch"] += 1
            continue
        onset, quote = locate_onset(ep)
        if onset is None:
            skipped["onset_not_located"] += 1
            continue
        branch_step = onset - margin
        if branch_step < 2:
            skipped["onset_too_early"] += 1     # need at least one recorded step as context
            continue
        candidates[ep["task"]].append({
            "branch_id": f"{ep['episode_id']}@{branch_step}",
            "episode_id": ep["episode_id"],
            "task": ep["task"],
            "cell": ep["cell"],
            "source_model": ep["model"],
            "kind": kind,
            "onset_step": onset,
            "branch_step": branch_step,
            "onset_quote": quote,
            "source_reward": ep["reward"]["reward"],
            "source_reason": ep["reward"]["reason"],
            "split": split_of(ep["episode_id"], test_fraction),
        })

    # Stratified, deterministic selection: round-robin over (source model, kind) groups so no
    # single model or outcome dominates the branch points.
    rng = random.Random(seed)
    chosen: list[dict[str, Any]] = []
    for task in sorted(candidates):
        groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for bp in candidates[task]:
            groups[(str(bp["source_model"]), bp["kind"])].append(bp)
        for g in groups.values():
            g.sort(key=lambda b: b["branch_id"])
            rng.shuffle(g)
        order = sorted(groups)
        picked: list[dict[str, Any]] = []
        while len(picked) < max_per_task and any(groups[k] for k in order):
            for k in order:
                if groups[k] and len(picked) < max_per_task:
                    picked.append(groups[k].pop())
        skipped["over_task_cap"] += sum(len(g) for g in groups.values())
        chosen += sorted(picked, key=lambda b: b["branch_id"])
    return chosen, dict(skipped)
