"""Byte-counter backends. Priority: IB > NCCL > proc_net > NVML > synthetic."""
from __future__ import annotations

import os
import re
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class CounterSample:
    t: float
    tx_bytes: int
    rx_bytes: int
    source: str
    meta: dict | None = None

    @property
    def total_bytes(self) -> int:
        return self.tx_bytes + self.rx_bytes


class Probe(ABC):
    name: str

    @abstractmethod
    def sample(self) -> CounterSample | None:
        ...


class ProcNetProbe(Probe):
    name = "proc_net"

    def __init__(self, iface: str | None = None):
        self.iface = iface

    def _read_proc(self) -> CounterSample | None:
        path = Path("/proc/net/dev")
        if not path.exists():
            return None
        lines = path.read_text().strip().splitlines()[2:]
        rows = {}
        for line in lines:
            name, rest = line.split(":", 1)
            parts = rest.split()
            rows[name.strip()] = (int(parts[0]), int(parts[8]))
        iface = self.iface
        if iface is None:
            candidates = [k for k in rows if k != "lo"]
            if not candidates:
                return None
            iface = max(candidates, key=lambda k: rows[k][0] + rows[k][1])
        if iface not in rows:
            return None
        rx, tx = rows[iface]
        return CounterSample(time.time(), tx, rx, self.name, {"iface": iface})

    def sample(self) -> CounterSample | None:
        got = self._read_proc()
        if got is not None:
            return got
        try:
            import psutil
        except ImportError:
            return None
        stats = psutil.net_io_counters(pernic=True)
        if self.iface and self.iface in stats:
            s = stats[self.iface]
            return CounterSample(
                time.time(), s.bytes_sent, s.bytes_recv, self.name, {"iface": self.iface}
            )
        tx = rx = 0
        used = []
        for name, s in stats.items():
            if name.startswith("lo"):
                continue
            tx += s.bytes_sent
            rx += s.bytes_recv
            used.append(name)
        if not used:
            return None
        return CounterSample(time.time(), tx, rx, self.name, {"ifaces": used})


class IBProbe(Probe):
    name = "ib"

    def __init__(self, device: str | None = None, port: int = 1):
        self.device = device
        self.port = port

    def _devices(self) -> list[str]:
        root = Path("/sys/class/infiniband")
        if not root.exists():
            return []
        return sorted(p.name for p in root.iterdir() if p.is_dir())

    def sample(self) -> CounterSample | None:
        devices = self._devices()
        if not devices:
            return None
        dev = self.device or devices[0]
        base = Path(f"/sys/class/infiniband/{dev}/ports/{self.port}/counters")
        if not base.exists():
            return None

        def read(name: str) -> int:
            return int((base / name).read_text().strip())

        try:
            tx = read("port_xmit_data") * 4
            rx = read("port_rcv_data") * 4
        except FileNotFoundError:
            return None
        return CounterSample(
            time.time(), tx, rx, self.name, {"device": dev, "port": self.port}
        )


class NVMLProbe(Probe):
    """NVLink throughput + SM util (Rahman-adjacent secondary channel)."""

    name = "nvml"

    def __init__(self):
        self._ok = False
        self._tx = 0
        self._rx = 0
        try:
            import pynvml

            pynvml.nvmlInit()
            self.pynvml = pynvml
            self._ok = True
        except Exception:
            self._ok = False

    def sample(self) -> CounterSample | None:
        if not self._ok:
            return None
        pynvml = self.pynvml
        n = pynvml.nvmlDeviceGetCount()
        d_tx = d_rx = 0
        utils = []
        powers = []
        for i in range(n):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            try:
                u = pynvml.nvmlDeviceGetUtilizationRates(h)
                utils.append(float(u.gpu))
            except Exception:
                pass
            try:
                powers.append(float(pynvml.nvmlDeviceGetPowerUsage(h)) / 1000.0)
            except Exception:
                pass
            for link in range(12):
                try:
                    # cumulative counters when available (driver-dependent)
                    t = pynvml.nvmlDeviceGetNvLinkThroughput(h, link, 0)  # type: ignore[attr-defined]
                    r = pynvml.nvmlDeviceGetNvLinkThroughput(h, link, 1)  # type: ignore[attr-defined]
                    d_tx += int(t)
                    d_rx += int(r)
                except Exception:
                    break
        # NVLink throughput APIs often return instantaneous MB/s — integrate
        now = time.time()
        if not hasattr(self, "_last_t"):
            self._last_t = now
        dt = max(now - self._last_t, 0.0)
        self._last_t = now
        # if values look like rates (small), treat as MB/s; if huge, cumulative
        if d_tx + d_rx < 1_000_000_000:
            self._tx += int(d_tx * 1e6 * dt)  # MB/s → bytes
            self._rx += int(d_rx * 1e6 * dt)
        else:
            self._tx, self._rx = d_tx, d_rx
        meta = {
            "gpus": n,
            "util_mean": float(sum(utils) / len(utils)) if utils else 0.0,
            "power_w_mean": float(sum(powers) / len(powers)) if powers else 0.0,
        }
        return CounterSample(now, self._tx, self._rx, self.name, meta)


class NCCLProbe(Probe):
    """Read cumulative collective bytes written by nccl_hook / log parser.

    Workloads call `src.monitor.nccl_hook.record_bytes(...)`.
    Also tails NCCL_DEBUG log if ICTD_NCCL_LOG is set.
    """

    name = "nccl"
    COUNTER_FILE = os.environ.get("ICTD_NCCL_COUNTER", "/tmp/ictd_nccl_bytes")

    def __init__(self, log_path: str | None = None):
        self.log_path = log_path or os.environ.get("ICTD_NCCL_LOG")
        self._log_pos = 0
        self._parsed_tx = 0
        self._parsed_rx = 0
        self._re = re.compile(
            r"(?:AllReduce|AllGather|ReduceScatter|Broadcast).*?(?:Bytes|bytes|size)[=\s:]+(\d+)",
            re.I,
        )

    def _from_counter_file(self) -> tuple[int, int, int] | None:
        p = Path(self.COUNTER_FILE)
        if not p.exists():
            return None
        try:
            # format: tx rx n_collectives
            parts = p.read_text().strip().split()
            tx = int(parts[0])
            rx = int(parts[1]) if len(parts) > 1 else tx
            n = int(parts[2]) if len(parts) > 2 else 0
            return tx, rx, n
        except Exception:
            return None

    def _from_log(self) -> None:
        if not self.log_path:
            return
        path = Path(self.log_path)
        if not path.exists():
            return
        try:
            with path.open("r", errors="ignore") as f:
                f.seek(self._log_pos)
                for line in f:
                    m = self._re.search(line)
                    if m:
                        b = int(m.group(1))
                        self._parsed_tx += b
                        self._parsed_rx += b
                self._log_pos = f.tell()
        except Exception:
            pass

    def sample(self) -> CounterSample | None:
        self._from_log()
        got = self._from_counter_file()
        if got is not None:
            tx, rx, n = got
            return CounterSample(
                time.time(), tx, rx, self.name, {"n_collectives": n, "via": "counter_file"}
            )
        if self._parsed_tx or self._parsed_rx:
            return CounterSample(
                time.time(), self._parsed_tx, self._parsed_rx, self.name, {"via": "log"}
            )
        # still emit zeros so source appears once hook starts
        if Path(self.COUNTER_FILE).exists() or self.log_path:
            return CounterSample(time.time(), 0, 0, self.name, {"via": "empty"})
        return None


class SyntheticProbe(Probe):
    name = "synthetic"
    RATES = {
        "idle": 1e3,
        "infer": 5e5,
        "diloco": 8e5,
        "train": 2e7,
    }

    def __init__(self):
        self._lock = threading.Lock()
        self._mode = os.environ.get("ICTD_SYNTH_MODE", "idle")
        self._tx = 0
        self._rx = 0
        self._last_t = time.time()

    def set_mode(self, mode: str) -> None:
        with self._lock:
            self._mode = mode

    def sample(self) -> CounterSample | None:
        with self._lock:
            now = time.time()
            dt = max(now - self._last_t, 0.0)
            rate = self.RATES.get(self._mode, self.RATES["idle"])
            add = int(rate * dt)
            self._tx += add // 2
            self._rx += add - add // 2
            self._last_t = now
            mode = self._mode
            tx, rx = self._tx, self._rx
        return CounterSample(now, tx, rx, self.name, {"mode": mode})


def build_probes(
    backends: Iterable[str],
    iface: str | None = None,
    ib_device: str | None = None,
) -> list[Probe]:
    out: list[Probe] = []
    for b in backends:
        if b == "ib":
            out.append(IBProbe(device=ib_device))
        elif b == "proc_net":
            out.append(ProcNetProbe(iface=iface))
        elif b == "nvml":
            out.append(NVMLProbe())
        elif b == "nccl":
            out.append(NCCLProbe())
        elif b == "synthetic":
            out.append(SyntheticProbe())
        else:
            raise ValueError(f"unknown probe backend: {b}")
    return out


def primary_sample(probes: list[Probe]) -> CounterSample | None:
    for p in probes:
        s = p.sample()
        if s is not None:
            return s
    return None
