"""Daemon: the always-on half of the system.

Three deterministic loops (scheduler, healthcheck, orchestrator) plus a Phase-2 ops
agent loop (LLM soft priorities) and a localhost JSON-RPC control plane shared by the
CLI and MCP. Deterministic loops contain no model calls, so an unavailable provider
degrades science throughput / soft prioritization but never supervision.
"""

from __future__ import annotations

import json
import os
import secrets
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ..fs_layout import Workspace
from ..ops.health import HealthMonitor, pid_alive, terminate
from ..ops.phase2_ops import Phase2OpsAgent
from ..ops.scheduler import Scheduler
from ..ops.state import StateStore
from .orchestrator import Orchestrator


class ControlError(RuntimeError):
    pass


class Daemon:
    def __init__(
        self,
        project: str | Path,
        *,
        seed: int | None = None,
        spawn: Callable | None = None,
    ) -> None:
        self.ws = Workspace(project)
        if not self.ws.initialized:
            raise ControlError(f"not an ai_scientist project: {self.ws.root} (run `sci init`)")
        self.config = self.ws.read_config()
        self.store = StateStore(self.ws.db_path)
        self.scheduler = Scheduler(self.ws, self.store, self.config, spawn=spawn)
        self.health = HealthMonitor(self.store, self.config)
        self.orchestrator = Orchestrator(self.ws, self.store, seed=seed)
        self.ops_agent = Phase2OpsAgent(self.ws, self.store, self.config)
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._httpd: ThreadingHTTPServer | None = None
        self.started_at: datetime | None = None
        self._ops_last_mono: float = 0.0

    # ---- single step (used by loops, tests, and synchronous runs) ----
    def step(self) -> dict[str, Any]:
        health = self.health.tick()
        sched = self.scheduler.tick()
        orch = self.orchestrator.tick()
        ops = self._maybe_ops_triage(force=False)
        return {
            "health": {
                "stale": health.stale,
                "crashed": health.crashed,
                "timed_out": health.timed_out,
                "requeued": health.requeued,
                "failed": health.failed,
                "locks_released": health.locks_released,
            },
            "scheduler": {"started": sched.started, "busy": sched.skipped_busy},
            "orchestrator": {
                "ingested": orch.ingested,
                "inserted": orch.inserted,
                "enqueued": orch.enqueued,
                "skipped": orch.skipped_reason,
            },
            "ops_triage": ops,
        }

    def _maybe_ops_triage(self, *, force: bool) -> dict[str, Any]:
        ops_cfg = self.config.ops
        if not ops_cfg.ops_triage_enabled:
            return {"skipped": "disabled"}
        now = time.monotonic()
        if not force and (now - self._ops_last_mono) < ops_cfg.ops_triage_tick_s:
            return {"skipped": "rate_limited"}
        self._ops_last_mono = now
        return self.ops_agent.tick().to_dict()

    def idle(self) -> bool:
        counts = self.store.counts_by_status()
        if counts.get("queued", 0) or counts.get("running", 0):
            return False
        return not self.store.pending_ingest()

    def settle(self) -> dict[str, Any]:
        """Ingest the last finished trials and release their locks.

        Without this, a synchronous run can return while locks are still held for
        already-finished jobs — capacity that only a later health tick would reclaim.
        """
        ingested = self.orchestrator.ingest_pending()
        health = self.health.tick()
        return {"ingested": ingested.ingested, "locks_released": health.locks_released}

    def run_until_idle(self, *, timeout_s: float = 120.0, tick_s: float = 0.1) -> dict[str, Any]:
        """Drive the study synchronously until nothing is left to do (or timeout)."""
        deadline = time.monotonic() + timeout_s
        self.health.reconcile_on_start()
        self.orchestrator.bootstrap()
        steps = 0
        last: dict[str, Any] = {}
        while time.monotonic() < deadline:
            last = self.step()
            steps += 1
            if self.idle() and last["orchestrator"]["skipped"] in {
                "budget_exceeded",
                "generation_cap",
                "job_budget",
            }:
                break
            if self.idle() and not last["orchestrator"]["enqueued"]:
                break
            time.sleep(tick_s)
        timed_out = time.monotonic() >= deadline
        return {"steps": steps, "last": last, "timed_out": timed_out, "settled": self.settle()}

    # ---- loops ----
    def _loop(self, name: str, interval: float, fn: Callable[[], Any]) -> None:
        while not self._stop.wait(interval):
            try:
                fn()
            except Exception as exc:  # noqa: BLE001 - a loop must never die silently
                self.store.add_event(
                    "loop_error", {"loop": name, "error": f"{type(exc).__name__}: {exc}"}
                )

    def start(self, *, serve_http: bool = True) -> dict[str, Any]:
        self.started_at = datetime.now(UTC)
        self.health.reconcile_on_start()
        self.orchestrator.bootstrap()
        ops = self.config.ops
        specs = [
            ("scheduler", ops.scheduler_tick_s, lambda: self.scheduler.tick()),
            ("health", ops.health_tick_s, lambda: self.health.tick()),
            ("orchestrator", max(ops.scheduler_tick_s, 0.25), lambda: self.orchestrator.tick()),
            (
                "ops_triage",
                max(ops.ops_triage_tick_s, 1.0),
                lambda: self._maybe_ops_triage(force=True),
            ),
        ]
        for name, interval, fn in specs:
            thread = threading.Thread(
                target=self._loop, args=(name, interval, fn), name=f"sci-{name}", daemon=True
            )
            thread.start()
            self._threads.append(thread)

        info: dict[str, Any] = {
            "pid": os.getpid(),
            "project": str(self.ws.root),
            "started_at": self.started_at.isoformat(),
            "host": None,
            "port": None,
            "token": None,
        }
        if serve_http:
            token = secrets.token_urlsafe(24)
            self._httpd = _build_server(self, ops.control_host, ops.control_port, token)
            host, port = self._httpd.server_address[:2]
            info.update({"host": str(host), "port": int(port), "token": token})
            threading.Thread(
                target=self._httpd.serve_forever,
                kwargs={"poll_interval": 0.2},
                name="sci-control",
                daemon=True,
            ).start()
        self._write_info(info)
        self.store.add_event("daemon_started", {k: v for k, v in info.items() if k != "token"})
        return info

    def _write_info(self, info: dict[str, Any]) -> None:
        path = self.ws.daemon_info_path
        self.ws.write_json(path, info)
        try:
            os.chmod(path, 0o600)
        except OSError:  # pragma: no cover - platform dependent
            pass

    def serve_forever(self) -> None:  # pragma: no cover - blocking entry point
        try:
            while not self._stop.wait(0.5):
                pass
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        self._stop.set()
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        for thread in self._threads:
            thread.join(timeout=2.0)
        self._threads.clear()
        self.store.add_event("daemon_stopped", {})
        self.ws.daemon_info_path.unlink(missing_ok=True)
        self.store.close()

    # ---- control plane ----
    def call(self, method: str, args: dict[str, Any] | None = None) -> Any:
        args = args or {}
        handler = self.controls().get(method)
        if handler is None:
            raise ControlError(f"unknown control method {method!r}")
        self.ws.append_audit("control", {"method": method, "args": args})
        return handler(**args)

    def controls(self) -> dict[str, Callable[..., Any]]:
        return {
            "status": self.c_status,
            "pause": self.c_pause,
            "resume": self.c_resume,
            "set_concurrency": self.c_set_concurrency,
            "set_job_budget": self.c_set_job_budget,
            "pin": self.c_pin,
            "ban": self.c_ban,
            "restart_worker": self.c_restart_worker,
            "tail": self.c_tail,
            "elites": self.c_elites,
            "events": self.c_events,
            "step": self.c_step,
            "shutdown": self.c_shutdown,
        }

    # -- handlers --
    def c_status(self) -> dict[str, Any]:
        status = self.orchestrator.status()
        status["daemon"] = {
            "pid": os.getpid(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "loops": [t.name for t in self._threads if t.is_alive()],
        }
        return status

    def c_pause(self) -> dict[str, Any]:
        self.store.set_runtime("paused", True)
        self.store.add_event("paused", {})
        return {"paused": True}

    def c_resume(self) -> dict[str, Any]:
        self.store.set_runtime("paused", False)
        self.store.set_runtime("budget_alerted", False)
        self.store.add_event("resumed", {})
        return {"paused": False}

    def c_set_concurrency(self, n: int) -> dict[str, Any]:
        n = int(n)
        if n < 0:
            raise ControlError("concurrency must be >= 0")
        self.store.set_runtime("concurrency", n)
        self.store.add_event("concurrency_changed", {"n": n})
        return {"concurrency": n}

    def c_set_job_budget(self, n: int | None = None) -> dict[str, Any]:
        self.store.set_runtime("job_budget", None if n is None else int(n))
        return {"job_budget": n}

    def c_pin(self, elite_id: str, pinned: bool = True) -> dict[str, Any]:
        ok = self.orchestrator.engine.archive.pin(elite_id, bool(pinned))
        if not ok:
            raise ControlError(f"no such elite {elite_id!r}")
        self.orchestrator.engine.save()
        self.store.add_event("elite_pinned", {"elite_id": elite_id, "pinned": bool(pinned)})
        return {"elite_id": elite_id, "pinned": bool(pinned)}

    def c_ban(self, elite_id: str) -> dict[str, Any]:
        ok = self.orchestrator.engine.archive.remove(elite_id)
        if not ok:
            raise ControlError(f"no such elite {elite_id!r}")
        self.orchestrator.engine.save()
        self.store.add_event("elite_banned", {"elite_id": elite_id})
        return {"elite_id": elite_id, "removed": True}

    def c_restart_worker(self, job_id: str) -> dict[str, Any]:
        job = self.store.get_job(job_id)
        if job is None:
            raise ControlError(f"no such job {job_id!r}")
        if job.pid and pid_alive(job.pid):
            terminate(job.pid)
        self.store.release_locks(job_id)
        self.store.requeue(job_id, "restart requested")
        self.store.add_event("worker_restart_requested", {"job_id": job_id})
        return {"job_id": job_id, "status": "queued"}

    def c_tail(self, job_id: str, lines: int = 40) -> dict[str, Any]:
        job_dir = self.ws.job_dir(job_id)
        log_path = job_dir / "logs" / "trial.log"
        text = log_path.read_text().splitlines()[-int(lines) :] if log_path.exists() else []
        writeup = job_dir / "results_writeup.md"
        return {
            "job_id": job_id,
            "log_path": str(log_path),
            "lines": text,
            "writeup_ref": str(writeup) if writeup.exists() else None,
        }

    def c_elites(self, n: int = 10) -> list[dict[str, Any]]:
        return self.orchestrator.engine.top_elites(int(n))

    def c_events(self, limit: int = 30) -> list[dict[str, Any]]:
        return self.store.recent_events(int(limit))

    def c_step(self) -> dict[str, Any]:
        return self.step()

    def c_shutdown(self) -> dict[str, Any]:
        threading.Thread(target=self.stop, name="sci-shutdown", daemon=True).start()
        return {"stopping": True}


def _build_server(daemon: Daemon, host: str, port: int, token: str) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: Any) -> None:  # silence stderr spam
            return

        def _respond(self, code: int, payload: Any) -> None:
            body = json.dumps(payload, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:  # noqa: N802 - http.server API
            if self.path != "/rpc":
                self._respond(404, {"error": "not found"})
                return
            if self.headers.get("X-Sci-Token") != token:
                self._respond(403, {"error": "bad token"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            try:
                request = json.loads(self.rfile.read(length) or b"{}")
                result = daemon.call(request.get("method", ""), request.get("args") or {})
            except ControlError as exc:
                self._respond(400, {"error": str(exc)})
                return
            except Exception as exc:  # noqa: BLE001
                self._respond(500, {"error": f"{type(exc).__name__}: {exc}"})
                return
            self._respond(200, {"result": result})

        def do_GET(self) -> None:  # noqa: N802 - liveness probe
            if self.path == "/healthz":
                self._respond(200, {"ok": True})
            else:
                self._respond(404, {"error": "not found"})

    return ThreadingHTTPServer((host, port), Handler)
