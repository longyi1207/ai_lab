"""Run one execution: a fresh MiniLab-lite world, the agents running concurrently in it, then grading.

Layout of runs/<exp>/exec/<scenario>/<condition>/<k>/:
  meta.json          config, plan revision, models, timing
  agent_<L>.json     events (timestamped) and full messages, checkpointed after every step
  grades.json        main-task and side-task grades
  statelog.jsonl     every shared-state write, in order
  done.json          summary; its presence marks the execution complete (checkpoint/resume)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path

from .agent import Mailbox, run_agent
from .llm import LLM
from .sandbox import IMAGE, Sandbox
from .scenarios import Scenario, build_agents

log = logging.getLogger(__name__)


def exec_dir(runs: Path, scenario: str, condition: str, k: int) -> Path:
    return runs / "exec" / scenario / condition / f"{k:02d}"


def is_valid(condition: str, main_ok: bool, side_ok: bool) -> bool:
    """Paper App. C: an attack run counts only if main tasks and side task succeed; a benign run if main tasks do."""
    return main_ok and (side_ok if condition in ("team_attack", "solo_attack", "team_noplan") else True)


async def run_execution(sc: Scenario, condition: str, k: int, runs: Path, llm: LLM, model: str,
                        max_steps: int, comms: bool = False, tick_seconds: float = 2.0) -> dict:
    d = exec_dir(runs, sc.name, condition, k)
    done = d / "done.json"
    if done.exists():
        return json.loads(done.read_text())
    d.mkdir(parents=True, exist_ok=True)
    for stale in d.glob("agent_*.json"):
        stale.unlink()
    agents = build_agents(sc, condition, model, max_steps, comms)
    meta = {"scenario": sc.name, "condition": condition, "k": k, "executor": model, "max_steps": max_steps,
            "comms": comms, "plan_revision": sc.revision, "image": IMAGE, "started": time.time(),
            "agents": [{"label": a.label, "account": a.account} for a in agents]}
    (d / "meta.json").write_text(json.dumps(meta, indent=1))
    mailbox = Mailbox([a.label for a in agents]) if comms else None
    t0 = time.time()
    async with Sandbox(label=f"{sc.name[:10]}-{condition[:6]}-{k}", tick_seconds=tick_seconds) as sb:
        results = await asyncio.gather(*[
            run_agent(a, sb, llm, mailbox, d / f"agent_{a.label}.json", purpose=f"exec:{sc.name}:{condition}")
            for a in agents])
        await sb.finalize()
        grades = await sb.grade(sc.main_tasks + [sc.side_task])
        statelog = await sb.statelog()
        ticker_err = await sb.ticker_errors()
    (d / "grades.json").write_text(json.dumps(grades, indent=1))
    with (d / "statelog.jsonl").open("w") as f:
        for row in statelog:
            f.write(json.dumps(row) + "\n")
    main_ok = all(g["success"] for g in grades[:-1])
    side_ok = grades[-1]["success"]
    summary = {"scenario": sc.name, "condition": condition, "k": k, "main_ok": main_ok, "side_ok": side_ok,
               "valid": is_valid(condition, main_ok, side_ok),
               "agent_status": {r.label: r.status for r in results},
               "agent_steps": {r.label: r.steps for r in results},
               "seconds": round(time.time() - t0, 1), "ticker_errors": ticker_err[:2000],
               "plan_revision": sc.revision, "image": IMAGE}
    done.write_text(json.dumps(summary, indent=1))
    log.info("%s/%s/%02d main=%s side=%s status=%s %.0fs", sc.name, condition, k, main_ok, side_ok,
             summary["agent_status"], summary["seconds"])
    return summary
