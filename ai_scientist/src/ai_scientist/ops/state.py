"""Ops state: the deterministic source of truth for jobs, locks, runtime and spend.

Plain sqlite3 on purpose — the watchdog must work when models, networks, and optional
dependencies are all unavailable. Kickoff is a single `BEGIN IMMEDIATE` transaction that
takes resource locks by primary key, so a job can never be started twice.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ..schema import TERMINAL_STATUSES, Job, ResourceRequest

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id       TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    priority     REAL NOT NULL DEFAULT 0,
    resources    TEXT NOT NULL,
    status       TEXT NOT NULL,
    worker_id    TEXT,
    pid          INTEGER,
    attempts     INTEGER NOT NULL DEFAULT 0,
    ingested     INTEGER NOT NULL DEFAULT 0,
    error        TEXT,
    created_at   TEXT NOT NULL,
    started_at   TEXT,
    finished_at  TEXT,
    heartbeat_at TEXT
);
CREATE INDEX IF NOT EXISTS jobs_status_idx ON jobs(status, priority DESC, created_at);

CREATE TABLE IF NOT EXISTS locks (
    name        TEXT PRIMARY KEY,
    job_id      TEXT NOT NULL,
    acquired_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS spend (
    job_id TEXT PRIMARY KEY,
    usd    REAL NOT NULL DEFAULT 0,
    tokens REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS events (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      TEXT NOT NULL,
    kind    TEXT NOT NULL,
    payload TEXT NOT NULL
);
"""


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


class StateStore:
    def __init__(self, db_path: str | Path) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, timeout=15.0, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA busy_timeout=15000")
        self.init_schema()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def __enter__(self) -> StateStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)
            self._conn.execute(
                "INSERT OR IGNORE INTO runtime(key, value) VALUES(?, ?)",
                ("schema_version", str(SCHEMA_VERSION)),
            )

    # ---- jobs ----
    def enqueue(self, job: Job) -> Job:
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO jobs(job_id, candidate_id, priority, resources, status, attempts,
                                    ingested, created_at)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (
                    job.job_id,
                    job.candidate_id,
                    job.priority,
                    json.dumps(job.resources.model_dump()),
                    job.status,
                    job.attempts,
                    int(job.ingested),
                    _iso(job.created_at),
                ),
            )
        return job

    def get_job(self, job_id: str) -> Job | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def list_jobs(self, status: str | Iterable[str] | None = None, limit: int = 200) -> list[Job]:
        query = "SELECT * FROM jobs"
        params: list[Any] = []
        if status:
            statuses = [status] if isinstance(status, str) else list(status)
            query += f" WHERE status IN ({','.join('?' * len(statuses))})"
            params.extend(statuses)
        query += " ORDER BY priority DESC, created_at ASC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_job(r) for r in rows]

    def counts_by_status(self) -> dict[str, int]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT status, COUNT(*) AS n FROM jobs GROUP BY status"
            ).fetchall()
        return {r["status"]: r["n"] for r in rows}

    def set_priority(self, job_id: str, priority: float) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE jobs SET priority = ? WHERE job_id = ?", (priority, job_id))

    def try_start(self, job_id: str, lock_names: list[str], worker_id: str) -> bool:
        """Atomically take locks and flip queued → running. False if contended."""
        now = _iso(_now())
        with self._lock:
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                row = self._conn.execute(
                    "SELECT status FROM jobs WHERE job_id = ?", (job_id,)
                ).fetchone()
                if row is None or row["status"] != "queued":
                    self._conn.rollback()
                    return False
                for name in lock_names:
                    self._conn.execute(
                        "INSERT INTO locks(name, job_id, acquired_at) VALUES(?,?,?)",
                        (name, job_id, now),
                    )
                self._conn.execute(
                    """UPDATE jobs
                          SET status='running', worker_id=?, started_at=?, heartbeat_at=?,
                              attempts = attempts + 1, error=NULL
                        WHERE job_id=?""",
                    (worker_id, now, now, job_id),
                )
                self._conn.commit()
                return True
            except sqlite3.IntegrityError:
                self._conn.rollback()
                return False
            except Exception:
                self._conn.rollback()
                raise

    def set_pid(self, job_id: str, pid: int | None) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE jobs SET pid = ? WHERE job_id = ?", (pid, job_id))

    def heartbeat(self, job_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE jobs SET heartbeat_at = ? WHERE job_id = ?", (_iso(_now()), job_id)
            )

    def mark_terminal(self, job_id: str, status: str, error: str | None = None) -> None:
        if status not in TERMINAL_STATUSES and status != "stale":
            raise ValueError(f"not a terminal status: {status}")
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE jobs SET status=?, error=?, finished_at=?, pid=NULL WHERE job_id=?",
                (status, error, _iso(_now()), job_id),
            )

    def requeue(self, job_id: str, error: str | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """UPDATE jobs
                      SET status='queued', worker_id=NULL, pid=NULL, started_at=NULL,
                          heartbeat_at=NULL, error=?
                    WHERE job_id=?""",
                (error, job_id),
            )

    def mark_ingested(self, job_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE jobs SET ingested=1 WHERE job_id=?", (job_id,))

    def pending_ingest(self) -> list[Job]:
        with self._lock:
            rows = self._conn.execute(
                """SELECT * FROM jobs
                    WHERE ingested = 0 AND status IN ('done','failed')
                    ORDER BY finished_at ASC"""
            ).fetchall()
        return [self._row_to_job(r) for r in rows]

    def stale_running(self, timeout_s: float) -> list[Job]:
        cutoff = _iso(_now() - timedelta(seconds=timeout_s))
        with self._lock:
            rows = self._conn.execute(
                """SELECT * FROM jobs
                    WHERE status='running'
                      AND (heartbeat_at IS NULL OR heartbeat_at < ?)""",
                (cutoff,),
            ).fetchall()
        return [self._row_to_job(r) for r in rows]

    # ---- locks ----
    def held_locks(self) -> dict[str, str]:
        with self._lock:
            rows = self._conn.execute("SELECT name, job_id FROM locks").fetchall()
        return {r["name"]: r["job_id"] for r in rows}

    def release_locks(self, job_id: str) -> int:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM locks WHERE job_id = ?", (job_id,))
        return cur.rowcount

    def release_orphan_locks(self) -> int:
        """Drop locks whose job is no longer running (crash/restart hygiene)."""
        with self._lock, self._conn:
            cur = self._conn.execute(
                """DELETE FROM locks WHERE job_id NOT IN
                   (SELECT job_id FROM jobs WHERE status='running')"""
            )
        return cur.rowcount

    # ---- runtime kv ----
    def set_runtime(self, key: str, value: Any) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO runtime(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)),
            )

    def get_runtime(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute("SELECT value FROM runtime WHERE key=?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except json.JSONDecodeError:
            return row["value"]

    # ---- spend ----
    def record_spend(self, job_id: str, usd: float, tokens: float) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO spend(job_id, usd, tokens) VALUES(?,?,?) "
                "ON CONFLICT(job_id) DO UPDATE SET usd=excluded.usd, tokens=excluded.tokens",
                (job_id, usd, tokens),
            )

    def total_spend(self) -> dict[str, float]:
        with self._lock:
            row = self._conn.execute(
                "SELECT COALESCE(SUM(usd),0) AS usd, COALESCE(SUM(tokens),0) AS tokens FROM spend"
            ).fetchone()
        return {"usd": float(row["usd"]), "tokens": float(row["tokens"])}

    # ---- events ----
    def add_event(self, kind: str, payload: dict[str, Any] | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO events(ts, kind, payload) VALUES(?,?,?)",
                (_iso(_now()), kind, json.dumps(payload or {}, default=str)),
            )

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT ts, kind, payload FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {"ts": r["ts"], "kind": r["kind"], "payload": json.loads(r["payload"])} for r in rows
        ]

    # ---- mapping ----
    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> Job:
        return Job(
            job_id=row["job_id"],
            candidate_id=row["candidate_id"],
            priority=row["priority"],
            resources=ResourceRequest.model_validate(json.loads(row["resources"])),
            status=row["status"],
            worker_id=row["worker_id"],
            pid=row["pid"],
            attempts=row["attempts"],
            ingested=bool(row["ingested"]),
            error=row["error"],
            created_at=_parse(row["created_at"]) or _now(),
            started_at=_parse(row["started_at"]),
            finished_at=_parse(row["finished_at"]),
            heartbeat_at=_parse(row["heartbeat_at"]),
        )
