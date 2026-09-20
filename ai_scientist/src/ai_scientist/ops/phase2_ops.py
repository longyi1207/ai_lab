"""Phase-2 ops agent — soft fleet brain via tool-calling Agent + `ops_triage` skill.

Deterministic substrate still owns heartbeats, locks, restart, and kickoff. This loop
only emits *intents* (priorities, failure classes, concurrency) and applies them through
state APIs. An unavailable model degrades prioritization; it never stops the scheduler.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..agent import Agent, ToolSpec
from ..fs_layout import Workspace
from ..llm import LLMClient, get_llm
from ..schema import EngineConfig
from ..skills_loader import SkillRegistry
from .state import StateStore

FAILURE_ACTIONS = {"retry", "requeue", "drop"}
FAILURE_CLASSES = {"transient", "resource", "plan_bug", "budget"}

OPS_ROLE = """\
You are the Phase-2 ops agent for ai_scientist: the soft scheduling brain.
The deterministic substrate owns heartbeats, locks, restarts, and kickoff — you only
express priorities and policy. Follow the `ops_triage` skill (read_skill).
Never claim to have restarted or killed anything yourself; emit intents / use tools.
"""


@dataclass
class OpsTriageResult:
    priorities: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    concurrency: int | None = None
    notes: str = ""
    skipped: str | None = None
    model_used: str = "unavailable"
    tool_trace: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "priorities": self.priorities,
            "failures": self.failures,
            "concurrency": self.concurrency,
            "notes": self.notes,
            "skipped": self.skipped,
            "model_used": self.model_used,
            "tool_trace": self.tool_trace,
        }


class Phase2OpsAgent:
    """Call `ops_triage` via Agent, then apply validated intents to `StateStore`."""

    def __init__(
        self,
        workspace: Workspace,
        store: StateStore,
        config: EngineConfig,
        *,
        llm: LLMClient | None = None,
        skills: SkillRegistry | None = None,
    ) -> None:
        self.ws = workspace
        self.store = store
        self.config = config
        self.llm = llm or get_llm()
        self.skills = skills or SkillRegistry().load()

    def tick(self) -> OpsTriageResult:
        if not self.config.ops.ops_triage_enabled:
            return OpsTriageResult(skipped="disabled")

        queue = self._queue_payload()
        fleet = self._fleet_payload()
        failures = self._untriaged_failures()
        if not queue and not failures:
            return OpsTriageResult(skipped="nothing_to_triage")

        result = OpsTriageResult()
        tools = [
            ToolSpec(
                name="get_queue",
                description="Queued jobs with claims/params.",
                parameters={"type": "object", "properties": {}},
                handler=lambda: queue,
            ),
            ToolSpec(
                name="get_fleet",
                description="Running jobs, concurrency, spend vs budget.",
                parameters={"type": "object", "properties": {}},
                handler=lambda: fleet,
            ),
            ToolSpec(
                name="get_failures",
                description="Recent untriaged failures.",
                parameters={"type": "object", "properties": {}},
                handler=lambda: failures,
            ),
        ]
        agent = Agent(
            role=OPS_ROLE,
            llm=self.llm,
            skills=self.skills,
            tools=tools,
            expect_json=True,
            max_rounds=6,
        )
        try:
            out = agent.run(
                (
                    "Triage the fleet. Use get_queue / get_fleet / get_failures as needed, "
                    "follow ops_triage, then return JSON:\n"
                    '{"priorities":[{"job_id":"...","priority":0.0,"why":"..."}],'
                    '"failures":[{"job_id":"...","class":"transient","action":"retry|requeue|drop"}],'
                    '"concurrency":2,"notes":"one line"}'
                ),
                hint_skill="ops_triage",
                preload_skill=True,
            )
            result.model_used = out.model_used
            result.tool_trace = out.tool_trace
            payload = out.parsed
            if not isinstance(payload, dict) or payload.get("fake") is True:
                result.skipped = "no_usable_decision"
                return result
            result.notes = str(payload.get("notes") or "")
            self._apply(payload, result, known_failures={f["job_id"] for f in failures})
        except Exception as exc:  # noqa: BLE001
            result.skipped = f"model_unavailable: {type(exc).__name__}: {exc}"
            # Do not flood the event log — one marker is enough for debugging.
            if not self.store.get_runtime("ops_triage_alerted", False):
                self.store.set_runtime("ops_triage_alerted", True)
                self.store.add_event("ops_triage_unavailable", {"error": result.skipped})
            return result

        if result.priorities or result.failures or result.concurrency is not None or result.notes:
            self.store.add_event("ops_triage", result.to_dict())
            self.ws.append_audit("ops_triage", result.to_dict())
        else:
            result.skipped = result.skipped or "noop"
        return result

    def _queue_payload(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for job in self.store.list_jobs("queued", limit=50):
            cand = None
            try:
                cand = self.ws.read_candidate(job.candidate_id)
            except Exception:  # noqa: BLE001
                pass
            out.append(
                {
                    "job_id": job.job_id,
                    "candidate_id": job.candidate_id,
                    "priority": job.priority,
                    "attempts": job.attempts,
                    "resources": job.resources.model_dump(),
                    "claim": cand.hypothesis.claim if cand else None,
                    "params": cand.plan.params if cand else None,
                }
            )
        return out

    def _fleet_payload(self) -> dict[str, Any]:
        meta = self.ws.read_metadata()
        spend = self.store.total_spend()
        return {
            "counts": self.store.counts_by_status(),
            "concurrency": int(
                self.store.get_runtime("concurrency", self.config.ops.concurrency)
            ),
            "paused": bool(self.store.get_runtime("paused", False)),
            "spend": spend,
            "budget_max_usd": meta.budget.max_usd,
            "running": [
                {
                    "job_id": j.job_id,
                    "worker_id": j.worker_id,
                    "attempts": j.attempts,
                    "started_at": j.started_at.isoformat() if j.started_at else None,
                }
                for j in self.store.list_jobs("running", limit=50)
            ],
        }

    def _untriaged_failures(self) -> list[dict[str, Any]]:
        seen = set(self.store.get_runtime("ops_triaged_failures", []) or [])
        out: list[dict[str, Any]] = []
        for job in self.store.list_jobs("failed", limit=50):
            if job.job_id in seen:
                continue
            out.append(
                {
                    "job_id": job.job_id,
                    "candidate_id": job.candidate_id,
                    "attempts": job.attempts,
                    "error": job.error,
                    "finished_at": job.finished_at.isoformat() if job.finished_at else None,
                }
            )
        return out

    def _apply(
        self, payload: dict[str, Any], result: OpsTriageResult, *, known_failures: set[str]
    ) -> None:
        for item in payload.get("priorities") or []:
            if not isinstance(item, dict):
                continue
            job_id = str(item.get("job_id") or "")
            if not job_id or self.store.get_job(job_id) is None:
                continue
            try:
                priority = float(item["priority"])
            except (KeyError, TypeError, ValueError):
                continue
            self.store.set_priority(job_id, priority)
            result.priorities.append(
                {"job_id": job_id, "priority": priority, "why": str(item.get("why") or "")}
            )

        for item in payload.get("failures") or []:
            if not isinstance(item, dict):
                continue
            job_id = str(item.get("job_id") or "")
            if job_id not in known_failures:
                continue
            action = str(item.get("action") or "").lower()
            klass = str(item.get("class") or "transient").lower()
            if action not in FAILURE_ACTIONS:
                continue
            if klass not in FAILURE_CLASSES:
                klass = "transient"
            self._apply_failure(job_id, action=action, klass=klass)
            result.failures.append({"job_id": job_id, "class": klass, "action": action})
            self._mark_triaged(job_id)

        raw_conc = payload.get("concurrency")
        if raw_conc is not None:
            try:
                n = int(raw_conc)
            except (TypeError, ValueError):
                n = -1
            if n >= 0:
                n = min(n, max(self.config.ops.concurrency * 4, 8))
                self.store.set_runtime("concurrency", n)
                self.store.add_event("concurrency_changed", {"n": n, "source": "ops_triage"})
                result.concurrency = n

    def _apply_failure(self, job_id: str, *, action: str, klass: str) -> None:
        job = self.store.get_job(job_id)
        if job is None:
            return
        if action == "drop" or klass in {"plan_bug", "budget"}:
            self.store.add_event(
                "ops_failure_drop", {"job_id": job_id, "class": klass, "action": action}
            )
            return
        if job.attempts >= self.config.ops.max_attempts:
            self.store.add_event(
                "ops_failure_exhausted",
                {"job_id": job_id, "attempts": job.attempts, "class": klass},
            )
            return
        self.store.release_locks(job_id)
        self.store.requeue(job_id, f"ops_triage:{klass}:{action}")
        self.store.add_event(
            "ops_failure_requeue", {"job_id": job_id, "class": klass, "action": action}
        )

    def _mark_triaged(self, job_id: str) -> None:
        seen = list(self.store.get_runtime("ops_triaged_failures", []) or [])
        if job_id not in seen:
            seen.append(job_id)
            self.store.set_runtime("ops_triaged_failures", seen[-200:])
