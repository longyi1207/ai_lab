"""Central collector: receives samples + workload markers, writes JSONL."""
from __future__ import annotations

import argparse
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ..util import append_jsonl, ensure_dir, now_s, setup_logging, write_json

log = setup_logging("collector")


class TraceStore:
    def __init__(self, out_dir: Path):
        self.out_dir = ensure_dir(out_dir)
        self.trace_path = self.out_dir / "trace.jsonl"
        self.lock = threading.Lock()
        self.n = 0

    def add(self, row: dict[str, Any]) -> None:
        row = {**row, "recv_t": now_s()}
        with self.lock:
            append_jsonl(self.trace_path, row)
            self.n += 1


def make_handler(store: TraceStore):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args) -> None:  # quieter
            log.debug("%s - " + fmt, self.address_string(), *args)

        def _read_json(self) -> dict:
            n = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(n) if n else b"{}"
            return json.loads(raw.decode("utf-8"))

        def _ok(self, body: dict | None = None) -> None:
            data = json.dumps(body or {"ok": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._ok({"ok": True, "n": store.n})
            else:
                self.send_error(404)

        def do_POST(self) -> None:
            if self.path not in ("/sample", "/marker", "/event"):
                self.send_error(404)
                return
            payload = self._read_json()
            kind = { "/sample": "sample", "/marker": "marker", "/event": "event"}[self.path]
            store.add({"kind": kind, **payload})
            self._ok()

    return Handler


def main() -> None:
    ap = argparse.ArgumentParser(description="ICTD collector server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--out", required=True, help="output directory for trace.jsonl")
    args = ap.parse_args()

    store = TraceStore(Path(args.out))
    write_json(store.out_dir / "collector_meta.json", {
        "host": args.host, "port": args.port, "started_t": now_s()
    })
    server = ThreadingHTTPServer((args.host, args.port), make_handler(store))
    log.info("collector listening on %s:%d → %s", args.host, args.port, store.trace_path)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("collector stopped (%d rows)", store.n)


if __name__ == "__main__":
    main()
