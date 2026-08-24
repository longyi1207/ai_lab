"""NVML 9-signal telemetry capture, following the signal set in Rahman &
Tajdari, "Detecting Hidden ML Training With Zero-Overhead Telemetry"
(arXiv:2606.19262): GPU utilization (%), memory utilization (%), memory
used (MB), power draw (W), temperature (C), SM clock (MHz), memory clock
(MHz), PCIe TX bandwidth (MB/s), PCIe RX bandwidth (MB/s) — sampled at 1 Hz.

This is deliberately a separate probe from `src/monitor/probes.py`'s
`NVMLProbe` (which reads NVLink throughput for the original cross-node
track's byte-rate pipeline). Same physical counters family, different
feature philosophy and downstream consumer — kept apart so neither track's
code has to know about the other. See docs/REDTEAM.md.

`NVMLTelemetrySource` needs `pynvml` + real NVIDIA hardware.
`SyntheticTelemetrySource` fabricates plausible per-mode traces (same idea
as `src/monitor/probes.py:SyntheticProbe`) so the rest of this track
(features, classifier, orchestration) is developable and testable on a
machine with no GPU — this repo's author works on a Mac — before the real
node lands.
"""
from __future__ import annotations

import math
import os
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import requests

SIGNAL_NAMES = (
    "gpu_util_pct",
    "mem_util_pct",
    "mem_used_mb",
    "power_w",
    "temp_c",
    "sm_clock_mhz",
    "mem_clock_mhz",
    "pcie_tx_mbps",
    "pcie_rx_mbps",
)


@dataclass
class NineSignalSample:
    t: float
    gpu_index: int
    values: dict[str, float]  # keys = SIGNAL_NAMES

    def to_dict(self) -> dict[str, Any]:
        return {"t": self.t, "gpu_index": self.gpu_index, **self.values}


class TelemetrySource:
    """Interface: `sample_all_gpus() -> list[NineSignalSample]`, one per visible GPU."""

    def sample_all_gpus(self) -> list[NineSignalSample]:
        raise NotImplementedError

    def gpu_count(self) -> int:
        raise NotImplementedError

    def set_mode(self, mode: str) -> None:
        """No-op on real hardware; overridden by SyntheticTelemetrySource.

        Callers may call this unconditionally (no isinstance check) — the
        orchestrator sets the mode itself before launching each workload,
        deliberately independent of the *original* track's
        `ICTD_SYNTH_MODE_FILE` signal (kv_disguise sets that one to
        "infer" on purpose, to fool the original probe — reusing it here
        would defeat the point of red-teaming this track honestly).
        """


class NVMLTelemetrySource(TelemetrySource):
    """Real hardware. Requires `pip install nvidia-ml-py` and NVIDIA GPUs.

    On a SHARED multi-tenant box — e.g. the Aug 2026 Italy North reservation
    (1 node, 8x NDm A100 v4, split across 3 projects via CUDA_VISIBLE_DEVICES)
    — this matters a lot: NVML sits below the CUDA runtime and does **not**
    automatically respect CUDA_VISIBLE_DEVICES. `nvmlDeviceGetCount()` /
    `nvmlDeviceGetHandleByIndex()` see every physical GPU on the box
    regardless of that env var, so naively polling "all of them" would
    silently mix other tenants' workloads into this project's trace —
    exactly the kind of correctness bug that's easy to miss until someone
    else's job pollutes your classifier's training data.

    `gpu_indices` is therefore explicit, not an optional filter. If left
    unset, falls back to parsing `CUDA_VISIBLE_DEVICES` (comma-separated
    physical indices) as a convenience — set it explicitly rather than
    relying on that fallback when running on a shared box.
    """

    def __init__(self, gpu_indices: list[int] | None = None) -> None:
        import pynvml  # local import: only required when actually used

        pynvml.nvmlInit()
        self.pynvml = pynvml
        total = pynvml.nvmlDeviceGetCount()

        if gpu_indices is None:
            cvd = os.environ.get("CUDA_VISIBLE_DEVICES", "").strip()
            gpu_indices = [int(x) for x in cvd.split(",") if x.strip() != ""] if cvd else list(range(total))

        bad = [i for i in gpu_indices if i < 0 or i >= total]
        if bad:
            raise ValueError(
                f"gpu_indices {bad} out of range — this box reports {total} physical GPUs. "
                "On a shared box, double-check you were given the right indices before running."
            )

        self._indices = gpu_indices
        self._n = len(gpu_indices)
        self._handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in gpu_indices]

    def gpu_count(self) -> int:
        return self._n

    def sample_all_gpus(self) -> list[NineSignalSample]:
        pynvml = self.pynvml
        t = time.time()
        out = []
        for i, h in zip(self._indices, self._handles):
            def _try(fn, *a, default=0.0):
                try:
                    return float(fn(*a))
                except Exception:
                    return default

            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            values = {
                "gpu_util_pct": float(util.gpu),
                "mem_util_pct": float(util.memory),
                "mem_used_mb": float(mem.used) / (1024 * 1024),
                "power_w": _try(pynvml.nvmlDeviceGetPowerUsage, h) / 1000.0,
                "temp_c": _try(
                    pynvml.nvmlDeviceGetTemperature, h,
                    pynvml.NVML_TEMPERATURE_GPU,
                ),
                "sm_clock_mhz": _try(pynvml.nvmlDeviceGetClockInfo, h, pynvml.NVML_CLOCK_SM),
                "mem_clock_mhz": _try(pynvml.nvmlDeviceGetClockInfo, h, pynvml.NVML_CLOCK_MEM),
                "pcie_tx_mbps": _try(pynvml.nvmlDeviceGetPcieThroughput, h, pynvml.NVML_PCIE_UTIL_TX_BYTES) / 1024.0,
                "pcie_rx_mbps": _try(pynvml.nvmlDeviceGetPcieThroughput, h, pynvml.NVML_PCIE_UTIL_RX_BYTES) / 1024.0,
            }
            out.append(NineSignalSample(t=t, gpu_index=i, values=values))
        return out


class SyntheticTelemetrySource(TelemetrySource):
    """Fabricated per-mode traces for GPU-less local dev.

    Modes mirror the workload labels this repo already uses: idle, train
    (train_ddp-shaped: high, steady util + power; monotonic memory ramp
    from optimizer state), infer (infer_dp/infer_tp-shaped: choppier,
    lower util/power, flat memory after the KV cache/weights are loaded),
    diloco (train-shaped compute but power dips periodically during the
    long local-SGD phases between outer syncs), train_disguised
    (kv_disguise-shaped: infer-like instantaneous util/power, because the
    disguise only reshapes the *communication*, not the compute — this is
    deliberately NOT the same recipe as `infer`, since honestly modeling
    the disguise is the point of the red-team).

    Not a validated hardware model — only meant to exercise the feature
    extraction / classifier / orchestration code paths before real
    telemetry exists. Do not treat classifier results trained on this data
    as saying anything about real evasion feasibility.
    """

    RATES = {
        "idle": dict(util=(2, 2), power=(30, 3), mem_ramp_mb_s=0.0, mem_base=(500, 5000)),
        "train": dict(util=(88, 6), power=(340, 25), mem_ramp_mb_s=4.0, mem_base=(6000, 12000)),
        "infer": dict(util=(45, 15), power=(150, 30), mem_ramp_mb_s=0.0, mem_base=(4000, 9000)),
        "diloco": dict(util=(70, 20), power=(260, 60), mem_ramp_mb_s=1.0, mem_base=(6000, 12000)),
        "train_disguised": dict(util=(48, 14), power=(155, 28), mem_ramp_mb_s=3.5, mem_base=(6000, 12000)),
    }

    def __init__(self, n_gpus: int = 8, seed: int = 0):
        self._n = n_gpus
        self._mode = "idle"
        self._mode_t0: dict[int, float] = {}
        self._rng = random.Random(seed)
        self._lock = threading.Lock()

    def gpu_count(self) -> int:
        return self._n

    def set_mode(self, mode: str) -> None:
        with self._lock:
            if mode != self._mode:
                self._mode = mode
                now = time.time()
                self._mode_t0 = {i: now for i in range(self._n)}

    def sample_all_gpus(self) -> list[NineSignalSample]:
        with self._lock:
            mode = self._mode
            t0_by_gpu = dict(self._mode_t0)
        t = time.time()
        params = self.RATES.get(mode, self.RATES["idle"])
        out = []
        for i in range(self._n):
            elapsed = t - t0_by_gpu.get(i, t)
            util = max(0.0, min(100.0, self._rng.gauss(*params["util"])))
            power = max(15.0, self._rng.gauss(*params["power"]))
            mem_base = self._rng.uniform(*params["mem_base"])
            mem_used = mem_base + params["mem_ramp_mb_s"] * min(elapsed, 300.0)
            # crude physical coupling so downstream features (power-memory
            # correlation, cumulative energy) have something non-degenerate
            values = {
                "gpu_util_pct": util,
                "mem_util_pct": max(0.0, min(100.0, util * 0.6 + self._rng.gauss(0, 5))),
                "mem_used_mb": mem_used,
                "power_w": power,
                "temp_c": 40.0 + power / 8.0 + self._rng.gauss(0, 1.5),
                "sm_clock_mhz": 1200.0 + util * 4.0 + self._rng.gauss(0, 20),
                "mem_clock_mhz": 1500.0 + self._rng.gauss(0, 10),
                "pcie_tx_mbps": max(0.0, self._rng.gauss(200 if mode in ("train", "diloco") else 500, 80)),
                "pcie_rx_mbps": max(0.0, self._rng.gauss(200 if mode in ("train", "diloco") else 500, 80)),
            }
            out.append(NineSignalSample(t=t, gpu_index=i, values=values))
        return out


def _aggregate(samples: list[NineSignalSample]) -> dict[str, float]:
    """Mean + std across GPUs for each signal at one timestep.

    Rahman & Tajdari's multi-GPU results note the classifier learns
    cross-GPU patterns (e.g. AllGather/ReduceScatter NVLink traffic even
    when an individual GPU shows only moderate utilization) — we don't
    have their exact multi-GPU aggregation method from the paper text we
    could extract, so mean+std-across-GPUs-per-tick is our own documented
    choice, not a reproduction of theirs. See docs/REDTEAM.md limitations.
    """
    agg: dict[str, float] = {}
    for name in SIGNAL_NAMES:
        vals = [s.values[name] for s in samples]
        n = len(vals)
        mean = sum(vals) / n if n else 0.0
        var = sum((v - mean) ** 2 for v in vals) / n if n else 0.0
        agg[f"mean_{name}"] = mean
        agg[f"std_{name}"] = math.sqrt(var)
    return agg


class TelemetryPoller:
    """Background 1 Hz poller: sample all GPUs, aggregate, POST to the
    (already-running, unmodified) `src.monitor.collector` as an `/event`
    row with `type="nvml9_sample"` — reuses the existing collector/trace
    format instead of inventing new transport. See docs/REDTEAM.md.
    """

    def __init__(
        self,
        source: TelemetrySource,
        collector_url: str,
        node: str,
        hz: float = 1.0,
    ):
        self.source = source
        self.url = collector_url.rstrip("/")
        self.node = node
        self.hz = hz
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _post(self, payload: dict[str, Any]) -> None:
        try:
            requests.post(f"{self.url}/event", json=payload, timeout=2.0)
        except Exception:
            pass  # telemetry must not crash the workload

    def _loop(self) -> None:
        dt = 1.0 / max(self.hz, 0.1)
        while not self._stop.is_set():
            samples = self.source.sample_all_gpus()
            if samples:
                agg = _aggregate(samples)
                self._post({
                    "node": self.node,
                    "t": time.time(),
                    "type": "nvml9_sample",
                    "n_gpus": len(samples),
                    **agg,
                })
            self._stop.wait(dt)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5.0)


def build_source(
    synthetic: bool,
    n_gpus_if_synthetic: int = 8,
    gpu_indices: list[int] | None = None,
) -> TelemetrySource:
    if synthetic:
        return SyntheticTelemetrySource(n_gpus=n_gpus_if_synthetic)
    try:
        return NVMLTelemetrySource(gpu_indices=gpu_indices)
    except Exception as e:
        raise RuntimeError(
            "NVML telemetry unavailable (no pynvml / no NVIDIA GPU, or bad "
            "gpu_indices — see NVMLTelemetrySource's docstring re: shared "
            "boxes). Pass --synthetic for local dry-runs."
        ) from e
