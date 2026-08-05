"""Seferis-style threshold detector on mean cross-node bandwidth."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .features import WindowFeatures


@dataclass
class Detection:
    name: str
    label: str
    predicted: str  # training | not_training
    gbps_mean: float
    threshold_gbps: float
    flagged: bool


def classify(
    windows: Iterable[WindowFeatures],
    bandwidth_threshold_gbps: float,
) -> list[Detection]:
    out = []
    for w in windows:
        flagged = w.gbps_mean >= bandwidth_threshold_gbps
        out.append(Detection(
            name=w.name,
            label=w.label,
            predicted="training" if flagged else "not_training",
            gbps_mean=w.gbps_mean,
            threshold_gbps=bandwidth_threshold_gbps,
            flagged=flagged,
        ))
    return out


def score_report(detections: list[Detection]) -> dict:
    """Binary: true train labels should be flagged; infer should not.

    diloco / train_disguised counted separately as evade success if not flagged.
    """
    def is_true_train(label: str) -> bool:
        return label == "train"

    def is_true_infer(label: str) -> bool:
        return label == "infer"

    tp = fp = tn = fn = 0
    evade_misses = []  # adversarial that slipped under threshold
    for d in detections:
        if is_true_train(d.label):
            if d.flagged:
                tp += 1
            else:
                fn += 1
        elif is_true_infer(d.label):
            if d.flagged:
                fp += 1
            else:
                tn += 1
        elif d.label in ("diloco", "train_disguised") and not d.flagged:
            evade_misses.append(d.name)

    n = tp + tn + fp + fn
    return {
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "accuracy": (tp + tn) / n if n else None,
        "train_recall": tp / (tp + fn) if (tp + fn) else None,
        "infer_specificity": tn / (tn + fp) if (tn + fp) else None,
        "evade_under_threshold": evade_misses,
        "detections": [
            {
                "name": d.name, "label": d.label, "predicted": d.predicted,
                "gbps_mean": d.gbps_mean, "threshold_gbps": d.threshold_gbps,
            }
            for d in detections
        ],
    }
