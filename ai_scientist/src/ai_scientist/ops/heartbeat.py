"""Worker heartbeat helper (own module to avoid import cycles)."""

from __future__ import annotations

import threading

from .state import StateStore


class Heartbeat:
    """Background heartbeat; `enabled=False` simulates a wedged worker in tests."""

    def __init__(self, store: StateStore, job_id: str, interval_s: float, enabled: bool = True):
        self.store = store
        self.job_id = job_id
        self.interval_s = interval_s
        self.enabled = enabled
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def beat(self) -> None:
        if self.enabled:
            self.store.heartbeat(self.job_id)

    def start(self) -> Heartbeat:
        if not self.enabled:
            return self
        self._thread = threading.Thread(target=self._loop, name="heartbeat", daemon=True)
        self._thread.start()
        return self

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_s):
            try:
                self.store.heartbeat(self.job_id)
            except Exception:  # noqa: BLE001 - a heartbeat failure must not kill the trial
                pass

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def __enter__(self) -> Heartbeat:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()
