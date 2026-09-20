"""Healthcheck: heartbeat timeouts, dead PIDs, job timeouts, lock hygiene.

This loop is the reason the daemon exists. It must keep working when the LLM provider is
down, so it contains no model calls and no optional imports.
"""

from __future__ import annotations

import os
import signal
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..schema import EngineConfig
from .state import StateStore


def pid_alive(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:  # exists, owned by someone else
        return True
    return True


def terminate(pid: int | None) -> None:
    if not pid:
        return
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            return
        except PermissionError:  # pragma: no cover - not ours to kill
            return


@dataclass
class HealthReport:
    stale: list[str] = field(default_factory=list)
    crashed: list[str] = field(default_factory=list)
    timed_out: list[str] = field(default_factory=list)
    requeued: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    locks_released: int = 0

    @property
    def acted(self) -> bool:
        return bool(self.stale or self.crashed or self.timed_out or self.locks_released)


class HealthMonitor:
    def __init__(self, store: StateStore, config: EngineConfig) -> None:
        self.store = store
        self.config = config

    def tick(self) -> HealthReport:
        report = HealthReport()
        ops = self.config.ops
        now = datetime.now(UTC)

        for job in self.store.list_jobs("running", limit=1000):
            reason: str | None = None
            if job.pid is not None and not pid_alive(job.pid):
                reason = f"worker pid {job.pid} vanished"
                report.crashed.append(job.job_id)
            elif ops.job_timeout_s and job.started_at:
                elapsed = (now - job.started_at).total_seconds()
                if elapsed > ops.job_timeout_s:
                    reason = f"exceeded job_timeout_s={ops.job_timeout_s:.0f} ({elapsed:.0f}s)"
                    report.timed_out.append(job.job_id)
            if reason is None:
                last = job.heartbeat_at or job.started_at
                if last and (now - last).total_seconds() > ops.heartbeat_timeout_s:
                    reason = (
                        f"heartbeat stale for {(now - last).total_seconds():.1f}s "
                        f"(timeout {ops.heartbeat_timeout_s:.0f}s)"
                    )
                    report.stale.append(job.job_id)
            if reason is None:
                continue
            self._recover(job.job_id, job.pid, job.attempts, reason, report)

        report.locks_released = self.store.release_orphan_locks()
        return report

    def _recover(
        self, job_id: str, pid: int | None, attempts: int, reason: str, report: HealthReport
    ) -> None:
        terminate(pid)
        self.store.release_locks(job_id)
        if attempts < self.config.ops.max_attempts:
            self.store.requeue(job_id, reason)
            report.requeued.append(job_id)
            self.store.add_event("job_requeued", {"job_id": job_id, "reason": reason})
        else:
            self.store.mark_terminal(job_id, "failed", f"{reason}; max attempts reached")
            report.failed.append(job_id)
            self.store.add_event("job_failed", {"job_id": job_id, "reason": reason})

    def reconcile_on_start(self) -> HealthReport:
        """After a daemon restart: adopt fresh workers, recover dead ones, drop stale locks."""
        report = HealthReport()
        for job in self.store.list_jobs("running", limit=1000):
            if pid_alive(job.pid):
                continue
            report.crashed.append(job.job_id)
            self._recover(job.job_id, job.pid, job.attempts, "daemon restart: worker gone", report)
        report.locks_released = self.store.release_orphan_locks()
        self.store.add_event(
            "daemon_reconciled",
            {"crashed": report.crashed, "locks_released": report.locks_released},
        )
        return report
