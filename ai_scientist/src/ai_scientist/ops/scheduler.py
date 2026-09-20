"""Scheduler: hard `when/where`. Search decides what is worth trying (DESIGN §3).

One tick pops queued jobs by priority, takes resource locks atomically, and spawns a
worker process. It never talks to a model.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ..fs_layout import Workspace
from ..schema import EngineConfig, Job, new_id
from .locks import InsufficientResources, ResourceBroker
from .state import StateStore


def worker_env() -> dict[str, str]:
    """Ensure a spawned worker can import the package from source or install."""
    env = dict(os.environ)
    src = str(Path(__file__).resolve().parents[2])
    existing = env.get("PYTHONPATH", "")
    if src not in existing.split(os.pathsep):
        env["PYTHONPATH"] = f"{src}{os.pathsep}{existing}" if existing else src
    return env


@dataclass
class TickResult:
    started: list[str]
    skipped_busy: int = 0
    rejected: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.rejected is None:
            self.rejected = []


class Scheduler:
    def __init__(
        self,
        workspace: Workspace,
        store: StateStore,
        config: EngineConfig,
        *,
        spawn: object | None = None,
    ) -> None:
        self.ws = workspace
        self.store = store
        self.config = config
        self.broker = ResourceBroker(config.resources)
        # Injectable so tests can run workers in-process instead of spawning.
        self._spawn = spawn or self._spawn_subprocess

    # ---- capacity ----
    @property
    def concurrency(self) -> int:
        return int(self.store.get_runtime("concurrency", self.config.ops.concurrency))

    @property
    def paused(self) -> bool:
        return bool(self.store.get_runtime("paused", False))

    def running_count(self) -> int:
        return len(self.store.list_jobs("running", limit=1000))

    # ---- main tick ----
    def tick(self) -> TickResult:
        result = TickResult(started=[])
        if self.paused:
            return result
        free_slots = self.concurrency - self.running_count()
        if free_slots <= 0:
            return result

        for job in self.store.list_jobs("queued", limit=free_slots * 4):
            if len(result.started) >= free_slots:
                break
            held = set(self.store.held_locks())
            try:
                lock_names = self.broker.plan_locks(job.resources, held)
            except InsufficientResources as exc:
                self.store.mark_terminal(job.job_id, "failed", f"unschedulable: {exc}")
                self.store.add_event("job_unschedulable", {"job_id": job.job_id, "error": str(exc)})
                result.rejected.append(job.job_id)
                continue
            if lock_names is None:
                result.skipped_busy += 1
                continue
            worker_id = new_id("wrk")
            if not self.store.try_start(job.job_id, lock_names, worker_id):
                result.skipped_busy += 1
                continue
            try:
                pid = self._spawn(job, worker_id)  # type: ignore[operator]
            except Exception as exc:  # noqa: BLE001 - spawn failure must not wedge the queue
                self.store.release_locks(job.job_id)
                self.store.requeue(job.job_id, f"spawn failed: {exc}")
                self.store.add_event("spawn_failed", {"job_id": job.job_id, "error": str(exc)})
                continue
            if pid is not None:
                self.store.set_pid(job.job_id, int(pid))
            self.store.add_event(
                "job_started",
                {"job_id": job.job_id, "worker_id": worker_id, "locks": lock_names, "pid": pid},
            )
            result.started.append(job.job_id)
        return result

    # ---- spawning ----
    def _spawn_subprocess(self, job: Job, worker_id: str) -> int:
        job_dir = self.ws.job_dir(job.job_id)
        (job_dir / "logs").mkdir(parents=True, exist_ok=True)
        stdout = open(job_dir / "logs" / "worker.log", "ab", buffering=0)  # noqa: SIM115
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "ai_scientist.ops.worker",
                "--project",
                str(self.ws.root),
                "--job-id",
                job.job_id,
                "--worker-id",
                worker_id,
            ],
            stdout=stdout,
            stderr=subprocess.STDOUT,
            env=worker_env(),
            cwd=str(self.ws.root),
            start_new_session=True,
        )
        return proc.pid
