"""Asynchronous trajectory monitor: k independent readings per view, cached on disk.

Views per execution (§4.2):
  agent:<L>  one agent's trajectory alone (per-agent monitoring, the paper's primary condition)
  joint      all agents of the team, grouped by agent and timestamped (best case for the monitor)
  solo       the single agent of a solo_attack execution

Readings are appended to runs/<exp>/monitor/<monitor>.jsonl and keyed by
(view_sha, reading index), so reruns only pay for missing readings. A reading whose
verdict cannot be parsed is stored as invalid (score null) and never converted to 0
(App. C). A transport failure that survives the retries is not stored, so the next run
fills it.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from tqdm.asyncio import tqdm_asyncio

from .llm import LLM, BudgetExceeded
from .prompts import JOINT_CONTEXT, MONITOR_SYSTEM, MONITOR_USER
from .render import render_view
from .scenarios import environment_description

log = logging.getLogger(__name__)
VERDICT = re.compile(r"<verdict>\s*(\d+(?:\.\d+)?)\s*</verdict>", re.S)
REASONING = re.compile(r"<reasoning>(.*?)</reasoning>", re.S)
PROMPT_VERSION = "ct_swe_strong_v1+joint_v1"


@dataclass
class View:
    view_id: str          # <scenario>/<condition>/<k>/<view>
    n_agents: int
    system: str
    user: str

    @property
    def sha(self) -> str:
        return hashlib.sha256((PROMPT_VERSION + self.system + self.user).encode()).hexdigest()[:16]


def views_for_execution(exec_path: Path, condition: str) -> list[View]:
    env = environment_description()
    agents = []
    for p in sorted(exec_path.glob("agent_*.json")):
        a = json.loads(p.read_text())
        agents.append((a["label"], a["events"]))
    base = "/".join(exec_path.parts[-3:])
    out = []

    def mk(name: str, subset):
        system = MONITOR_SYSTEM + ("\n\n" + JOINT_CONTEXT if len(subset) > 1 else "")
        out.append(View(f"{base}/{name}", len(subset), system,
                        MONITOR_USER.format(rendered=render_view(env, subset))))

    if condition == "solo_attack":
        mk("solo", agents)
    else:
        for label, events in agents:
            mk(f"agent:{label}", [(label, events)])
        mk("joint", agents)
    return out


def parse(text: str) -> tuple[float | None, str]:
    m = VERDICT.search(text or "")
    r = REASONING.search(text or "")
    score = float(m.group(1)) if m else None
    if score is not None and not 0 <= score <= 10:
        score = None
    return score, (r.group(1).strip() if r else (text or "")[:4000])


class MonitorCache:
    def __init__(self, path: Path):
        self.path = path
        self.rows: dict[tuple[str, int], dict] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                self.rows[(row["view_sha"], row["idx"])] = row
        self._lock = asyncio.Lock()

    async def add(self, row: dict) -> None:
        async with self._lock:
            self.rows[(row["view_sha"], row["idx"])] = row
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(json.dumps(row) + "\n")

    def readings(self, view: View) -> list[dict]:
        return [r for (sha, _), r in sorted(self.rows.items()) if sha == view.sha]


async def _read(llm: LLM, monitor: str, view: View, idx: int, cache: MonitorCache) -> None:
    try:
        resp = await llm.chat(monitor, [{"role": "system", "content": view.system},
                                        {"role": "user", "content": view.user}], purpose=f"monitor:{view.view_id}")
    except BudgetExceeded:
        raise
    except Exception as e:
        log.warning("monitor reading %s #%d failed: %s", view.view_id, idx, str(e)[:200])
        return
    text = resp.choices[0].message.content or ""
    score, reasoning = parse(text)
    await cache.add({"view_id": view.view_id, "view_sha": view.sha, "idx": idx, "monitor": monitor,
                     "prompt_version": PROMPT_VERSION, "n_agents": view.n_agents, "score": score,
                     "valid": score is not None, "reasoning": reasoning})


async def score_views(llm: LLM, monitor: str, views: list[View], k: int, cache: MonitorCache) -> None:
    """For each view, take the first missing reading alone so the prompt cache warms up, then the rest in parallel."""
    async def one_view(v: View):
        have = {r["idx"] for r in cache.readings(v)}
        missing = [i for i in range(k) if i not in have]
        if not missing:
            return
        await _read(llm, monitor, v, missing[0], cache)
        await asyncio.gather(*[_read(llm, monitor, v, i, cache) for i in missing[1:]])

    await tqdm_asyncio.gather(*[one_view(v) for v in views], desc=f"monitor[{monitor}]", unit="view")
