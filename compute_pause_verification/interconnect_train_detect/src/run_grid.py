"""Batch × seq grid sweep — falsify “bigger batch = more traffic” confound."""
from __future__ import annotations

import argparse
import copy
import os
import subprocess
import sys
from pathlib import Path

import yaml

from .dashboard.render import render_dashboard
from .detect.evaluate import evaluate_many
from .util import ROOT, ensure_dir, load_config, setup_logging, write_json

log = setup_logging("run_grid")

MODULE = {
    "train_ddp": "src.workloads.train_ddp",
    "infer_dp": "src.workloads.infer_dp",
    "infer_tp": "src.workloads.infer_tp",
    "diloco": "src.workloads.diloco_train",
    "kv_disguise": "src.workloads.kv_disguise",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs/grid_small.yaml"))
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--nproc", type=int, default=2)
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_root = ensure_dir(ROOT / cfg.get("output_dir", "outputs/grid_small"))
    batches = cfg.get("grid", {}).get("batch_sizes", [1, 4])
    seqs = cfg.get("grid", {}).get("seq_lens", [32, 64])
    kinds = cfg.get("workloads_kinds", ["train_ddp", "infer_dp"])

    traces = []
    cell_meta = []
    py = sys.executable
    base_port = int(cfg.get("collector", {}).get("port", 8765))
    cell_i = 0

    for bs in batches:
        for sl in seqs:
            for kind in kinds:
                cell_i += 1
                cell_dir = ensure_dir(out_root / f"b{bs}_s{sl}_{kind}")
                port = base_port + cell_i
                cell_cfg = copy.deepcopy(cfg)
                cell_cfg["mode"] = "smoke"
                cell_cfg["output_dir"] = str(cell_dir)
                cell_cfg["collector"] = {**cfg.get("collector", {}), "host": "127.0.0.1", "port": port}
                cell_cfg["monitor"] = cfg.get("monitor", {"backends": ["synthetic"]})
                cell_cfg["workloads"] = [{
                    "name": f"{kind}_b{bs}_s{sl}",
                    "kind": kind,
                    "steps": args.steps,
                    "warmup_steps": 2,
                    "inner_steps": 4,
                    "batch_size": bs,
                    "seq_len": sl,
                    "nproc": args.nproc,
                    "tp_size": 2,
                }]
                # model block_size must cover seq
                model = dict(cfg.get("model", {}))
                model["block_size"] = max(int(model.get("block_size", sl)), sl)
                cell_cfg["model"] = model
                cfg_path = cell_dir / "config.yaml"
                cfg_path.write_text(yaml.safe_dump(cell_cfg))

                log.info("=== grid cell batch=%d seq=%d kind=%s ===", bs, sl, kind)
                env = os.environ.copy()
                env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
                env.setdefault("GLOO_SOCKET_IFNAME", "lo0")
                rc = subprocess.run(
                    [py, "-m", "src.run_experiment", "--config", str(cfg_path)],
                    cwd=str(ROOT), env=env,
                )
                cell_meta.append({"batch": bs, "seq": sl, "kind": kind, "rc": rc.returncode})
                trace = cell_dir / "trace.jsonl"
                if rc.returncode == 0 and trace.exists():
                    traces.append(trace)

    if len(traces) < 2:
        raise SystemExit(f"grid produced {len(traces)} traces — need ≥2")

    prefer = "synthetic" if "synthetic" in cfg.get("monitor", {}).get("backends", []) else None
    report = evaluate_many(
        traces, None, out_root / "merged_report.json",
        prefer_source=prefer, calibrate="youden",
        alpha=float(cfg.get("detect", {}).get("alpha", 0.05)),
        d_min=float(cfg.get("detect", {}).get("d_min", 0.8)),
    )
    render_dashboard(report, out_root / "dashboard.html", title="grid_small")
    write_json(out_root / "grid_meta.json", {"cells": cell_meta, "n_traces": len(traces)})
    log.info("grid done cells=%d traces=%d thr=%s", len(cell_meta), len(traces), report.get("threshold_gbps"))


if __name__ == "__main__":
    main()
