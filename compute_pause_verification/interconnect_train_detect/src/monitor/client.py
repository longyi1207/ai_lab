"""Client helpers for workloads to talk to collector + optional local agent synth mode."""
from __future__ import annotations

import os
import time
from typing import Any

import requests


class MonitorClient:
    def __init__(self, collector_url: str | None = None, node: str | None = None):
        self.url = (collector_url or os.environ.get("ICTD_COLLECTOR", "http://127.0.0.1:8765")).rstrip("/")
        self.node = node or os.environ.get("ICTD_NODE", "local")
        self.session = requests.Session()

    def _post(self, path: str, payload: dict[str, Any]) -> None:
        try:
            self.session.post(f"{self.url}{path}", json=payload, timeout=2.0)
        except Exception:
            pass  # workloads must not die if monitor is down

    def marker(self, name: str, phase: str, **extra: Any) -> None:
        self._post("/marker", {
            "node": self.node,
            "t": time.time(),
            "name": name,
            "phase": phase,
            **extra,
        })

    def event(self, typ: str, **extra: Any) -> None:
        self._post("/event", {"node": self.node, "t": time.time(), "type": typ, **extra})

    def set_synth_mode(self, mode: str) -> None:
        """Best-effort: tell collector via event; agent may also watch ICTD_SYNTH_MODE file."""
        os.environ["ICTD_SYNTH_MODE"] = mode
        path = os.environ.get("ICTD_SYNTH_MODE_FILE", "/tmp/ictd_synth_mode")
        try:
            with open(path, "w") as f:
                f.write(mode)
        except OSError:
            pass
        self.event("synth_mode", mode=mode)
