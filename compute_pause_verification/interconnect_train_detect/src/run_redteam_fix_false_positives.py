"""Fix the false-positive gap found by run_false_positive_check.py: fold
heavy-but-legitimate inference examples into the training corpus as
correctly-labeled NEGATIVE (is_training=False) examples — same mechanism
run_redteam_loop.py uses for adversarial positives, opposite class, not
part of that loop (its validate_rounds() requires every round resolve
True; this script is deliberately separate, see docs/REDTEAM.md).

Two-sided check, not just "does it stop false-positiving":
  (a) a FRESH execution of heavy-inference variants (different batch/seq
      than what got folded in, so this tests generalization, not
      memorization of the exact prior false-positive trace) should now
      score low P(training).
  (b) the retrained classifier must still catch every PRIOR round's
      held-out adversarial disguise (reuses
      run_redteam_loop._load_prior_loop's chain-walking) — fixing false
      positives by making the classifier permissive in a way that
      reopens old evasions would be a regression, not a fix.

Usage:
    python -m src.run_redteam_fix_false_positives \\
        --resume-from outputs/azure_redteam_loop_continued4 \\
        --false-positive-trace outputs/azure_false_positive_check/trace.jsonl \\
        --false-positive-names infer_dp_bigbatch infer_dp_longctx infer_tp_heavy \\
        --config configs/azure_redteam_false_positive_fix.yaml \\
        --out outputs/azure_redteam_fp_fix
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .redteam.classifier import evaluate, save, to_matrix, train_classifier
from .redteam.features import extract_redteam_features, load_trace
from .run_redteam import execute_session
from .run_redteam_loop import _load_prior_loop
from .util import ROOT, ensure_dir, load_config, setup_logging, write_json

log = setup_logging("run_redteam_fix_false_positives")


def run(
    resume_from: Path,
    fp_trace_path: Path,
    fp_names: list[str],
    cfg: dict,
    config_path: str,
    out_dir: Path,
) -> dict:
    ensure_dir(out_dir)

    # --- reconstruct the full cumulative training set from the adversarial loop ---
    prior_trajectory, prior_held_out = _load_prior_loop(resume_from)
    log.info("reconstructed %d prior adversarial rounds from %s", len(prior_trajectory), resume_from)

    # cumulative_X/y start from the SAME benign baseline the loop itself used —
    # its trace.jsonl is unchanged and still on disk, path comes from this
    # script's own config.
    benign_out = Path(cfg["baseline_out"])
    if not benign_out.is_absolute():
        benign_out = ROOT / benign_out
    baseline_rows = load_trace(benign_out / "trace.jsonl")
    baseline_feats = extract_redteam_features(baseline_rows)
    benign_names = {w.get("name", w["kind"]) for w in cfg.get("benign_workloads", [])}
    benign_feats = [f for f in baseline_feats if f.name in benign_names]

    X_cum, y_cum, _ = to_matrix(benign_feats)
    for _, X, y, _n in prior_held_out:
        X_cum = np.concatenate([X_cum, X], axis=0)
        y_cum = np.concatenate([y_cum, y], axis=0)
    n_before_fix = len(y_cum)

    # --- fold in the false-positive examples as NEGATIVE (is_training=False) ---
    fp_rows = load_trace(fp_trace_path)
    fp_feats = [f for f in extract_redteam_features(fp_rows) if f.name in fp_names]
    if not fp_feats:
        raise RuntimeError(f"no matching windows for {fp_names} in {fp_trace_path}")
    X_fp, y_fp, names_fp = to_matrix(fp_feats)
    if not (y_fp == 0).all():
        raise RuntimeError(
            f"expected all false-positive-fix examples to resolve is_training=False, "
            f"got y={y_fp.tolist()} — check that {fp_names} match features.py's infer-labeling"
        )
    log.info("folding in %d false-positive (negative) windows from %s", len(y_fp), fp_trace_path)

    X_fixed = np.concatenate([X_cum, X_fp], axis=0)
    y_fixed = np.concatenate([y_cum, y_fp], axis=0)
    fixed_clf, train_result = train_classifier(X_fixed, y_fixed)
    save(fixed_clf, out_dir / "classifier_fixed.joblib")

    # --- (a) FRESH heavy-inference execution: different params than what was folded in ---
    fresh_workloads = cfg.get("fresh_benign_stress_workloads", [])
    fresh_results = execute_session(cfg, config_path, fresh_workloads, out_dir, "fresh_benign_stress")
    fresh_rows = load_trace(out_dir / "trace.jsonl")
    fresh_eval_by_name = {}
    for w in fresh_workloads:
        name = w.get("name", w["kind"])
        feats = [f for f in extract_redteam_features(fresh_rows) if f.name == name]
        if not feats:
            log.warning("no feature windows for fresh check %s", name)
            continue
        X, y, names = to_matrix(feats)
        ev = evaluate(fixed_clf, X, y, names)
        fresh_eval_by_name[name] = ev
        log.info("fresh heavy-inference %-20s n=%d mean_P(training)=%.3f (want LOW now)",
                  name, ev["n_windows"], sum(r["p_training"] for r in ev["rows"]) / max(len(ev["rows"]), 1))

    # --- (b) regression check: still catches every PRIOR adversarial round? ---
    regression_check = []
    for round_name, X_round, y_round, names_round in prior_held_out:
        ev = evaluate(fixed_clf, X_round, y_round, names_round)
        regression_check.append({"round_name": round_name, "accuracy": ev.get("accuracy"), "n_windows": ev["n_windows"]})
        log.info("regression check vs %-20s acc=%.3f (want still ~1.0)", round_name, ev.get("accuracy", float("nan")))

    n_regressed = sum(1 for r in regression_check if (r["accuracy"] or 0) < 0.9)

    report = {
        "resume_from": str(resume_from),
        "false_positive_trace": str(fp_trace_path),
        "n_before_fix": n_before_fix,
        "n_false_positive_examples_folded_in": len(y_fp),
        "n_after_fix": len(y_fixed),
        "fresh_heavy_inference_eval": {
            name: {k: v for k, v in ev.items() if k != "rows"} | {"mean_p_training": sum(r["p_training"] for r in ev["rows"]) / max(len(ev["rows"]), 1), "rows": ev["rows"]}
            for name, ev in fresh_eval_by_name.items()
        },
        "regression_check_vs_prior_rounds": regression_check,
        "n_rounds_regressed": n_regressed,
        "interpretation": (
            "fresh_heavy_inference_eval should now show LOW mean_p_training (fixed) for "
            "workload variants the classifier never saw folded in as negatives — this is "
            "generalization, not memorization, since the folded-in and fresh-tested batch/seq "
            "values differ. regression_check_vs_prior_rounds should stay ~1.0 across every "
            "entry — n_rounds_regressed > 0 means fixing false positives reopened an old "
            "evasion, which would make this a bad trade, not a fix."
        ),
    }
    write_json(out_dir / "false_positive_fix_report.json", report)
    log.info("DONE — folded %d negatives, n_rounds_regressed=%d/%d", len(y_fp), n_regressed, len(regression_check))
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--resume-from", required=True, help="a completed run_redteam_loop.py output dir")
    ap.add_argument("--false-positive-trace", required=True)
    ap.add_argument("--false-positive-names", nargs="+", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)

    def _abs(p: str) -> Path:
        pp = Path(p)
        return pp if pp.is_absolute() else ROOT / pp

    run(
        _abs(args.resume_from), _abs(args.false_positive_trace), args.false_positive_names,
        cfg, args.config, _abs(args.out),
    )


if __name__ == "__main__":
    main()
