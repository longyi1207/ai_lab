"""Shared state for every MiniLab-lite service.

One SQLite file holds every record as JSON documents keyed by (kind, id). Every write
also appends a row to `statelog`, so a run leaves a complete, ordered record of how
shared state changed. The paper's monitors never see state logs (Kitaoka et al. 2026,
§4.2); we keep them so that state-aware monitors can be tested later.

Each CLI invocation and each standing-process tick runs inside one IMMEDIATE
transaction, which serialises concurrent agents.
"""
from __future__ import annotations

import contextlib
import json
import sqlite3
import time

DB_PATH = "/srv/minilab/state.db"
ROOT = "/srv/minilab"
CYCLE = "2026-W42"

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
    kind TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL, rev INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (kind, id));
CREATE TABLE IF NOT EXISTS statelog (
    seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, actor TEXT NOT NULL,
    kind TEXT NOT NULL, id TEXT NOT NULL, op TEXT NOT NULL, before TEXT, after TEXT);
"""


class Store:
    def __init__(self, actor: str, path: str = DB_PATH):
        self.actor = actor
        self.conn = sqlite3.connect(path, timeout=60, isolation_level=None)
        self.conn.execute("PRAGMA busy_timeout=60000")
        self.conn.execute("PRAGMA journal_mode=WAL")

    def init_schema(self) -> None:
        self.conn.executescript(SCHEMA)

    @contextlib.contextmanager
    def tx(self):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        else:
            self.conn.execute("COMMIT")

    def get(self, kind: str, id: str, default=None):
        row = self.conn.execute("SELECT data FROM docs WHERE kind=? AND id=?", (kind, id)).fetchone()
        return json.loads(row[0]) if row else default

    def all(self, kind: str) -> list[tuple[str, dict]]:
        rows = self.conn.execute("SELECT id, data FROM docs WHERE kind=? ORDER BY id", (kind,)).fetchall()
        return [(r[0], json.loads(r[1])) for r in rows]

    def put(self, kind: str, id: str, data, op: str = "put") -> None:
        before = self.get(kind, id)
        if before == data:
            return
        self.conn.execute(
            "INSERT INTO docs(kind, id, data) VALUES(?,?,?) "
            "ON CONFLICT(kind, id) DO UPDATE SET data=excluded.data, rev=rev+1",
            (kind, id, json.dumps(data, sort_keys=True)))
        self._log(kind, id, op, before, data)

    def delete(self, kind: str, id: str, op: str = "delete") -> None:
        before = self.get(kind, id)
        if before is None:
            return
        self.conn.execute("DELETE FROM docs WHERE kind=? AND id=?", (kind, id))
        self._log(kind, id, op, before, None)

    def next_id(self, counter: str, prefix: str, start: int) -> str:
        n = self.get("counter", counter, start)
        self.put("counter", counter, n + 1, op="counter")
        return f"{prefix}{n}"

    def _log(self, kind, id, op, before, after) -> None:
        self.conn.execute(
            "INSERT INTO statelog(ts, actor, kind, id, op, before, after) VALUES(?,?,?,?,?,?,?)",
            (time.time(), self.actor, kind, id, op,
             None if before is None else json.dumps(before, sort_keys=True),
             None if after is None else json.dumps(after, sort_keys=True)))

    def statelog(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT seq, ts, actor, kind, id, op, before, after FROM statelog ORDER BY seq").fetchall()
        keys = ("seq", "ts", "actor", "kind", "id", "op", "before", "after")
        return [dict(zip(keys, r)) for r in rows]


class Refused(Exception):
    """A service refused the request. The message is shown to the caller."""
