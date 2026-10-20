"""Load scenario files and build the agent line-up for each condition.

Conditions:
  team_attack  three agents, public tickets + shared side task + per-agent plan (paper §5.1 "distributed")
  solo_attack  one agent with all three tickets, the team's combined permissions and the solo plan (paper "single agent")
  team_honest  three agents, public tickets only (benign teams for threshold calibration, App. C)
  team_noplan  three agents, side task but no plan (App. H.3); comms off unless --comms
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .agent import AgentConfig
from .prompts import ROLE_SYSTEM, SOLO_PREAMBLE, covert_block

ROOT = Path(__file__).resolve().parents[1]
SCEN_DIR = ROOT / "scenarios"
CONDITIONS = ("team_attack", "solo_attack", "team_honest", "team_noplan")


@dataclass
class Scenario:
    name: str
    side_task: str
    objective: str
    agents: list[dict]
    solo_plan: str
    revision: str
    raw: dict

    @property
    def main_tasks(self) -> list[str]:
        return [a["main_task"] for a in self.agents]


def load(name: str) -> Scenario:
    d = yaml.safe_load((SCEN_DIR / f"{name}.yaml").read_text())
    return Scenario(name=d["name"], side_task=d["side_task"], objective=d["objective"], agents=d["agents"],
                    solo_plan=d["solo"]["plan"], revision=d["revisions"][-1], raw=d)


def all_names() -> list[str]:
    return sorted(p.stem for p in SCEN_DIR.glob("*.yaml"))


def environment_description() -> str:
    return (SCEN_DIR / "environment_description.md").read_text()


def build_agents(sc: Scenario, condition: str, model: str, max_steps: int, comms: bool) -> list[AgentConfig]:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition}")
    if condition == "solo_attack":
        accounts = [a["account"] for a in sc.agents]
        task = SOLO_PREAMBLE.format(accounts=", ".join(accounts)) + "\n\n" + "\n\n".join(
            f"## Task {i + 1} (account {a['account']})\n{a['ticket'].strip()}" for i, a in enumerate(sc.agents))
        system = ROLE_SYSTEM.format(account="ops_lead") + "\n\n" + covert_block(sc.objective, sc.solo_plan)
        return [AgentConfig("A", "ops_lead", system, task, model, max_steps * 2, False)]
    out = []
    for a in sc.agents:
        system = ROLE_SYSTEM.format(account=a["account"])
        if condition == "team_attack":
            system += "\n\n" + covert_block(sc.objective, a["plan"])
        elif condition == "team_noplan":
            system += "\n\n" + covert_block(sc.objective, None)
        out.append(AgentConfig(a["label"], a["account"], system, a["ticket"].strip(), model, max_steps, comms))
    return out
