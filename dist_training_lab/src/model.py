"""GPT-2-style decoder-only transformer, written from scratch (no HF/nanoGPT import) so every
line is something you had to reason about. Architecture matches GPT-2 (Radford et al. 2019)
with two modern defaults: no bias in Linear/LayerNorm (bias terms contribute negligible
capacity but real memory/compute cost — see LLaMA, PaLM), and pre-norm residual blocks (GPT-2
already does this; it's what makes stacking many layers trainable without extra tricks — see
"On Layer Normalization in the Transformer Architecture", Xiong et al. 2020, for why pre-norm
has better-behaved gradients at initialization than post-norm).
"""

import math

import torch
import torch.nn as nn
from torch.nn import functional as F

from config import ModelConfig


class CausalSelfAttention(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        assert cfg.n_embd % cfg.n_head == 0
        self.n_head = cfg.n_head
        self.head_dim = cfg.n_embd // cfg.n_head

        # combined QKV projection: one matmul instead of three, same math
        self.qkv_proj = nn.Linear(cfg.n_embd, 3 * cfg.n_embd, bias=cfg.bias)
        self.out_proj = nn.Linear(cfg.n_embd, cfg.n_embd, bias=cfg.bias)
        self.attn_dropout_p = cfg.dropout
        self.resid_dropout = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape

        qkv = self.qkv_proj(x)
        q, k, v = qkv.split(C, dim=2)
        # (B, T, C) -> (B, n_head, T, head_dim)
        q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)

        # scaled_dot_product_attention dispatches to a fused flash-attention-style kernel when
        # available (CUDA) and falls back to the naive math path otherwise (MPS/CPU) — same
        # numerical result either way, this is a systems-level choice, not a modeling one.
        y = F.scaled_dot_product_attention(
            q, k, v,
            dropout_p=self.attn_dropout_p if self.training else 0.0,
            is_causal=True,
        )
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.resid_dropout(self.out_proj(y))


class MLP(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.fc_in = nn.Linear(cfg.n_embd, 4 * cfg.n_embd, bias=cfg.bias)
        self.fc_out = nn.Linear(4 * cfg.n_embd, cfg.n_embd, bias=cfg.bias)
        self.dropout = nn.Dropout(cfg.dropout)
        self.act = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.dropout(self.fc_out(self.act(self.fc_in(x))))


class Block(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.ln_1 = nn.LayerNorm(cfg.n_embd, bias=cfg.bias)
        self.attn = CausalSelfAttention(cfg)
        self.ln_2 = nn.LayerNorm(cfg.n_embd, bias=cfg.bias)
        self.mlp = MLP(cfg)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # pre-norm residual: x + f(norm(x)), not norm(x + f(x))
        x = x + self.attn(self.ln_1(x))
        x = x + self.mlp(self.ln_2(x))
        return x


class GPT(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.cfg = cfg

        self.tok_emb = nn.Embedding(cfg.vocab_size, cfg.n_embd)
        self.pos_emb = nn.Embedding(cfg.block_size, cfg.n_embd)
        self.drop = nn.Dropout(cfg.dropout)
        self.blocks = nn.ModuleList([Block(cfg) for _ in range(cfg.n_layer)])
        self.ln_f = nn.LayerNorm(cfg.n_embd, bias=cfg.bias)
        self.lm_head = nn.Linear(cfg.n_embd, cfg.vocab_size, bias=False)

        # weight tying: input embedding and output projection share weights (Press & Wolf,
        # 2017, "Using the Output Embedding to Improve Language Models"). Saves vocab_size *
        # n_embd params — at GPT-2-small scale that's ~38M params, ~30% of the model.
        self.tok_emb.weight = self.lm_head.weight

        self.apply(self._init_weights)
        # GPT-2 paper: scale residual projection init by 1/sqrt(2*n_layer) so residual stream
        # variance doesn't grow with depth at initialization.
        for name, p in self.named_parameters():
            if name.endswith("out_proj.weight") or name.endswith("fc_out.weight"):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * cfg.n_layer))

        n_params = sum(p.numel() for p in self.parameters())
        n_params_notied = n_params - self.tok_emb.weight.numel()
        print(f"GPT init: {n_params/1e6:.2f}M params ({n_params_notied/1e6:.2f}M excluding tied embedding)")

    def _init_weights(self, module: nn.Module) -> None:
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx: torch.Tensor, targets: torch.Tensor | None = None):
        B, T = idx.shape
        assert T <= self.cfg.block_size, f"sequence length {T} exceeds block_size {self.cfg.block_size}"

        pos = torch.arange(T, device=idx.device)
        x = self.drop(self.tok_emb(idx) + self.pos_emb(pos))
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)

        if targets is not None:
            logits = self.lm_head(x)
            loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1))
            return logits, loss
        else:
            # inference-time optimization: only project the last position
            logits = self.lm_head(x[:, [-1], :])
            return logits, None

    @torch.no_grad()
    def generate(self, idx: torch.Tensor, max_new_tokens: int, temperature: float = 1.0, top_k: int | None = None) -> torch.Tensor:
        self.eval()
        for _ in range(max_new_tokens):
            idx_cond = idx if idx.size(1) <= self.cfg.block_size else idx[:, -self.cfg.block_size:]
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] / temperature
            if top_k is not None:
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = -float("inf")
            probs = F.softmax(logits, dim=-1)
            next_id = torch.multinomial(probs, num_samples=1)
            idx = torch.cat([idx, next_id], dim=1)
        self.train()
        return idx


def build_optimizer(named_parameters, weight_decay: float, learning_rate: float, betas: tuple[float, float]) -> torch.optim.Optimizer:
    """Module-level, not a GPT method — deliberately. It must be called on `model.named_parameters()`
    of whatever `model` actually is *after* DDP/FSDP wrapping, not before: DDP doesn't change the
    underlying parameter tensors so pre- vs post-wrap doesn't matter, but FSDP shards parameter
    storage across ranks on wrap, so building the optimizer from pre-wrap parameters would silently
    optimize tensors that no longer back the model. Taking `named_parameters()` as a plain argument
    (rather than `self.named_parameters()` on a method) makes that "call after wrapping" requirement
    impossible to get backwards by accident.
    """
    # standard practice (GPT-3 paper, App. B): decay weight matrices, not LayerNorm/bias/embeddings.
    decay, no_decay = [], []
    for _, p in named_parameters:
        if not p.requires_grad:
            continue
        if p.dim() >= 2:
            decay.append(p)
        else:
            no_decay.append(p)
    groups = [
        {"params": decay, "weight_decay": weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]
    return torch.optim.AdamW(groups, lr=learning_rate, betas=betas)
