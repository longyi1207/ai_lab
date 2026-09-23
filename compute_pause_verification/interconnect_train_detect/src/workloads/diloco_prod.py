#!/usr/bin/env python3
"""Production DiLoCo workload for ICTD (OpenDiLoCo + optional Streaming).

Replaces the toy per-param loop in diloco_train.py for real multi-node fabric:
  - bucketed NCCL AllReduceMean of outer pseudo-grads
  - H default 500 (OpenDiLoCo); FP16/BF16/FP8 wire dtype
  - streaming fragment schedule + async overlap
  - MonitorClient STEP markers + nccl_hook byte counters

Kind: diloco_prod  (keep kind=diloco for the smoke toy)

  torchrun --nproc_per_node=8 -m src.workloads.diloco_prod \\
    --config configs/diloco_prod.yaml --local-steps 500 --reduce-dtype fp16
"""
from __future__ import annotations

import argparse

import torch

from ..model.build import build_model, vocab_size_of
from ..monitor import nccl_hook
from ..monitor.client import MonitorClient
from ..util import load_config, setup_logging
from .diloco_core import CommLogger, DiLoCoController
from .dist_utils import dist_cleanup, dist_setup, is_main, random_batch

log = setup_logging("diloco_prod")


def run(
    model_cfg: dict,
    steps: int,
    local_steps: int,
    batch_size: int,
    seq_len: int,
    *,
    lr: float = 4e-4,
    weight_decay: float = 0.1,
    outer_lr: float = 0.7,
    outer_momentum: float = 0.9,
    reduce_dtype: str = "fp16",
    bucket_cap_mb: float = 256.0,
    streaming: bool = False,
    num_fragments: int = 4,
    fragment_sync_delay: int = 0,
    backup_device: str = "cpu",
    precision: str = "bf16",
    workload_name: str = "diloco_prod",
) -> None:
    rank, world, _, device = dist_setup()
    mon = MonitorClient()
    if is_main(rank):
        nccl_hook.reset()
        mon.set_synth_mode("diloco")
        mon.marker(
            workload_name,
            "start",
            world_size=world,
            inner_steps=local_steps,
            streaming=streaming,
            num_fragments=num_fragments if streaming else 1,
            reduce_dtype=reduce_dtype,
        )

    model = build_model(model_cfg).to(device)
    vocab = vocab_size_of(model, model_cfg)
    inner = torch.optim.AdamW(
        model.parameters(), lr=lr, weight_decay=weight_decay, betas=(0.9, 0.95)
    )

    comm = CommLogger(path=None, rank=rank)
    ctrl = DiLoCoController(
        model,
        inner,
        local_steps=local_steps,
        outer_lr=outer_lr,
        outer_momentum=outer_momentum,
        reduce_dtype=reduce_dtype,  # type: ignore[arg-type]
        bucket_cap_mb=bucket_cap_mb,
        streaming=streaming,
        num_fragments=num_fragments,
        fragment_sync_delay=fragment_sync_delay,
        backup_device=backup_device,
        logger=comm,
    )

    use_autocast = precision in ("bf16", "fp16") and device.type == "cuda"
    amp_dtype = torch.bfloat16 if precision == "bf16" else torch.float16
    scaler = torch.cuda.amp.GradScaler(enabled=(precision == "fp16" and device.type == "cuda"))

    model.train()
    for step in range(1, steps + 1):
        x, y = random_batch(batch_size, seq_len, vocab, device)
        inner.zero_grad(set_to_none=True)
        if use_autocast:
            with torch.cuda.amp.autocast(dtype=amp_dtype):
                _, loss = model(x, y)
        else:
            _, loss = model(x, y)

        if precision == "fp16" and device.type == "cuda":
            scaler.scale(loss).backward()
            scaler.unscale_(inner)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(inner)
            scaler.update()
        else:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            inner.step()

        phase = ctrl.after_inner_step()
        if is_main(rank) and (step % 5 == 0 or phase != "inner"):
            mon.marker(
                workload_name,
                "step",
                step=step,
                sync_phase=phase,
                loss=float(loss.detach()),
            )
            if phase in ("outer_sync", "fragment_prepare", "fragment_wait"):
                nccl_hook.maybe_emit_event(mon, 0, op="OuterAllReduce")

    ctrl.force_sync()
    if is_main(rank):
        mon.marker(workload_name, "end", steps=steps)
        mon.set_synth_mode("idle")
        log.info(
            "diloco_prod done steps=%d H=%d streaming=%s reduce=%s world=%d",
            steps,
            local_steps,
            streaming,
            reduce_dtype,
            world,
        )
    dist_cleanup()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=2000)
    ap.add_argument("--local-steps", type=int, default=500, help="H (OpenDiLoCo default 500)")
    ap.add_argument("--inner-steps", type=int, default=None, help="alias for --local-steps")
    ap.add_argument("--batch-size", type=int, default=2)
    ap.add_argument("--seq-len", type=int, default=512)
    ap.add_argument("--lr", type=float, default=4e-4)
    ap.add_argument("--outer-lr", type=float, default=0.7)
    ap.add_argument("--outer-momentum", type=float, default=0.9)
    ap.add_argument("--reduce-dtype", choices=["fp32", "fp16", "bf16", "fp8"], default="fp16")
    ap.add_argument("--bucket-cap-mb", type=float, default=256.0)
    ap.add_argument("--streaming", action="store_true")
    ap.add_argument("--num-fragments", type=int, default=4)
    ap.add_argument("--fragment-sync-delay", type=int, default=0)
    ap.add_argument("--backup-device", default="cpu")
    ap.add_argument("--precision", choices=["fp32", "fp16", "bf16"], default="bf16")
    ap.add_argument("--name", default="diloco_prod")
    args = ap.parse_args()

    if args.inner_steps is not None:
        args.local_steps = args.inner_steps

    model_cfg = {
        "backend": "tiny",
        "n_layer": 12,
        "n_head": 12,
        "n_embd": 768,
        "vocab_size": 32000,
        "block_size": max(args.seq_len, 512),
    }
    if args.config:
        cfg = load_config(args.config)
        model_cfg = {**model_cfg, **cfg.get("model", {})}
        for w in cfg.get("workloads", []):
            if w.get("kind") in ("diloco_prod", "diloco"):
                args.steps = w.get("steps", args.steps)
                args.local_steps = w.get("local_steps", w.get("inner_steps", args.local_steps))
                args.batch_size = w.get("batch_size", args.batch_size)
                args.seq_len = w.get("seq_len", args.seq_len)
                args.reduce_dtype = w.get("reduce_dtype", args.reduce_dtype)
                args.streaming = bool(w.get("streaming", args.streaming))
                args.num_fragments = int(w.get("num_fragments", args.num_fragments))
                args.fragment_sync_delay = int(
                    w.get("fragment_sync_delay", args.fragment_sync_delay)
                )
                args.precision = w.get("precision", args.precision)
                break

    run(
        model_cfg,
        args.steps,
        args.local_steps,
        args.batch_size,
        args.seq_len,
        lr=args.lr,
        outer_lr=args.outer_lr,
        outer_momentum=args.outer_momentum,
        reduce_dtype=args.reduce_dtype,
        bucket_cap_mb=args.bucket_cap_mb,
        streaming=args.streaming,
        num_fragments=args.num_fragments,
        fragment_sync_delay=args.fragment_sync_delay,
        backup_device=args.backup_device,
        precision=args.precision,
        workload_name=args.name,
    )


if __name__ == "__main__":
    main()
