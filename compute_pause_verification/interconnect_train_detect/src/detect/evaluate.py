"""Production evaluation: threshold (+auto-calibrate) + Welch/Cohen + features."""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from ..util import setup_logging, write_json
from .calibrate import calibrate_threshold
from .features import WindowFeatures, extract_window_features, load_trace
from .stats import pairwise_by_label
from .threshold import classify, score_report

log = setup_logging("evaluate")


def group_gbps_by_label(feats: list[WindowFeatures]) -> dict[str, list[float]]:
    g: dict[str, list[float]] = defaultdict(list)
    for f in feats:
        g[f.label].append(f.gbps_mean)
    return dict(g)


def _comparisons(by_label: dict[str, list[float]], alpha: float, d_min: float, n_boot: int) -> list[dict]:
    out = []
    for a, b in (("train", "infer"), ("train", "diloco"), ("infer", "diloco"),
                 ("train", "train_disguised"), ("infer", "train_disguised")):
        if a in by_label and b in by_label and len(by_label[a]) >= 2 and len(by_label[b]) >= 2:
            out.append(
                pairwise_by_label(
                    {a: by_label[a], b: by_label[b]},
                    pairs=[(a, b)], alpha=alpha, d_min=d_min, n_boot=n_boot,
                )[0].to_dict()
            )
    return out


def _verdict(comparisons: list[dict]) -> dict:
    primary = next((c for c in comparisons if c["name_a"] == "train" and c["name_b"] == "infer"), None)
    return {
        "train_vs_infer": primary,
        "separable": bool(primary and primary["separable"] and primary["mean_diff"] > 0) if primary else None,
        "note": (
            "Need ≥2 replicate windows per label for t/d."
            if primary is None else
            ("SEPARABLE" if primary["separable"] and primary["mean_diff"] > 0 else "NOT SEPARABLE / weak")
        ),
    }


def evaluate(
    trace_path: str | Path,
    threshold_gbps: float | None = None,
    out_path: str | Path | None = None,
    prefer_source: str | None = None,
    alpha: float = 0.05,
    d_min: float = 0.8,
    n_boot: int = 5000,
    calibrate: str | None = "youden",
) -> dict[str, Any]:
    rows = load_trace(trace_path)
    feats = extract_window_features(rows, prefer_source=prefer_source)
    by_label = group_gbps_by_label(feats)

    calib = None
    if calibrate and "train" in by_label and "infer" in by_label:
        calib = calibrate_threshold(by_label["train"], by_label["infer"], method=calibrate)
        if threshold_gbps is None:
            threshold_gbps = calib.threshold_gbps
    if threshold_gbps is None:
        threshold_gbps = 0.05

    dets = classify(feats, float(threshold_gbps))
    report: dict[str, Any] = score_report(dets)
    report["n_windows"] = len(feats)
    report["features"] = [f.to_dict() for f in feats]
    report["trace"] = str(trace_path)
    report["threshold_gbps"] = float(threshold_gbps)
    report["calibration"] = calib.to_dict() if calib else None
    report["samples_gbps"] = {k: v for k, v in by_label.items()}
    report["n_per_label"] = {k: len(v) for k, v in by_label.items()}

    comparisons = _comparisons(by_label, alpha, d_min, n_boot)
    report["stats"] = {
        "alpha": alpha, "d_min": d_min, "n_boot": n_boot,
        "comparisons": comparisons,
        "hypothesis": (
            "H1: mean cross-node GB/s(train) > mean GB/s(infer) with |Cohen d|≥d_min "
            "and Welch p<alpha under benign configs."
        ),
    }
    report["verdict"] = _verdict(comparisons)

    if out_path:
        write_json(out_path, report)
        log.info(
            "wrote %s accuracy=%s thr=%.4g separable=%s",
            out_path, report.get("accuracy"), threshold_gbps, report["verdict"].get("separable"),
        )
    return report


def evaluate_many(
    trace_paths: list[str | Path],
    threshold_gbps: float | None,
    out_path: str | Path,
    prefer_source: str | None = None,
    calibrate: str | None = "youden",
    **kwargs,
) -> dict[str, Any]:
    all_feats: list[WindowFeatures] = []
    for p in trace_paths:
        all_feats.extend(extract_window_features(load_trace(p), prefer_source=prefer_source))
    by_label = group_gbps_by_label(all_feats)
    calib = None
    if calibrate and "train" in by_label and "infer" in by_label:
        calib = calibrate_threshold(by_label["train"], by_label["infer"], method=calibrate)
        if threshold_gbps is None:
            threshold_gbps = calib.threshold_gbps
    if threshold_gbps is None:
        threshold_gbps = 0.05

    dets = classify(all_feats, float(threshold_gbps))
    report: dict[str, Any] = score_report(dets)
    report["n_windows"] = len(all_feats)
    report["features"] = [f.to_dict() for f in all_feats]
    report["traces"] = [str(p) for p in trace_paths]
    report["threshold_gbps"] = float(threshold_gbps)
    report["calibration"] = calib.to_dict() if calib else None
    report["samples_gbps"] = by_label
    report["n_per_label"] = {k: len(v) for k, v in by_label.items()}
    alpha = float(kwargs.get("alpha", 0.05))
    d_min = float(kwargs.get("d_min", 0.8))
    n_boot = int(kwargs.get("n_boot", 5000))
    comparisons = _comparisons(by_label, alpha, d_min, n_boot)
    report["stats"] = {"comparisons": comparisons, "alpha": alpha, "d_min": d_min, "n_boot": n_boot}
    report["verdict"] = _verdict(comparisons)
    write_json(out_path, report)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", default=None)
    ap.add_argument("--traces", nargs="*", default=None)
    ap.add_argument("--threshold-gbps", type=float, default=None)
    ap.add_argument("--calibrate", default="youden",
                    choices=["youden", "midpoint", "quantile", "none"])
    ap.add_argument("--prefer-source", default=None)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--d-min", type=float, default=0.8)
    ap.add_argument("--n-boot", type=int, default=5000)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    calib = None if args.calibrate == "none" else args.calibrate

    if args.traces:
        out = args.out or "outputs/merged_report.json"
        evaluate_many(
            args.traces, args.threshold_gbps, out, args.prefer_source,
            calibrate=calib, alpha=args.alpha, d_min=args.d_min, n_boot=args.n_boot,
        )
    elif args.trace:
        out = args.out or str(Path(args.trace).with_name("report.json"))
        evaluate(
            args.trace, args.threshold_gbps, out, args.prefer_source,
            alpha=args.alpha, d_min=args.d_min, n_boot=args.n_boot, calibrate=calib,
        )
    else:
        raise SystemExit("pass --trace or --traces")


if __name__ == "__main__":
    main()
