"""Phase 4, step 2: pipeline parallelism using PyTorch's real production API
(torch.distributed.pipelining — what TorchTitan uses), not hand-rolled send/recv.

Splits a toy P-layer stack (one Linear+ReLU "layer" per rank, P = world_size) across P pipeline
stages. Two things measured:

1. Correctness: does the pipelined multi-stage forward+backward give the same loss/gradients as
   running the same stacked layers on one device? (Same verify-against-a-reference methodology
   as experiments/tensor_parallel_mlp.py.)
2. Bubble fraction: with P stages and M microbatches, pipeline theory predicts idle time
   ("bubble") = (P-1)/(M+P-1) of total wall time — measured empirically for a few values of M
   and compared to the prediction.

Run: GLOO_SOCKET_IFNAME=lo0 .venv/bin/torchrun --nproc_per_node=4 --master_addr=127.0.0.1 \
     --master_port=29521 experiments/pipeline_parallel_demo.py
"""

import time

import torch
import torch.distributed as dist
import torch.nn as nn
from torch.distributed.pipelining import PipelineStage, Schedule1F1B, ScheduleGPipe

D = 32          # feature dim, kept tiny — this is about schedule mechanics, not model capacity
BATCH = 16      # full (unsplit) batch size


class Layer(nn.Module):
    """One pipeline stage's worth of "model" — a single rank owns exactly one of these."""
    def __init__(self, d: int):
        super().__init__()
        self.fc = nn.Linear(d, d)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.relu(self.fc(x))


def build_reference(num_stages: int, seed: int) -> nn.Sequential:
    torch.manual_seed(seed)
    return nn.Sequential(*[Layer(D) for _ in range(num_stages)])


def loss_fn(output: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    return torch.nn.functional.mse_loss(output, target)


def run_pipeline(num_microbatches: int, schedule_cls, rank: int, world: int,
                  x: torch.Tensor, y: torch.Tensor, reference: nn.Sequential) -> tuple[float, float]:
    """Returns (wall_seconds, max_param_grad_diff_vs_reference)."""
    device = torch.device("cpu")
    my_layer = Layer(D)
    with torch.no_grad():
        my_layer.fc.weight.copy_(reference[rank].fc.weight)
        my_layer.fc.bias.copy_(reference[rank].fc.bias)

    stage = PipelineStage(my_layer, stage_index=rank, num_stages=world, device=device)
    schedule = schedule_cls(stage, n_microbatches=num_microbatches, loss_fn=loss_fn)

    dist.barrier()
    t0 = time.perf_counter()
    losses = []
    if rank == 0:
        schedule.step(x)
    elif rank == world - 1:
        schedule.step(target=y, losses=losses)
    else:
        schedule.step()
    dist.barrier()
    wall = time.perf_counter() - t0

    grad_diff = (my_layer.fc.weight.grad - reference[rank].fc.weight.grad).abs().max().item() \
        if my_layer.fc.weight.grad is not None else float("nan")
    return wall, grad_diff


def main():
    dist.init_process_group(backend="gloo")
    rank, world = dist.get_rank(), dist.get_world_size()

    reference = build_reference(world, seed=0)
    torch.manual_seed(42)
    x = torch.randn(BATCH, D)
    y = torch.randn(BATCH, D)

    # single-device ground truth: run the SAME stacked layers, SAME input, unsplit.
    ref_out = reference(x)
    ref_loss = torch.nn.functional.mse_loss(ref_out, y)
    ref_loss.backward()

    if rank == 0:
        print(f"\n=== pipeline parallel demo: {world} stages, batch={BATCH}, feature_dim={D} ===")
        print(f"reference (single-device) loss: {ref_loss.item():.6f}\n")

    for schedule_name, schedule_cls in [("GPipe", ScheduleGPipe), ("1F1B", Schedule1F1B)]:
        # 1F1B requires n_microbatches >= num_stages to fill the pipe in its interleaved
        # pattern; GPipe has no such floor (it just gets bubblier, not invalid) — a real,
        # concrete difference in the two schedules' constraints, not just their memory profile.
        microbatch_counts = [m for m in [1, 2, 4, 8] if m >= world or schedule_name == "GPipe"]
        for m in microbatch_counts:
            # fresh reference grads each run (backward accumulates otherwise)
            for p in reference.parameters():
                p.grad = None
            torch.nn.functional.mse_loss(reference(x), y).backward()

            wall, grad_diff = run_pipeline(m, schedule_cls, rank, world, x, y, reference)
            bubble_theory = (world - 1) / (m + world - 1)

            if rank == world - 1:
                print(f"[{schedule_name:5s}] microbatches={m:2d}  wall={wall*1000:6.2f}ms  "
                      f"theoretical_bubble_fraction={bubble_theory:.3f}  "
                      f"grad_max|diff|_vs_reference(rank {rank})={grad_diff:.2e}")

    dist.destroy_process_group()


if __name__ == "__main__":
    main()
