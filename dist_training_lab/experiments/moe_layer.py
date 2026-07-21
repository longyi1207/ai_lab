"""Phase 4, step 3a: a real Mixture-of-Experts FFN layer, single-device — routing + top-k
dispatch + DeepSeek-V3-style auxiliary-loss-free load balancing. This is the mechanism that
matters before the distributed part (expert_parallel_demo.py) makes any sense: you can't reason
about "all-to-all communication pattern for routing tokens to experts" without first having a
concrete, correct picture of what "routing tokens to experts" IS.

Why auxiliary-loss-free (not the classic Switch-Transformer/GShard auxiliary loss): the older
approach adds a load-balancing term to the training loss (penalizing uneven expert usage), which
means the model is being optimized for two objectives at once (predict the next token well, AND
keep routing balanced) — these can conflict, and the balancing term's weight is an extra
hyperparameter to tune. DeepSeek-V3 (technical report, §2.1.2) replaces this with a per-expert
bias that affects ONLY which experts get selected (not the loss, not even the gate weight used
to scale a selected expert's output) and is updated by a simple hand-written rule after each
step. No gradient ever flows through it — it's a buffer, not a parameter — so there's no
optimization conflict with the primary training objective.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ExpertFFN(nn.Module):
    """One expert = one small MLP, identical shape to the dense MLP in model.py but usually
    narrower per-expert (that's the whole point of MoE: many narrow experts, few active per
    token, so capacity scales with n_experts while compute per token stays roughly fixed)."""
    def __init__(self, n_embd: int, hidden_mult: int = 4):
        super().__init__()
        self.fc_in = nn.Linear(n_embd, hidden_mult * n_embd, bias=False)
        self.fc_out = nn.Linear(hidden_mult * n_embd, n_embd, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc_out(F.gelu(self.fc_in(x)))


class MoELayer(nn.Module):
    def __init__(self, n_embd: int, n_experts: int, top_k: int, bias_update_rate: float = 0.001):
        super().__init__()
        self.n_experts = n_experts
        self.top_k = top_k
        self.bias_update_rate = bias_update_rate

        self.router = nn.Linear(n_embd, n_experts, bias=False)
        self.experts = nn.ModuleList([ExpertFFN(n_embd) for _ in range(n_experts)])
        # a BUFFER, not a Parameter — deliberately outside the autograd graph. See module
        # docstring: this is what makes the load balancing "auxiliary-loss-free."
        self.register_buffer("expert_bias", torch.zeros(n_experts))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        x_flat = x.reshape(-1, C)  # (N, C), N = B*T tokens

        logits = self.router(x_flat)              # (N, n_experts) — differentiable
        scores = logits.softmax(dim=-1)            # (N, n_experts) — differentiable

        # the bias affects WHICH experts get picked (routing decision), never the gate WEIGHT
        # applied to a picked expert's output — that still comes from the unbiased `scores`.
        # This split is the whole trick: bias steers traffic without ever appearing in a loss.
        biased_scores = scores + self.expert_bias
        _, topk_idx = biased_scores.topk(self.top_k, dim=-1)     # (N, top_k), no gradient (topk)
        gate = scores.gather(-1, topk_idx)                        # (N, top_k), differentiable
        gate = gate / gate.sum(-1, keepdim=True)                  # normalize among chosen top_k

        out = torch.zeros_like(x_flat)
        tokens_per_expert = torch.zeros(self.n_experts)
        for e in range(self.n_experts):
            # which (token, slot) pairs chose expert e as one of their top_k?
            token_idx, slot_idx = (topk_idx == e).nonzero(as_tuple=True)
            tokens_per_expert[e] = token_idx.numel()
            if token_idx.numel() == 0:
                continue  # an expert with zero tokens this batch gets literally zero gradient —
                          # this is the "dead expert" failure mode load balancing exists to avoid
            expert_out = self.experts[e](x_flat[token_idx])       # (n_tokens_e, C)
            out.index_add_(0, token_idx, expert_out * gate[token_idx, slot_idx].unsqueeze(-1))

        if self.training:
            with torch.no_grad():
                target = tokens_per_expert.mean()
                # overloaded (more tokens than average) -> bias down (less attractive next step)
                # underloaded -> bias up. Sign-based, not magnitude-based: DeepSeek-V3 uses a
                # fixed step size specifically so one extreme batch can't overcorrect.
                self.expert_bias += self.bias_update_rate * torch.sign(target - tokens_per_expert)

        return out.reshape(B, T, C), tokens_per_expert


def main():
    torch.manual_seed(0)
    n_embd, n_experts, top_k = 32, 8, 2
    moe = MoELayer(n_embd, n_experts, top_k)
    moe.train()

    x = torch.randn(4, 16, n_embd, requires_grad=True)  # (batch=4, seq=16, C) -> 64 tokens
    out, counts = moe(x)

    print(f"output shape: {tuple(out.shape)} (expect (4, 16, {n_embd}))")
    print(f"tokens per expert this batch: {counts.tolist()} (sum={counts.sum().item():.0f}, "
          f"expect {4*16*top_k}={4*16}*{top_k})")

    out.sum().backward()

    # correctness property 1: router got a gradient (it's used by every token, always active)
    print(f"\nrouter.weight.grad is not None: {moe.router.weight.grad is not None}, "
          f"norm={moe.router.weight.grad.norm().item():.4f}")

    # correctness property 2: an expert that got zero tokens has NO gradient at all — proves
    # the routing/gather really does isolate gradient flow per-expert, not leak into unused ones.
    unused = [e for e in range(n_experts) if counts[e] == 0]
    used = [e for e in range(n_experts) if counts[e] > 0]
    print(f"experts with 0 tokens this batch: {unused}")
    for e in unused[:1]:
        g = moe.experts[e].fc_in.weight.grad
        print(f"  expert {e} (unused) fc_in.weight.grad is None: {g is None}")
    for e in used[:1]:
        g = moe.experts[e].fc_in.weight.grad
        print(f"  expert {e} (used, {counts[e]:.0f} tokens) fc_in.weight.grad norm: {g.norm().item():.4f}")

    # correctness property 3: bias update pushed overloaded experts down, underloaded experts up
    overloaded = counts.argmax().item()
    underloaded = counts.argmin().item()
    print(f"\nexpert_bias after one step: {moe.expert_bias.tolist()}")
    print(f"  most-loaded expert {overloaded} ({counts[overloaded]:.0f} tokens): "
          f"bias={moe.expert_bias[overloaded].item():+.4f} (expect <= 0)")
    print(f"  least-loaded expert {underloaded} ({counts[underloaded]:.0f} tokens): "
          f"bias={moe.expert_bias[underloaded].item():+.4f} (expect >= 0)")


if __name__ == "__main__":
    main()
