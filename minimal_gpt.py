"""
Minimal decoder-only GPT for learning.

Intentionally small and readable (~150 lines of model code).
Matches concepts in notes/transformer_interview_visual.md:
  - causal self-attention + multi-head
  - pre-norm transformer block
  - parallel teacher-forcing forward (training)
  - optional KV cache path (inference)
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor


class CausalSelfAttention(nn.Module):
    def __init__(self, n_heads: int, d_model: int, dropout: float = 0.0) -> None:
        super().__init__()
        assert d_model % n_heads == 0
        self.n_heads = n_heads
        self.d_head = d_model // n_heads
        self.qkv = nn.Linear(d_model, 3 * d_model)
        self.proj = nn.Linear(d_model, d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(
        self,
        x: Tensor,
        *,
        past_kv: tuple[Tensor, Tensor] | None = None,
        use_cache: bool = False,
    ) -> tuple[Tensor, tuple[Tensor, Tensor] | None]:
        b, t, c = x.shape
        qkv = self.qkv(x).reshape(b, t, 3, self.n_heads, self.d_head)
        q, k, v = qkv.unbind(dim=2)
        q = q.transpose(1, 2)  # (b, nh, t, dh)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        if past_kv is not None:
            pk, pv = past_kv
            k = torch.cat([pk, k], dim=2)
            v = torch.cat([pv, v], dim=2)

        attn = (q @ k.transpose(-2, -1)) / math.sqrt(self.d_head)
        if past_kv is None:
            mask = torch.triu(
                torch.ones(t, t, device=x.device, dtype=torch.bool), diagonal=1
            )
            attn = attn.masked_fill(mask, float("-inf"))
        else:
            # Single new query attends to full cached keys.
            pass

        attn = F.softmax(attn, dim=-1)
        attn = self.dropout(attn)
        y = attn @ v
        y = y.transpose(1, 2).reshape(b, t, c)
        y = self.proj(y)
        new_cache = (k, v) if use_cache else None
        return y, new_cache


class Block(nn.Module):
    def __init__(self, n_heads: int, d_model: int, d_ff: int, dropout: float) -> None:
        super().__init__()
        self.ln1 = nn.LayerNorm(d_model)
        self.attn = CausalSelfAttention(n_heads, d_model, dropout)
        self.ln2 = nn.LayerNorm(d_model)
        self.mlp = nn.Sequential(
            nn.Linear(d_model, d_ff),
            nn.GELU(),
            nn.Linear(d_ff, d_model),
            nn.Dropout(dropout),
        )

    def forward(
        self,
        x: Tensor,
        *,
        past_kv: tuple[Tensor, Tensor] | None = None,
        use_cache: bool = False,
    ) -> tuple[Tensor, tuple[Tensor, Tensor] | None]:
        h, cache = self.attn(self.ln1(x), past_kv=past_kv, use_cache=use_cache)
        x = x + h
        x = x + self.mlp(self.ln2(x))
        return x, cache


class MiniGPT(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        n_layers: int = 4,
        n_heads: int = 4,
        d_model: int = 128,
        d_ff: int = 512,
        max_seq_len: int = 256,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.max_seq_len = max_seq_len
        self.token_emb = nn.Embedding(vocab_size, d_model)
        self.pos_emb = nn.Embedding(max_seq_len, d_model)
        self.drop = nn.Dropout(dropout)
        self.blocks = nn.ModuleList(
            [Block(n_heads, d_model, d_ff, dropout) for _ in range(n_layers)]
        )
        self.ln_f = nn.LayerNorm(d_model)
        self.lm_head = nn.Linear(d_model, vocab_size, bias=False)
        self.lm_head.weight = self.token_emb.weight  # weight tying

    def forward(
        self,
        idx: Tensor,
        *,
        past_caches: list[tuple[Tensor, Tensor] | None] | None = None,
        use_cache: bool = False,
    ) -> tuple[Tensor, list[tuple[Tensor, Tensor] | None] | None]:
        b, t = idx.shape
        if past_caches is None:
            pos = torch.arange(t, device=idx.device).unsqueeze(0)
        else:
            past_len = past_caches[0][0].shape[2] if past_caches[0] is not None else 0
            pos = torch.arange(past_len, past_len + t, device=idx.device).unsqueeze(0)

        x = self.drop(self.token_emb(idx) + self.pos_emb(pos))
        new_caches: list[tuple[Tensor, Tensor] | None] = []
        for i, block in enumerate(self.blocks):
            past = past_caches[i] if past_caches is not None else None
            x, cache = block(x, past_kv=past, use_cache=use_cache)
            new_caches.append(cache)

        logits = self.lm_head(self.ln_f(x))
        return logits, new_caches if use_cache else None

    @torch.no_grad()
    def generate(
        self,
        idx: Tensor,
        max_new_tokens: int,
        *,
        use_cache: bool = True,
    ) -> Tensor:
        caches: list[tuple[Tensor, Tensor] | None] | None = None
        for _ in range(max_new_tokens):
            ctx = idx[:, -1:] if caches is not None else idx
            logits, caches = self.forward(ctx, past_caches=caches, use_cache=use_cache)
            next_id = logits[:, -1].argmax(dim=-1, keepdim=True)
            idx = torch.cat([idx, next_id], dim=1)
        return idx
