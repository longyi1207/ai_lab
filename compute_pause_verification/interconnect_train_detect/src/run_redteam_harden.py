"""One hardening round for the H2 red-team track (see docs/REDTEAM.md
"Hardening loop"): Rahman & Tajdari's methodology is iterative — train,
get fooled by an evasion strategy, fold those examples into the training
set as (correctly) positive "is training" examples, retrain, then test
against FRESH executions of the same and new strategies. `run_redteam.py`
only does the first half (train once on clean data, test once) — this
script does one round of the retrain-and-retest loop on top of an
existing `run_redteam.py` output.

Design, to avoid a circularity trap: the adversarial windows from the
BASELINE run become training data for the hardened classifier — they are
NOT reused as the held-out test set (a classifier "detecting" the exact
windows it was just trained on proves nothing). Held-out testing uses a
FRESH execution of the adversarial workloads instead, and the SAME
held-out set is scored against both the baseline and hardened classifiers
so any difference is attributable to hardening, not to a different test
set.

Usage:
    python -m src.run_redteam_harden --baseline-out outputs/azure_redteam_single_node \\
        --config configs/azure_redteam_single_node.yaml \\
        --out outputs/azure_redteam_single_node_round2
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .redteam.classifier import evaluate, load, save, to_matrix, train_classifier
from .redteam.features import extract_redteam_features, load_trace
from .run_redteam import execute_session
from .util import ROOT, ensure_dir, load_config, setup_logging, write_json

log = setup_logging("run_redteam_harden")


def run(baseline_out: Path, cfg: dict, config_path: str, out_dir: Path) -> dict:
    ensure_dir(out_dir)

    # --- baseline (round 1) data ---
    baseline_rows = load_trace(baseline_out / "trace.jsonl")
    baseline_feats = extract_redteam_features(baseline_rows)
    benign_names = {w.get("name", w["kind"]) for w in cfg.get("benign_workloads", [])}
    adv_names = {w.get("name", w["kind"]) for w in cfg.get("adversarial_workloads", [])}
    baseline_benign = [f for f in baseline_feats if f.name in benign_names]
    baseline_adv = [f for f in baseline_feats if f.name in adv_names]

    if not baseline_adv:
        raise RuntimeError(
            f"no adversarial windows found in {baseline_out}/trace.jsonl — "
            "nothing to fold into hardening. Was this really a completed round-1 run?"
        )

    baseline_clf = load(baseline_out / "classifier.joblib")

    # --- fresh, held-out adversarial execution (round 2's test set) ---
    log.info("running FRESH adversarial workloads for held-out round-2 testing (not reused for training)")
    fresh_results = execute_session(
        cfg, config_path, cfg.get("adversarial_workloads", []), out_dir,
        "adversarial_heldout", node_name="redteam0_round2",
    )
    fresh_rows = load_trace(out_dir / "trace.jsonl")
    fresh_feats = [f for f in extract_redteam_features(fresh_rows) if f.name in adv_names]
    if not fresh_feats:
        raise RuntimeError("fresh adversarial run produced no feature windows — check step counts / GPU indices")
    X_heldout, y_heldout, names_heldout = to_matrix(fresh_feats)

    # --- evaluate the UNMODIFIED round-1 classifier against the fresh held-out set ---
    baseline_vs_fresh = evaluate(baseline_clf, X_heldout, y_heldout, names_heldout)

    # --- hardened (round 2) classifier: round-1 benign + round-1 adversarial (as positive examples) ---
    X_benign, y_benign, _ = to_matrix(baseline_benign)
    X_adv_train, y_adv_train, _ = to_matrix(baseline_adv)
    X_hardened = np.concatenate([X_benign, X_adv_train], axis=0)
    y_hardened = np.concatenate([y_benign, y_adv_train], axis=0)
    hardened_clf, hardened_train_result = train_classifier(X_hardened, y_hardened)
    save(hardened_clf, out_dir / "classifier_round2.joblib")

    # --- evaluate the HARDENED classifier against the SAME fresh held-out set ---
    hardened_vs_fresh = evaluate(hardened_clf, X_heldout, y_heldout, names_heldout)

    report = {
        "baseline_out": str(baseline_out),
        "n_baseline_benign_windows": len(baseline_benign),
        "n_baseline_adversarial_windows_folded_into_training": len(baseline_adv),
        "n_heldout_windows": len(fresh_feats),
        "hardened_train_result": hardened_train_result.to_dict(),
        "round1_classifier_vs_fresh_heldout": baseline_vs_fresh,
        "round2_hardened_classifier_vs_SAME_fresh_heldout": hardened_vs_fresh,
        "workload_results": fresh_results,
        "interpretation": (
            "round1_classifier_vs_fresh_heldout.accuracy is the baseline classifier's "
            "detection rate on evasion attempts it never saw a version of. "
            "round2_hardened_classifier_vs_SAME_fresh_heldout.accuracy is the SAME "
            "held-out set scored by a classifier that had round-1's evasion examples "
            "folded into training — an improvement here is attributable to hardening, "
            "not to an easier test set, since both numbers are against identical windows."
        ),
        "limitations": [
            "One hardening round only (Rahman & Tajdari did 5) — this shows whether "
            "hardening helps at all, not whether it converges to their ~99% multi-GPU "
            "detection rate.",
            "Small N throughout (see docs/REDTEAM.md) — directional, not statistically "
            "powered.",
            "Fresh held-out windows come from the SAME workload implementations "
            "(kv_disguise/diloco) with the same parameters as round 1 — this tests "
            "whether hardening catches a repeat of the same trick, not a genuinely "
            "new evasion strategy (that would need a third workload variant).",
        ],
    }
    write_json(out_dir / "hardening_report.json", report)
    log.info(
        "DONE round1_acc=%.3f round2_acc=%.3f (higher is better detection) n_heldout=%d",
        baseline_vs_fresh.get("accuracy", float("nan")),
        hardened_vs_fresh.get("accuracy", float("nan")),
        len(fresh_feats),
    )
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-out", required=True, help="round-1 run_redteam.py output_dir")
    ap.add_argument("--config", required=True, help="same config used for the baseline run")
    ap.add_argument("--out", required=True, help="output dir for round-2 fresh run + hardening_report.json")
    args = ap.parse_args()
    cfg = load_config(args.config)
    baseline_out = Path(args.baseline_out)
    if not baseline_out.is_absolute():
        baseline_out = ROOT / baseline_out
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    run(baseline_out, cfg, args.config, out_dir)


if __name__ == "__main__":
    main()
