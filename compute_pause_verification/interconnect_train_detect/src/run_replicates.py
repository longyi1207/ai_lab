"""Run each workload N times so Welch t / Cohen d have sample size.

Writes outputs/<run>/rep_XXX/trace.jsonl then merged report + dashboard.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml

from .dashboard.render import render_dashboard
from .detect.evaluate import evaluate_many
from .util import ROOT, ensure_dir, load_config, setup_logging, write_json

log = setup_logging("run_replicates")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs/smoke.yaml"))
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--out", default=None)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--d-min", type=float, default=0.8)
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_root = ensure_dir(args.out or ROOT / cfg.get("output_dir", "outputs/smoke") / "reps")
    traces = []
    py = sys.executable

    for i in range(args.reps):
        rep_dir = ensure_dir(out_root / f"rep_{i:03d}")
        # write a per-rep config with unique output_dir + port offset
        rep_cfg = dict(cfg)
        rep_cfg["output_dir"] = str(rep_dir.relative_to(ROOT)) if str(rep_dir).startswith(str(ROOT)) else str(rep_dir)
        # absolute safer
        rep_cfg["output_dir"] = str(rep_dir)
        port = int(cfg.get("collector", {}).get("port", 8765)) + 1 + i
        rep_cfg.setdefault("collector", {})
        rep_cfg["collector"] = {**cfg.get("collector", {}), "port": port, "host": "127.0.0.1"}
        cfg_path = rep_dir / "config.yaml"
        cfg_path.write_text(yaml.safe_dump(rep_cfg))
        log.info("=== replicate %d/%d port=%d ===", i + 1, args.reps, port)
        env = {"PYTHONPATH": str(ROOT)}
        import os
        full_env = os.environ.copy()
        full_env["PYTHONPATH"] = str(ROOT) + os.pathsep + full_env.get("PYTHONPATH", "")
        full_env.setdefault("GLOO_SOCKET_IFNAME", "lo0")
        rc = subprocess.run(
            [py, "-m", "src.run_experiment", "--config", str(cfg_path)],
            cwd=str(ROOT),
            env=full_env,
        )
        if rc.returncode != 0:
            log.error("rep %d failed rc=%d", i, rc.returncode)
            continue
        trace = rep_dir / "trace.jsonl"
        if trace.exists():
            traces.append(trace)

    if len(traces) < 2:
        raise SystemExit(f"need ≥2 successful traces, got {len(traces)}")

    prefer = None
    if "synthetic" in cfg.get("monitor", {}).get("backends", []):
        prefer = "synthetic"
    thr = float(cfg.get("detect", {}).get("bandwidth_threshold_gbps", 0.05))
    merged = out_root / "merged_report.json"
    report = evaluate_many(
        traces, thr, merged, prefer_source=prefer,
        alpha=args.alpha, d_min=args.d_min, n_boot=5000,
    )
    dash = render_dashboard(report, out_root / "dashboard.html", title=f"reps={len(traces)}")
    write_json(out_root / "run_meta.json", {"traces": [str(t) for t in traces], "dashboard": str(dash)})
    log.info("merged report → %s", merged)
    log.info("dashboard → %s", dash)
    v = report.get("verdict") or {}
    log.info("separable=%s", v.get("separable"))


if __name__ == "__main__":
    main()
