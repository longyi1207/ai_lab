"""Multi-round hardening LOOP (see docs/REDTEAM.md "Hardening loop").

`run_redteam_harden.py` does exactly one round (fold in one evasion
strategy's examples, retrain, test against a fresh repeat of the same
strategy). Rahman & Tajdari's actual methodology is an iterative arms
race: round i's classifier (hardened on rounds 0..i-1) meets a NEW
strategy, gets scored, then that strategy's examples get folded in for
round i+1. This script chains N such rounds using genuinely different
evasion parameterizations — not the same trick repeated — analogous in
spirit to their Table 5, though far smaller in scale (this repo's own
mechanisms + parameter sweeps + one composite workload, not 20
independently-designed evasion families).

Usage:
    python -m src.run_redteam_loop --baseline-out outputs/azure_redteam_single_node \\
        --config configs/azure_redteam_hardening_loop.yaml \\
        --out outputs/azure_redteam_loop
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .redteam.classifier import evaluate, save, to_matrix, train_classifier
from .redteam.features import _label_from_name, extract_redteam_features, is_training_label, load_trace
from .run_redteam import execute_session
from .util import ROOT, ensure_dir, load_config, setup_logging, write_json

log = setup_logging("run_redteam_loop")


def validate_rounds(rounds: list[dict]) -> None:
    """Fail fast, before any GPU time is spent, if a round's name won't
    resolve to a valid is_training=True label — this is exactly the bug
    that first surfaced this ("composite_a" silently labeled "other" before
    src/redteam/features.py learned about "composite"). Every round here
    is meant to be real training in disguise, so every one must resolve
    True, not just non-None.
    """
    bad = []
    for r in rounds:
        name = r.get("name", r.get("kind", "?"))
        label = _label_from_name(name)
        if is_training_label(label) is not True:
            bad.append((name, label))
    if bad:
        raise ValueError(
            "hardening_rounds contains names that won't be labeled as training "
            f"(would silently produce empty/wrong feature data): {bad}. "
            "Rename so src/redteam/features.py:_label_from_name recognizes it, or "
            "extend that function — do not run overnight with this unresolved."
        )


def _load_prior_loop(resume_from: Path) -> tuple[list[dict], list[tuple]]:
    """Reconstruct a completed loop's cumulative training data and
    held-out sets by re-extracting features from its already-saved
    per-round trace.jsonl files — no GPU time needed, unlike re-running
    those rounds. Returns (prior_trajectory_entries, held_out_sets).

    RECURSIVE through the whole resume chain: a loop that was itself
    resumed only has round subdirectories on disk for the rounds IT
    actually ran — earlier rounds live under whatever directory ran THEM.
    Naively reconstructing every path as `resume_from / f"round_{i}_{name}"`
    breaks on a resume-of-a-resume (confirmed 2026-08-22: round 0 isn't
    under the round-8/9 continuation dir, it's under the original loop's
    dir). Each entry's own `round_out_dir` (recorded going forward) is
    authoritative when present; index-based filtering against
    `n_rounds_resumed` is the fallback for older reports that predate that
    field.
    """
    prior_report = json.loads((resume_from / "loop_report.json").read_text())
    grandparent = prior_report.get("resumed_from")
    if grandparent:
        earlier_trajectory, earlier_held_out = _load_prior_loop(Path(grandparent))
    else:
        earlier_trajectory, earlier_held_out = [], []

    # Only this report's OWN rounds live under `resume_from` — rounds it
    # itself inherited (already covered by the recursive call above) must
    # not be double-counted.
    n_inherited = prior_report.get("n_rounds_resumed", 0)
    own_ok = [t for t in prior_report["trajectory"] if t.get("status") == "ok" and t["round"] >= n_inherited]

    held_out_sets: list[tuple[str, np.ndarray, np.ndarray, list[str]]] = list(earlier_held_out)
    for t in own_ok:
        round_out = Path(t["round_out_dir"]) if "round_out_dir" in t else resume_from / f"round_{t['round']}_{t['name']}"
        rows = load_trace(round_out / "trace.jsonl")
        feats = [f for f in extract_redteam_features(rows) if f.name == t["name"]]
        if not feats:
            raise RuntimeError(
                f"resume-from round {t['round']} ({t['name']}): trace at {round_out} "
                "produced no matching feature windows — can't reconstruct cumulative training data"
            )
        X, y, names = to_matrix(feats)
        held_out_sets.append((t["name"], X, y, names))
    return earlier_trajectory + own_ok, held_out_sets


def run(baseline_out: Path, cfg: dict, config_path: str, out_dir: Path, resume_from: Path | None = None) -> dict:
    ensure_dir(out_dir)

    rounds = cfg.get("hardening_rounds", [])
    if not rounds:
        raise RuntimeError("config has no hardening_rounds — nothing to loop over")
    validate_rounds(rounds)  # before spending any GPU time

    # Round 0: benign-only baseline, reused from an existing run_redteam.py
    # output rather than re-collected (vanilla train_ddp/infer_dp/infer_tp
    # telemetry doesn't need re-running — only the adversarial rounds need
    # fresh, held-out executions).
    baseline_rows = load_trace(baseline_out / "trace.jsonl")
    baseline_feats = extract_redteam_features(baseline_rows)
    benign_names = {w.get("name", w["kind"]) for w in cfg.get("benign_workloads", [])}
    benign_feats = [f for f in baseline_feats if f.name in benign_names]
    if not benign_feats:
        raise RuntimeError(f"no benign windows found in {baseline_out}/trace.jsonl matching {benign_names}")

    cumulative_X, cumulative_y, _ = to_matrix(benign_feats)

    trajectory: list[dict] = []
    held_out_sets: list[tuple[str, np.ndarray, np.ndarray, list[str]]] = []
    round_offset = 0

    if resume_from is not None:
        log.info("resuming from completed loop at %s — reconstructing cumulative data from saved traces (no GPU time)", resume_from)
        prior_trajectory, prior_held_out = _load_prior_loop(resume_from)
        trajectory.extend(prior_trajectory)
        held_out_sets.extend(prior_held_out)
        for _, X, y, _names in prior_held_out:
            cumulative_X = np.concatenate([cumulative_X, X], axis=0)
            cumulative_y = np.concatenate([cumulative_y, y], axis=0)
        round_offset = len(prior_trajectory)
        log.info("reconstructed %d prior rounds, cumulative n=%d — starting new rounds at index %d",
                  round_offset, len(cumulative_y), round_offset)

    current_clf, _ = train_classifier(cumulative_X, cumulative_y)

    def _flush_partial() -> None:
        # Written after every round, not just at the end — an unattended
        # overnight run that dies on round 4 of 6 should still leave rounds
        # 0-3's results readable, not nothing. See CLAUDE.md's
        # background-job-progress rule.
        write_json(out_dir / "loop_report.json", {
            "baseline_out": str(baseline_out),
            "resumed_from": str(resume_from) if resume_from else None,
            "n_rounds_configured": round_offset + len(rounds),
            "n_rounds_completed": len(trajectory),
            "trajectory": trajectory,
            "status": "in_progress",
        })

    for j, round_cfg in enumerate(rounds):
        i = round_offset + j  # global round index, continuing past any resumed-from rounds
        round_name = round_cfg.get("name", round_cfg["kind"])
        round_out = out_dir / f"round_{i}_{round_name}"
        log.info("=== round %d/%d (new; %d resumed): %s (fresh execution, held out from training) ===",
                  j + 1, len(rounds), round_offset, round_name)

        try:
            results = execute_session(cfg, config_path, [round_cfg], round_out, f"round{i}_{round_name}")
            rc = results[0]["returncode"] if results else 1
            if rc != 0:
                raise RuntimeError(f"workload exited rc={rc}")

            rows = load_trace(round_out / "trace.jsonl")
            feats = [f for f in extract_redteam_features(rows) if f.name == round_cfg.get("name", round_cfg["kind"])]
            if not feats:
                raise RuntimeError(
                    "produced no feature windows — check step count vs WINDOW_S in src/redteam/features.py"
                )
            X_round, y_round, names_round = to_matrix(feats)

            # score BEFORE folding in — this is the real "does this new
            # trick evade the classifier as currently hardened" number
            pre_eval = evaluate(current_clf, X_round, y_round, names_round)
            held_out_sets.append((round_name, X_round, y_round, names_round))

            cumulative_X = np.concatenate([cumulative_X, X_round], axis=0)
            cumulative_y = np.concatenate([cumulative_y, y_round], axis=0)
            current_clf, train_result = train_classifier(cumulative_X, cumulative_y)
            save(current_clf, round_out / "classifier.joblib")

            trajectory.append({
                "round": i,
                "name": round_name,
                "kind": round_cfg["kind"],
                "status": "ok",
                "round_out_dir": str(round_out),
                "n_windows_this_round": len(feats),
                "pre_hardening_accuracy": pre_eval.get("accuracy"),
                "pre_hardening_eval": pre_eval,
                "cumulative_training_size": int(len(cumulative_y)),
            })
            log.info(
                "round %d (%s): pre-hardening accuracy=%.3f — folding %d windows in, cumulative n=%d",
                i, round_name, pre_eval.get("accuracy", float("nan")), len(feats), len(cumulative_y),
            )
        except Exception as e:
            # An unattended overnight run should survive one bad round —
            # log it, record it as failed (not silently dropped), leave
            # cumulative_X/y/current_clf untouched, move on to the next
            # round. Sequential/cumulative design means a skipped round
            # just means one fewer trick got folded in, not a corrupted run.
            log.error("round %d (%s) FAILED, skipping (classifier unchanged): %s", i, round_name, e)
            trajectory.append({
                "round": i, "name": round_name, "kind": round_cfg["kind"],
                "status": "failed", "error": str(e),
            })
        _flush_partial()

    # Catastrophic-forgetting check: does the FINAL (all-rounds-hardened)
    # classifier still catch every earlier round's held-out set, or did
    # hardening on later rounds regress performance on earlier ones?
    final_vs_each_round = []
    for round_name, X_round, y_round, names_round in held_out_sets:
        ev = evaluate(current_clf, X_round, y_round, names_round)
        final_vs_each_round.append({"round_name": round_name, "accuracy": ev.get("accuracy"), "n_windows": ev["n_windows"]})

    n_failed = sum(1 for t in trajectory if t.get("status") == "failed")
    report = {
        "baseline_out": str(baseline_out),
        "resumed_from": str(resume_from) if resume_from else None,
        "n_rounds_resumed": round_offset,
        "n_rounds_new": len(rounds),
        "n_rounds": len(trajectory),
        "n_rounds_failed": n_failed,
        "status": "done" if n_failed == 0 else "done_with_failures",
        "trajectory": trajectory,
        "final_classifier_vs_each_round_held_out": final_vs_each_round,
        "interpretation": (
            "trajectory[i].pre_hardening_accuracy is round i's evasion strategy scored "
            "against the classifier hardened on rounds 0..i-1 only (never having seen "
            "round i's specific trick) -- the real 'does this new trick evade the CURRENT "
            "defense' signal, analogous to Rahman & Tajdari's Table 5 per-round rates. "
            "final_classifier_vs_each_round_held_out re-scores every round's held-out set "
            "against the FINAL classifier (hardened on ALL rounds) -- a low score on an "
            "EARLY round here would mean later hardening hurt performance on an earlier "
            "trick (catastrophic forgetting); training on the cumulative set each round "
            "(not just the latest) is specifically meant to avoid this."
        ),
        "limitations": [
            "Rounds are parameter variants of 2 mechanisms (kv_disguise chunk size, "
            "diloco inner_steps) plus one composite workload — not 20 independently "
            "designed evasion families like Rahman & Tajdari. Directional, not a "
            "replication of their scale or rigor.",
            "Small N per round (see docs/REDTEAM.md) — single runs per round, not "
            "replicated.",
            "Held-out sets are still the SAME workload implementations with different "
            "parameters, not adversarially novel code — this tests parametric "
            "generalization, not robustness to an evader who writes new attack code.",
        ],
    }
    write_json(out_dir / "loop_report.json", report)
    log.info(
        "DONE — %d/%d total rounds ok (%d resumed + %d new), final cumulative training n=%d",
        len(trajectory) - n_failed, len(trajectory), round_offset, len(rounds), len(cumulative_y),
    )
    for row in trajectory:
        if row.get("status") == "failed":
            log.info("  round %d %-20s FAILED: %s", row["round"], row["name"], row.get("error"))
        else:
            log.info("  round %d %-20s pre_hardening_acc=%.3f", row["round"], row["name"], row["pre_hardening_accuracy"])
    for row in final_vs_each_round:
        log.info("  final_clf vs %-20s acc=%.3f", row["round_name"], row["accuracy"])
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-out", required=True, help="an existing run_redteam.py output_dir (for benign windows)")
    ap.add_argument("--config", required=True, help="config with benign_workloads + hardening_rounds (the NEW rounds only, when --resume-from is set)")
    ap.add_argument("--out", required=True)
    ap.add_argument(
        "--resume-from", default=None,
        help="a completed run_redteam_loop.py output dir — reconstructs cumulative training "
             "data from its saved per-round traces (no GPU time) and continues numbering/folding "
             "from there. --config's hardening_rounds should list only the NEW rounds to add.",
    )
    args = ap.parse_args()
    cfg = load_config(args.config)
    baseline_out = Path(args.baseline_out)
    if not baseline_out.is_absolute():
        baseline_out = ROOT / baseline_out
    resume_from = None
    if args.resume_from:
        resume_from = Path(args.resume_from)
        if not resume_from.is_absolute():
            resume_from = ROOT / resume_from
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    run(baseline_out, cfg, args.config, out_dir, resume_from=resume_from)


if __name__ == "__main__":
    main()
