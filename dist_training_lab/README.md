# dist_training_lab — ML Infra / Distributed Training Curriculum

**Goal:** build real, hands-on depth in the skills frontier-lab research-infra / ML platform
engineering roles screen for:

- Deep experience with PyTorch (and later JAX) internals, not just the high-level API.
- Distributed-training stacks: DDP → FSDP/ZeRO → tensor/pipeline/expert parallelism → FP8.
- **Reliability & control-plane engineering** — fault tolerance, self-healing, observability —
  the part that specifically distinguishes "research infrastructure / ML platform engineering"
  job descriptions from "can write a training loop" (see Phase 6).
- The systems judgment that comes from having actually scaled something, even a toy model,
  across multiple devices and diagnosed why it was slow.

This is not a tutorial-following exercise. Every phase below ends with **a script that runs,
a metric that was measured, and a short writeup of what broke and why.** That writeup is the
actual deliverable — it's what you'd talk about in an interview.

Related: [`../../CAREER.md`](../../CAREER.md) (Path #1 — frontier safety lab, specifically the
research-infra/systems angle within it), [`../../LEARNING_PLAN.md`](../../LEARNING_PLAN.md)
(hands-on coding hours this draws from), [`../transformer_lab/`](../transformer_lab/) (earlier,
more interpretability-flavored GPT experiments — this project is systems-flavored instead).

## How this is organized

```
dist_training_lab/
  README.md          # this file — roadmap + phase logs
  .venv/              # uv-managed venv, Python 3.12 (gitignored)
  requirements.txt
  configs/            # yaml configs per run
  src/
    model.py          # GPT implementation, dependency-free (no nanoGPT/HF import)
    data.py            # tokenization + memmap-backed dataset
    config.py          # dataclasses for model/train/run config
    utils.py            # seeding, logging setup, checkpoint save/load, device selection
    train.py            # main training loop — torchrun-compatible from day one
  data_prep/
    prepare_shakespeare.py   # Phase 1 dataset: tiny, fast to iterate on
  experiments/          # Phase 4/5 standalone, verified-against-a-reference demos (not wired
    tensor_parallel_mlp.py    # into src/train.py — each is self-contained, run directly)
    pipeline_parallel_demo.py
    moe_layer.py
    expert_parallel_demo.py
    fp8_quantization.py     # Phase 5: single-device, no distributed anything
  scripts/
    run_local.sh        # single-process (MPS/CPU) launch
    run_ddp_local.sh     # torchrun with N processes, CPU gloo backend (Phase 2, sim) — verified
    run_fsdp_local.sh      # same, --parallelism fsdp (Phase 3, sim) — verified
    run_ddp_cloud.sh      # torchrun on a rented multi-GPU box (Phase 2+, real — not written yet)
    make_dashboard.py       # JSONL log -> self-contained HTML loss dashboard
  checkpoints/          # gitignored
  logs/                  # gitignored
```

**Design decision, and why it matters:** `train.py` is written to be DDP-ready from Phase 1,
even though Phase 1 runs on a single MPS device. It checks `WORLD_SIZE`/`RANK` env vars (the
same ones `torchrun` sets) and only wraps the model in `DistributedDataParallel` if
`WORLD_SIZE > 1`. This mirrors how real training codebases (nanoGPT, GPT-NeoX, litgpt) are
structured — you do not rewrite the training loop when you add GPUs, you change how you launch
it. Understanding *why* that pattern exists is itself part of the lesson.

## Phase 1 — Single-device foundations (local, M4 MacBook, MPS backend)

**Status:** done, 2026-07-20. Core loop + best-checkpoint tracking + early stopping all
verified end to end. Ready to move to Phase 2 (DDP).

**What "done" looks like:** a GPT trained on tiny-Shakespeare from scratch, on MPS, with:
- Mixed precision (bfloat16 autocast — MPS has no `GradScaler` support so this must be
  understood, not copy-pasted from a CUDA tutorial).
- Gradient accumulation (simulate a larger batch size than fits in unified memory).
- Gradient clipping + cosine LR schedule with linear warmup (the standard GPT-3/Chinchilla
  recipe — see [Chinchilla paper, Hoffmann et al. 2022](https://arxiv.org/abs/2203.15556) for
  why warmup+cosine, not just "everyone does it").
- Checkpointing that saves model + optimizer + step, and **resumes stably** (loss curve has no
  discontinuity/spike across a kill -9 + restart — this is the single most-tested property of a
  real training stack, and the easiest thing to get subtly wrong). **Correction, found via the
  Phase 6 elastic-restart test (2026-07-21):** this line originally claimed RNG state was saved
  too — it isn't (`utils.py`'s checkpoint dict never included it). What's actually verified is
  *no loss discontinuity*, not *bit-exact reproducibility of the data order* — a resumed run
  samples a different sequence of random batches than an uninterrupted run would have, because
  `seed_everything(seed, rank)` reseeds fresh from `seed+rank` on every process start rather than
  continuing a saved generator state. This is a real, common simplification (not obviously worth
  fixing) — production systems at real scale generally don't guarantee bit-exact data-order
  reproducibility across a crash either, only stability. Flagging the earlier claim as wrong
  rather than quietly editing it away, since catching your own documentation overclaiming a
  property that was never actually tested is itself the kind of thing worth being able to say
  happened.
- Structured logging: every N steps, log loss, LR, grad norm, tokens/sec, memory — to both
  stdout and a JSONL file (so it's plottable later, not just eyeballed).
- Deterministic seeding.

**What you should be able to explain after this phase:**
- Why bfloat16 (not fp16) is the right choice for MPS/Apple Silicon and for most modern
  training in general (dynamic range vs. precision tradeoff — fp16 needs loss scaling because
  its exponent range is too small for typical gradient magnitudes; bf16 has the same exponent
  range as fp32 so it doesn't).
- Why gradient accumulation is mathematically equivalent to a larger batch (and where it isn't
  — e.g. batchnorm statistics, though GPT has none).
- What exactly is in a "complete" checkpoint and why (optimizer state for Adam is 2x model size
  — this fact alone is why ZeRO exists, foreshadowing Phase 3).

**Reference implementations to read (not copy) after writing your own:**
- [nanoGPT](https://github.com/karpathy/nanoGPT) — Karpathy's minimal, readable GPT-2 trainer.
  The canonical "small but real" reference.
- [GPT-2 paper](https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf)
  and [Attention Is All You Need](https://arxiv.org/abs/1706.03762) for the architecture itself.

## Phase 2 — Multi-process data parallelism (DDP)

**Status:** local (CPU/gloo) correctness test done, 2026-07-20. Real multi-GPU cloud run not
started yet.

**Plan:**
1. First, simulate multi-process DDP *locally* with `torchrun --nproc_per_node=4` using the
   `gloo` CPU backend — this validates the training loop's DDP-readiness without needing real
   GPUs or spending money.
2. Then, rent a real multi-GPU box (see **Cloud budget** below) and run the same script with
   the `nccl` backend, comparing tokens/sec scaling: is 4 GPUs ~4x one GPU? If not, why not
   (communication overhead, small batch size, bad overlap of compute/communication)?

**What "done" looks like:** a short writeup answering: what does `DistributedDataParallel`
actually do on `.backward()` (all-reduce of gradients, bucketed and overlapped with backward
compute)? What's the difference between DP (deprecated, single-process multi-GPU) and DDP
(multi-process)? Measured scaling efficiency on a real multi-GPU run.

**Reference:** [PyTorch DDP paper, Li et al. 2020](https://arxiv.org/abs/2006.15704) — the
actual systems paper behind `torch.nn.parallel.DistributedDataParallel`, not just the docs.

## Phase 3 — Memory-efficient training at larger scale (FSDP2 / ZeRO)

**Status:** core implementation done and verified free/local, 2026-07-20. Real memory-ceiling
numbers on actual multi-GPU hardware not measured yet (needs real GPUs — written code, not run,
see Cloud budget below).

Used **FSDP2** (`torch.distributed.fsdp.fully_shard`), not the older wrapper-style
`FullyShardedDataParallel` class — FSDP2 is the composable, DTensor-based API and is what
current large-scale training code (e.g. Meta's TorchTitan) actually uses; it also sidesteps a
real problem the old API has (see below). Compare against DeepSpeed ZeRO stage 2/3 conceptually
(same idea, different implementation) — [Rajbhandari et al. 2019, ZeRO](https://arxiv.org/abs/1910.02054)
is the paper that introduced this and is worth reading since it's the intellectual ancestor of
both FSDP APIs.

**What "done" looks like:** measured max model size trainable under DDP vs FSDP on the same
hardware (not done — needs real GPUs), and — done — an explanation of *why*: sharding optimizer
states, then gradients, then parameters across ranks (ZeRO stages 1/2/3), each trading more
communication for less per-device memory.

**Three real correctness properties that DDP doesn't have to worry about, and why:**
1. **Optimizer must be built *after* wrapping.** FSDP shards parameter storage on wrap; an
   optimizer built from pre-wrap parameter references would silently optimize tensors that no
   longer back the model. Fixed by making `build_optimizer` a plain function over
   `model.named_parameters()` called post-wrap (`model.py`), instead of a method on `GPT` that's
   easy to call at the wrong time.
2. **Forward pass is a collective.** Every FSDP block does an all-gather to materialize its full
   parameters before computing, then reshards after. That means **anything that calls
   forward — including eval — must run on every rank**, not just rank 0. Phase 1/2's
   `if is_master: estimate_loss(...)` pattern was safe under DDP (forward has no collectives)
   and would **deadlock** under FSDP (master waiting at an all-gather nothing else joins).
   Fixed: `estimate_loss` now always runs on every rank; only the logging/decision-making after
   it is master-gated.
3. **Checkpointing is also a collective.** Gathering a full (unsharded) state dict from FSDP's
   per-rank shards is an all-gather too — every rank must call it, even though only rank 0 uses
   the result. Fixed via `gather_state_dicts()` in `train.py`, using the modern
   `torch.distributed.checkpoint.state_dict` (DCP) helpers
   (`get_model_state_dict`/`get_optimizer_state_dict` with `full_state_dict=True`), called
   unconditionally by every rank before the `is_master`-gated disk write.

**A real bug hit and fixed, worth remembering:** FSDP2's default device-mesh auto-detection
probes for "the current accelerator" and picks MPS just because `torch.backends.mps.is_available()`
is True on this machine — regardless of the `gloo`/CPU backend actually initialized — and then
crashes (`torch.mps` has no `is_initialized()`, which the probe expects every accelerator module
to have). Fixed by constructing the `DeviceMesh` explicitly (`init_device_mesh(device.type, ...)`)
instead of letting `fully_shard()` guess. This is exactly the kind of Apple-Silicon-specific rough
edge you only find by actually running the thing, not by reading the docs.

**Verified for free, 2026-07-20, via `scripts/run_fsdp_local.sh 4` (CPU/gloo, 4 real
processes):** training loss decreased normally (10.84 → 10.35 over 30 steps); eval ran without
deadlocking (confirms the collective-forward fix); `best.pt` saved and — checked directly — its
tensor shapes are the **full, ungathered shape** (e.g. `blocks.0.mlp.fc_in.weight` = `(256, 64)`,
matching the single-process shape exactly, not a shard fragment), confirming DCP's gather is
correct; **resume worked**, including optimizer state (`set_optimizer_state_dict`), with the
same no-discontinuity property verified in Phase 1 (loss continued smoothly step 29→30 across
the restart). All of this on CPU with zero real sharding benefit (gloo has no real memory
pressure to shard away) — what's verified is *correctness of the collective logic*, not memory
savings or speed. Real memory-ceiling and speed numbers need actual multi-GPU hardware — see
Cloud budget.

**Known simplification, not fixed:** `gather_state_dicts` runs the full collective gather on
*every* eval step regardless of whether it turns out to be a new best (the decision is only
knowable after computing eval loss, by which point the collective already had to happen for
every rank to stay in sync). At 100B+ scale, eagerly all-gathering the full model to one rank
every eval step would be a real cost — production systems instead use fully sharded/parallel
checkpoint I/O (`torch.distributed.checkpoint.save`, each rank writes its own shard to storage
independently, no single-rank gather at all) or checkpoint less frequently. Worth revisiting if
this curriculum ever runs at a scale where it matters; not worth solving for a 30M-param model.

## Phase 4 — 3D parallelism + MoE/expert parallelism (tensor + pipeline + expert)

**Status:** tensor parallelism, pipeline parallelism, and MoE/expert-parallelism all implemented
+ numerically verified, 2026-07-21 — Phase 4 core is done. Only DualPipe's precise scheduling
algorithm is deliberately left as reading-only (see below). Next: Phase 5 (FP8) or Phase 6
(reliability/control plane).

**Tensor parallelism (`experiments/tensor_parallel_mlp.py`):** hand-rolled column-parallel +
row-parallel `nn.Linear` (Megatron's `f`/`g` autograd-function pattern: `f` = identity forward /
all-reduce backward, `g` = all-reduce forward / identity backward), applied to an MLP block.
Standalone, not wired into `src/train.py` — its only job is proving the sharded computation is
numerically identical to a single-device reference doing the same math unsplit. Verified via
free local CPU/gloo (`torchrun --nproc_per_node=4`): forward output, gradient w.r.t. input, and
gradient w.r.t. both weight matrices all match a single-device reference to ~1e-8 (float32
rounding noise from a different summation order, not a real discrepancy) — all 4 ranks PASS.
This is the correctness property that matters: at 100B+ scale you never have a spare single
device to check against, so the confidence has to come from having verified the *pattern* works
at small scale, not from checking each real run against a ground truth that doesn't exist.

**Pipeline parallelism (`experiments/pipeline_parallel_demo.py`):** used PyTorch's real
production API, `torch.distributed.pipelining` (`PipelineStage`, `ScheduleGPipe`,
`Schedule1F1B` — what TorchTitan uses), not hand-rolled send/recv. 4 stages, one toy
`Linear+ReLU` layer per rank. Verified via free local CPU/gloo:

- **Correctness**: gradients from both GPipe and 1F1B schedules matched a single-device
  reference running the same stacked layers unsplit, to ~1e-9.
- **A real, discovered constraint**: `Schedule1F1B` raises `ValueError` if
  `n_microbatches < num_stages` ("must be >= number of stages"); `ScheduleGPipe` has no such
  floor (just gets bubblier). Found by hitting it, not by reading docs first.
- **The bubble-fraction-vs-memory distinction, confirmed empirically**: GPipe and 1F1B showed
  near-identical wall-clock time at the same microbatch count (e.g. M=8: GPipe 5.19ms, 1F1B
  4.46ms) — because they have the **same** theoretical bubble fraction `(P-1)/(M+P-1)`. 1F1B's
  actual advantage is **peak activation memory** (≈P microbatches held at once vs GPipe's ≈M),
  not speed — a distinction worth having verified rather than just repeated, since a lot of
  secondary sources imply 1F1B is faster.
- **Honest limitation**: wall-clock time did not cleanly track the theoretical bubble-fraction
  curve as M increased (M=8 was slower than M=4 for both schedules) — at this toy scale
  (4 layers, 32-dim), gloo's per-microbatch point-to-point communication overhead over loopback
  dominates the actual compute, swamping the theoretical bubble-shrinkage signal. This would
  resolve on real hardware where compute >> communication latency, but is a genuine limit of
  what small-scale CPU simulation can show — a concrete instance of "conclusions from toy-scale
  distributed experiments don't always transfer to real scale," worth remembering generally.

**MoE + expert parallelism (`experiments/moe_layer.py`, `experiments/expert_parallel_demo.py`):**
implemented and verified in two layers:

1. **Single-device MoE routing** (`moe_layer.py`): router + top-k dispatch + DeepSeek-V3-style
   *auxiliary-loss-free* load balancing. The key mechanism: `expert_bias` is a **buffer, not a
   Parameter** — it steers which experts get selected but never appears in the loss or receives
   gradient, unlike the older Switch-Transformer/GShard approach of adding a load-balancing
   penalty to the training loss (which can conflict with the primary objective). Verified: an
   expert with zero tokens in a batch gets literally zero gradient (structurally, not just
   empirically — the `continue` in the dispatch loop never touches its parameters); after one
   step, the most-loaded expert's bias moved down and the least-loaded moved up, exactly as
   designed.
2. **Expert parallelism** (`expert_parallel_demo.py`): experts distributed across 4 ranks (2
   each), tokens dispatched via `all_to_all_single` to whichever rank owns their selected
   expert(s), computed there, results combined back. Verified against the single-device
   `MoELayer` computing the identical routing decision unsplit: all 4 ranks matched to ~1e-7.
   **Real backend gotcha found by hitting it**: the list-based `dist.all_to_all` does not
   reliably support ragged (different-size-per-rank) tensors on the `gloo` backend — errors
   with a tensor-size mismatch the moment two ranks send different amounts. Fix: `all_to_all_single`
   with explicit `input_split_sizes`/`output_split_sizes` handles variable sizes correctly. This
   isn't a toy inconvenience — it's a direct, small-scale instance of why MoE dispatch needs a
   real "how much am I about to receive from you" round-trip before the actual payload transfer
   (which is exactly what production dispatch kernels like DeepSeek's DeepEP are built around),
   unlike tensor parallelism's all-reduce or pipeline parallelism's point-to-point send/recv,
   both of which have a communication shape that's fixed and known ahead of time, not
   data-dependent.

**DualPipe — concept only, not implemented, confidence-graded honestly:** the *problem* DualPipe
solves is well-understood and stated with confidence above (MoE's two-all-to-all-per-layer
dispatch+combine has a much worse compute:communication ratio than dense pipeline parallelism,
so naively waiting on it wastes real time). The *precise scheduling mechanism* — the actual
bidirectional forward/backward chunk interleaving DeepSeek-V3 uses to hide that communication —
is deliberately not summarized from memory here beyond "chunks flowing through the pipeline in
both directions simultaneously so communication on some stages overlaps compute on others."
Read [DeepSeek-V3 Technical Report](https://arxiv.org/pdf/2412.19437) §3.2 directly for the real
schedule diagram rather than trusting a paraphrase — this is a case where the gap between
"paraphrased from a summary" and "actually understood from the source" matters, and implementing
a naive/wrong version of DualPipe would be worse than not implementing it at all.

*(Original planning notes below, retained for context.)*

**Revised 2026-07-20** after checking what's *actually* current (not just the 2019-2022 papers
below, which are the correct foundation but not the whole story anymore): dense-model 3D
parallelism (Megatron-style) is still the right thing to learn first, but **MoE + expert
parallelism is now how labs actually get past ~100B params efficiently**, not just bigger dense
3D-parallel models. DeepSeek-V3 (671B total / 37B active params) is trained with **16-way
pipeline parallelism + 64-way expert parallelism (8 nodes) + ZeRO-1 data parallelism**, and uses
**DualPipe** — a pipeline schedule that overlaps forward/backward compute with communication
*bidirectionally*, built specifically because cross-node expert-parallel all-to-all
communication in MoE has a much worse compute:communication ratio than dense-model pipeline
parallelism. This is a materially different (and newer) scheduling problem than the classic
GPipe/1F1B bubble problem below — worth treating as its own reading item, not a footnote.

**Reading list:**
- [Megatron-LM, Shoeybi et al. 2019](https://arxiv.org/abs/1909.08053) — tensor parallelism
  for transformers (splitting individual weight matrices across devices). **Do this first.**
- [Megatron-LM 3D parallelism, Narayanan et al. 2021](https://arxiv.org/abs/2104.04473) — how
  data + tensor + pipeline parallelism combine at GPT-3/PaLM scale.
- [PaLM paper, Chowdhery et al. 2022](https://arxiv.org/abs/2204.02311), §3 — the actual infra
  section describing how a 540B model was trained across two TPU v4 pods.
- [GPT-NeoX library](https://github.com/EleutherAI/gpt-neox) — a real, readable, open-source
  3D-parallel training codebase (built on Megatron + DeepSpeed) — read the code, not just the
  paper.
- [DeepSeek-V3 Technical Report](https://arxiv.org/pdf/2412.19437) — **read this after the
  above, not instead of.** §3.2 (DualPipe) and the expert-parallelism / cross-node all-to-all
  discussion are the 2024-2025 evolution past classic Megatron 3D parallelism.
- [PyTorch/TorchTitan blog: MXFP8 + DeepEP for DeepSeek-V3 on B200](https://pytorch.org/blog/enabling-up-to-41-faster-pre-training-mxfp8-and-deepep-for-deepseek-v3-on-b200-with-torchtitan/)
  — a real, current (2026) open reimplementation of this stack, worth reading as code.

**What "done" looks like:** a small (2-4 "device", CPU-simulated) hand-rolled implementation
of pipeline-parallel forward/backward with microbatching (the GPipe/PipeDream bubble problem),
enough to explain pipeline bubbles, 1F1B scheduling, why tensor parallelism needs
high-bandwidth interconnect (NVLink) while pipeline parallelism tolerates slower links, **and**
a written explanation (not necessarily code) of why MoE expert-parallelism's communication
pattern (all-to-all across nodes) is a different problem from dense-model pipeline/tensor
parallelism, and what DualPipe does about it.

## Phase 5 — Low-precision training (FP8 / MXFP8)

**Status:** implemented and verified (single-device, free), 2026-07-21. One originally-expected
dramatic result did NOT materialize on this hardware — reported honestly below, with the reason
worked out rather than hand-waved, which turned out to be the more valuable finding.

DeepSeek-V3 is the first large, openly-documented production model trained substantially in
**FP8** — both compute and storage — for real speed and memory wins, not just quantized
inference. The engineering problem is real: H800 Tensor Cores only have 14-bit FP8 accumulation
precision, so naive FP8 training loses accuracy. The fix was **fine-grained tile-wise/block-wise
quantization** (rescale in small blocks so outliers don't blow the dynamic range) plus promoting
accumulation to higher precision every 128 elements. **MXFP8** (microscaling FP8 — a shared
exponent per 32-element block) is the 2025-2026 refinement, with native hardware support on
NVIDIA Blackwell (as of March 2026).

**`experiments/fp8_quantization.py`** — no distributed anything here (single device, pure
numerics); FP8 tensor cores don't exist on CPU/MPS so this uses "fake quantization" (cast to
fp8, immediately back to fp32) — honest for studying rounding/dynamic-range error, not for
measuring real speed.

- **Part 1 (quantization error, naive per-tensor vs block-wise scale)**: built a weight tensor
  with injected outliers (40x typical magnitude, mimicking the documented "outlier feature"
  phenomenon in transformers — Dettmers et al. 2022, LLM.int8()). **Result, and it corrected a
  wrong intuition going in**: per-tensor scaling barely hurt "typical" values' relative precision
  (0.0226 → 0.0220 going to block-wise) — *not* what naive intuition predicts. Reasoning why:
  **FP8 is still floating point, not fixed point** — relative precision stays roughly constant
  across its representable range regardless of scale, *unless* values get pushed toward
  underflow. Checked directly: at this outlier ratio, typical values land around 11.6 in the
  rescaled range, nowhere near FP8's underflow floor (~0.002) — nowhere close to where the
  naive-intuition failure mode would actually bite. What block-wise scaling *did* measurably fix:
  the outliers' own reconstruction error (0.0224 → 0.0027, ~8x) — each outlier gets a scale
  sized to its own block instead of being stretched by unrelated far-away outliers.
- **Real bug found and fixed along the way**: initially chained `(x/scale).to(fp8).to(fp32)*scale`
  directly and called `.backward()` — the gradient this produces is NOT a clean 1.0
  straight-through estimator; it's an undocumented artifact that depends on `scale` (measured
  1.95 at scale=0.001 vs the correct 1.0 at scale=1.0, same logical operation). Fixed by
  implementing an explicit `torch.autograd.Function` with a proper STE backward (identity
  gradient) — the standard, correct quantization-aware-training technique (Bengio et al. 2013),
  not something to leave to whatever a cast operator's autograd formula happens to do.
- **Part 2 (does this matter for actual training?) — the honest, non-dramatic result**: with the
  STE fix in place, full-precision, naive-per-tensor-FP8, and block-wise-FP8 all trained to
  nearly identical loss curves in this toy setup. Worked out why rather than declaring
  "no effect": this is consistent with Part 1's finding (no underflow at this outlier ratio, so
  quantization error stays small and roughly uniform) — and it suggests DeepSeek-V3's actual
  documented pain point (§3.3, the 14-bit accumulation precision limit, fixed by promoting to
  CUDA-core accumulation every 128 elements) may matter *more* for real training quality than
  pure quantization-scale granularity. **That accumulation-precision problem is structurally
  unreproducible on CPU** — CPU matmul always accumulates internally in full fp32/fp64, so there's
  no way to simulate a hardware accumulator's limited precision without an actual FP8 tensor
  core. Flagging the boundary of what this kind of free/local experiment can and can't show,
  rather than overclaiming.

**Reading:** [DeepSeek-V3 Technical Report](https://arxiv.org/pdf/2412.19437) §3.3;
[To FP8 and Back Again, 2024](https://arxiv.org/pdf/2405.18710) (stability effects of reduced
precision — the failure modes, not just the happy path).

## Phase 6 — Reliability & control plane (fault tolerance, self-healing, observability)

**Status:** conceptual foundation + `torch.distributed.elastic` verified live, 2026-07-21.
torchft and DCGM/Prometheus/Grafana not implemented (need real GPU hardware for the latter;
torchft has no macOS wheel — `torchft-nightly` on PyPI ships `manylinux` x86_64 only, source
build needs a Rust toolchain — deferred to the eventual Linux cloud session rather than fighting
a source build on M4 for something being learned conceptually right now).

**torchft, grounded from the actual repo** ([meta-pytorch/torchft](https://github.com/meta-pytorch/torchft),
README fetched directly 2026-07-21, not paraphrased from a search snippet): the **Lighthouse
coordinator is a standalone Rust binary** (`torchft_lighthouse`), launched independently of any
training process — `torchft_lighthouse --quorum_tick_ms 100 --join_timeout_ms 10000` (100ms
heartbeat, 10s to join or you're considered failed). **Correction to how "replica group" was
described earlier**: a replica group is not "some ranks within one `torchrun` call" — it's an
entire *independent* `torchrun` invocation (potentially a different machine), pointed at the
shared Lighthouse via `TORCHFT_LIGHTHOUSE=http://host:port`. torchft coordinates fault tolerance
*across* these independent replica groups; `torch.distributed.elastic` (verified above) handles
membership *within* one. The two are complementary layers, not alternatives. Training code
barely changes — `Manager`/`DistributedDataParallel`/`Optimizer` wrapper classes absorb nearly
all the complexity, so a fault-tolerant training loop reads almost identically to a normal DDP
one. Algorithms provided: Fault Tolerant DDP, Fault Tolerant HSDP (replication dimension
fault-tolerant, any mix of FSDP/TP on the other dimensions), and (marked experimental) LocalSGD
and DiLoCo — DeepMind's low-communication-frequency training algorithm, which pairs naturally
with fault tolerance since infrequent synchronization means a single dropped replica matters
less. One detail worth remembering: checkpoint recovery can pull weights **live from a healthy
peer over the network**, not just from disk — skips the disk-I/O bottleneck that dominates
recovery time for large models.

**A four-level fault-tolerance taxonomy** (useful vocabulary, not just this project's framing):
Level 0 = no automation, a human notices and restarts manually. Level 1 = an external
supervisor (Slurm/k8s/`torchrun --max-restarts`) detects the crash and restarts the **whole
worker group**, relying entirely on checkpoint/resume to not lose progress. Level 2 =
`torch.distributed.elastic`'s true elastic mode, membership can shrink/grow via rendezvous
without necessarily killing everyone. Level 3 = torchft's per-step fault tolerance — surviving
replicas never pause at all; this is the only one that's actually "self-healing" in the sense of
making progress *through* a failure, not just recovering *after* one.

**Verified Level 1 for real** (free, local): launched `torchrun --nnodes=1 --nproc_per_node=4
--max-restarts=2` training, then `kill -9`'d one of the 4 worker processes mid-run (step 130) to
simulate a hard hardware failure. Observed exactly what the taxonomy predicts: the elastic agent
detected the death within ~40ms, sent SIGTERM to all 3 *surviving* workers (confirms the "whole
group" granularity — it doesn't try to save the healthy ones), respawned 4 fresh processes, and
training resumed from the last checkpoint (step 100) with no manual intervention. This is the
concrete mechanism behind "Llama 3 405B had 419 unexpected interruptions over 54 days and kept
training anyway" — not magic, just this loop running automatically, over and over.

**A real finding from that same test, honestly reported, not smoothed over:** the resumed run's
loss at step 110 (8.0846) differed from the original run's step-110 loss (8.1602) — small, no
instability, but a real discrepancy. Cause: the Phase 1 README claimed checkpoints saved "RNG
state," but they never did (`utils.py` only ever saved model/optimizer/step). `seed_everything`
reseeds fresh from `seed+rank` on every process start rather than resuming a saved generator
state, so a resumed run samples a *different* sequence of random batches than an uninterrupted
run would have — no discontinuity in the loss curve (verified, real), but not bit-exact data-order
reproducibility (never verified, and the docs incorrectly implied it was). Corrected in the
Phase 1 section above rather than quietly editing the original claim away.

*(Original planning notes below.)*

**This is the part standard distributed-training tutorials skip
entirely, and it's the part that most directly matches "research infrastructure / ML platform
engineering" as a job description rather than "I can write a training loop."**

**Why this phase exists:** Meta's Llama 3 405B training run had **419 unexpected interruptions
over 54 days** (~1 every 3 hours), 78% attributed to hardware failures (GPU faults, HBM3
issues). Synchronous training (DDP/FSDP) means one dead GPU can stall or kill the entire job —
at 100B+ scale with thousands of GPUs, hardware failure isn't an edge case, it's the steady
background condition you design around. "Can this training run survive its own hardware" is a
distinct engineering problem from "is this training loop mathematically correct," and it's the
one this phase is about.

**Concrete systems to study (all real, all current as of 2026):**
- [**torchft**](https://github.com/meta-pytorch/torchft) (Meta/PyTorch) — per-step fault
  tolerance: when a replica dies, the survivors keep training uninterrupted; the dead replica
  restarts and rejoins later, coordinated by a "Lighthouse" server. As of Feb 2026, integrated
  with TorchTitan on AMD's Primus-SaFE for checkpoint-less resilient training at 100-GPU scale.
  This is the direct, hands-on-installable version of "self-healing."
- [**Google Pathways**, Barham et al. 2022](https://arxiv.org/abs/2203.12533) — the clearest
  real **control plane** architecture, and NOT solving the same problem as torchft (checked the
  actual paper text, 2026-07-21, not just a summary — see below). What Gemini is trained on.
  **Correction to an earlier overstated claim in this file:** the paper does *not* dwell on fault
  tolerance mechanisms much (the only concrete FT-adjacent detail: objects are ownership-tagged
  so they're garbage-collected if a client fails) — its real contribution is the
  **single-controller** execution model itself, not fault tolerance per se. Read for the
  *architectural idea* (single-controller async dataflow) even without TPU access.
  [torch.distributed.elastic](https://docs.pytorch.org/tutorials/beginner/ddp_series_fault_tolerance.html)
  is the much smaller-scoped PyTorch-native analog worth actually running.
- **GPU-level observability**: NVIDIA DCGM → `dcgm-exporter` → Prometheus → Grafana is the
  actual production stack (not homegrown) — structurally the same "structured metrics →
  time-series store → dashboard/alerting" pattern as `scripts/make_dashboard.py` from Phase 1,
  one layer down (hardware telemetry instead of loss/grad-norm). Worth standing up for real —
  see plan below.
- Skim for landscape, not depth: [PHOENIX (2026)](https://arxiv.org/pdf/2607.01646) — hot-swap
  recovery via zero-overhead checkpointing; [TrainMover](https://uccl-project.github.io/posts/continuum-blog/)
  — cuts failure-recovery time to ~20 seconds by migrating rather than restarting.

**Multi-controller (SPMD) vs single-controller — the real axis Pathways and torchft sit on
opposite sides of.** Quoting the actual paper text (fetched 2026-07-21, not a secondhand
summary): multi-controller systems (MPI, PyTorch DDP/FSDP, torchft — **everything hand-built in
this project**) mean "any communication beyond standard collectives ... requires users to
implement their own coordination primitives." That sentence describes exactly what this whole
Phase 4 was: hand-writing the `f`/`g` autograd functions for tensor parallelism, hand-fixing
FSDP's eval/checkpoint collective-safety, hand-writing expert-parallel dispatch/combine — none
of that coordination is provided for free under SPMD, which is why it took real code each time.
Pathways' single-controller alternative — one client program, not replicated per-worker — is
built specifically so that patterns like pipelining or sparse (MoE) computation don't require
that hand-written coordination, and additionally enables cluster-level resource *sharing*
(multi-controller "typically assumes exclusive ownership of hardware resources" — one job, one
fixed set of machines, for its whole lifetime; single-controller enables finer-grained,
dynamically shared allocation). torchft doesn't compete with this — it's a fault-tolerance layer
bolted onto the existing multi-controller model PyTorch already uses, not a replacement for it.
Crude analogy: torchft is "add a supervisor that restarts your existing independent processes
when they die"; Pathways is "redesign the process model so a global scheduler can place and
migrate any computation anywhere."

**Other production-grade tools worth knowing (landscape, not all hands-on yet):**
- **TorchTitan** (Meta) — the real, open-source reference implementation using everything built
  in this project (FSDP2, `torch.distributed.pipelining`, torchft) at actual pretraining scale.
  The single most directly useful next read: `src/train.py` next to TorchTitan's equivalent,
  line by line, to see what a "grown up" version handles that ours doesn't.
- **DeepSpeed** (Microsoft) — the other major ZeRO implementation (FSDP is PyTorch's native
  version); adds ZeRO-Infinity (NVMe offload when even sharded state doesn't fit in GPU memory),
  DeepSpeed-MoE, RLHF pipelines.
- **Megatron-Core** (NVIDIA) — not just the paper, an actively-maintained production 3D-parallel
  library; NVIDIA's NeMo framework is built on it.
- **NCCL** (NVIDIA) — the real communication library GPU clusters use (gloo, used throughout
  this project, is its free/CPU-friendly stand-in); ring/tree collective algorithms,
  NVLink/InfiniBand topology-aware.
- **Slurm**, **Kubernetes + Kubeflow's PyTorchJob** — the control-plane/scheduling layer under
  real clusters; `torchrun --max-restarts` is a small taste of what these do at job-management
  granularity.
- **Ray / Ray Train** — a genuinely different paradigm from SPMD: actor-based distributed
  computing, not "N copies of the same script coordinating via collectives." Worth knowing as a
  third point of comparison alongside SPMD and Pathways' single-controller model.
- **vLLM / SGLang** — production LLM *inference* serving (PagedAttention, continuous batching,
  speculative decoding) — adjacent to training, and "ML platform engineering" job descriptions
  often span both.
- **Weights & Biases / MLflow** — the real, hosted version of `scripts/make_dashboard.py`;
  complements DCGM (hardware layer) rather than competing with it (experiment/metrics layer).

**Plan:**
1. Run `torch.distributed.elastic` locally (`torchrun --nnodes=1:2 --max-restarts=3`) and kill a
   worker process mid-training on purpose — watch it actually recover, not just read that it can.
2. Stand up `nvtop` or `dcgm-exporter` + a local Prometheus/Grafana against whatever GPU is
   running Phase 2+ cloud experiments — a real (if small) instance of the production monitoring
   pattern, not a slide about it.
3. Read `torchft`'s design closely enough to explain: what does "per-step fault tolerance" cost
   in normal-case overhead, and why is that trade worth it at 1000+-GPU scale but not at 4-GPU
   scale (this is a judgment question interviewers actually ask).

**What "done" looks like:** you can explain, with a concrete example from something you ran
(even the local elastic-restart test), the difference between "fault tolerance" (job survives a
failure, possibly with a pause) and "self-healing" (job keeps making progress *through* a
failure) — and why frontier labs increasingly care about the latter as cluster size grows
(recovery speed, not raw FLOPs, becomes the bottleneck once failures happen every few hours).

## Phase 7 — JAX track (optional, if targeting DeepMind-style labs)

**Status:** not started. Re-implement Phase 1-3 in JAX using `jax.experimental.shard_map` /
`pjit` and a device mesh, to build the equivalent muscle memory for the JAX ecosystem.
[JAX's own scaling guide](https://jax.readthedocs.io/en/latest/notebooks/Distributed_arrays_and_automatic_parallelization.html)
and the [GDM Gemma / T5X codebases] are the reference points.

## Cloud budget

**Revised 2026-07-20: total budget for this entire project is ~$30**, not $50/session — this is
a learning project, not production training, and Long doesn't want to spend more than that on
it overall. Working approach:

- **Default to free verification.** Where a phase's correctness (not speed) can be checked with
  a local CPU/gloo multi-process simulation — like Phase 2's DDP test — do that instead of
  renting anything. This covers correctness of most of Phase 2-4's *logic*; it just can't show
  real speedup or real memory-ceiling numbers.
- **For anything that genuinely requires real GPU hardware** (real DDP/FSDP speedup and memory
  numbers, real FP8 tensor cores, real multi-node networking): write the experiment code and a
  clearly reasoned **expected outcome** (from the underlying math/papers), and hold off running
  it. Flag it clearly as "written, not run" in the log below.
- **Spend the $30 in one deliberate batched session, not piecemeal** — rent one multi-GPU box
  once, run several of the "written, not run" experiments back to back in that single rental
  (e.g. DDP speedup + FSDP memory ceiling in the same session), then tear down. More signal per
  dollar than renting separately for each phase. Decide exactly when to do this together before
  spending anything, and confirm actual estimated cost first regardless of the $30 ceiling.

## Log

### 2026-07-21 (6)
- **Phase 5 (FP8) implemented and verified** — `experiments/fp8_quantization.py`, single-device,
  no distributed anything. Full honest account in the Phase 5 section above; short version: (1)
  block-wise quantization measurably fixes outlier-element reconstruction error (~8x) but barely
  touches "typical" values' error, contradicting the naive intuition going in — because FP8 is
  floating point, not fixed point, so relative precision doesn't degrade with scale until you
  hit underflow, which this outlier ratio doesn't reach; (2) found and fixed a real bug — naively
  chaining `.to(fp8).to(fp32)` through a scale division gives an undocumented, scale-dependent
  gradient, not a clean straight-through estimator — fixed with an explicit
  `torch.autograd.Function`; (3) with that fix, naive-vs-block-wise FP8 trained a toy model
  nearly identically — a real, non-dramatic result, reasoned through rather than forced into a
  neater story, and it points at DeepSeek-V3's actual accumulation-precision problem (not
  quantization granularity) as the more likely dominant factor, which is structurally
  unreproducible without real FP8 hardware. **All six planned phases (1-6) now have at least a
  verified core implementation.** Remaining real-hardware work (Phase 2/3 speed+memory numbers,
  DCGM observability, torchft) stays deferred to the batched cloud session per the $30 budget.

### 2026-07-21 (5)
- **Corrected an overstated claim from the previous entry**: fetched the actual Pathways paper
  text (ar5iv, not a secondhand summary) — it does not dwell on fault tolerance the way the
  earlier note implied; its real contribution is the single-controller execution model.
  Grounded the multi-controller (SPMD) vs single-controller distinction precisely, and connected
  it directly to this session's own work: the paper's line about multi-controller systems
  needing users to "implement their own coordination primitives" beyond standard collectives is
  a precise description of what Phase 4's tensor/pipeline/expert-parallel implementations
  actually required by hand. Also added a broader landscape of production tools (TorchTitan,
  DeepSpeed, Megatron-Core, NCCL, Slurm/Kubeflow, Ray, vLLM/SGLang, W&B/MLflow) — see Phase 6
  section. Next natural step if pursued: read TorchTitan's real source next to this project's
  `src/train.py`, since it's the most direct "grown-up version" of everything built here.

### 2026-07-21 (4)
- Grounded the torchft explanation against the actual repo (`gh api repos/meta-pytorch/torchft/readme`)
  instead of relying on the earlier web-search summary — corrected the "replica group" framing
  (an independent `torchrun` invocation, not ranks within one), confirmed Lighthouse is a
  standalone Rust binary, and found the live-peer-recovery and DiLoCo/LocalSGD details. Also
  confirmed `torchft-nightly` has no macOS wheel (Linux x86_64 only) — hands-on deferred to the
  Linux cloud session. Also clarified: "Pathways" (Phase 6, Google) is a proper noun — the
  specific named system from Barham et al. 2022, not a generic term.

### 2026-07-21 (2)
- **Phase 4 core complete: MoE + expert parallelism** implemented and verified (see Phase 4
  section above) — single-device routing/top-k/auxiliary-loss-free load balancing
  (`moe_layer.py`), then experts distributed across 4 ranks with real `all_to_all_single`
  dispatch/combine (`expert_parallel_demo.py`), matched a single-device reference to ~1e-7. Hit
  and fixed a real gloo-backend limitation (list-based `all_to_all` doesn't support ragged
  tensor sizes; `all_to_all_single` with explicit split_sizes does) — a small, concrete instance
  of why MoE's data-dependent communication pattern needs different plumbing than tensor/
  pipeline parallelism's fixed-shape collectives. DualPipe's precise schedule deliberately left
  as reading-only (paper §3.2), not paraphrased from memory — see Phase 4 section for the
  reasoning. **This closes out Phase 4's core implementation work.**

### 2026-07-21 (3)
- **Phase 6 teaching session** (concept-first, per how this session works best): control plane
  vs data plane distinction, a four-level fault-tolerance taxonomy (Level 0 manual → Level 1
  external-supervisor whole-group restart → Level 2 elastic membership → Level 3 torchft
  per-step self-healing), torchft's Lighthouse/quorum mechanism and its real cost/benefit
  tradeoff by cluster size, and the DCGM→Prometheus→Grafana observability stack (explicitly
  mapped onto our own Phase 1 `make_dashboard.py` as the same pattern one layer down). See Phase
  6 section above for detail.
- **Live-verified Level 1** for real: killed a worker mid-training with `kill -9`, watched
  `torchrun`'s elastic agent detect it, kill the survivors, respawn, and resume from checkpoint
  automatically — and in the process **found and corrected a real documentation overclaim**
  (Phase 1's README said checkpoints saved RNG state; they never did). See Phase 6 section for
  the full account. A good example of why actually running things surfaces things reading/
  writing the plan doesn't.

### 2026-07-21
- Deep-dive teaching session on Phase 3 (FSDP), no new implementation — walked through the
  ZeRO/FSDP memory math with concrete numbers (30M model: 480MB "model state" at 16 bytes/param;
  100B model: 1.6TB, doesn't fit on any single GPU, which is *why* FSDP isn't optional past a
  certain scale), and ran a live demo confirming DTensor sharding empirically (each of 4 ranks
  held exactly 25.0% of parameters; a `(1536, 384)` weight's local shard was `(384, 384)`).
- **Phase 4, pipeline parallelism** implemented and verified too (see Phase 4 section above) —
  `torch.distributed.pipelining` (GPipe + 1F1B schedules), correctness matched a single-device
  reference to ~1e-9, and empirically confirmed the easy-to-misremember fact that 1F1B's real
  advantage over GPipe is peak memory, not speed (same measured wall-clock at the same
  microbatch count, matching the shared bubble-fraction formula). Next: MoE/expert parallelism +
  DualPipe, the last piece of Phase 4.
- **Phase 4 started: tensor parallelism**, implemented and numerically verified (see Phase 4
  section above) — column/row-parallel Linear layers with the Megatron `f`/`g` autograd-function
  pattern, checked against a single-device reference to ~1e-8. Free, local, CPU/gloo.
- Next: pipeline parallelism (microbatching, bubble problem, 1F1B), then MoE/expert parallelism
  + DualPipe.

### 2026-07-20 (4)
- **Budget note**: Long capped total cloud spend for this project at ~$30 (see Cloud budget
  above) — shifted approach to prioritize free local verification and writing-but-not-running
  real-GPU experiments, batching actual cloud spend into one deliberate session later.
- **Phase 3 (FSDP2) implemented and fully verified for free** via `scripts/run_fsdp_local.sh`
  (CPU/gloo, 4 real processes) — training, eval, best/periodic/final checkpoint save, and resume
  (with optimizer state) all round-trip correctly. Required real, non-cosmetic changes beyond
  Phase 2's DDP code: optimizer construction moved to a post-wrap module-level function
  (`build_optimizer` in `model.py`), eval's forward pass made collective-safe (runs on every
  rank, not just master — FSDP's all-gather requires it), and checkpoint state-dict gathering
  made collective-safe via `torch.distributed.checkpoint.state_dict` (DCP) helpers. Also hit and
  fixed a real Apple-Silicon-specific bug: FSDP2's default device-mesh autodetection crashes by
  trying to use MPS just because it's *available*, regardless of the actual backend in use —
  fixed with an explicit `DeviceMesh`. Full narrative in the Phase 3 section above.
- Real multi-GPU memory-ceiling/speed numbers for both DDP (Phase 2) and FSDP (Phase 3) are
  **written but not run** — need actual GPU hardware, deferred to the batched cloud session.

### 2026-07-20 (3)
- **Phase 2 started: ran real DDP for the first time** — `scripts/run_ddp_local.sh 4` (=
  `torchrun --nproc_per_node=4 src/train.py --device cpu`), 4 real processes, `gloo` backend
  (CPU-only, since gloo has no MPS collective support — added a `--device` override to force
  CPU for this test regardless of MPS availability). Confirmed `world_size=4` in the log, loss
  decreased smoothly (10.84 → 10.20 over 40 steps) with no NaN/hang, and — the actual
  correctness signal — **only rank 0 emitted eval/checkpoint log lines**, meaning the
  `is_master` gating that was only ever exercised at `world_size=1` before now works correctly
  with real concurrent processes.
- **Hit and fixed a real macOS/gloo gotcha**: the default `torchrun` rendezvous address
  (`localhost`) triggers a reverse-DNS (PTR) lookup for `::1` that hangs/retries for minutes on
  macOS if no PTR record is configured — visible as repeated `[c10d] The IPv6 network addresses
  of (1.0.0.127.in-addr.arpa, ...) cannot be retrieved` warnings with growing backoff. Fix:
  pass `--master_addr=127.0.0.1` (an IP literal, so no DNS lookup happens) instead of the
  hostname default. Baked into `scripts/run_ddp_local.sh`.
- **What this did *not* yet verify**: real speedup (CPU contention across 4 processes on one
  machine means no speedup is expected or observed) and NCCL (only exercised gloo — nccl needs
  real CUDA GPUs, next up is a real cloud multi-GPU box).

### 2026-07-20 (2)
- Revised the Phase 2-7 roadmap after explicitly checking (web search, not memory) what's
  current in production at frontier labs as of mid-2026, prompted by wanting to confirm this
  curriculum teaches SOTA production technique, not a textbook-frozen 2019-2022 snapshot.
  Changes: Phase 4 now explicitly covers MoE/expert-parallelism + DualPipe (DeepSeek-V3) on top
  of classic Megatron 3D parallelism; new Phase 5 (FP8/MXFP8 training); new **Phase 6
  (reliability & control plane)** covering torchft (per-step fault tolerance), Google Pathways
  (single-controller control plane, what Gemini trains on), and DCGM/Prometheus/Grafana GPU
  observability — this phase didn't exist before and directly matches "research infrastructure /
  ML platform engineering" job-description language rather than generic distributed-training
  tutorials. JAX track renumbered to Phase 7.
- Also covered, this session: local monitoring — `top` for CPU (no sudo), `sudo powermetrics`
  or `asitop` for Apple Silicon GPU (no `nvidia-smi` equivalent on M-series), `nvidia-smi`/
  `nvtop`/DCGM for cloud NVIDIA GPUs later.

### 2026-07-19
- Project created: `model.py` (from-scratch GPT-2), `data.py` (memmap dataset), `utils.py`
  (DDP bootstrap, checkpointing, logging), `train.py` (DDP-ready training loop), tiny-Shakespeare
  data prep, `sample.py` (generation script).
- Verified on M4 MPS: 10-step smoke test, then verified **checkpoint resume has no loss-curve
  discontinuity** (killed at step 9, resumed to step 14, loss continued smoothly:
  10.6748 → 10.6271, no jump). This was the single property most worth testing per the Phase 1
  goals above, and it worked on the first real attempt.
- Ran the real Phase 1 training: 30M-param GPT (6 layer, 6 head, 384 dim, block_size 256),
  3000 steps, ~28-31k tok/s throughout, ~30 min wall clock on M4 MPS.
- **Result — train loss 10.9 → 0.81, but val loss 6.47 → 6.70 (got *worse* over the second half
  of training).** This is overfitting, and it's the expected outcome, not a bug: tiny-Shakespeare
  is ~304K train tokens; at ~16K tokens/step × 3000 steps ≈ 49M tokens seen, that's roughly
  **160 epochs** over the same 300K tokens. A 30M-parameter model has more than enough capacity
  to memorize a corpus that small many times over. Generation confirms it — prompting `"ROMEO:"`
  produces fluent, structurally correct Shakespeare-format dialogue
  (`ROMEO:\nI do repent me.\n\nJULIET:\nDo not read by, if thou mayst stand there...`) that reads
  well but is likely partially reproducing memorized spans rather than generalizing.
- **This is deliberately left as-is rather than "fixed" immediately** — the point of Phase 1 was
  the infra (does checkpointing work, does the loop run, is throughput sane), not achieving a
  good val loss on a toy dataset. The overfitting is itself a useful, correctly-diagnosed result.
- Built `scripts/make_dashboard.py`: turns a `train.py` JSONL log into a self-contained HTML
  dashboard (loss curves, LR schedule, grad norm, throughput) with hover tooltips — a minimal
  from-scratch version of what wandb/TensorBoard automate at scale. Confirmed the overfitting
  visually: val loss **bottoms at step 500 (4.72) and rises monotonically after that** while
  train loss keeps falling — real generalization stopped 1/6 of the way through the run.
- **Found and fixed a real infra bug this exposed:** `save_checkpoint`'s "keep last N" pruning
  policy had already deleted the step-500 checkpoint by the time training finished — the only
  checkpoints left on disk (steps 2000/2500/2999) were all *worse* than the one that actually
  generalized best. "Can I resume after a crash" and "which checkpoint should I deploy" are
  different questions and were wrongly served by the same mechanism.
- **Fix:** added `save_best_checkpoint`/`load_best_meta` (`utils.py`) — a `best.pt` +
  `best_meta.json` tracked independently of the rolling/pruned checkpoints, updated whenever
  eval val loss improves. Added early stopping to `train.py` (`early_stop_patience=4`): stop
  once val loss hasn't improved in 4 consecutive evals, with a `dist.broadcast` so all DDP ranks
  agree to stop together (not exercised yet under real DDP, but wired correctly for when it is).
- **Reran as `shakespeare_gpt_v2` with the fix.** Result: best val loss 4.7187 at step 500
  (matches the v1 diagnosis exactly), then no improvement through evals at 750/1000/1250/1500 →
  **auto-stopped at step 1500**, half the compute of the v1 run, with `best.pt` correctly pinned
  to step 500. Confirms the fix works end to end, not just in a unit-test sense.
- **Honest caveat, not smoothed over:** sampling from `best.pt` (step 500) reads *less* fluent
  than sampling from the v1 overfit checkpoint (step 2999) — some garbled tokens, rougher
  grammar. Lower val loss is a better proxy for generalization, but on a corpus this tiny
  (304K tokens) "generalizes better" doesn't automatically mean "sounds better" to a human
  reader — the checkpoint that memorized more of actual Shakespeare reads more like Shakespeare.
  This is a real instance of the general lesson that loss is a proxy objective, not the thing
  you actually care about — worth remembering before trusting a val-loss number uncritically at
  any scale.
- Interactive dashboards (v1, before the fix; v2, after):
  [`analysis/shakespeare_gpt_v1_dashboard.html`](analysis/shakespeare_gpt_v1_dashboard.html),
  [`analysis/shakespeare_gpt_v2_dashboard.html`](analysis/shakespeare_gpt_v2_dashboard.html).

**Phase 1 is done.** Next: Phase 2 (DDP) — first exercise the `is_ddp` code path for real via
`torchrun --nproc_per_node=4 src/train.py` locally (CPU/gloo backend, free), then a real
multi-GPU cloud run.
