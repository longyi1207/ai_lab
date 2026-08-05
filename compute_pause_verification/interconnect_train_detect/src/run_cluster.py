"""Multi-node CUDA cluster orchestration (2 nodes × 8 GPUs).

Assumes:
  - ICTD_NODE0 / ICTD_NODE1 hostnames or IPs
  - passwordless SSH between nodes (or run via pdsh/srun)
  - NCCL + EFA configured (see infra/scripts/bootstrap_node.sh)

Usage on node0:
  python -m src.run_cluster --config configs/aws_p4d.yaml
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from .dashboard.render import render_dashboard
from .detect.evaluate import evaluate
from .util import ROOT, ensure_dir, load_config, setup_logging, write_json

log = setup_logging("run_cluster")

MODULE = {
    "train_ddp": "src.workloads.train_ddp",
    "infer_dp": "src.workloads.infer_dp",
    "infer_tp": "src.workloads.infer_tp",
    "diloco": "src.workloads.diloco_train",
    "kv_disguise": "src.workloads.kv_disguise",
}


def out_dir_from_cfg(cfg: dict) -> Path:
    p = Path(cfg.get("output_dir", "outputs/cluster"))
    return ensure_dir(p if p.is_absolute() else ROOT / p)


def torchrun_cmd(
    module: str,
    nnodes: int,
    nproc: int,
    node_rank: int,
    master_addr: str,
    master_port: int,
    extra: list[str],
) -> list[str]:
    return [
        sys.executable, "-m", "torch.distributed.run",
        f"--nnodes={nnodes}",
        f"--nproc_per_node={nproc}",
        f"--node_rank={node_rank}",
        f"--master_addr={master_addr}",
        f"--master_port={master_port}",
        "-m", module,
        *extra,
    ]


def start_local_monitor(cfg: dict, out: Path, node_name: str) -> tuple[subprocess.Popen | None, subprocess.Popen]:
    """Node0 starts collector; every node starts agent."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["ICTD_COLLECTOR"] = cfg["collector_url"]
    env["ICTD_NODE"] = node_name
    env["NCCL_DEBUG"] = env.get("NCCL_DEBUG", "INFO")
    env["NCCL_ASYNC_ERROR_HANDLING"] = "1"

    collector = None
    if cfg.get("start_collector", False):
        collector = subprocess.Popen([
            sys.executable, "-m", "src.monitor.collector",
            "--host", cfg["collector"]["host"],
            "--port", str(cfg["collector"]["port"]),
            "--out", str(out),
        ], cwd=str(ROOT), env=env)
        time.sleep(1.0)

    backends = ",".join(cfg["monitor"]["backends"])
    agent_cmd = [
        sys.executable, "-m", "src.monitor.agent",
        "--collector", cfg["collector_url"],
        "--node", node_name,
        "--backends", backends,
        "--poll-hz", str(cfg["collector"].get("poll_hz", 20)),
    ]
    if cfg["monitor"].get("iface"):
        agent_cmd += ["--iface", cfg["monitor"]["iface"]]
    if cfg["monitor"].get("ib_device"):
        agent_cmd += ["--ib-device", cfg["monitor"]["ib_device"]]
    agent = subprocess.Popen(agent_cmd, cwd=str(ROOT), env=env)
    return collector, agent


def run_workload_local_rank0(cfg: dict, w: dict, master_addr: str, master_port: int) -> int:
    """Launch torchrun on this node only — peer node must run matching node_rank=1."""
    kind = w["kind"]
    nnodes = int(cfg.get("nnodes", 2))
    nproc = int(cfg.get("nproc_per_node", 8))
    node_rank = int(os.environ.get("ICTD_NODE_RANK", cfg.get("node_rank", 0)))
    extra = [
        "--name", w.get("name", kind),
        "--steps", str(w.get("steps", 100)),
        "--batch-size", str(w.get("batch_size", 1)),
        "--seq-len", str(w.get("seq_len", 512)),
    ]
    if kind == "train_ddp":
        extra += ["--warmup-steps", str(w.get("warmup_steps", 10))]
    if kind == "diloco":
        extra += ["--inner-steps", str(w.get("inner_steps", 8))]
    if kind == "infer_tp":
        extra += ["--tp-size", str(w.get("tp_size", 2))]

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["ICTD_COLLECTOR"] = cfg["collector_url"]
    # EFA / NCCL defaults for p4/p5
    env.setdefault("FI_PROVIDER", "efa")
    env.setdefault("FI_EFA_USE_DEVICE_RDMA", "1")
    env.setdefault("NCCL_PROTO", "simple")
    env.setdefault("TORCH_NCCL_ASYNC_ERROR_HANDLING", "1")

    cmd = torchrun_cmd(MODULE[kind], nnodes, nproc, node_rank, master_addr, master_port, extra)
    log.info("$ %s", " ".join(cmd))
    return subprocess.run(cmd, cwd=str(ROOT), env=env).returncode


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs/aws_p4d.yaml"))
    ap.add_argument("--workloads-only", action="store_true",
                    help="peer node: skip collector, just agent+workloads")
    args = ap.parse_args()
    cfg = load_config(args.config)
    out = out_dir_from_cfg(cfg)

    master_addr = os.environ.get("ICTD_MASTER_ADDR") or cfg.get("master_addr") or "127.0.0.1"
    master_port = int(os.environ.get("ICTD_MASTER_PORT") or cfg.get("master_port") or 29500)
    node_rank = int(os.environ.get("ICTD_NODE_RANK", cfg.get("node_rank", 0)))
    node_name = os.environ.get("ICTD_NODE", f"node{node_rank}")

    collector_host = cfg["collector"].get("host", "0.0.0.0")
    collector_port = int(cfg["collector"].get("port", 8765))
    # agents always hit node0 private IP
    cfg["collector_url"] = os.environ.get(
        "ICTD_COLLECTOR",
        cfg.get("collector_url") or f"http://{master_addr}:{collector_port}",
    )
    cfg["start_collector"] = (node_rank == 0) and not args.workloads_only
    cfg["node_rank"] = node_rank

    write_json(out / "cluster_meta.json", {
        "master_addr": master_addr, "node_rank": node_rank, "node": node_name,
        "collector_url": cfg["collector_url"],
    })

    collector, agent = start_local_monitor(cfg, out, node_name)
    try:
        results = []
        for i, w in enumerate(cfg.get("workloads", [])):
            port = master_port + i
            log.info("workload %s master_port=%d", w["kind"], port)
            time.sleep(1.0)
            rc = run_workload_local_rank0(cfg, w, master_addr, port)
            results.append({"kind": w["kind"], "returncode": rc})
            time.sleep(2.0)
        write_json(out / "workload_results.json", results)

        if node_rank == 0:
            thr_raw = cfg["detect"].get("bandwidth_threshold_gbps")
            thr = float(thr_raw) if thr_raw is not None else None
            prefer = None
            if "ib" in cfg["monitor"]["backends"]:
                prefer = "ib"
            elif "nccl" in cfg["monitor"]["backends"]:
                prefer = "nccl"
            report = evaluate(
                out / "trace.jsonl", thr, out / "report.json", prefer_source=prefer,
                alpha=float(cfg.get("detect", {}).get("alpha", 0.05)),
                d_min=float(cfg.get("detect", {}).get("d_min", 0.8)),
                calibrate=cfg.get("detect", {}).get("calibrate", "youden"),
            )
            render_dashboard(report, out / "dashboard.html", title=cfg.get("run_name", "cluster"))
    finally:
        agent.terminate()
        if collector:
            collector.terminate()


if __name__ == "__main__":
    main()
