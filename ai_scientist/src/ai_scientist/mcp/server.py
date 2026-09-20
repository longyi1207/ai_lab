"""MCP server over the same control plane the CLI uses (SPEC §4.4).

Transport is newline-delimited JSON-RPC 2.0 on stdio, implemented against the protocol
directly so the package keeps zero runtime dependencies for this path.

Read-only tools work with no daemon (they read `fs` + state); tools that change running work
start the daemon on demand. That is what makes the IDE-primary UX honest: the chat drives,
the daemon survives the chat.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..daemon.client import DaemonClient, DaemonUnavailable
from ..domain import available as available_domains
from ..domain import load_domain
from ..fs_layout import Workspace
from ..ops.state import StateStore
from ..report import build_report
from ..search import MapElites
from ..skills_loader import SkillRegistry

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "ai-scientist"


class ToolError(RuntimeError):
    pass


def _project_schema(**extra: Any) -> dict[str, Any]:
    properties = {"project": {"type": "string", "description": "Project workspace directory"}}
    properties.update(extra)
    return {
        "type": "object",
        "properties": properties,
        "required": ["project"],
    }


class ToolRegistry:
    """Maps MCP tool names onto control-plane calls and offline readers."""

    def __init__(self, default_project: str | None = None) -> None:
        self.default_project = default_project

    # ---- helpers ----
    def _resolve(self, args: dict[str, Any]) -> Workspace:
        project = args.get("project") or self.default_project
        if not project:
            raise ToolError("no project given and no default project configured")
        ws = Workspace(project)
        if not ws.initialized:
            raise ToolError(f"not an ai_scientist project: {ws.root} (run sci_init first)")
        return ws

    def _control(self, args: dict[str, Any], method: str, *, ensure: bool = False, **kwargs: Any):
        ws = self._resolve(args)
        client = DaemonClient(ws.root)
        if ensure and not client.running:
            client.ensure()
        try:
            return client.call(method, **kwargs)
        except DaemonUnavailable as exc:
            raise ToolError(str(exc)) from exc

    # ---- tools ----
    def definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "sci_init",
                "description": "Create a project workspace (metadata + config + fs skeleton).",
                "inputSchema": _project_schema(
                    question={"type": "string"},
                    domain={"type": "string", "description": f"one of {available_domains()}"},
                    budget_usd={"type": "number"},
                ),
            },
            {
                "name": "sci_status",
                "description": (
                    "Queue depth, workers, locks, spend, archive occupancy, top elites. "
                    "Works without a daemon."
                ),
                "inputSchema": _project_schema(),
            },
            {
                "name": "sci_start_run",
                "description": (
                    "Start (or attach to) the daemon and let it search up to job_budget jobs. "
                    "Returns immediately; the daemon keeps running after this chat ends."
                ),
                "inputSchema": _project_schema(job_budget={"type": "integer"}),
            },
            {
                "name": "sci_run_sync",
                "description": (
                    "Run a bounded study synchronously and return the final status. Use only for "
                    "small job counts; long runs belong to sci_start_run."
                ),
                "inputSchema": _project_schema(
                    jobs={"type": "integer"}, timeout_s={"type": "number"}
                ),
            },
            {
                "name": "sci_pause",
                "description": "Gate the scheduler; running jobs finish.",
                "inputSchema": _project_schema(),
            },
            {
                "name": "sci_resume",
                "description": "Un-gate the scheduler.",
                "inputSchema": _project_schema(),
            },
            {
                "name": "sci_set_concurrency",
                "description": "Change max concurrent jobs at runtime (no code change).",
                "inputSchema": {
                    **_project_schema(n={"type": "integer"}),
                    "required": ["project", "n"],
                },
            },
            {
                "name": "sci_elites",
                "description": "Top archive elites with fitness, cell, flags, and claims.",
                "inputSchema": _project_schema(n={"type": "integer"}),
            },
            {
                "name": "sci_map",
                "description": "Archive occupancy over the domain's descriptor axes.",
                "inputSchema": _project_schema(),
            },
            {
                "name": "sci_pin",
                "description": "Make an elite immortal in its cell (taste injection).",
                "inputSchema": {
                    **_project_schema(elite_id={"type": "string"}, pinned={"type": "boolean"}),
                    "required": ["project", "elite_id"],
                },
            },
            {
                "name": "sci_ban",
                "description": "Remove an elite from the archive.",
                "inputSchema": {
                    **_project_schema(elite_id={"type": "string"}),
                    "required": ["project", "elite_id"],
                },
            },
            {
                "name": "sci_restart_worker",
                "description": "Kill and requeue one job's worker.",
                "inputSchema": {
                    **_project_schema(job_id={"type": "string"}),
                    "required": ["project", "job_id"],
                },
            },
            {
                "name": "sci_tail",
                "description": "Tail one job's trial log and locate its results writeup.",
                "inputSchema": {
                    **_project_schema(job_id={"type": "string"}, lines={"type": "integer"}),
                    "required": ["project", "job_id"],
                },
            },
            {
                "name": "sci_events",
                "description": "Recent ops events (starts, requeues, budget stops, ingests).",
                "inputSchema": _project_schema(limit={"type": "integer"}),
            },
            {
                "name": "sci_report",
                "description": "Build the Phase-3 final report and return its path.",
                "inputSchema": _project_schema(narrative={"type": "boolean"}),
            },
            {
                "name": "sci_stop",
                "description": "Stop the daemon for this project.",
                "inputSchema": _project_schema(),
            },
            {
                "name": "sci_skills",
                "description": "List available agent skills (portable to any host).",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "sci_ask",
                "description": (
                    "Outer harness agent: route anytime human NL via outer_route, "
                    "optionally executing control calls."
                ),
                "inputSchema": _project_schema(
                    message={"type": "string", "description": "Human utterance"},
                    dry_run={
                        "type": "boolean",
                        "description": "If true, route only; do not execute controls",
                    },
                ),
            },
            {
                "name": "sci_domains",
                "description": "List registered domain packs and their descriptor axes.",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    def handlers(self) -> dict[str, Callable[[dict[str, Any]], Any]]:
        return {
            "sci_init": self.t_init,
            "sci_status": self.t_status,
            "sci_start_run": self.t_start_run,
            "sci_run_sync": self.t_run_sync,
            "sci_pause": lambda a: self._control(a, "pause"),
            "sci_resume": lambda a: self._control(a, "resume"),
            "sci_set_concurrency": lambda a: self._control(a, "set_concurrency", n=int(a["n"])),
            "sci_elites": lambda a: self._elites(a),
            "sci_map": self.t_map,
            "sci_pin": lambda a: self._control(
                a, "pin", elite_id=a["elite_id"], pinned=bool(a.get("pinned", True))
            ),
            "sci_ban": lambda a: self._control(a, "ban", elite_id=a["elite_id"]),
            "sci_restart_worker": lambda a: self._control(a, "restart_worker", job_id=a["job_id"]),
            "sci_tail": self.t_tail,
            "sci_events": self.t_events,
            "sci_report": self.t_report,
            "sci_stop": self.t_stop,
            "sci_skills": lambda a: [
                {"id": s.id, "role": s.role, "description": s.description}
                for s in SkillRegistry().load().all()
            ],
            "sci_ask": self.t_ask,
            "sci_domains": lambda a: [
                {
                    "domain": d,
                    "axes": [{"name": ax.name, "bins": ax.bins} for ax in load_domain(d).axes()],
                }
                for d in available_domains()
            ],
        }

    def call(self, name: str, args: dict[str, Any]) -> Any:
        handler = self.handlers().get(name)
        if handler is None:
            raise ToolError(f"unknown tool {name!r}")
        return handler(args or {})

    # -- individual tools --
    def t_init(self, args: dict[str, Any]) -> dict[str, Any]:
        from ..schema import Budget, EngineConfig, Metadata

        project = args.get("project") or self.default_project
        if not project:
            raise ToolError("project is required")
        ws = Workspace(project)
        domain = str(args.get("domain", "fake_toy"))
        load_domain(domain)
        ws.init(
            metadata=Metadata(
                project_id=ws.root.name,
                question=str(args.get("question", "")),
                budget=Budget(max_usd=float(args.get("budget_usd", 30.0))),
                credentials_refs=[
                    "AZURE_OPENAI_ENDPOINT",
                    "AZURE_OPENAI_API_KEY",
                    "AZURE_OPENAI_DEPLOYMENT",
                ],
            ),
            config=EngineConfig(domain=domain),
        )
        return {"project": str(ws.root), "domain": domain}

    def t_status(self, args: dict[str, Any]) -> dict[str, Any]:
        ws = self._resolve(args)
        client = DaemonClient(ws.root)
        if client.running:
            return client.call("status")
        from ..daemon.orchestrator import Orchestrator

        store = StateStore(ws.db_path)
        try:
            payload = Orchestrator(ws, store).status()
        finally:
            store.close()
        payload["daemon"] = None
        return payload

    def t_start_run(self, args: dict[str, Any]) -> dict[str, Any]:
        ws = self._resolve(args)
        client = DaemonClient(ws.root)
        info = client.ensure()
        budget = args.get("job_budget")
        if budget is not None:
            client.call("set_job_budget", n=int(budget))
        return {
            "daemon_pid": info["pid"],
            "control_port": info["port"],
            "job_budget": budget,
            "note": "daemon runs independently of this chat session",
        }

    def t_run_sync(self, args: dict[str, Any]) -> dict[str, Any]:
        from ..daemon.server import Daemon

        ws = self._resolve(args)
        if DaemonClient(ws.root).running:
            raise ToolError("a daemon is already running for this project; use sci_status instead")
        daemon = Daemon(ws.root)
        try:
            daemon.store.set_runtime("job_budget", int(args.get("jobs", 6)))
            outcome = daemon.run_until_idle(timeout_s=float(args.get("timeout_s", 120.0)))
            status = daemon.c_status()
        finally:
            daemon.stop()
        return {
            "steps": outcome["steps"],
            "timed_out": outcome["timed_out"],
            "jobs": status["jobs"],
            "search": status["search"],
            "spend": status["spend"],
        }

    def _elites(self, args: dict[str, Any]) -> Any:
        ws = self._resolve(args)
        client = DaemonClient(ws.root)
        n = int(args.get("n", 10))
        if client.running:
            return client.call("elites", n=n)
        return self.t_status(args)["top_elites"][:n]

    def t_map(self, args: dict[str, Any]) -> dict[str, Any]:
        ws = self._resolve(args)
        domain = load_domain(ws.read_config().domain)
        archive = MapElites.load(ws.map_path, domain.axes())
        return {
            "axes": [{"name": a.name, "bins": a.bins, "edges": a.edges} for a in archive.axes],
            "cells_filled": len(archive.cells),
            "cells_total": archive.total_cells,
            "occupancy": round(archive.occupancy, 4),
            "cells": [
                {"cell": list(cell), "fitness": rec.fitness, "elite_id": rec.elite_id}
                for cell, rec in sorted(archive.cells.items())
            ],
        }

    def t_tail(self, args: dict[str, Any]) -> dict[str, Any]:
        ws = self._resolve(args)
        job_id = str(args["job_id"])
        lines = int(args.get("lines", 40))
        log_path = ws.job_dir(job_id) / "logs" / "trial.log"
        writeup = ws.job_dir(job_id) / "results_writeup.md"
        return {
            "job_id": job_id,
            "log_path": str(log_path),
            "lines": log_path.read_text().splitlines()[-lines:] if log_path.exists() else [],
            "writeup": writeup.read_text() if writeup.exists() else None,
        }

    def t_events(self, args: dict[str, Any]) -> list[dict[str, Any]]:
        ws = self._resolve(args)
        store = StateStore(ws.db_path)
        try:
            return store.recent_events(int(args.get("limit", 30)))
        finally:
            store.close()

    def t_report(self, args: dict[str, Any]) -> dict[str, Any]:
        ws = self._resolve(args)
        path = build_report(ws.root, narrative=bool(args.get("narrative", True)))
        return {"path": str(path), "text": path.read_text()[:20000]}

    def t_stop(self, args: dict[str, Any]) -> dict[str, Any]:
        ws = self._resolve(args)
        return {"stopped": DaemonClient(ws.root).stop()}

    def t_ask(self, args: dict[str, Any]) -> dict[str, Any]:
        from ..outer import OuterAgent

        ws = self._resolve(args)
        message = str(args.get("message") or "").strip()
        if not message:
            raise ToolError("message is required")
        dry_run = bool(args.get("dry_run", False))
        client = DaemonClient(ws.root)

        def call_control(method: str, call_args: dict[str, Any]) -> Any:
            if client.running:
                return client.call(method, **call_args)
            # Start daemon for mutating calls so Outer can actually steer.
            if method not in {"status", "elites", "events", "tail"}:
                client.ensure()
                return client.call(method, **call_args)
            from ..daemon.orchestrator import Orchestrator

            store = StateStore(ws.db_path)
            try:
                if method == "status":
                    return Orchestrator(ws, store).status()
                if method == "elites":
                    return client.call("elites") if client.running else []
                if method == "events":
                    return store.recent_events(int(call_args.get("limit", 30)))
                return {"job_id": call_args.get("job_id")}
            finally:
                store.close()

        decision = OuterAgent(
            ws, execute=not dry_run, call_control=call_control if not dry_run else None
        ).handle(message)
        return decision.to_dict()


class McpServer:
    """Minimal MCP request dispatcher (transport-agnostic, so it is unit-testable)."""

    def __init__(self, default_project: str | None = None) -> None:
        self.tools = ToolRegistry(default_project)
        self.initialized = False

    def handle(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method", "")
        req_id = request.get("id")
        if method == "initialize":
            self.initialized = True
            return _ok(
                req_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": _version()},
                },
            )
        if method in {"notifications/initialized", "initialized"}:
            return None  # notification: no response
        if method == "ping":
            return _ok(req_id, {})
        if method == "tools/list":
            return _ok(req_id, {"tools": self.tools.definitions()})
        if method == "tools/call":
            params = request.get("params") or {}
            name = params.get("name", "")
            args = params.get("arguments") or {}
            try:
                result = self.tools.call(name, args)
            except ToolError as exc:
                return _ok(req_id, _content(str(exc), is_error=True))
            except Exception as exc:  # noqa: BLE001 - surface as tool error, not transport error
                return _ok(req_id, _content(f"{type(exc).__name__}: {exc}", is_error=True))
            return _ok(req_id, _content(json.dumps(result, indent=2, default=str)))
        if req_id is None:
            return None
        return _error(req_id, -32601, f"method not found: {method}")

    def serve_stdio(self, stdin: Any = None, stdout: Any = None) -> None:
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                stdout.write(json.dumps(_error(None, -32700, "parse error")) + "\n")
                stdout.flush()
                continue
            response = self.handle(request)
            if response is not None:
                stdout.write(json.dumps(response, default=str) + "\n")
                stdout.flush()


def _version() -> str:
    from .. import __version__

    return __version__


def _ok(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _content(text: str, *, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="ai_scientist MCP server (stdio)")
    parser.add_argument("--project", default=None, help="Default project so tool calls can omit it")
    args = parser.parse_args(argv)
    project = str(Path(args.project).resolve()) if args.project else None
    McpServer(project).serve_stdio()
    return 0


if __name__ == "__main__":  # pragma: no cover - process entry point
    raise SystemExit(main())
