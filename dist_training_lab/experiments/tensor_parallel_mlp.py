"""Phase 4, step 1: tensor parallelism from scratch — a column-parallel + row-parallel MLP
block, verified against a single-device reference computing the identical math.

This is NOT wired into src/train.py — it's a standalone, from-scratch implementation whose only
job is to prove (numerically, to float precision) that splitting a matmul across ranks and
combining with the right collective gives EXACTLY the same result as doing it on one device.
That correctness property is the whole point of tensor parallelism; if you can't verify it,
you can't trust it at 100B+ scale where you'll never have a single device to check against.

Run: GLOO_SOCKET_IFNAME=lo0 .venv/bin/torchrun --nproc_per_node=4 --master_addr=127.0.0.1 \
     --master_port=29520 experiments/tensor_parallel_mlp.py
"""

import torch
import torch.distributed as dist
import torch.nn as nn
import torch.nn.functional as F


class _ToParallelInput(torch.autograd.Function):
    """Megatron's "f": identity forward, all-reduce backward.

    Applied to the input of a column-parallel layer. Forward needs no communication — the input
    is already replicated (identical on every rank), so each rank can just use it directly to
    compute its column slice of the output. But each rank's local backward pass only computes a
    PARTIAL contribution to dL/d(input) (from its own column slice of the weight) — the true
    gradient w.r.t. the shared input is the SUM of every rank's partial contribution, hence the
    all-reduce in backward.
    """
    @staticmethod
    def forward(ctx, x):
        return x

    @staticmethod
    def backward(ctx, grad_output):
        grad_output = grad_output.contiguous()
        dist.all_reduce(grad_output, op=dist.ReduceOp.SUM)
        return grad_output


class _FromParallelOutput(torch.autograd.Function):
    """Megatron's "g": all-reduce forward, identity backward.

    Applied to the output of a row-parallel layer. Forward needs an all-reduce — each rank only
    summed over its slice of the input features, so the true output is the SUM across ranks.
    Backward needs no communication: once every rank receives the same (already-summed)
    upstream gradient, it can independently compute its own local weight gradient — the
    all-reduce's backward is just "pass the gradient through unchanged to every contributor,"
    which is what a sum's gradient always is.
    """
    @staticmethod
    def forward(ctx, x):
        x = x.contiguous()
        dist.all_reduce(x, op=dist.ReduceOp.SUM)
        return x

    @staticmethod
    def backward(ctx, grad_output):
        return grad_output


class ColumnParallelLinear(nn.Module):
    """out_features split across ranks: rank r holds rows [r*local_out : (r+1)*local_out] of
    the full weight matrix. No communication in forward (input already replicated); the
    _ToParallelInput wrapper on the *input* handles the backward-side all-reduce.
    """
    def __init__(self, in_features: int, out_features: int, world_size: int):
        super().__init__()
        assert out_features % world_size == 0
        self.local_out = out_features // world_size
        self.weight = nn.Parameter(torch.empty(self.local_out, in_features))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = _ToParallelInput.apply(x)
        return F.linear(x, self.weight)


class RowParallelLinear(nn.Module):
    """in_features split across ranks: rank r holds columns [r*local_in : (r+1)*local_in] of
    the full weight matrix. Forward produces only a partial sum; _FromParallelOutput's
    all-reduce combines every rank's partial sum into the true output.
    """
    def __init__(self, in_features: int, out_features: int, world_size: int):
        super().__init__()
        assert in_features % world_size == 0
        self.local_in = in_features // world_size
        self.weight = nn.Parameter(torch.empty(out_features, self.local_in))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        partial = F.linear(x, self.weight)
        return _FromParallelOutput.apply(partial)


class TensorParallelMLP(nn.Module):
    def __init__(self, n_embd: int, world_size: int):
        super().__init__()
        self.fc_in = ColumnParallelLinear(n_embd, 4 * n_embd, world_size)
        self.fc_out = RowParallelLinear(4 * n_embd, n_embd, world_size)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc_out(F.gelu(self.fc_in(x)))


class ReferenceMLP(nn.Module):
    """Ordinary single-device MLP — the ground truth we check the sharded version against."""
    def __init__(self, n_embd: int):
        super().__init__()
        self.fc_in = nn.Linear(n_embd, 4 * n_embd, bias=False)
        self.fc_out = nn.Linear(4 * n_embd, n_embd, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc_out(F.gelu(self.fc_in(x)))


def main():
    dist.init_process_group(backend="gloo")
    rank, world = dist.get_rank(), dist.get_world_size()
    torch.manual_seed(0)  # every rank builds the SAME reference weights independently — no
                          # broadcast needed, determinism does the synchronization for free.

    n_embd = 32
    reference = ReferenceMLP(n_embd)
    nn.init.normal_(reference.fc_in.weight, std=0.02)
    nn.init.normal_(reference.fc_out.weight, std=0.02)

    tp_mlp = TensorParallelMLP(n_embd, world)
    local_out = (4 * n_embd) // world
    local_in = (4 * n_embd) // world
    with torch.no_grad():
        # slice the SAME reference weights this rank is responsible for — guarantees the
        # sharded computation and the reference are doing literally the same arithmetic,
        # just partitioned differently.
        tp_mlp.fc_in.weight.copy_(reference.fc_in.weight[rank * local_out:(rank + 1) * local_out, :])
        tp_mlp.fc_out.weight.copy_(reference.fc_out.weight[:, rank * local_in:(rank + 1) * local_in])

    torch.manual_seed(123)  # same input X on every rank (X must be replicated to start with)
    x_ref = torch.randn(2, 8, n_embd, requires_grad=True)
    x_tp = x_ref.detach().clone().requires_grad_(True)

    y_ref = reference(x_ref)
    y_tp = tp_mlp(x_tp)

    fwd_max_diff = (y_ref - y_tp).abs().max().item()

    y_ref.sum().backward()
    y_tp.sum().backward()

    grad_x_diff = (x_ref.grad - x_tp.grad).abs().max().item()
    grad_fc_in_diff = (reference.fc_in.weight.grad[rank * local_out:(rank + 1) * local_out, :]
                        - tp_mlp.fc_in.weight.grad).abs().max().item()
    grad_fc_out_diff = (reference.fc_out.weight.grad[:, rank * local_in:(rank + 1) * local_in]
                         - tp_mlp.fc_out.weight.grad).abs().max().item()

    print(f"[rank {rank}] forward max|diff|={fwd_max_diff:.2e}  "
          f"grad_x max|diff|={grad_x_diff:.2e}  "
          f"grad_fc_in max|diff|={grad_fc_in_diff:.2e}  "
          f"grad_fc_out max|diff|={grad_fc_out_diff:.2e}  "
          f"{'PASS' if max(fwd_max_diff, grad_x_diff, grad_fc_in_diff, grad_fc_out_diff) < 1e-5 else 'FAIL'}")

    dist.destroy_process_group()


if __name__ == "__main__":
    main()
