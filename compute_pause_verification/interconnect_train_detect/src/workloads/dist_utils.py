"""Shared distributed helpers for workloads."""
from __future__ import annotations

import os

import torch
import torch.distributed as dist


def dist_setup() -> tuple[int, int, int, torch.device]:
    rank = int(os.environ.get("RANK", "0"))
    world = int(os.environ.get("WORLD_SIZE", "1"))
    local = int(os.environ.get("LOCAL_RANK", "0"))
    if world > 1 and not dist.is_initialized():
        backend = "nccl" if torch.cuda.is_available() else "gloo"
        dist.init_process_group(backend=backend)
    if torch.cuda.is_available():
        torch.cuda.set_device(local)
        device = torch.device(f"cuda:{local}")
    else:
        device = torch.device("cpu")
    return rank, world, local, device


def dist_cleanup() -> None:
    if dist.is_initialized():
        dist.barrier()
        dist.destroy_process_group()


def is_main(rank: int) -> bool:
    return rank == 0


def random_batch(batch: int, seq: int, vocab: int, device: torch.device):
    x = torch.randint(0, vocab, (batch, seq), device=device)
    y = torch.randint(0, vocab, (batch, seq), device=device)
    return x, y
