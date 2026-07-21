"""PyTorch basics drill — tensor / nn.Module / einops / no_grad.

Run from repo root of this lab:
  cd code/dist_training_lab
  source .venv/bin/activate   # or: uv run
  pip install einops          # one-time
  python learn/00_tensor_module_einops.py

Read the prints. Then uncomment the EXERCISES at the bottom and make them pass.
"""

from __future__ import annotations

import torch
import torch.nn as nn
from torch.nn import functional as F

try:
    from einops import rearrange, reduce, repeat
    from einops.layers.torch import Rearrange
except ImportError as e:
    raise SystemExit("pip install einops  then re-run") from e


# =============================================================================
# 1. Tensor — the only datatype that matters
# =============================================================================
# Tensor = ndarray + device + dtype + (optional) autograd tape.
# Shape convention in transformers: (batch, seq, channels) aka (B, T, C)

print("=" * 60)
print("1. TENSOR")

x = torch.randn(2, 4, 8)  # B=2, T=4, C=8
print(f"shape={x.shape} dtype={x.dtype} device={x.device}")
print(f"requires_grad={x.requires_grad}")  # False — leaf float tensors default OFF

# Autograd only tracks ops on tensors that need grad
w = torch.randn(8, 8, requires_grad=True)
y = (x @ w).sum()
y.backward()
print(f"w.grad shape={w.grad.shape}")  # same shape as w
print(f"x.grad is None? {x.grad is None}")  # True — x didn't require_grad

# Common ops you'll hit constantly in model.py
B, T, C = 2, 4, 8
n_head, head_dim = 2, 4
q = torch.randn(B, T, C)
# view/reshape need contiguous memory layout for some patterns; transpose breaks contiguity
q_heads = q.view(B, T, n_head, head_dim).transpose(1, 2)  # (B, n_head, T, head_dim)
print(f"after transpose contiguous? {q_heads.is_contiguous()}")
q_flat = q_heads.transpose(1, 2).contiguous().view(B, T, C)  # why .contiguous() before view
print(f"roundtrip ok? {torch.allclose(q, q_flat)}")

# Indexing gotcha used in GPT.forward inference path: x[:, [-1], :] keeps dim
logits_last_keep = q[:, [-1], :]   # (B, 1, C)
logits_last_drop = q[:, -1, :]     # (B, C)
print(f"keep dim {logits_last_keep.shape} vs squeeze {logits_last_drop.shape}")


# =============================================================================
# 2. @torch.no_grad() — why generate() has it
# =============================================================================
# Training: build graph → backward → update weights.
# Inference / generate: you only need values. Building the graph wastes memory
# and can accidentally accumulate grads if someone later calls .backward().
#
# Three related APIs:
#   torch.no_grad()          — disable grad tracking (most common)
#   torch.inference_mode()   — stricter/faster; almost always prefer for pure infer
#   tensor.detach()          — keep value, cut THIS tensor out of the graph

print("=" * 60)
print("2. no_grad")


class Tiny(nn.Module):
    def __init__(self):
        super().__init__()
        self.lin = nn.Linear(4, 4)

    def forward(self, x):
        return self.lin(x)


m = Tiny()
inp = torch.randn(2, 4)

# WITH grad (training-style)
out = m(inp)
print(f"train forward: out.requires_grad={out.requires_grad}")  # True — depends on params

# Decorator form — same as `with torch.no_grad(): ...` wrapping the whole function
@torch.no_grad()
def generate_step(model, x):
    return model(x)


out2 = generate_step(m, inp)
print(f"no_grad forward: out2.requires_grad={out2.requires_grad}")  # False

# model.eval() ≠ no_grad
#   eval()  → flips Dropout/BatchNorm behavior
#   no_grad → stops building autograd graph
# generate() in model.py does BOTH. You need both.


# =============================================================================
# 3. nn.Module — the container pattern
# =============================================================================
# Rule: anything that is a Parameter / submodule MUST be assigned as an attribute
# in __init__ (or ModuleList/ModuleDict), or .parameters() / .to(device) / state_dict
# will miss it.

print("=" * 60)
print("3. nn.Module")


class Bad(nn.Module):
    def __init__(self):
        super().__init__()
        self.weights = [nn.Linear(4, 4)]  # plain list — NOT registered


class Good(nn.Module):
    def __init__(self):
        super().__init__()
        self.weights = nn.ModuleList([nn.Linear(4, 4)])  # registered


print(f"Bad  n_params={sum(p.numel() for p in Bad().parameters())}")   # 0 — bug
print(f"Good n_params={sum(p.numel() for p in Good().parameters())}")  # 20

# Your GPT uses ModuleList for blocks — same reason.
# nn.Parameter wraps a tensor so it's a learnable weight:
class ManualLinear(nn.Module):
    def __init__(self, din, dout):
        super().__init__()
        self.weight = nn.Parameter(torch.randn(dout, din) * 0.02)
        self.bias = nn.Parameter(torch.zeros(dout))

    def forward(self, x):
        return x @ self.weight.T + self.bias


# .train() / .eval() recurse into children — that's why generate() calls self.eval()
# then self.train() at the end: restore training mode for the caller.


# =============================================================================
# 4. einops — readable reshape (replaces your attention view/transpose mess)
# =============================================================================
# Your CausalSelfAttention does:
#   q.view(B, T, n_head, head_dim).transpose(1, 2)
# einops makes the axis names explicit — fewer off-by-one bugs.

print("=" * 60)
print("4. einops")

B, T, C, H, D = 2, 4, 8, 2, 4
q = torch.randn(B, T, C)

# BEFORE (model.py style)
q1 = q.view(B, T, H, D).transpose(1, 2)

# AFTER
q2 = rearrange(q, "b t (h d) -> b h t d", h=H)
print(f"match view/transpose? {torch.allclose(q1, q2)}")

# merge heads back
y = rearrange(q2, "b h t d -> b t (h d)")
print(f"merge back shape={y.shape}")

# reduce: mean over heads
mean_h = reduce(q2, "b h t d -> b t d", "mean")
print(f"reduce mean over h: {mean_h.shape}")

# repeat: broadcast a position embedding mentally
pos = torch.randn(T, C)
pos_b = repeat(pos, "t c -> b t c", b=B)
print(f"repeat pos to batch: {pos_b.shape}")

# as a Module layer (useful in Sequential)
to_heads = Rearrange("b t (h d) -> b h t d", h=H)
print(f"Rearrange module: {to_heads(q).shape}")


# =============================================================================
# 5. Mini attention with einops — same math as CausalSelfAttention, smaller
# =============================================================================
print("=" * 60)
print("5. mini attention")


class MiniAttn(nn.Module):
    def __init__(self, n_embd=8, n_head=2):
        super().__init__()
        assert n_embd % n_head == 0
        self.n_head = n_head
        self.qkv = nn.Linear(n_embd, 3 * n_embd, bias=False)
        self.out = nn.Linear(n_embd, n_embd, bias=False)

    def forward(self, x):
        # x: (b, t, c)
        qkv = self.qkv(x)
        q, k, v = rearrange(qkv, "b t (three h d) -> three b h t d", three=3, h=self.n_head)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        y = rearrange(y, "b h t d -> b t (h d)")
        return self.out(y)


attn = MiniAttn()
x = torch.randn(2, 4, 8)
with torch.no_grad():
    print(f"MiniAttn out={attn(x).shape}")


# =============================================================================
# EXERCISES — uncomment & fill until asserts pass
# =============================================================================
def exercises():
    # E1: make a (3, 5) float tensor on the same device as `x`, requires_grad=True
    a = torch.randn(3, 5, requires_grad=True)
    assert a.shape == (3, 5) and a.requires_grad

    # E2: without using view/transpose, rearrange (b,t,c) -> (b,h,t,d) with h=4, c=16
    z = torch.randn(2, 8, 16)
    z2 = rearrange(z, "b t (h d) -> b h t d", h=4)
    assert z2.shape == (2, 4, 8, 4)

    # E3: write a function that returns model(x) under no_grad AND eval mode,
    #     then restores train mode. Mirror GPT.generate's bookkeeping.
    def safe_infer(model, x):
        with torch.no_grad():
            with torch.inference_mode():
                out = model(x)
        return out
    m = Tiny()
    m.train()
    out = safe_infer(m, torch.randn(2, 4))
    assert not out.requires_grad and m.training

    print("exercises: uncomment & fill")


if __name__ == "__main__":
    exercises()
    print("=" * 60)
    print("done. Next: open src/model.py CausalSelfAttention + generate,")
    print("rewrite the q/k/v reshape with einops rearrange, keep tests green.")
