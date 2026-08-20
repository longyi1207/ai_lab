"""Supervisor daemon (pillar 3.2): watches RUNNING runs for a dead
heartbeat, marks them STALE, alerts, and attempts auto-resume by launching
`dojo run --resume` as a detached subprocess. Also re-enqueues DLQ entries
whose backoff has elapsed.

`dojo supervisor start [--poll-interval 30]` runs `loop()`; `--detach` forks
it into the background. Pidfile at `<data_dir>/supervisor.pid`.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from research_dojo.alerts import dispatcher, rules
from research_dojo.config.settings import get_settings
from research_dojo.db.models import Run, RunStatus
from research_dojo.db.repositories import DLQRepo, RunRepo
from research_dojo.db.session import new_session

logger = logging.getLogger("research_dojo.supervisor")

DLQ_BASE_RETRY_SECONDS = 60
DLQ_MAX_RETRY_SECONDS = 3600


def pidfile_path() -> Path:
    return get_settings().resolve_data_dir() / "supervisor.pid"


def write_pidfile() -> None:
    pidfile_path().write_text(str(os.getpid()))


def remove_pidfile() -> None:
    path = pidfile_path()
    if path.exists():
        path.unlink()


def running_pid() -> int | None:
    path = pidfile_path()
    if not path.exists():
        return None
    try:
        pid = int(path.read_text().strip())
    except ValueError:
        return None
    try:
        os.kill(pid, 0)
    except OSError:
        return None
    return pid


def _seconds_since(dt: datetime | None) -> float:
    if dt is None:
        return 0.0
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return (datetime.now(UTC) - dt).total_seconds()


def _stale_threshold_for(run: Run, default_seconds: int) -> int:
    spec = run.spec_frozen_json or {}
    return int(spec.get("supervisor", {}).get("stale_after_seconds", default_seconds))


def _launch_resume(run_id: str, spec_path: str) -> bool:
    cmd = [sys.executable, "-m", "research_dojo.cli.main", "run",
           "--spec", spec_path, "--resume", "--run-id", run_id]
    logger.info("supervisor: auto-resuming run %s: %s", run_id, " ".join(cmd))
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return True
    except OSError as e:
        logger.error("supervisor: failed to launch resume for %s: %s", run_id, e)
        return False


def check_once(auto_resume: bool = True) -> dict:
    """One supervisor pass: mark stale runs, alert, auto-resume; re-enqueue
    due DLQ entries. Returns a summary dict (used by tests + `status`)."""
    settings = get_settings()
    session = new_session()
    summary = {"stale_marked": [], "resumed": [], "dlq_retried": []}
    try:
        running = [r for r in RunRepo.list(session) if r.status == RunStatus.RUNNING.value]
        for run in running:
            threshold = _stale_threshold_for(run, settings.stale_threshold_seconds)
            since = _seconds_since(run.heartbeat_at)
            if since <= threshold:
                continue

            RunRepo.set_status(session, run.run_id, RunStatus.STALE, error_summary=f"heartbeat stale {since:.0f}s")
            trigger = rules.run_stale(run.run_id, since, threshold)
            if trigger:
                dispatcher.dispatch(session, trigger, run.run_id)
            session.commit()
            summary["stale_marked"].append(run.run_id)

            spec_path = (run.spec_frozen_json or {}).get("_spec_path")
            if auto_resume and spec_path and Path(spec_path).exists():
                RunRepo.set_status(session, run.run_id, RunStatus.RUNNING)
                session.commit()
                if _launch_resume(run.run_id, spec_path):
                    summary["resumed"].append(run.run_id)
            else:
                logger.warning(
                    "supervisor: run %s marked STALE, no spec_path on record — manual `dojo resume` needed",
                    run.run_id,
                )

        resumed_this_tick: set[str] = set()
        for entry in DLQRepo.due_for_retry(session, settings.max_dlq_attempts):
            run = RunRepo.get(session, entry.run_id)
            if run is None:
                continue
            delay = min(DLQ_BASE_RETRY_SECONDS * (2 ** entry.attempts), DLQ_MAX_RETRY_SECONDS)
            DLQRepo.bump_attempt(session, entry.id, delay)
            session.commit()
            summary["dlq_retried"].append(entry.id)

            spec_path = (run.spec_frozen_json or {}).get("_spec_path")
            if run.run_id not in resumed_this_tick and spec_path and Path(spec_path).exists():
                if run.status != RunStatus.RUNNING.value:
                    RunRepo.set_status(session, run.run_id, RunStatus.RUNNING)
                    session.commit()
                _launch_resume(run.run_id, spec_path)
                resumed_this_tick.add(run.run_id)
    finally:
        session.close()
    return summary


def loop(poll_interval: int = 30, once: bool = False, auto_resume: bool = True) -> None:
    write_pidfile()
    logger.info("supervisor started (pid=%d, poll_interval=%ds)", os.getpid(), poll_interval)
    try:
        while True:
            try:
                summary = check_once(auto_resume=auto_resume)
                if summary["stale_marked"] or summary["resumed"] or summary["dlq_retried"]:
                    logger.info("supervisor tick: %s", summary)
            except Exception:  # noqa: BLE001 — one bad tick must not kill the daemon
                logger.exception("supervisor tick failed")
            if once:
                return
            time.sleep(poll_interval)
    finally:
        remove_pidfile()
