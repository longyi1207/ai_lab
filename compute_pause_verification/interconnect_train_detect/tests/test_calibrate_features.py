"""Tests for calibration + richer features + power."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from src.detect.calibrate import calibrate_threshold
from src.detect.features import extract_window_features, load_trace
from src.detect.power import n_per_group_two_sample
from src.detect.threshold import classify, score_report


def test_calibrate_youden_separates():
    train = [10.0, 11.0, 12.0, 9.5]
    infer = [0.5, 0.8, 1.0, 0.6]
    r = calibrate_threshold(train, infer, method="youden")
    assert r.ok
    assert r.mean_infer < r.threshold_gbps < r.mean_train


def test_power_n_reasonable():
    r = n_per_group_two_sample(0.8, 0.05, 0.8)
    assert 20 <= r.n_per_group <= 40


def test_rich_features_burstiness():
    rows = [
        {"kind": "marker", "name": "train_ddp", "phase": "start", "t": 0.0},
        {"kind": "sample", "source": "synthetic", "t": 0.1, "d_total": 1_000_000},
        {"kind": "sample", "source": "synthetic", "t": 0.2, "d_total": 5_000_000},
        {"kind": "sample", "source": "synthetic", "t": 0.3, "d_total": 1_000_000},
        {"kind": "marker", "name": "train_ddp", "phase": "step", "t": 0.15},
        {"kind": "marker", "name": "train_ddp", "phase": "step", "t": 0.25},
        {"kind": "event", "type": "nccl_collective", "t": 0.12, "bytes": 1000},
        {"kind": "marker", "name": "train_ddp", "phase": "end", "t": 0.4},
    ]
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    Path(path).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    feats = extract_window_features(load_trace(path), prefer_source="synthetic")
    assert len(feats) == 1
    f = feats[0]
    assert f.n_steps == 2
    assert f.burstiness > 0
    assert f.n_nccl_collectives == 1
    dets = classify(feats, 0.01)
    assert score_report(dets)["tp"] + score_report(dets)["fn"] == 1
