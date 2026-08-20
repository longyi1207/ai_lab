"""Pluggable alert notifiers (pillar 5.2): log (default), file, webhook.
Selected and fanned out by alerts/dispatcher.py.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Protocol

import httpx

logger = logging.getLogger("research_dojo.alerts")


class Notifier(Protocol):
    name: str

    def notify(self, *, rule: str, severity: str, message: str, run_id: str | None) -> dict: ...


class LogNotifier:
    name = "log"

    def notify(self, *, rule: str, severity: str, message: str, run_id: str | None) -> dict:
        log_fn = {"info": logger.info, "warning": logger.warning, "critical": logger.error}.get(
            severity, logger.info
        )
        log_fn("ALERT[%s] rule=%s run_id=%s: %s", severity, rule, run_id, message)
        return {"delivered": True}


class FileNotifier:
    name = "file"

    def __init__(self, path: Path):
        self.path = path

    def notify(self, *, rule: str, severity: str, message: str, run_id: str | None) -> dict:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a") as f:
            f.write(json.dumps({"rule": rule, "severity": severity, "message": message, "run_id": run_id}) + "\n")
            f.flush()
            os.fsync(f.fileno())
        return {"delivered": True, "path": str(self.path)}


class WebhookNotifier:
    name = "webhook"

    def __init__(self, url: str, timeout: float = 10.0):
        self.url = url
        self.timeout = timeout

    def notify(self, *, rule: str, severity: str, message: str, run_id: str | None) -> dict:
        try:
            resp = httpx.post(
                self.url,
                json={"rule": rule, "severity": severity, "message": message, "run_id": run_id},
                timeout=self.timeout,
            )
            return {"delivered": resp.status_code < 400, "status_code": resp.status_code}
        except httpx.HTTPError as e:
            logger.warning("webhook notify failed: %s", e)
            return {"delivered": False, "error": str(e)}
