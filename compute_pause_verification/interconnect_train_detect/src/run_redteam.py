"""Orchestrate the NVML red-team track (H2): build a benign train-vs-infer
corpus, train a Rahman&Tajdari-style classifier on it, then red-team that
classifier with ICTD's own adversarial workloads (kv_disguise, diloco) —
workload shapes that don't obviously match any of their 20 published
evasion families. See docs/REDTEAM.md for the full design writeup and
citations; docs/REDTEAM.md also has the honest limitations list (small N
vs. their 1,396 runs, our own feature/aggregation choices where their
paper text didn't give us the exact formula, no access to their actual
trained weights).

This module is independent of `run_experiment.py`/`run_cluster.py` (the
original cross-node byte-rate track) — same repo, two detection channels,
neither one modifies the other's code.

Usage (local, no GPU — validates the pipeline end to end with fabricated
telemetry):
    python -m src.run_redteam --config configs/redteam_smoke.yaml

Usage (real 8-GPU node, once Azure quota lands):
    python -m src.run_redteam --config configs/azure_redteam_single_node.yaml
"""
from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import requests

from .redteam.classifier import evaluate, save, to_matrix, train_classifier
from .redteam.features import extract_redteam_features, load_trace
from .redteam.telemetry import SyntheticTelemetrySource, TelemetryPoller, build_source
from .util import ROOT, ensure_dir, load_config, setup_logging, write_json

log = setup_logging("run_redteam")

MODULE = {
    "train_ddp": "src.workloads.train_ddp",
    "infer_dp": "src.workloads.infer_dp",
    "infer_tp": "src.workloads.infer_tp",
    "diloco": "src.workloads.diloco_train",
    "kv_disguise": "src.workloads.kv_disguise",
    "kv_diloco_composite": "src.workloads.kv_diloco_composite",
    "low_mem_disguise": "src.workloads.low_mem_disguise",
    "grad_accum_disguise": "src.workloads.grad_accum_disguise",
    "white_box_disguise": "src.workloads.white_box_disguise",
    "grad_checkpoint_disguise": "src.workloads.grad_checkpoint_disguise",
}


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


def _launch_workload(w: dict, env: dict, py: str, config_path: str) -> int:
    kind = w["kind"]
    nproc = int(w.get("nproc", 2))
    cmd = [
        py, "-m", "torch.distributed.run",
        f"--nproc_per_node={nproc}",
        "--master_addr=127.0.0.1",
        "--master_port=" + str(w.get("master_port", 29511)),
        "-m", MODULE[kind],
        # each workload script's own --config handling only overrides
        # steps/batch/seq from a top-level `workloads:` list (see e.g.
        # src/workloads/train_ddp.py:main) — this config's top-level keys
        # are `benign_workloads`/`adversarial_workloads`, so passing
        # --config here only pulls in `model:` (real HF sizing on the
        # Azure config), it will NOT clobber the --steps/--batch-size/etc
        # CLI flags below.
        "--config", config_path,
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
    if kind == "kv_disguise":
        cmd += ["--kv-chunk-tokens", str(w.get("kv_chunk_tokens", 2048))]
    if kind == "kv_diloco_composite":
        cmd += [
            "--inner-steps", str(w.get("inner_steps", 8)),
            "--kv-chunk-tokens", str(w.get("kv_chunk_tokens", 2048)),
        ]
    if kind == "low_mem_disguise":
        if w.get("chunk_grad_sync", False):
            cmd += ["--chunk-grad-sync"]
        cmd += ["--kv-chunk-tokens", str(w.get("kv_chunk_tokens", 2048))]
    if kind == "grad_accum_disguise":
        cmd += ["--accum-steps", str(w.get("accum_steps", 4))]
    if kind == "white_box_disguise":
        cmd += ["--idle-frac", str(w.get("idle_frac", 1.0))]
    log.info("$ %s", " ".join(cmd))
    # A per-invocation timeout, not just the overall unattended run relying
    # on someone noticing a hang — real, generous headroom (real hardware:
    # 1000 steps ~2-3 min, 2000 steps well under 10 min per earlier timing),
    # not a tight bound. NCCL deadlocks don't self-resolve; an unattended
    # overnight loop needs SOMETHING to turn a hang into a clean failure
    # (caught by run_redteam_loop.py's per-round try/except) rather than
    # blocking every remaining round indefinitely.
    #
    # Plain subprocess.run(timeout=...) would only SIGKILL the direct
    # torchrun process on timeout — torchrun has already spawned its own
    # worker processes by then, and SIGKILL (unlike SIGTERM) gives it no
    # chance to cascade-terminate them, so they'd be orphaned: still
    # holding GPU memory and the rendezvous port, breaking every
    # subsequent round. Launch in a new process group instead so a timeout
    # can signal the WHOLE group — SIGTERM first (torchrun's own signal
    # handling can then clean up its workers), SIGKILL only if that alone
    # doesn't clear it.
    timeout_s = int(w.get("timeout_s", 1800))
    proc = subprocess.Popen(cmd, cwd=str(ROOT), env=env, start_new_session=True)
    try:
        rc = proc.wait(timeout=timeout_s)
        return rc
    except subprocess.TimeoutExpired:
        log.error("workload %s timed out after %ds — terminating its process group", w.get("name", kind), timeout_s)
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            log.error("process group for %s didn't exit after SIGTERM, SIGKILL", w.get("name", kind))
            os.killpg(pgid, signal.SIGKILL)
            proc.wait(timeout=10)
        return 124  # conventional timeout exit code


def resolve_gpu_indices(cfg: dict, synthetic: bool) -> list[int] | None:
    """ICTD_GPU_INDICES env var (comma-separated, e.g. "3,4,5") overrides the
    config file's telemetry.gpu_indices — lets the GPU split be
    reconciled/changed at the last minute on a shared box without editing
    and re-syncing the yaml. See docs/REDTEAM.md "Shared-box operation".
    """
    import os

    tcfg = cfg.get("telemetry", {})
    env_gpu_indices = os.environ.get("ICTD_GPU_INDICES", "").strip()
    if env_gpu_indices:
        gpu_indices = [int(x) for x in env_gpu_indices.split(",") if x.strip() != ""]
        log.info("gpu_indices from ICTD_GPU_INDICES env override: %s", gpu_indices)
    else:
        gpu_indices = tcfg.get("gpu_indices")

    if not synthetic and gpu_indices:
        for w in cfg.get("benign_workloads", []) + cfg.get("adversarial_workloads", []):
            if int(w.get("nproc", 0)) > len(gpu_indices):
                raise ValueError(
                    f"workload '{w.get('name', w.get('kind'))}' requests nproc="
                    f"{w['nproc']} but gpu_indices only lists "
                    f"{len(gpu_indices)} GPUs ({gpu_indices}) — would oversubscribe "
                    "or spill onto another project's GPUs on a shared box."
                )
    elif not synthetic and not gpu_indices:
        log.warning(
            "gpu_indices is unset with synthetic=false — if this box is "
            "shared with other projects (see docs/REDTEAM.md), this will poll ALL "
            "physical GPUs and torchrun will bind to physical GPUs 0..nproc-1, "
            "which may not be the ones assigned to this project."
        )
    return gpu_indices


def execute_session(
    cfg: dict,
    config_path: str,
    workloads: list[dict],
    out_dir: Path,
    phase_label: str,
    node_name: str = "redteam0",
) -> list[dict]:
    """Run one collector+telemetry+workload session, `workloads` in order,
    tagged `phase_label` in the results list, writing trace.jsonl into
    `out_dir`. Shared by `run()` (Phase A+C in one session) and
    `run_redteam_harden.py` (a fresh, separate session for held-out
    adversarial examples — see docs/REDTEAM.md "Hardening loop").
    """
    ensure_dir(out_dir)
    host = cfg["collector"]["host"]
    port = cfg["collector"]["port"]
    url = f"http://127.0.0.1:{port}"

    import os
    env = os.environ.copy()
    env["ICTD_COLLECTOR"] = url
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env.setdefault("GLOO_SOCKET_IFNAME", "lo0")
    env.setdefault("MASTER_ADDR", "127.0.0.1")
    py = sys.executable

    tcfg = cfg.get("telemetry", {})
    synthetic = bool(tcfg.get("synthetic", True))
    gpu_indices = resolve_gpu_indices(cfg, synthetic)

    if not synthetic and gpu_indices:
        # CUDA_VISIBLE_DEVICES gates torchrun's spawned processes AND (for
        # NVMLTelemetrySource, via its own CUDA_VISIBLE_DEVICES fallback)
        # keeps telemetry scoped to this project's GPUs — both matter on a
        # shared box (see docs/REDTEAM.md "Shared-box operation"). Without
        # this, LOCAL_RANK 0..N-1 binds to physical GPUs 0..N-1, which on a
        # shared box likely belong to a DIFFERENT project.
        env["CUDA_VISIBLE_DEVICES"] = ",".join(str(i) for i in gpu_indices)
        log.info("shared-box mode: CUDA_VISIBLE_DEVICES=%s", env["CUDA_VISIBLE_DEVICES"])

    source = build_source(
        synthetic,
        n_gpus_if_synthetic=int(tcfg.get("n_gpus_if_synthetic", 8)),
        gpu_indices=gpu_indices,
    )

    collector = subprocess.Popen([
        py, "-m", "src.monitor.collector",
        "--host", host, "--port", str(port), "--out", str(out_dir),
    ], cwd=str(ROOT), env=env)

    results = []
    try:
        wait_health(url)
        poller = TelemetryPoller(source, url, node=node_name, hz=float(tcfg.get("hz", 1.0)))
        poller.start()
        try:
            for w in workloads:
                if isinstance(source, SyntheticTelemetrySource):
                    mode = {
                        "train_ddp": "train", "infer_dp": "infer", "infer_tp": "infer",
                        "diloco": "diloco", "kv_disguise": "train_disguised",
                        "kv_diloco_composite": "train_disguised",
                        "low_mem_disguise": "train_disguised",
                        "grad_accum_disguise": "train_disguised",
                        "white_box_disguise": "train_disguised",
                        "grad_checkpoint_disguise": "train_disguised",
                    }.get(w["kind"], "idle")
                    source.set_mode(mode)
                time.sleep(0.3)
                rc = _launch_workload(w, env, py, config_path)
                results.append({"kind": w["kind"], "name": w.get("name", w["kind"]), "phase": phase_label, "returncode": rc})
                time.sleep(0.5)
        finally:
            poller.stop()
    finally:
        collector.terminate()
        collector.wait(timeout=5)
    return results


def run(cfg: dict, config_path: str) -> dict:
    raw_out = Path(cfg.get("output_dir", "outputs/redteam"))
    out_dir = ensure_dir(raw_out if raw_out.is_absolute() else ROOT / raw_out)
    for stale in ("trace.jsonl", "report.json"):
        p = out_dir / stale
        if p.exists():
            p.unlink()

    tcfg = cfg.get("telemetry", {})
    synthetic = bool(tcfg.get("synthetic", True))

    results = execute_session(cfg, config_path, cfg.get("benign_workloads", []), out_dir, "benign")
    results += execute_session(cfg, config_path, cfg.get("adversarial_workloads", []), out_dir, "adversarial")

    # --- Phase B: train on the benign corpus ---
    rows = load_trace(out_dir / "trace.jsonl")
    feats = extract_redteam_features(rows)
    benign_names = {w.get("name", w["kind"]) for w in cfg.get("benign_workloads", [])}
    adv_names = {w.get("name", w["kind"]) for w in cfg.get("adversarial_workloads", [])}

    benign_feats = [f for f in feats if f.name in benign_names]
    adv_feats = [f for f in feats if f.name in adv_names]

    X_train, y_train, names_train = to_matrix(benign_feats)
    if len(X_train) == 0:
        raise RuntimeError(
            "no benign feature windows extracted — check that workloads ran "
            "long enough to produce >=1 window (see WINDOW_S in src/redteam/features.py) "
            "and that the collector received nvml9_sample events"
        )
    clf, train_result = train_classifier(X_train, y_train)
    in_sample = evaluate(clf, X_train, y_train, names_train)

    # --- Phase C: red-team on the adversarial corpus ---
    X_adv, y_adv, names_adv = to_matrix(adv_feats)
    adversarial_eval = evaluate(clf, X_adv, y_adv, names_adv) if len(X_adv) else {"n_windows": 0, "rows": []}

    save(clf, out_dir / "classifier.joblib")

    report = {
        "run_name": cfg.get("run_name", "redteam"),
        "telemetry_synthetic": synthetic,
        "n_benign_windows": len(benign_feats),
        "n_adversarial_windows": len(adv_feats),
        "train_result": train_result.to_dict(),
        "in_sample_eval": in_sample,
        "adversarial_evasion_eval": adversarial_eval,
        "workload_results": results,
        "limitations": [
            "Synthetic telemetry (--telemetry.synthetic) is a fabricated stand-in, "
            "not validated hardware data — only exercises the pipeline, says nothing "
            "about real evasion feasibility." if synthetic else
            "Real NVML telemetry, but a single hardware config and far fewer runs "
            "than Rahman & Tajdari's 1,396-run / 26,496-window corpus — treat as "
            "directional, not a statistically powered replication.",
            "Feature formulas (esp. cumulative energy, power-memory correlation, "
            "memory-plateau timing) are our own reading of the paper's text, not "
            "verified against their source (no public repo located as of this run).",
            "Cross-GPU aggregation (mean+std per signal per tick) is our own design "
            "choice — the paper's exact multi-GPU aggregation wasn't recoverable "
            "from the sections we could extract.",
        ],
    }
    write_json(out_dir / "report.json", report)
    log.info(
        "DONE benign_windows=%d adv_windows=%d in_sample_acc=%s",
        len(benign_feats), len(adv_feats), in_sample.get("accuracy"),
    )
    if adversarial_eval["rows"]:
        for r in adversarial_eval["rows"]:
            log.info("  adversarial window name=%s P(training)=%.3f predicted_training=%s",
                      r["name"], r["p_training"], r["predicted_training"])
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs/redteam_smoke.yaml"))
    args = ap.parse_args()
    cfg = load_config(args.config)
    run(cfg, args.config)


if __name__ == "__main__":
    main()
