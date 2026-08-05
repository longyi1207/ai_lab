"""Richer window features: rate shape, periodicity, burstiness, bytes/step."""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterator

import numpy as np


@dataclass
class WindowFeatures:
    name: str
    label: str
    t0: float
    t1: float
    duration_s: float
    bytes_total: int
    gbps_mean: float
    gbps_p95: float
    sample_hz: float
    source: str
    n_samples: int
    # richer
    bytes_per_step: float = 0.0
    n_steps: int = 0
    burstiness: float = 0.0          # CV of inter-sample rates
    duty_cycle: float = 0.0          # fraction of samples above mean rate
    spectral_peak_hz: float = 0.0    # dominant FFT frequency of rate series
    spectral_peak_power: float = 0.0
    periodicity_score: float = 0.0   # peak / mean spectral power
    rate_autocorr_lag1: float = 0.0
    n_nccl_collectives: int = 0
    nccl_bytes: int = 0
    nvml_util_mean: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _label_from_name(name: str) -> str:
    n = name.lower()
    if "diloco" in n:
        return "diloco"
    if "kv_disguise" in n or "disguise" in n:
        return "train_disguised"
    if "train" in n:
        return "train"
    if "infer" in n:
        return "infer"
    return "other"


def load_trace(path: str | Path) -> list[dict]:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def iter_windows(rows: list[dict]) -> Iterator[tuple[str, float, float]]:
    open_m: dict[str, float] = {}
    for r in rows:
        if r.get("kind") != "marker":
            continue
        name = r.get("name", "unknown")
        phase = r.get("phase")
        t = float(r.get("t", r.get("recv_t", 0)))
        if phase == "start":
            open_m[name] = t
        elif phase == "end" and name in open_m:
            yield name, open_m.pop(name), t


def _prefer_source(samples: list[dict]) -> str:
    priority = ["ib", "nccl", "synthetic", "proc_net", "nvml"]
    present = {s.get("source") for s in samples}
    for p in priority:
        if p in present:
            return p
    return next(iter(present)) if present else "none"


def _spectral(rates: np.ndarray, dts: np.ndarray) -> tuple[float, float, float]:
    if len(rates) < 8:
        return 0.0, 0.0, 0.0
    # resample onto uniform grid
    t = dts - dts[0]
    if t[-1] <= 0:
        return 0.0, 0.0, 0.0
    hz = min(50.0, max(2.0, (len(rates) - 1) / t[-1]))
    grid = np.arange(0, t[-1], 1.0 / hz)
    if len(grid) < 8:
        return 0.0, 0.0, 0.0
    y = np.interp(grid, t, rates)
    y = y - y.mean()
    spec = np.abs(np.fft.rfft(y)) ** 2
    freqs = np.fft.rfftfreq(len(y), d=1.0 / hz)
    if len(spec) < 2:
        return 0.0, 0.0, 0.0
    # ignore DC
    peak_i = int(np.argmax(spec[1:]) + 1)
    peak_hz = float(freqs[peak_i])
    peak_pow = float(spec[peak_i])
    mean_pow = float(np.mean(spec[1:])) + 1e-12
    return peak_hz, peak_pow, peak_pow / mean_pow


def extract_window_features(rows: list[dict], prefer_source: str | None = None) -> list[WindowFeatures]:
    samples = [r for r in rows if r.get("kind") == "sample"]
    markers = [r for r in rows if r.get("kind") == "marker"]
    events = [r for r in rows if r.get("kind") == "event"]
    out: list[WindowFeatures] = []

    for name, t0, t1 in iter_windows(rows):
        win = [s for s in samples if t0 <= float(s.get("t", 0)) <= t1]
        if not win:
            continue
        src = prefer_source or _prefer_source(win)
        win_src = [s for s in win if s.get("source") == src] or win
        dts = np.array([float(s.get("t", 0)) for s in win_src], dtype=np.float64)
        deltas = np.array([int(s.get("d_total", 0)) for s in win_src], dtype=np.float64)
        duration = max(t1 - t0, 1e-6)
        bytes_total = int(deltas.sum())

        rates = []
        for i in range(1, len(win_src)):
            dt = dts[i] - dts[i - 1]
            if dt > 0:
                rates.append(deltas[i] / dt)
        rates_a = np.asarray(rates, dtype=np.float64) if rates else np.array([bytes_total / duration])
        rates_sorted = np.sort(rates_a)
        mean_bps = bytes_total / duration
        p95 = float(rates_sorted[int(0.95 * (len(rates_sorted) - 1))])

        # steps from markers
        steps = [
            m for m in markers
            if m.get("name") == name and m.get("phase") == "step"
            and t0 <= float(m.get("t", 0)) <= t1
        ]
        n_steps = len(steps)
        bytes_per_step = bytes_total / max(n_steps, 1)

        burst = float(rates_a.std(ddof=1) / (rates_a.mean() + 1e-12)) if len(rates_a) > 1 else 0.0
        duty = float(np.mean(rates_a > rates_a.mean())) if len(rates_a) else 0.0
        peak_hz, peak_pow, per_score = _spectral(rates_a, dts if len(dts) == len(rates_a) else dts[1:] if len(dts) > 1 else dts)

        # lag-1 autocorr of rates
        ac1 = 0.0
        if len(rates_a) > 2:
            x = rates_a - rates_a.mean()
            ac1 = float(np.dot(x[1:], x[:-1]) / (np.dot(x, x) + 1e-12))

        # NCCL events in window
        nccl_ev = [
            e for e in events
            if e.get("type") in ("nccl_collective", "nccl_bytes")
            and t0 <= float(e.get("t", 0)) <= t1
        ]
        n_nccl = len(nccl_ev)
        nccl_bytes = int(sum(int(e.get("bytes", 0)) for e in nccl_ev))

        # NVML util from samples tagged nvml
        nvml_win = [s for s in win if s.get("source") == "nvml"]
        util = 0.0
        if nvml_win:
            utils = [float((s.get("meta") or {}).get("util_mean", 0)) for s in nvml_win]
            util = float(np.mean(utils)) if utils else 0.0

        out.append(WindowFeatures(
            name=name,
            label=_label_from_name(name),
            t0=t0,
            t1=t1,
            duration_s=duration,
            bytes_total=bytes_total,
            gbps_mean=mean_bps * 8 / 1e9,
            gbps_p95=p95 * 8 / 1e9,
            sample_hz=(len(win_src) - 1) / duration if len(win_src) > 1 else 0.0,
            source=src,
            n_samples=len(win_src),
            bytes_per_step=bytes_per_step,
            n_steps=n_steps,
            burstiness=burst,
            duty_cycle=duty,
            spectral_peak_hz=peak_hz,
            spectral_peak_power=peak_pow,
            periodicity_score=per_score,
            rate_autocorr_lag1=ac1,
            n_nccl_collectives=n_nccl,
            nccl_bytes=nccl_bytes,
            nvml_util_mean=util,
        ))
    return out
