"""Shared infra: device selection, deterministic seeding, structured logging, checkpointing,
and the DDP bootstrap. Kept separate from train.py so the training loop itself stays readable.
"""

import json
import logging
import os
import random
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch
import torch.distributed as dist


# --------------------------------------------------------------------------------------
# Distributed bootstrap
# --------------------------------------------------------------------------------------

class DistState:
    """Reads the env vars torchrun sets (WORLD_SIZE, RANK, LOCAL_RANK). WORLD_SIZE=1 (the
    default when launched with plain `python train.py`) means single-process — is_ddp is False
    and every rank-gated codepath just runs normally. This is the mechanism that lets the same
    train.py serve Phase 1 (single device) and Phase 2 (torchrun --nproc_per_node=N) unchanged.
    """

    def __init__(self):
        self.world_size = int(os.environ.get("WORLD_SIZE", 1))
        self.rank = int(os.environ.get("RANK", 0))
        self.local_rank = int(os.environ.get("LOCAL_RANK", 0))
        self.is_ddp = self.world_size > 1
        self.is_master = self.rank == 0

    def init_process_group(self) -> None:
        if not self.is_ddp:
            return
        # nccl for CUDA multi-GPU, gloo for CPU-simulated DDP (Phase 2 local test), MPS has no
        # native process-group backend so DDP is only exercised via CPU/CUDA in this repo.
        backend = "nccl" if torch.cuda.is_available() else "gloo"
        dist.init_process_group(backend=backend)

    def destroy(self) -> None:
        if self.is_ddp:
            dist.destroy_process_group()

    def barrier(self) -> None:
        if self.is_ddp:
            dist.barrier()


def select_device(dist_state: DistState, override: str | None = None) -> torch.device:
    if override is not None:
        return torch.device(f"{override}:{dist_state.local_rank}" if override == "cuda" else override)
    if torch.cuda.is_available():
        return torch.device(f"cuda:{dist_state.local_rank}")
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


# --------------------------------------------------------------------------------------
# Reproducibility
# --------------------------------------------------------------------------------------

def seed_everything(seed: int, rank: int) -> torch.Generator:
    """Each rank gets seed + rank so DDP workers don't sample identical data-parallel batches."""
    actual_seed = seed + rank
    random.seed(actual_seed)
    np.random.seed(actual_seed)
    torch.manual_seed(actual_seed)
    gen = torch.Generator()
    gen.manual_seed(actual_seed)
    return gen


# --------------------------------------------------------------------------------------
# Logging: stdout (human) + JSONL (machine, for plotting)
# --------------------------------------------------------------------------------------

def setup_logging(log_dir: str, run_name: str, is_master: bool) -> tuple[logging.Logger, Path | None]:
    logger = logging.getLogger("train")
    logger.setLevel(logging.INFO if is_master else logging.WARNING)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    logger.addHandler(stream_handler)

    jsonl_path = None
    if is_master:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        jsonl_path = log_path / f"{run_name}.jsonl"
        file_handler = logging.FileHandler(log_path / f"{run_name}.log")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

    return logger, jsonl_path


def log_metrics_jsonl(jsonl_path: Path | None, metrics: dict) -> None:
    if jsonl_path is None:
        return
    metrics = {**metrics, "wall_time": time.time()}
    with open(jsonl_path, "a") as f:
        f.write(json.dumps(metrics) + "\n")


# --------------------------------------------------------------------------------------
# Checkpointing — the part that's easy to get subtly wrong.
# --------------------------------------------------------------------------------------

def save_checkpoint(out_dir: str, step: int, model_state_dict: dict, optimizer_state_dict: dict,
                     model_cfg, train_cfg, keep_last_n: int) -> Path:
    """Saves everything needed to resume with zero discontinuity in the loss curve:
    model weights, optimizer state (momentum/variance for Adam — this is 2x model size in fp32,
    the fact that motivates ZeRO/FSDP in Phase 3), step counter, and both configs for
    provenance.

    Takes already-gathered state dicts, not a model/optimizer object, deliberately: under DDP,
    `raw_model.state_dict()` (the un-wrapped model) is a cheap local call any single rank can
    make. Under FSDP, gathering a *full* (unsharded) state dict is a collective all-gather that
    every rank must participate in — see `train.py`'s `gather_state_dicts`. Only rank 0 calls
    this function to actually write to disk, but the gather itself had to happen on every rank
    first. Accepting plain dicts here keeps that FSDP-specific collective logic in train.py's
    orchestration layer, out of this generic I/O helper.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    ckpt_path = out_path / f"ckpt_step{step:06d}.pt"

    torch.save({
        "step": step,
        "model_state_dict": model_state_dict,
        "optimizer_state_dict": optimizer_state_dict,
        "model_config": asdict(model_cfg),
        "train_config": asdict(train_cfg),
    }, ckpt_path)

    latest_link = out_path / "latest.pt"
    if latest_link.exists() or latest_link.is_symlink():
        latest_link.unlink()
    latest_link.symlink_to(ckpt_path.name)

    _prune_old_checkpoints(out_path, keep_last_n)
    return ckpt_path


def _prune_old_checkpoints(out_path: Path, keep_last_n: int) -> None:
    ckpts = sorted(out_path.glob("ckpt_step*.pt"))
    for stale in ckpts[:-keep_last_n]:
        stale.unlink()


def load_checkpoint(out_dir: str, device: torch.device) -> dict | None:
    latest_link = Path(out_dir) / "latest.pt"
    if not latest_link.exists():
        return None
    resolved = latest_link.parent / latest_link.readlink()
    return torch.load(resolved, map_location=device)


# --------------------------------------------------------------------------------------
# Best-checkpoint tracking — separate from save_checkpoint/_prune_old_checkpoints above.
# "keep last N" answers "can I resume after a crash"; this answers "which checkpoint
# should I actually deploy" — conflating them silently discards the checkpoint you
# actually want the moment training runs past it (see README Phase 1 log, 2026-07-19).
# --------------------------------------------------------------------------------------

def save_best_checkpoint(out_dir: str, step: int, val_loss: float, model_state_dict: dict,
                          optimizer_state_dict: dict, model_cfg, train_cfg) -> Path:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    best_path = out_path / "best.pt"
    torch.save({
        "step": step,
        "val_loss": val_loss,
        "model_state_dict": model_state_dict,
        "optimizer_state_dict": optimizer_state_dict,
        "model_config": asdict(model_cfg),
        "train_config": asdict(train_cfg),
    }, best_path)
    with open(out_path / "best_meta.json", "w") as f:
        json.dump({"step": step, "val_loss": val_loss}, f, indent=2)
    return best_path


def load_best_meta(out_dir: str) -> dict | None:
    meta_path = Path(out_dir) / "best_meta.json"
    if not meta_path.exists():
        return None
    with open(meta_path) as f:
        return json.load(f)
