"""Unit tests for the NVML red-team track's feature extraction + classifier
(no GPU, no network — pure in-memory trace rows)."""
from __future__ import annotations

import random

from src.redteam.classifier import evaluate, to_matrix, train_classifier
from src.redteam.features import extract_redteam_features


def _nvml_row(t, power, mem, util=60.0):
    return {
        "kind": "event", "type": "nvml9_sample", "t": t,
        "mean_gpu_util_pct": util, "std_gpu_util_pct": 2.0,
        "mean_power_w": power, "std_power_w": 5.0,
        "mean_mem_used_mb": mem, "std_mem_used_mb": 10.0,
        "mean_mem_util_pct": util * 0.6, "std_mem_util_pct": 2.0,
        "mean_temp_c": 60.0, "std_temp_c": 1.0,
        "mean_sm_clock_mhz": 1400.0, "std_sm_clock_mhz": 10.0,
        "mean_mem_clock_mhz": 1500.0, "std_mem_clock_mhz": 5.0,
        "mean_pcie_tx_mbps": 100.0, "std_pcie_tx_mbps": 10.0,
        "mean_pcie_rx_mbps": 100.0, "std_pcie_rx_mbps": 10.0,
    }


def _synth_run(name: str, t0: float, duration: float, power_level: float, mem_ramp: float, hz: float = 5.0):
    rng = random.Random(42)
    rows = [{"kind": "marker", "name": name, "phase": "start", "t": t0}]
    n = int(duration * hz)
    for i in range(n):
        t = t0 + i / hz
        power = power_level + rng.gauss(0, 3)
        mem = 4000.0 + mem_ramp * (t - t0)
        rows.append(_nvml_row(t, power, mem))
    rows.append({"kind": "marker", "name": name, "phase": "end", "t": t0 + duration})
    return rows


def test_extract_redteam_features_labels_and_windows():
    rows = []
    rows += _synth_run("train_ddp", 0.0, 12.0, power_level=320.0, mem_ramp=50.0)
    rows += _synth_run("infer_dp", 20.0, 12.0, power_level=140.0, mem_ramp=0.0)

    feats = extract_redteam_features(rows, window_s=30.0, stride_s=15.0)
    labels = {f.name: f.label for f in feats}
    assert labels["train_ddp"] == "train"
    assert labels["infer_dp"] == "infer"
    # short runs (< window_s) collapse to exactly one window each
    assert sum(1 for f in feats if f.name == "train_ddp") == 1
    assert sum(1 for f in feats if f.name == "infer_dp") == 1

    train_f = next(f for f in feats if f.name == "train_ddp")
    infer_f = next(f for f in feats if f.name == "infer_dp")
    assert train_f.is_training is True
    assert infer_f.is_training is False
    assert train_f.mean_power_w > infer_f.mean_power_w
    assert train_f.cumulative_energy_j > infer_f.cumulative_energy_j


def test_classifier_train_and_evaluate_roundtrip():
    rows = []
    # several benign runs per class so RandomForest has something to learn from
    for i in range(4):
        rows += _synth_run(f"train_ddp_{i}", i * 20.0, 12.0, power_level=320.0, mem_ramp=50.0)
        rows += _synth_run(f"infer_dp_{i}", i * 20.0 + 100.0, 12.0, power_level=140.0, mem_ramp=0.0)

    feats = extract_redteam_features(rows)
    X, y, names = to_matrix(feats)
    assert len(X) == 8
    assert set(y.tolist()) == {0, 1}

    clf, result = train_classifier(X, y)
    assert result.n_train == 8
    assert set(result.feature_importance.keys()) == {
        "mean_power_w", "mean_util_pct", "cv_power", "cv_util",
        "autocorr1_power", "autocorr1_util", "periodicity_power", "periodicity_util",
        "cumulative_energy_j", "power_mem_corr", "first_30s_mem_delta_mb", "time_to_mem_plateau_s",
    }

    ev = evaluate(clf, X, y, names)
    assert ev["accuracy"] >= 0.5  # trivially separable synthetic power gap
    assert ev["n_windows"] == 8


def test_non_ml_labels_excluded_from_binary_task():
    rows = _synth_run("cryptomining", 0.0, 12.0, power_level=250.0, mem_ramp=0.0)
    feats = extract_redteam_features(rows)
    assert feats[0].label == "other"
    assert feats[0].is_training is None
    X, y, names = to_matrix(feats)
    assert len(X) == 0  # dropped, matches the paper's binary framing
