"""Window feature extraction for the NVML red-team track.

Reproduces the shape of Rahman & Tajdari (arXiv:2606.19262) §4.2's feature
design as closely as the published paper text lets us: a structural/roofline
layer (mean power, mean utilization — placing the workload in
arithmetic-intensity space) plus a temporal layer (autocorrelation, CV,
periodicity) that disambiguates within that region, plus the
"physics-based evasion-resistant" features they call out by name in their
Round 3+ hardening (cumulative energy, power-memory correlation,
pre-allocation memory-plateau features). We do not have their source code
(see docs/REDTEAM.md — we looked and couldn't locate a public repo), so
this is a faithful-to-the-paper-text reimplementation, not a byte-identical
reproduction; exact feature formulas (e.g. how "time to memory plateau" is
defined) are our own reasonable reading, documented inline.

Windowing: 30 s primary window, 15 s stride, matching their §5.1 setup.
Reuses `src.detect.features.iter_windows` (unmodified import) to find each
workload's [start, end] marker span, then slides window/stride within it —
`iter_windows` itself only returns the whole span, sub-windowing is new
here.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ..detect.features import iter_windows, load_trace  # noqa: F401  (load_trace re-exported for convenience)
from .telemetry import SIGNAL_NAMES

WINDOW_S = 30.0
STRIDE_S = 15.0

# Binary governance question per Rahman & Tajdari §2.3: "is a monitored GPU
# being used for training?" — kv_disguise counts as ground-truth training
# (it *is* real backward passes + real gradient sync, just reshaped), which
# is exactly the case their classifier is meant to catch.
TRAIN_LIKE = {"train", "diloco", "train_disguised", "composite", "low_mem_disguised", "grad_accum_disguised", "white_box_disguised", "grad_checkpoint_disguised"}
NOT_TRAIN_LIKE = {"infer"}


def _label_from_name(name: str) -> str:
    n = name.lower()
    # order matters: "composite" is checked before "diloco"/"disguise" so a
    # kv_diloco_composite-style name (which contains both substrings) gets
    # its own label rather than silently aliasing to one of the mechanisms
    # it's actually combining.
    if "composite" in n:
        return "composite"
    if "low_mem" in n:
        return "low_mem_disguised"
    if "grad_accum" in n:
        return "grad_accum_disguised"
    if "white_box" in n:
        return "white_box_disguised"
    if "grad_checkpoint" in n:
        return "grad_checkpoint_disguised"
    if "diloco" in n:
        return "diloco"
    if "kv_disguise" in n or "disguise" in n:
        return "train_disguised"
    if "train" in n:
        return "train"
    if "infer" in n:
        return "infer"
    return "other"


def is_training_label(label: str) -> bool | None:
    if label in TRAIN_LIKE:
        return True
    if label in NOT_TRAIN_LIKE:
        return False
    return None  # "other" / non-ML — excluded from the binary task


@dataclass
class RedteamWindowFeatures:
    name: str
    label: str
    is_training: bool | None
    t0: float
    t1: float
    duration_s: float
    n_samples: int
    # structural (roofline) layer
    mean_power_w: float = 0.0
    mean_util_pct: float = 0.0
    # temporal layer, per key signal (power, util)
    cv_power: float = 0.0
    cv_util: float = 0.0
    autocorr1_power: float = 0.0
    autocorr1_util: float = 0.0
    periodicity_power: float = 0.0
    periodicity_util: float = 0.0
    # physics-based evasion-resistant features — computed once per
    # workload run (from its full marker span), attached to every window
    # of that run, since they describe the run's trajectory, not a 30s slice
    cumulative_energy_j: float = 0.0
    power_mem_corr: float = 0.0
    first_30s_mem_delta_mb: float = 0.0
    time_to_mem_plateau_s: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _nvml_rows(rows: list[dict]) -> list[dict]:
    return [
        r for r in rows
        if r.get("kind") == "event" and r.get("type") == "nvml9_sample"
    ]


def _cv(x: np.ndarray) -> float:
    m = float(x.mean())
    if abs(m) < 1e-9:
        return 0.0
    return float(x.std(ddof=1) / m) if len(x) > 1 else 0.0


def _autocorr1(x: np.ndarray) -> float:
    if len(x) < 3:
        return 0.0
    d = x - x.mean()
    denom = float(np.dot(d, d))
    if denom < 1e-12:
        return 0.0
    return float(np.dot(d[1:], d[:-1]) / denom)


def _periodicity(x: np.ndarray) -> float:
    """Spectral peak / mean power ratio on an (assumed ~1Hz) series."""
    if len(x) < 8:
        return 0.0
    y = x - x.mean()
    spec = np.abs(np.fft.rfft(y)) ** 2
    if len(spec) < 2:
        return 0.0
    peak = float(np.max(spec[1:]))
    mean = float(np.mean(spec[1:])) + 1e-12
    return peak / mean


def _run_level_physics_features(run_rows: list[dict]) -> dict[str, float]:
    """Cumulative energy, power-memory correlation, memory-plateau timing,
    computed once over a workload's *entire* marker span (not a 30s slice)
    — these describe the run's trajectory, matching how the paper frames
    them as invariants an evader "cannot suppress without aborting
    training".
    """
    if not run_rows:
        return dict(
            cumulative_energy_j=0.0, power_mem_corr=0.0,
            first_30s_mem_delta_mb=0.0, time_to_mem_plateau_s=0.0,
        )
    ts = np.array([float(r["t"]) for r in run_rows])
    order = np.argsort(ts)
    ts = ts[order]
    power = np.array([float(r.get("mean_power_w", 0.0)) for r in run_rows])[order]
    mem = np.array([float(r.get("mean_mem_used_mb", 0.0)) for r in run_rows])[order]
    t0 = ts[0]
    rel_t = ts - t0

    # cumulative energy: trapezoidal integral of power dt (manual, not
    # np.trapz/np.trapezoid — that function's name changed across the
    # numpy 1.x/2.x versions this repo's requirements.txt spans)
    if len(power) > 1:
        dt = np.diff(rel_t)
        energy = float(np.sum((power[:-1] + power[1:]) / 2.0 * dt))
    else:
        energy = 0.0

    # power-memory correlation
    if len(power) > 2 and power.std() > 1e-9 and mem.std() > 1e-9:
        corr = float(np.corrcoef(power, mem)[0, 1])
    else:
        corr = 0.0

    # first-30s memory delta: mem_used at ~30s into the run minus at t0
    idx_30s = int(np.searchsorted(rel_t, 30.0))
    idx_30s = min(idx_30s, len(mem) - 1)
    first_30s_delta = float(mem[idx_30s] - mem[0])

    # time-to-plateau: first t where a trailing 5s window's memory range
    # stays below 2% of that window's mean for the rest of the run.
    # Heuristic reading of the paper's "pre-allocation memory-plateau"
    # idea, not a reproduction of their exact formula (unavailable to us).
    plateau_t = float(rel_t[-1])  # default: never plateaus within the run
    for i in range(len(rel_t)):
        window_mask = (rel_t >= rel_t[i]) & (rel_t <= rel_t[i] + 5.0)
        if window_mask.sum() < 2:
            continue
        w = mem[window_mask]
        spread = float(w.max() - w.min())
        level = float(w.mean()) + 1e-9
        if spread / level < 0.02:
            # check it stays flat for the remainder too, else keep scanning
            tail = mem[i:]
            tail_level = float(tail.mean()) + 1e-9
            if (float(tail.max()) - float(tail.min())) / tail_level < 0.05:
                plateau_t = float(rel_t[i])
                break

    return dict(
        cumulative_energy_j=energy,
        power_mem_corr=corr,
        first_30s_mem_delta_mb=first_30s_delta,
        time_to_mem_plateau_s=plateau_t,
    )


def extract_redteam_features(
    rows: list[dict],
    window_s: float = WINDOW_S,
    stride_s: float = STRIDE_S,
) -> list[RedteamWindowFeatures]:
    nvml = _nvml_rows(rows)
    out: list[RedteamWindowFeatures] = []

    for name, t0, t1 in iter_windows(rows):
        run_rows = [r for r in nvml if t0 <= float(r["t"]) <= t1]
        if not run_rows:
            continue
        physics = _run_level_physics_features(run_rows)
        label = _label_from_name(name)
        span = max(t1 - t0, 1e-6)

        starts = [t0] if span <= window_s else list(np.arange(t0, t1 - window_s + 1e-9, stride_s))
        if not starts:
            starts = [t0]

        for w_start in starts:
            w_end = min(w_start + window_s, t1)
            win_rows = [r for r in run_rows if w_start <= float(r["t"]) <= w_end]
            if len(win_rows) < 3:
                continue
            ts = np.array([float(r["t"]) for r in win_rows])
            order = np.argsort(ts)
            power = np.array([float(r.get("mean_power_w", 0.0)) for r in win_rows])[order]
            util = np.array([float(r.get("mean_gpu_util_pct", 0.0)) for r in win_rows])[order]

            out.append(RedteamWindowFeatures(
                name=name,
                label=label,
                is_training=is_training_label(label),
                t0=float(w_start),
                t1=float(w_end),
                duration_s=float(w_end - w_start),
                n_samples=len(win_rows),
                mean_power_w=float(power.mean()),
                mean_util_pct=float(util.mean()),
                cv_power=_cv(power),
                cv_util=_cv(util),
                autocorr1_power=_autocorr1(power),
                autocorr1_util=_autocorr1(util),
                periodicity_power=_periodicity(power),
                periodicity_util=_periodicity(util),
                **physics,
            ))
    return out


__all__ = [
    "SIGNAL_NAMES",
    "WINDOW_S",
    "STRIDE_S",
    "RedteamWindowFeatures",
    "extract_redteam_features",
    "is_training_label",
    "load_trace",
]
