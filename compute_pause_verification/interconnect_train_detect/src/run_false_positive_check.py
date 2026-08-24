"""False-positive check (see docs/REDTEAM.md): every round so far tested
one direction of error — does disguised TRAINING evade detection? This
tests the direction that actually matters for real deployment
viability — does a classifier hardened on many disguised-training
examples start crying wolf on heavier-than-baseline but entirely
LEGITIMATE inference traffic (bigger batch, longer context — the kind of
thing a busy real inference server actually does)?

Deliberately NOT part of run_redteam_loop.py: these are true negatives
(is_training=False), and that loop's validate_rounds() enforces every
round resolve to real training in disguise. Nothing here gets folded into
training regardless of outcome — these are correctly non-training inputs;
a wrong classification is the finding to report, not a defect to silently
patch by relabeling data.

Usage:
    python -m src.run_false_positive_check \\
        --classifier outputs/azure_redteam_loop_continued3/round_13_.../classifier.joblib \\
        --config configs/azure_false_positive_check.yaml \\
        --out outputs/azure_false_positive_check
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .redteam.classifier import evaluate, load, to_matrix
from .redteam.features import extract_redteam_features, load_trace
from .run_redteam import execute_session
from .util import ROOT, ensure_dir, load_config, setup_logging, write_json

log = setup_logging("run_false_positive_check")


def run(classifier_path: Path, cfg: dict, config_path: str, out_dir: Path) -> dict:
    ensure_dir(out_dir)
    clf = load(classifier_path)

    workloads = cfg.get("benign_stress_workloads", [])
    if not workloads:
        raise RuntimeError("config has no benign_stress_workloads — nothing to check")

    results = execute_session(cfg, config_path, workloads, out_dir, "benign_stress_test")
    rows = load_trace(out_dir / "trace.jsonl")

    per_workload = []
    any_false_positive = False
    for w in workloads:
        name = w.get("name", w["kind"])
        feats = [f for f in extract_redteam_features(rows) if f.name == name]
        if not feats:
            log.warning("no feature windows for %s — skipping", name)
            continue
        X, y, names = to_matrix(feats)
        # y from to_matrix would be all 0s (is_training=False, correctly)
        # since this is legitimate inference — evaluate without asserting
        # ground truth, just report what the classifier says
        ev = evaluate(clf, X, y, names)
        false_positives = [r for r in ev["rows"] if r["predicted_training"]]
        if false_positives:
            any_false_positive = True
        per_workload.append({
            "name": name,
            "kind": w["kind"],
            "n_windows": ev["n_windows"],
            "n_false_positives": len(false_positives),
            "mean_p_training": sum(r["p_training"] for r in ev["rows"]) / len(ev["rows"]) if ev["rows"] else None,
            "rows": ev["rows"],
        })
        log.info(
            "%-20s n=%d false_positives=%d/%d mean_P(training)=%.3f",
            name, ev["n_windows"], len(false_positives), ev["n_windows"],
            per_workload[-1]["mean_p_training"] or float("nan"),
        )

    report = {
        "classifier_path": str(classifier_path),
        "any_false_positive": any_false_positive,
        "per_workload": per_workload,
        "workload_results": results,
        "interpretation": (
            "Every workload here is genuinely legitimate inference (is_training=False), "
            "just heavier than the baseline infer_dp/infer_tp configs (bigger batch, "
            "longer context). n_false_positives > 0 for any workload means the classifier "
            "misclassified real, benign inference traffic as training — the deployment-"
            "relevant error mode, not the evasion-relevant one every other round tested."
        ),
    }
    write_json(out_dir / "false_positive_report.json", report)
    log.info("DONE — any_false_positive=%s", any_false_positive)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--classifier", required=True, help="path to a classifier.joblib from any completed round")
    ap.add_argument("--config", required=True, help="config with benign_stress_workloads")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    cfg = load_config(args.config)
    classifier_path = Path(args.classifier)
    if not classifier_path.is_absolute():
        classifier_path = ROOT / classifier_path
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    run(classifier_path, cfg, args.config, out_dir)


if __name__ == "__main__":
    main()
