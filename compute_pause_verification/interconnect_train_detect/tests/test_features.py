"""Unit tests for features + threshold (no GPU)."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from src.detect.features import extract_window_features, load_trace
from src.detect.threshold import classify, score_report


def _trace(rows):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    Path(path).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def test_window_features_and_threshold():
    rows = [
        {"kind": "marker", "name": "train_ddp", "phase": "start", "t": 0.0},
        {"kind": "sample", "source": "synthetic", "t": 0.1, "d_total": 2_000_000},
        {"kind": "sample", "source": "synthetic", "t": 1.1, "d_total": 2_000_000},
        {"kind": "marker", "name": "train_ddp", "phase": "end", "t": 2.0},
        {"kind": "marker", "name": "infer_dp", "phase": "start", "t": 3.0},
        {"kind": "sample", "source": "synthetic", "t": 3.1, "d_total": 50_000},
        {"kind": "sample", "source": "synthetic", "t": 4.1, "d_total": 50_000},
        {"kind": "marker", "name": "infer_dp", "phase": "end", "t": 5.0},
        {"kind": "marker", "name": "diloco", "phase": "start", "t": 6.0},
        {"kind": "sample", "source": "synthetic", "t": 6.1, "d_total": 80_000},
        {"kind": "sample", "source": "synthetic", "t": 7.1, "d_total": 80_000},
        {"kind": "marker", "name": "diloco", "phase": "end", "t": 8.0},
    ]
    path = _trace(rows)
    feats = extract_window_features(load_trace(path), prefer_source="synthetic")
    assert len(feats) == 3
    dets = classify(feats, bandwidth_threshold_gbps=0.01)
    report = score_report(dets)
    assert report["tp"] == 1
    assert report["tn"] == 1
    assert "diloco" in report["evade_under_threshold"] or report["evade_under_threshold"] == ["diloco"]
