"""Orchestrate smoke/cluster experiment: collector + agent + workloads + evaluate."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import requests

from .detect.evaluate import evaluate
from .dashboard.render import render_dashboard
from .util import ROOT, ensure_dir, load_config, setup_logging, write_json

log = setup_logging("run_experiment")


def wait_health(url: str, timeout: float = 30.0) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = requests.get(f"{url}/health", timeout=1.0)
            if r.ok:
                return
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"collector not healthy: {url}")


def Popen(cmd: list[str], **kw) -> subprocess.Popen:
    log.info("$ %s", " ".join(cmd))
    return subprocess.Popen(cmd, **kw)


def run_smoke(cfg: dict) -> dict:
    raw_out = Path(cfg.get("output_dir", "outputs/smoke"))
    out_dir = ensure_dir(raw_out if raw_out.is_absolute() else ROOT / raw_out)
    # fresh trace each smoke run
    for stale in ("trace.jsonl", "report.json", "dashboard.html"):
        p = out_dir / stale
        if p.exists():
            p.unlink()
    host = cfg["collector"]["host"]
    port = cfg["collector"]["port"]
    url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["ICTD_COLLECTOR"] = url
    env["ICTD_NODE"] = "smoke0"
    env["ICTD_SYNTH_MODE_FILE"] = str(out_dir / "synth_mode")
    env["ICTD_NCCL_COUNTER"] = str(out_dir / "nccl_bytes")
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    # macOS gloo: avoid localhost reverse-DNS hang
    env.setdefault("GLOO_SOCKET_IFNAME", "lo0")
    env.setdefault("MASTER_ADDR", "127.0.0.1")

    py = sys.executable
    collector = Popen([
        py, "-m", "src.monitor.collector",
        "--host", host, "--port", str(port), "--out", str(out_dir),
    ], cwd=str(ROOT), env=env)
    try:
        wait_health(url)
        backends = ",".join(cfg["monitor"]["backends"])
        agent = Popen([
            py, "-m", "src.monitor.agent",
            "--collector", url, "--node", "smoke0",
            "--backends", backends,
            "--iface", str(cfg["monitor"].get("iface") or "lo0"),
            "--poll-hz", str(cfg["collector"].get("poll_hz", 10)),
        ], cwd=str(ROOT), env=env)

        config_path = out_dir / "resolved_config.yaml"
        # workloads expect --config pointing at original; pass path via argv later
        results = []
        for w in cfg.get("workloads", []):
            kind = w["kind"]
            nproc = int(w.get("nproc", 2))
            module = {
                "train_ddp": "src.workloads.train_ddp",
                "infer_dp": "src.workloads.infer_dp",
                "infer_tp": "src.workloads.infer_tp",
                "diloco": "src.workloads.diloco_train",
                "kv_disguise": "src.workloads.kv_disguise",
            }[kind]
            # brief idle so windows don't abut
            time.sleep(0.5)
            cmd = [
                py, "-m", "torch.distributed.run",
                f"--nproc_per_node={nproc}",
                "--master_addr=127.0.0.1",
                "--master_port=29501",
                "-m", module,
                "--name", w.get("name", kind),
                "--steps", str(w.get("steps", 40)),
                "--batch-size", str(w.get("batch_size", 4)),
                "--seq-len", str(w.get("seq_len", 64)),
            ]
            if kind == "train_ddp":
                cmd += ["--warmup-steps", str(w.get("warmup_steps", 5))]
            if kind == "diloco":
                cmd += ["--inner-steps", str(w.get("inner_steps", 8))]
            if kind == "infer_tp":
                cmd += ["--tp-size", str(w.get("tp_size", 2))]
            log.info("workload %s", kind)
            proc = subprocess.run(cmd, cwd=str(ROOT), env=env)
            results.append({"kind": kind, "returncode": proc.returncode})
            if proc.returncode != 0:
                log.error("workload %s failed rc=%d", kind, proc.returncode)
            time.sleep(0.8)

        agent.terminate()
        agent.wait(timeout=5)
    finally:
        collector.terminate()
        collector.wait(timeout=5)

    thr_raw = cfg.get("detect", {}).get("bandwidth_threshold_gbps", None)
    thr = float(thr_raw) if thr_raw is not None else None
    calib_method = cfg.get("detect", {}).get("calibrate", "youden")
    report = evaluate(
        out_dir / "trace.jsonl",
        thr,
        out_dir / "report.json",
        prefer_source="synthetic" if "synthetic" in cfg["monitor"]["backends"] else None,
        alpha=float(cfg.get("detect", {}).get("alpha", 0.05)),
        d_min=float(cfg.get("detect", {}).get("d_min", 0.8)),
        calibrate=None if calib_method in (None, "none") else calib_method,
    )
    render_dashboard(report, out_dir / "dashboard.html", title=cfg.get("run_name", "smoke"))
    write_json(out_dir / "workload_results.json", results)
    write_json(out_dir / "run_meta.json", {
        "mode": "smoke", "threshold_gbps": report.get("threshold_gbps"), "workloads": results,
        "dashboard": str(out_dir / "dashboard.html"),
        "calibration": report.get("calibration"),
    })
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs/smoke.yaml"))
    args = ap.parse_args()
    cfg = load_config(args.config)
    mode = cfg.get("mode", "smoke")
    if mode == "smoke":
        report = run_smoke(cfg)
        log.info(
            "DONE accuracy=%s evade=%s",
            report.get("accuracy"),
            report.get("evade_under_threshold"),
        )
        # print one-line verdict
        dets = report.get("detections", [])
        for d in dets:
            log.info(
                "  %s label=%s pred=%s gbps=%.4g",
                d["name"], d["label"], d["predicted"], d["gbps_mean"],
            )
    else:
        log.error(
            "mode=%s: start collector/agent with scripts/, run workloads via torchrun, "
            "then: python -m src.detect.evaluate --trace outputs/.../trace.jsonl",
            mode,
        )
        sys.exit(2)


if __name__ == "__main__":
    main()
