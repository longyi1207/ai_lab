"""Outer harness agent — headless twin of the IDE Outer.

In Cursor / Claude Code the Outer *is* the host agent: it discovers skills under
`.cursor/skills/` and calls MCP `sci_*` tools. This module exists for CLI / scripts /
tests when there is no IDE agent.

It runs a real tool-calling loop (`Agent`): system prompt = role + skill catalog + tools;
user message = human NL; skill body is loaded via `read_skill` (or preloaded for FakeLLM).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from .agent import Agent, ToolSpec
from .daemon.client import DaemonClient, DaemonUnavailable
from .daemon.orchestrator import Orchestrator
from .fs_layout import Workspace
from .llm import LLMClient, get_llm
from .ops.state import StateStore
from .skills_loader import SkillRegistry

ALLOWED_CONTROLS = frozenset(
    {
        "status",
        "pause",
        "resume",
        "set_concurrency",
        "set_job_budget",
        "pin",
        "ban",
        "restart_worker",
        "tail",
        "elites",
        "events",
    }
)
TARGETS = frozenset({"phase1", "orchestrator", "ops", "job", "report", "none"})

OUTER_ROLE = """\
You are the Outer harness agent for ai_scientist: the human's single conversational
entry point into a running study. You route and steer; you do not run experiments.

Follow the `outer_route` skill (read it with read_skill). Prefer reading state via tools
over guessing. Anything that spends money or kills work must be an explicit tool call.
If the message is ambiguous, ask one clarifying question instead of acting.
"""


@dataclass
class OuterDecision:
    target: str = "none"
    controls: list[dict[str, Any]] = field(default_factory=list)
    reply: str = ""
    clarify: str | None = None
    results: list[dict[str, Any]] = field(default_factory=list)
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    model_used: str = "unavailable"
    skipped: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "controls": self.controls,
            "reply": self.reply,
            "clarify": self.clarify,
            "results": self.results,
            "tool_trace": self.tool_trace,
            "model_used": self.model_used,
            "skipped": self.skipped,
        }


class OuterAgent:
    def __init__(
        self,
        workspace: Workspace,
        *,
        llm: LLMClient | None = None,
        skills: SkillRegistry | None = None,
        execute: bool = True,
        call_control: Callable[[str, dict[str, Any]], Any] | None = None,
    ) -> None:
        self.ws = workspace
        self.llm = llm or get_llm()
        self.skills = skills or SkillRegistry().load()
        self.execute = execute
        self._call_control = call_control

    def handle(self, message: str) -> OuterDecision:
        decision = OuterDecision()
        tools = self._control_tools()
        agent = Agent(
            role=OUTER_ROLE,
            llm=self.llm,
            skills=self.skills,
            tools=tools,
            expect_json=True,
            max_rounds=10,
        )
        try:
            result = agent.run(
                (
                    f"Human said:\n{message.strip()}\n\n"
                    f"Project: {self.ws.root}\n"
                    "Use tools as needed, then return JSON:\n"
                    '{"target":"phase1|orchestrator|ops|job|report|none",'
                    '"controls":[{"method":"...","args":{}}],'
                    '"reply":"...","clarify":null}'
                ),
                hint_skill="outer_route",
                preload_skill=True,
            )
        except Exception as exc:  # noqa: BLE001
            decision.skipped = f"agent_failed: {type(exc).__name__}: {exc}"
            decision.reply = (
                "Outer agent failed. Try `sci status` or use Cursor with MCP + skills. "
                f"({decision.skipped})"
            )
            return decision

        decision.model_used = result.model_used
        decision.tool_trace = result.tool_trace
        # Tool calls already executed during the loop when execute=True (handlers do it).
        for step in result.tool_trace:
            decision.results.append(
                {
                    "method": step.get("tool"),
                    "ok": "error" not in (step.get("result") or {}),
                    "result": step.get("result"),
                }
            )

        payload = result.parsed if isinstance(result.parsed, dict) else None
        if payload is None:
            decision.reply = result.text or "No structured reply."
            decision.skipped = "no_json_decision"
            self.ws.append_audit("outer_route", decision.to_dict())
            return decision

        decision.target = str(payload.get("target") or "none").lower()
        if decision.target not in TARGETS:
            decision.target = "none"
        decision.reply = str(payload.get("reply") or "")
        clarify = payload.get("clarify")
        decision.clarify = str(clarify) if clarify else None
        for item in payload.get("controls") or []:
            if isinstance(item, dict) and item.get("method") in ALLOWED_CONTROLS:
                args = item.get("args") if isinstance(item.get("args"), dict) else {}
                decision.controls.append({"method": str(item["method"]), "args": args})

        # If the model listed controls in JSON but didn't call tools (and execute), run them.
        if self.execute and decision.controls and not decision.clarify:
            already = {r.get("method") for r in decision.results}
            for call in decision.controls:
                if call["method"] in already:
                    continue
                try:
                    out = self._invoke(call["method"], call.get("args") or {})
                    decision.results.append(
                        {"method": call["method"], "ok": True, "result": out}
                    )
                except Exception as exc:  # noqa: BLE001
                    decision.results.append(
                        {
                            "method": call["method"],
                            "ok": False,
                            "error": f"{type(exc).__name__}: {exc}",
                        }
                    )

        self.ws.append_audit("outer_route", decision.to_dict())
        return decision

    def _control_tools(self) -> list[ToolSpec]:
        """MCP-equivalent tools the headless Outer can call."""

        def make(method: str, description: str, properties: dict[str, Any], required: list[str]):
            def handler(**kwargs: Any) -> Any:
                if not self.execute:
                    return {"dry_run": True, "method": method, "args": kwargs}
                return self._invoke(method, kwargs)

            return ToolSpec(
                name=method,
                description=description,
                parameters={
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
                handler=handler,
            )

        return [
            make("status", "Queue, workers, spend, top elites.", {}, []),
            make("pause", "Pause the scheduler (stop starting new jobs).", {}, []),
            make("resume", "Resume the scheduler.", {}, []),
            make(
                "set_concurrency",
                "Set runtime worker concurrency.",
                {"n": {"type": "integer"}},
                ["n"],
            ),
            make(
                "pin",
                "Pin an elite so search will not replace it.",
                {
                    "elite_id": {"type": "string"},
                    "pinned": {"type": "boolean"},
                },
                ["elite_id"],
            ),
            make("ban", "Remove an elite from the archive.", {"elite_id": {"type": "string"}}, ["elite_id"]),
            make(
                "restart_worker",
                "Kill and requeue a running job.",
                {"job_id": {"type": "string"}},
                ["job_id"],
            ),
            make(
                "tail",
                "Fetch writeup / log paths for a job.",
                {"job_id": {"type": "string"}},
                ["job_id"],
            ),
            make("elites", "List top elites.", {}, []),
            make(
                "events",
                "Recent ops events.",
                {"limit": {"type": "integer"}},
                [],
            ),
        ]

    def _invoke(self, method: str, args: dict[str, Any]) -> Any:
        if self._call_control is not None:
            return self._call_control(method, args)
        client = DaemonClient(self.ws.root)
        if client.running:
            return client.call(method, **args)
        if method in {"status", "elites", "events", "tail"}:
            return self._local_read(method, args)
        raise DaemonUnavailable(
            f"daemon not running; cannot execute mutating control {method!r} "
            "(start with `sci serve`, or use Cursor MCP)"
        )

    def _local_read(self, method: str, args: dict[str, Any]) -> Any:
        store = StateStore(self.ws.db_path)
        try:
            if method == "status":
                return Orchestrator(self.ws, store).status()
            if method == "elites":
                from .domain import load_domain
                from .search import MapElites

                archive = MapElites.load(
                    self.ws.map_path, load_domain(self.ws.read_config().domain).axes()
                )
                return [e.model_dump(mode="json") for e in archive.top(10)]
            if method == "events":
                return store.recent_events(int(args.get("limit", 30)))
            if method == "tail":
                job_id = str(args.get("job_id") or "")
                job_dir = self.ws.job_dir(job_id)
                writeup = job_dir / "results_writeup.md"
                log = job_dir / "logs" / "trial.log"
                return {
                    "job_id": job_id,
                    "writeup": writeup.read_text()[:8000] if writeup.exists() else None,
                    "log_tail": log.read_text()[-4000:] if log.exists() else None,
                }
        finally:
            store.close()
        raise RuntimeError(f"unsupported local read {method!r}")


__all__ = ["ALLOWED_CONTROLS", "OUTER_ROLE", "OuterAgent", "OuterDecision", "TARGETS"]
