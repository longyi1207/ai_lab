"""Per-node monitor agent: poll probes, POST deltas to collector."""
from __future__ import annotations

import argparse
import os
import socket
import time
from typing import Any

import requests

from ..util import setup_logging
from .probes import SyntheticProbe, build_probes, primary_sample

log = setup_logging("agent")


class Agent:
    def __init__(
        self,
        collector_url: str,
        node: str,
        backends: list[str],
        iface: str | None,
        ib_device: str | None,
        poll_hz: float,
    ):
        self.url = collector_url.rstrip("/")
        self.node = node
        self.poll_hz = poll_hz
        self.probes = build_probes(backends, iface=iface, ib_device=ib_device)
        self._synth = next((p for p in self.probes if isinstance(p, SyntheticProbe)), None)
        self._prev: dict[str, tuple[int, int]] = {}

    def set_synth_mode(self, mode: str) -> None:
        if self._synth is not None:
            self._synth.set_mode(mode)
            os.environ["ICTD_SYNTH_MODE"] = mode

    def _post(self, path: str, payload: dict[str, Any]) -> None:
        try:
            r = requests.post(f"{self.url}{path}", json=payload, timeout=2.0)
            r.raise_for_status()
        except Exception as e:
            log.warning("post %s failed: %s", path, e)

    def emit_marker(self, name: str, phase: str, **extra: Any) -> None:
        self._post("/marker", {
            "node": self.node,
            "t": time.time(),
            "name": name,
            "phase": phase,  # start | end | step
            **extra,
        })

    def _refresh_synth_mode_file(self) -> None:
        if self._synth is None:
            return
        path = os.environ.get("ICTD_SYNTH_MODE_FILE", "/tmp/ictd_synth_mode")
        try:
            with open(path) as f:
                mode = f.read().strip()
            if mode:
                self._synth.set_mode(mode)
        except OSError:
            pass

    def poll_once(self) -> None:
        self._refresh_synth_mode_file()
        for p in self.probes:
            s = p.sample()
            if s is None:
                continue
            key = s.source
            prev = self._prev.get(key)
            d_tx = d_rx = 0
            if prev is not None:
                d_tx = max(0, s.tx_bytes - prev[0])
                d_rx = max(0, s.rx_bytes - prev[1])
            self._prev[key] = (s.tx_bytes, s.rx_bytes)
            self._post("/sample", {
                "node": self.node,
                "t": s.t,
                "source": s.source,
                "tx_bytes": s.tx_bytes,
                "rx_bytes": s.rx_bytes,
                "d_tx": d_tx,
                "d_rx": d_rx,
                "d_total": d_tx + d_rx,
                "meta": s.meta or {},
            })

    def run_forever(self) -> None:
        dt = 1.0 / max(self.poll_hz, 0.1)
        log.info("agent node=%s backends=%s → %s", self.node, [p.name for p in self.probes], self.url)
        while True:
            self.poll_once()
            time.sleep(dt)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--collector", default="http://127.0.0.1:8765")
    ap.add_argument("--node", default=socket.gethostname())
    ap.add_argument("--backends", default="synthetic,proc_net",
                    help="comma list: ib,proc_net,nvml,synthetic")
    ap.add_argument("--iface", default=None)
    ap.add_argument("--ib-device", default=None)
    ap.add_argument("--poll-hz", type=float, default=10.0)
    ap.add_argument("--synth-mode", default=None, help="set synthetic probe mode once")
    args = ap.parse_args()

    agent = Agent(
        collector_url=args.collector,
        node=args.node,
        backends=[b.strip() for b in args.backends.split(",") if b.strip()],
        iface=args.iface,
        ib_device=args.ib_device,
        poll_hz=args.poll_hz,
    )
    if args.synth_mode:
        agent.set_synth_mode(args.synth_mode)
    agent.run_forever()


if __name__ == "__main__":
    main()
