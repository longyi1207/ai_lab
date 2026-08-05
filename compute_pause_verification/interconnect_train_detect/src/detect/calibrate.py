"""Auto-calibrate Seferis-style bandwidth threshold from labeled GB/s samples.

Methods:
  midpoint  — (mean_train + mean_infer) / 2
  youden    — maximize TPR - FPR on pooled samples (needs ≥1 each)
  quantile  — midpoint of train q_lo and infer q_hi (robust to outliers)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import numpy as np


@dataclass
class CalibrationResult:
    threshold_gbps: float
    method: str
    mean_train: float
    mean_infer: float
    n_train: int
    n_infer: int
    train_below: int  # false negatives at threshold
    infer_above: int  # false positives
    separation_gap: float  # mean_train - mean_infer
    ok: bool
    note: str

    def to_dict(self) -> dict:
        return asdict(self)


def _arr(x: Sequence[float]) -> np.ndarray:
    return np.asarray(list(x), dtype=np.float64)


def calibrate_threshold(
    train: Sequence[float],
    infer: Sequence[float],
    method: str = "youden",
    quantile_lo: float = 0.1,
    quantile_hi: float = 0.9,
) -> CalibrationResult:
    a, b = _arr(train), _arr(infer)
    if len(a) < 1 or len(b) < 1:
        return CalibrationResult(
            threshold_gbps=float("nan"), method=method,
            mean_train=float(a.mean()) if len(a) else float("nan"),
            mean_infer=float(b.mean()) if len(b) else float("nan"),
            n_train=len(a), n_infer=len(b),
            train_below=0, infer_above=0, separation_gap=float("nan"),
            ok=False, note="need ≥1 train and ≥1 infer sample",
        )

    method = method.lower()
    if method == "midpoint":
        thr = float((a.mean() + b.mean()) / 2.0)
    elif method == "quantile":
        thr = float((np.quantile(a, quantile_lo) + np.quantile(b, quantile_hi)) / 2.0)
    elif method == "youden":
        # candidate thresholds = all unique sample values + midpoints
        vals = np.sort(np.unique(np.concatenate([a, b])))
        if len(vals) == 1:
            thr = float(vals[0])
        else:
            cands = list(vals) + list((vals[:-1] + vals[1:]) / 2.0)
            best_j, thr = -1e9, float(vals.mean())
            for t in cands:
                tpr = float(np.mean(a >= t))
                fpr = float(np.mean(b >= t))
                j = tpr - fpr
                if j > best_j:
                    best_j, thr = j, float(t)
    else:
        raise ValueError(f"unknown calibration method: {method}")

    train_below = int(np.sum(a < thr))
    infer_above = int(np.sum(b >= thr))
    gap = float(a.mean() - b.mean())
    ok = gap > 0 and train_below == 0 and infer_above == 0
    note = "clean separation" if ok else (
        "overlap — threshold cannot perfectly separate; use stats gate / richer features"
    )
    return CalibrationResult(
        threshold_gbps=thr, method=method,
        mean_train=float(a.mean()), mean_infer=float(b.mean()),
        n_train=len(a), n_infer=len(b),
        train_below=train_below, infer_above=infer_above,
        separation_gap=gap, ok=ok, note=note,
    )
