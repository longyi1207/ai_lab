"""Phase 5: FP8 quantization from scratch — why a single per-tensor scale factor fails in the
presence of outliers, and why block-wise (tile-wise) scaling fixes it. This is the mechanism
DeepSeek-V3 (Technical Report §3.3) had to engineer around to train in FP8 without accuracy loss.

No distributed anything here — single device, pure numerics. FP8 tensor cores (the hardware that
makes FP8 actually FAST) aren't available on CPU/MPS, so forward/backward below use "fake
quantization": cast to fp8 and immediately back up to fp32 before the real matmul. This still
lets us honestly study the NUMERICS (what error FP8 introduces) even though we can't measure the
real speed/memory win without real FP8 tensor cores — same "written for correctness, not for
speed" boundary as the rest of this project's free/local experiments.

Run: .venv/bin/python experiments/fp8_quantization.py
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

E4M3_MAX = 448.0  # torch.finfo(torch.float8_e4m3fn).max


class _QuantizeDequantizeSTE(torch.autograd.Function):
    """Straight-through estimator (Bengio et al. 2013), the standard quantization-aware-training
    technique — NOT relying on whatever gradient torch's raw `.to(float8_e4m3fn)` cast happens
    to produce. Found out the hard way that matters: composing `(x/scale).to(fp8).to(fp32)*scale`
    directly and calling .backward() gives a gradient that silently depends on `scale` (measured
    1.95 at scale=0.001 vs the correct 1.0 at scale=1.0, on the exact same logical operation) —
    an undocumented artifact of how autograd differentiates the fp8 cast composed with division,
    not a real STE. Real quantization-aware training never leans on that; it defines the backward
    pass explicitly, forward = quantize+dequantize, backward = identity (gradient passes through
    unchanged, as if quantization hadn't happened) — that's what "straight-through" means.
    """
    @staticmethod
    def forward(ctx, x: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
        x_fp8 = (x / scale).to(torch.float8_e4m3fn)
        return x_fp8.to(torch.float32) * scale

    @staticmethod
    def backward(ctx, grad_output: torch.Tensor):
        return grad_output, None  # identity w.r.t. x; scale is a fixed (non-learned) buffer


def quantize_dequantize(x: torch.Tensor, scale: torch.Tensor) -> torch.Tensor:
    """x -> fp8 -> back to fp32, using `scale` to map x's range onto fp8's representable range
    before casting (and back out after). This is the "fake quant" round-trip: the VALUES have
    already lost whatever precision the fp8 cast destroyed (that's what we study in Part 1);
    gradients flow through as a clean straight-through estimator (see class above) — that's what
    makes Part 2's training experiment measure the quantization error's effect specifically, not
    an unrelated autograd artifact.
    """
    return _QuantizeDequantizeSTE.apply(x, scale)


def per_tensor_scale(x: torch.Tensor) -> torch.Tensor:
    """One scale for the whole tensor, sized so the single largest-magnitude element just
    reaches E4M3_MAX. Every other element inherits this scale whether it needs it or not."""
    return x.abs().max() / E4M3_MAX


def block_quantize_dequantize(x: torch.Tensor, block_size: int) -> torch.Tensor:
    """Independent scale per contiguous block of `block_size` elements (flattened). DeepSeek-V3
    uses 128; this function works for any block_size so we can sweep it."""
    flat = x.flatten()
    n = flat.numel()
    pad = (-n) % block_size
    if pad:
        flat = torch.cat([flat, torch.zeros(pad)])
    blocks = flat.view(-1, block_size)
    scales = blocks.abs().amax(dim=1, keepdim=True) / E4M3_MAX
    scales = scales.clamp(min=1e-12)  # an all-zero block would otherwise divide by zero
    out = quantize_dequantize(blocks, scales)
    return out.flatten()[:n].view_as(x)


def make_realistic_weight_with_outliers(shape, base_std=0.02, n_outliers=3, outlier_mult=40, seed=0):
    """A weight-init-scale tensor (std=0.02, matching this project's GPT init — see model.py)
    with a handful of much-larger values sprinkled in. This mimics the real, well-documented
    "outlier feature" phenomenon in transformers (Dettmers et al. 2022, LLM.int8()) that breaks
    naive low-precision quantization — a few channels/values run 10-100x the typical magnitude,
    and a shared scale factor has to accommodate them at the expense of everything else.
    """
    torch.manual_seed(seed)
    x = torch.randn(shape) * base_std
    flat = x.flatten()
    idx = torch.randperm(flat.numel())[:n_outliers]
    flat[idx] = torch.randn(n_outliers).sign() * base_std * outlier_mult
    return flat.view(shape)


def report_error(name: str, original: torch.Tensor, reconstructed: torch.Tensor) -> None:
    err = (original - reconstructed).abs()
    rel_err = err / original.abs().clamp(min=1e-8)
    # separate the outliers (top 1% by magnitude) from the "typical" values — the whole point
    # is that per-tensor scaling sacrifices the typical values to accommodate the outliers.
    k = max(1, original.numel() // 100)
    outlier_idx = original.flatten().abs().topk(k).indices
    mask = torch.zeros_like(original.flatten(), dtype=torch.bool)
    mask[outlier_idx] = True
    mask = mask.view_as(original)

    print(f"{name:22s} overall_mean_rel_err={rel_err.mean().item():.4f}  "
          f"typical_values_mean_rel_err={rel_err[~mask].mean().item():.4f}  "
          f"outlier_values_mean_rel_err={rel_err[mask].mean().item():.4f}")


def part1_quantization_error():
    print("=== Part 1: quantization error, naive per-tensor vs block-wise ===\n")
    w = make_realistic_weight_with_outliers((256, 256))
    print(f"weight stats: std={w.std():.4f}, max|w|={w.abs().max():.4f} "
          f"({(w.abs() > 0.1).sum().item()} of {w.numel()} elements are the injected outliers)\n")

    naive = quantize_dequantize(w, per_tensor_scale(w))
    report_error("naive per-tensor", w, naive)

    for block in [128, 32]:
        blockwise = block_quantize_dequantize(w, block)
        report_error(f"block-wise (n={block})", w, blockwise)

    print("\n-> Notice typical_values_mean_rel_err barely changes (0.0226 -> 0.0220) — NOT what "
          "naive intuition predicts ('outlier-driven scale wrecks every other value's precision'). "
          "FP8 is floating point, not fixed point: relative precision stays roughly constant "
          "across its representable range regardless of scale, as long as values don't underflow. "
          "What DOES change dramatically is outlier_values_mean_rel_err (0.0224 -> 0.0027, ~8x) — "
          "block-wise scaling's real, measured benefit here is precision for the outliers "
          "THEMSELVES (each gets a scale sized to its own block, not stretched by unrelated "
          "far-away outliers), not rescuing everyone else from them. See Part 2 for why this "
          "matters (or doesn't, in this toy setup) for actual training.\n")


class FakeFP8Linear(nn.Module):
    """A Linear layer whose forward simulates FP8 compute: quantize input & weight (via the
    given quantization function) immediately before the matmul, dequantize immediately after
    casting — the matmul itself still runs in fp32, but on values that already carry FP8's
    rounding error. Gradients use E5M2-style wider-range treatment conceptually (same E4M3 cast
    used here for simplicity; real systems use E5M2 for gradients specifically because gradients
    have a wider dynamic range than weights/activations — noted, not implemented, to keep this
    focused on the one variable under test: per-tensor vs block-wise scaling).
    """
    def __init__(self, in_features: int, out_features: int, quant_fn):
        super().__init__()
        self.weight = nn.Parameter(torch.randn(out_features, in_features) * 0.02)
        self.quant_fn = quant_fn

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x_q = self.quant_fn(x)
        w_q = self.quant_fn(self.weight)
        return F.linear(x_q, w_q)


def part2_training_impact():
    print("=== Part 2: does this actually matter for training, or just for one tensor? ===\n")
    torch.manual_seed(0)
    x = torch.randn(8, 256)
    target = torch.randn(8, 256)

    configs = {
        "full precision (no quant)": lambda t: t,
        "naive per-tensor fp8": lambda t: quantize_dequantize(t, per_tensor_scale(t)),
        "block-wise fp8 (n=32)": lambda t: block_quantize_dequantize(t, 32),
    }

    for name, quant_fn in configs.items():
        torch.manual_seed(1)  # identical init across configs
        layer = FakeFP8Linear(256, 256, quant_fn)
        # inject the same outlier structure into the weight as part 1, so this isn't a
        # best-case (well-behaved) weight matrix — real transformer weights/activations do
        # exhibit this outlier-channel structure (Dettmers et al. 2022).
        with torch.no_grad():
            layer.weight.copy_(make_realistic_weight_with_outliers((256, 256), seed=1))
        opt = torch.optim.SGD(layer.parameters(), lr=0.1)

        losses = []
        for _ in range(30):
            opt.zero_grad()
            out = layer(x)
            loss = F.mse_loss(out, target)
            loss.backward()
            opt.step()
            losses.append(loss.item())

        print(f"{name:28s} loss: {losses[0]:.4f} -> {losses[-1]:.4f}  "
              f"(first 5: {[round(l, 3) for l in losses[:5]]})")

    print("\n-> HONEST RESULT (not the dramatic one originally expected): all three configs "
          "train nearly identically here. Reasoning through why matters more than the number:\n"
          "   FP8 is still FLOATING point (unlike INT8), so relative precision for 'typical' "
          "values stays roughly constant regardless of scale, UNLESS the scale pushes them "
          "toward underflow. At this outlier ratio (40x), typical values land at ~11.6 in the "
          "rescaled range — nowhere near FP8's underflow floor (~0.002) — so they're barely hurt.\n"
          "   This also suggests DeepSeek-V3's actual documented pain point (§3.3: H800 Tensor "
          "Cores' FP8 *accumulation* is only 14-bit precision, fixed by promoting to CUDA-core "
          "accumulation every 128 elements) may matter MORE than pure quantization-scale "
          "granularity for real training quality — and that's a hardware accumulator behavior "
          "this CPU experiment structurally cannot reproduce (CPU matmul always accumulates in "
          "full fp32/fp64 internally). What's verified here for real: block-wise scaling reduces "
          "outlier-element reconstruction error (Part 1, ~8x). What's NOT verified: that this "
          "specific mechanism alone explains DeepSeek's real training-quality engineering effort.")


if __name__ == "__main__":
    part1_quantization_error()
    part2_training_impact()
