"""Regression test for a real bug found 2026-08-22: resuming from a loop
that was ITSELF a resume (chained resume) raised FileNotFoundError,
because round 0's trace.jsonl lives under the ORIGINAL loop's directory,
not the intermediate continuation directory that only ran rounds 8-9.
`_load_prior_loop` must walk the whole `resumed_from` chain, not assume
every prior round's subdirectory sits under the immediate resume_from.
"""
from __future__ import annotations

import json

from src.run_redteam_loop import _load_prior_loop


def _write_round(base, round_idx, name, t=0.0):
    round_dir = base / f"round_{round_idx}_{name}"
    round_dir.mkdir(parents=True)
    rows = [{"kind": "marker", "name": name, "phase": "start", "t": t}]
    for i in range(10):
        rows.append({
            "kind": "event", "type": "nvml9_sample", "t": t + i,
            "mean_gpu_util_pct": 80.0, "mean_power_w": 300.0,
            "mean_mem_used_mb": 8000.0, "mean_mem_util_pct": 50.0,
        })
    rows.append({"kind": "marker", "name": name, "phase": "end", "t": t + 10})
    (round_dir / "trace.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return round_dir


def test_chained_resume_finds_rounds_across_multiple_directories(tmp_path):
    # root loop: rounds 0-1, no resumed_from
    root = tmp_path / "loop_root"
    root.mkdir()
    _write_round(root, 0, "kv_disguise_2048")
    _write_round(root, 1, "diloco_25")
    (root / "loop_report.json").write_text(json.dumps({
        "resumed_from": None,
        "n_rounds_resumed": 0,
        "trajectory": [
            {"round": 0, "name": "kv_disguise_2048", "status": "ok"},
            {"round": 1, "name": "diloco_25", "status": "ok"},
        ],
    }))

    # first continuation: resumes root (rounds 0-1 inherited), runs round 2 itself
    cont1 = tmp_path / "loop_cont1"
    cont1.mkdir()
    _write_round(cont1, 2, "low_mem_8")
    (cont1 / "loop_report.json").write_text(json.dumps({
        "resumed_from": str(root),
        "n_rounds_resumed": 2,
        "trajectory": [
            {"round": 0, "name": "kv_disguise_2048", "status": "ok"},
            {"round": 1, "name": "diloco_25", "status": "ok"},
            {"round": 2, "name": "low_mem_8", "status": "ok"},
        ],
    }))

    # second continuation: resumes cont1 (rounds 0-2 inherited) -- this is
    # the exact scenario that raised FileNotFoundError before the fix,
    # since round 0's trace lives under `root`, not `cont1`
    trajectory, held_out = _load_prior_loop(cont1)

    assert [t["round"] for t in trajectory] == [0, 1, 2]
    assert [t["name"] for t in trajectory] == ["kv_disguise_2048", "diloco_25", "low_mem_8"]
    assert len(held_out) == 3
    for name, X, y, names in held_out:
        assert len(X) > 0
        assert all(v == 1 for v in y)  # every round here is real training in disguise


def test_round_out_dir_field_used_when_present(tmp_path):
    # if a trajectory entry carries its own round_out_dir, that's
    # authoritative even if it doesn't match the f"round_{i}_{name}"
    # convention -- defense in depth beyond the index-based fallback
    weird_dir = tmp_path / "not_the_usual_name"
    _write_round(weird_dir.parent, 0, "kv_disguise_2048")
    (weird_dir.parent / f"round_0_kv_disguise_2048").rename(weird_dir)

    report_dir = tmp_path / "loop"
    report_dir.mkdir()
    (report_dir / "loop_report.json").write_text(json.dumps({
        "resumed_from": None,
        "n_rounds_resumed": 0,
        "trajectory": [
            {"round": 0, "name": "kv_disguise_2048", "status": "ok", "round_out_dir": str(weird_dir)},
        ],
    }))

    trajectory, held_out = _load_prior_loop(report_dir)
    assert len(held_out) == 1
