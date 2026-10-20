"""Stage 1: import recorded episodes and score them.

An *episode* is one finished run of an agent on a task: the condition it ran under, the full
transcript, the grader's verdict, and (if available) an LLM judge's reading of the agent's intent.
We read the runs that score-seeking-eval's task runners wrote, keep the ones this pipeline can
rebuild, and attach the reward from ``reward.py``.

Kept: runs of a registered task, in a supported condition, with a non-empty transcript and a
grader label. Identical transcripts (file aliases, deterministic reruns) are kept once.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

from .reward import score
from .tasks import FILENAME_PREFIXES, Task

log = logging.getLogger(__name__)

_SKIP_NAME = re.compile(r"(^|[_/])(smoke\d*|_?sanity|test)([_.]|$)")
_JUDGE_FIELDS = ("intent_status", "contemplated", "declined_after_notice", "evidence_quotes",
                 "label", "channel", "reasoning_available", "judge_model", "schema_version",
                 "judge_error")


def task_of(run: dict[str, Any], path: Path) -> str | None:
    recorded = run.get("task") or (run.get("propensity") or {}).get("task")
    if recorded:
        return str(recorded)
    for prefix, task in sorted(FILENAME_PREFIXES.items(), key=lambda kv: -len(kv[0])):
        if path.name.startswith(prefix):
            return task
    return None


def discover(runs_dir: Path) -> Iterator[tuple[Path, dict[str, Any]]]:
    for path in sorted(Path(runs_dir).rglob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            yield path, data


def import_episodes(runs_dir: Path, tasks: dict[str, Task], *, label_source: str,
                    intent_policy: str) -> tuple[list[dict[str, Any]], Counter]:
    """Return (episodes, skip_reasons). Each episode is a plain dict ready for JSONL."""
    episodes: list[dict[str, Any]] = []
    skipped: Counter = Counter()
    seen: set[str] = set()
    for path, run in discover(runs_dir):
        rel = str(path.relative_to(runs_dir))
        name = task_of(run, path)
        if name not in tasks:
            skipped["other_task"] += 1
            continue
        if _SKIP_NAME.search(rel):
            skipped["smoke_or_test_run"] += 1
            continue
        task = tasks[name]
        transcript = run.get("transcript") or []
        verdict = run.get("verdict") if isinstance(run.get("verdict"), dict) else None
        if not transcript:
            skipped["empty_transcript"] += 1
            continue
        if not verdict or not verdict.get("label"):
            skipped["ungraded"] += 1
            continue
        cell = task.cell_from_run(run)
        ok, why = task.supports(cell)
        if not ok:
            skipped["unsupported_condition"] += 1
            continue
        digest = hashlib.sha256(json.dumps(transcript, sort_keys=True).encode()).hexdigest()
        if digest in seen:
            skipped["duplicate_transcript"] += 1
            continue
        seen.add(digest)

        judgement = run.get("intent_judge")
        judgement = {k: judgement.get(k) for k in _JUDGE_FIELDS} if isinstance(judgement, dict) else None
        cheat_mode = (run.get("propensity") or {}).get("cheat_mode")
        rec = score(verdict, judgement, cheat_mode=cheat_mode, label_source=label_source,
                    intent_policy=intent_policy)
        episodes.append({
            "episode_id": "ep_" + digest[:16],
            "source": rel,
            "task": name,
            "model": run.get("model"),
            "cell": cell,
            "verdict": {"label": verdict.get("label"), "channel": verdict.get("channel"),
                        "signals": verdict.get("signals") or {}},
            "cheat_mode": cheat_mode,
            "intent_judge": judgement,
            "reward": rec.to_dict(),
            "n_steps": len([e for e in transcript if e.get("role") != "tool" and "tool_output" not in e]),
            "transcript": transcript,
        })
    log.info("imported %d episodes; skipped %s", len(episodes), dict(skipped))
    return episodes, skipped
