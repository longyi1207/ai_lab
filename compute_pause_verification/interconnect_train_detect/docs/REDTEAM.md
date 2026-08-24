# H2: NVML red-team track — design, citations, limitations

**Status (2026-08-17, updated):** pipeline built and validated end-to-end on
synthetic telemetry (`configs/redteam_smoke.yaml`, no GPU needed). Real
hardware access is now confirmed: **2026-08-21 (morning PT) – 2026-08-23**,
one Azure ML Compute Instance (SSH-enabled, not a raw VM), 8x NDm A100 v4
(`Standard_ND96amsr_A100_v4`), region **Italy North** — RG
`scfx-italynorth`, workspace `scfx-ws-italynorth`, same subscription
(`27ad7138-...`). This is a **shared box**: `shortcut_forensics` and
`theory-of-mind`/`empathy` are running on the same node concurrently, split
via `CUDA_VISIBLE_DEVICES` (proposed, not final: ICTD gets GPUs 3-5). See
"Shared-box operation" below — this superseded the original plan of a
dedicated `infra/azure/terraform` VM in `IncidentFox`/`eastus` for *this*
window; that Terraform module is kept as a reference for a possible future
dedicated deployment, but is not what to use for Aug 21-23.

## Findings summary as of 2026-08-22 19:00 UTC (read this first, details below)

16 rounds of real-hardware hardening (0-15) plus a dedicated false-positive
check and fix, all on GPUs 3-5 of the shared box. Full blow-by-blow in the
dated sections below; this is the compressed version.

**The core result**: a classifier using only NVML telemetry (power,
memory, utilization — no code/data access) can be hardened, cheaply and
fast, against every evasion mechanism tried across 16 rounds of real
adversarial iteration:

| axis tried | result | rounds |
|---|---|---|
| Communication shape (chunk size, sync frequency, composites) | Evaded once (round 0, undefended). After one fold-in, EVERY subsequent variant caught with escalating confidence (0.8→1.0) — the classifier learned "unusual comm pattern" itself as a positive tell, so more disguise = more confident, not less | 0-9, 12-13 |
| Memory (SGD replacing AdamW, gradient checkpointing) | Partial success — the only axis that ever got close to real evasion. Round 8: mean P(training)=0.586 (near coin-flip). Round 15 (cleaner method, lower memory delta than round 8): 0.777 — caught more confidently once the classifier had seen more memory-focused attempts | 8-9, 15 |
| Extreme parameter values (batch=1/seq=128, idle-gap duty cycling) | Backfired — pushed mean power to 133-199W/153W, outside the 239-351W range the original benign+adversarial baseline established (round 2's 170.8W, caught later, shows this band isn't a strict universal floor either — see "Rounds 10-11" for the correction). Read as "left the region where the classifier's judgment means anything," not "harder to evade" | 10-11, 14 |
| Different mechanism, same effect (gradient accumulation vs diloco) | Confirms the classifier learned a genuine mechanism-agnostic pattern, not a diloco-specific signature — grad_accum caught even more confidently (0.996-0.997) than diloco itself | 12-13 |

**The other real result, arguably the most consequential**: the classifier
also produces **false positives on legitimate traffic** — heavier-than-
baseline but genuinely benign inference (bigger batch, longer context)
was misclassified as training with 81-82% confidence, because inference's
memory footprint scales with batch×context just like training's does —
this project's `infer_dp`/`infer_tp` workloads have **no KV-cache at all**
(their `generate()` recomputes a full forward pass every step), so both
training and inference here share the exact same activation-memory
scaling law; inference just never adds training's extra
gradient/optimizer-state memory on top (see "False-positive check" below
for the full mechanism and its external-validity caveat against real
KV-cached inference engines) — and the benign training corpus never
included large-scale inference. A first
fix (folding in 3 negative examples) looked clean on the two points it was
tested against — **but this was an illusion of a properly-powered result,
not one**: a follow-up boundary sweep (12 well-powered points, corrected
after an initial labeling-bug false start) showed the "fixed" classifier
still false-positives on several nearby, never-folded-in points — 9/9
windows for batch=16/seq=512, 9/9 for batch=8/seq=1024, 10/10 for
batch=8/seq=3072, and majority-false-positive on 3 of 4 tensor-parallel
points **including the tp axis's own true training-distribution baseline**
(1/2 windows). Root cause, confirmed by direct feature inspection: the
"fixed" classifier's entire negative class was **39 windows across only 6
distinct configs** (vs. 263 positive windows across 16 adversarial
rounds) — and the *entire tensor-parallel axis* was represented by just
**2 windows total**. Not enough to define a real boundary; a `class_weight
="balanced"` RandomForest can't compensate for a diversity gap, only a
raw-count one. A **second fix** broadened the negative corpus using this
sweep's own 12 points (~12 distinct configs, 108 negative windows total,
real tp diversity) and retested on **6 brand-new points never executed
before** — all 6 read correctly low (0.01-0.41), and all 16 prior
adversarial rounds still hold at accuracy=1.000 (zero regression). One of
the 6 (`b12/s512`, 0.409) sat close enough to the 0.5 line to need a
follow-up: **4 fresh replicates** of that exact point (no fixed random
seed in these workloads, so reruns are genuine independent samples) came
back 0.41/0.23/0.14/0.15 (mean 0.232) against a confidently-correct
control point's 0.023/0.019/0.015 (mean 0.019) — the original 0.409 was
the noisy high tail of a distribution whose mean is safely below
threshold, not a hidden second gap. Real, replicated, honestly-scoped
progress: closed the specific gap this campaign found, not a claim that
false positives are impossible everywhere. See "Second false-positive
fix" and "Statistical replication" below for the full results.

**Real infra lessons** (3 code bugs fixed + tested, 2 operational lessons
learned the hard way): a labeling gap that silently produced empty
training data for unrecognized names, caught twice — once in the feature
layer (`_label_from_name` needs `"train"`/`"infer"` as a name substring,
not just the `kind` field) and once by extension in the boundary sweep's
own workload names, which cost ~19 real GPU-minutes before being caught
and fixed; a chained-resume bug that couldn't find early rounds' data
after resuming from a resume; a stale rc-file false-failure-signal; and at
least one confirmed case of a background job dying silently mid-run from
something external to this project (see `/mnt/SHARED.md`,
2026-08-22 16:31 UTC) that cost ~3 GPU-minutes and required re-running.

**What hasn't been tried**: a real HF model (deprioritized — everything
above is on the small synthetic "tiny" backend); statistical replication
of the 16 adversarial rounds themselves (still single-run each, no error
bars — only the one flagged false-positive boundary point got a
replicated check); an evasion that touches BOTH memory and the temporal/duty-cycle axis
without the OOD confound round 14 hit; a benign corpus broad enough to
make a real, principled claim about where the false-positive boundary
sits (the second fix, below, is a step in that direction, not a final
answer); re-testing the false-positive finding against a real KV-cached
inference engine — this project's `generate()` has no KV-cache at all
(recomputes a full forward pass every step), so the false-positive
boundary measured here is driven by the same activation-memory scaling
law training uses, not by KV-cache growth as an earlier draft of this doc
claimed (see the correction under "False-positive check" below) — and
should not be assumed to transfer to a real inference stack (vLLM, TGI)
without checking; four specific untested evasion vectors that are more
realistic than most of what actually got tested — mixed-precision (bf16/fp8)
activations, LoRA/adapter fine-tuning, activation offloading to CPU, and
sequence/activation-parallel sharding across GPUs — recorded in priority
order under "Untested evasion vectors worth flagging" near the end of this
doc rather than left as a vague gesture.

## Shared-box operation (Aug 21-23 Italy North window)

- **Do not run `infra/azure/scripts/launch.sh`** for this window — it
  provisions a brand-new VM via this project's own Terraform, in the wrong
  subscription context (`IncidentFox`/`eastus`) entirely. The actual node
  is created once by `shortcut_forensics`' `infra/launch_aml.sh` and shared.
- Once connection details exist (host/port/user/key — not available until
  the compute instance is created), run:
  `infra/azure/scripts/join_shared_box.sh <host> <port> <user> <key>` (or
  `--from-env <path-to-shortcut_forensics'-own-.active/<run_id>.env>`) —
  this writes `infra/azure/.active/node.env` in the format
  `bootstrap.sh`/`sync.sh`/`run.sh`/`pull.sh`/`status.sh`/`ssh.sh` already
  expect, so the rest of this project's tooling works against the shared
  box unmodified. Then: `./bootstrap.sh && ./sync.sh`.
- **GPU isolation is not automatic.** NVML (used by
  `src/redteam/telemetry.py:NVMLTelemetrySource`) sits below the CUDA
  runtime and does not respect `CUDA_VISIBLE_DEVICES` on its own — polling
  "all GPUs" on this shared box would mix other tenants' workloads into
  ICTD's trace. `configs/azure_redteam_single_node.yaml`'s
  `telemetry.gpu_indices` (or the `ICTD_GPU_INDICES` env var, which takes
  priority and doesn't require editing/re-syncing the config — useful since
  the split is explicitly not final yet) must be set correctly, and
  `run_redteam.py` also uses it to set `CUDA_VISIBLE_DEVICES` before
  launching `torchrun`, since `LOCAL_RANK` alone would otherwise bind to
  physical GPUs 0..nproc-1 regardless of which GPUs are actually this
  project's. `run_redteam.py` raises an error before running anything if a
  workload's `nproc` exceeds the number of assigned GPUs.
- `nproc`/`tp_size` in every workload in `configs/azure_redteam_single_node.yaml`
  are set to 3 to match the proposed 3-GPU slice — keep them consistent
  with whatever the final reconciled split turns out to be.
- Reservation end (`2026-08-23`, hard cutoff) matters more than the usual
  budget-driven `autodestroy.sh` — this project doesn't own the compute
  instance's lifecycle on a shared box, so it can't unilaterally destroy it
  early or extend it late; coordinate teardown timing with the other two
  projects and whoever runs `shortcut_forensics`' teardown.
- **`/mnt` is Azure ephemeral temp disk, not persistent storage** — confirmed
  via `/mnt/EPHEMERAL_DISK_DATALOSS_WARNING.txt` on the box: subject to loss
  with no recovery, can be wiped even while running, not just on
  deallocation. `join_shared_box.sh` defaults `REMOTE_DIR` to `/mnt/...`
  anyway (it's still the right fix for the earlier root-disk-full problem —
  code+venv there is fine, cheap to rebuild via `sync.sh` if lost), but
  `bootstrap.sh` now also creates `/home/<user>/<project>_outputs` on the
  OS disk (persistent) and symlinks `$REMOTE_DIR/outputs` to it — so
  `output_dir: outputs/...` in every config transparently lands on
  persistent storage without any config changes. Don't rely on `/mnt` for
  anything you'd be sad to lose. Same pattern `shortcut_forensics` uses
  (`scfx_ly_persistent_outputs`), matched for consistency.
- A shared ledger lives at `/mnt/SHARED.md` (world-writable, append your own
  project's row / update it, don't edit others' — matches "the isolation
  proposal" this doc grew out of) listing every project's GPU claim,
  code/output paths, tmux session name, and ports in use. Check it before
  claiming anything; it's more likely to be current than any external chat
  log.

## Why this track exists

The original ICTD design (`README.md`, `src/monitor` + `src/detect`,
`infra/terraform` AWS) measures **cross-node** collective/interconnect byte
rates to separate benign training from inference — a 2-node experiment. As
of this writing we only have a real path to **one** multi-GPU Azure node
(Microsoft hasn't confirmed whether a second node is available; treat it as
low-probability, not planned-for). A single node has no cross-node fabric to
measure at all — GPU-to-GPU traffic inside one box stays on NVLink/NVSwitch
and never touches a NIC, so the original track's probes (`ib`, `nccl`,
`proc_net`) would see near-zero signal regardless of workload.

This track (`src/redteam/`, `src/run_redteam.py`) is a **separate,
independent addition** — it does not modify anything under `src/monitor`,
`src/detect`, `src/run_experiment.py`, `src/run_cluster.py`, or
`infra/terraform`/`infra/scripts` (AWS). If a second node does materialize
later, the original cross-node track still works unchanged — see
"Graduating back to 2 nodes" below.

## What already exists in the literature — don't rebuild this blind

Before writing any code here we checked for prior work, per repo owner's
explicit instruction not to reinvent an already-solved problem. Full search
notes: see `/private/tmp/.../nvlink_prior_work_notes.md` (session scratch,
not checked in) for the broader literature scan; the load-bearing finding
for this track's design is:

**Robi Rahman & Sabiha Tajdari, "Detecting Hidden ML Training With
Zero-Overhead Telemetry."** Proceedings of the Second Workshop on Technical
AI Governance Research (TAIGR) at ICML 2026, Seoul. arXiv:2606.19262v1
(2026-06-17). Already cited in `README.md` as "Rahman & Tajdari" — that
citation undersold how directly on-point this paper is. Verified by reading
the PDF directly (not just the abstract):

- Exactly this problem: single-node (up to 8-GPU), zero-overhead NVML-only
  telemetry, binary train-vs-not-training classification, adversarially
  red-teamed.
- **9 raw NVML signals at 1 Hz**: GPU utilization (%), memory utilization
  (%), memory used (MB), power draw (W), temperature (°C), SM clock (MHz),
  memory clock (MHz), PCIe TX bandwidth (MB/s), PCIe RX bandwidth (MB/s).
- **RandomForest, 400 trees, no max depth**, class-balanced weights (XGBoost
  close second; SVM-RBF/logistic regression worse).
- **Feature design**: structural/roofline layer (mean power, mean
  utilization) + temporal layer (autocorrelation, CV, periodicity) +
  "physics-based evasion-resistant" features added in later hardening
  rounds (cumulative energy, power-memory correlation, pre-allocation
  memory-plateau features).
- **Dataset**: 1,404 runs / 162 distinct workloads / 445,310 telemetry
  readings, nodes of up to 8 datacenter GPUs, 9 GPU models across 4
  architecture generations (Ampere through Blackwell — i.e. includes A100
  and H100-class hardware, exactly our target).
- **5 rounds of adversary-defender co-evolution, 20 evasion strategy
  families**, including utilization manipulation, memory reduction,
  training-as-inference camouflage, multi-GPU structuring, and white-box
  attacks with access to the defender's own classifier internals.
- **Results that matter most for scoping this track**: pooled non-adversarial
  accuracy 98.2%±0.84%; leave-one-GPU-out generalizes to 99.4–100% on unseen
  hardware; **all 4 of their multi-GPU evasion strategies (DDP online
  learning, DDP diluted training, staggered dilution, gradient accumulation
  across ranks) are detected at 99.6–100%** in leave-one-strategy-out
  evaluation — multi-GPU evasion is, per their own results, close to solved.
  The one real remaining weak point is **single-GPU** evasion (~6.2% mean
  evasion rate; only white-box LoRA fine-tuning gets under 50% detection).
- They explicitly invite external red-teaming: *"We invite the AI governance
  and ML research communities to red-team our classifier and publish new
  evasion strategies that might defeat it."*
- §6.5 "Implications for HEMs" independently derives the same three
  requirements as FlexHEG (tamper-resistant NVML read path, authenticated
  telemetry channel, secure boot of the monitoring software) — useful
  connective tissue if this ever comes up next to FlexHEG/Petrie material.

**We could not locate their source code.** The paper states "source code
... is available in the project repository" but no working link was
findable via GitHub search (`robirahman`'s public repos don't include it),
arXiv ancillary files, or PDF link annotations, as of 2026-08-17. If the
repo owner obtains it later (e.g. by asking at SPAR — Rahman mentors the
Fall 2026 SPAR cohort and is reachable through that channel), swap it in;
until then, everything in `src/redteam/` is **our own reimplementation from
the paper's text**, not their actual code or trained weights.

## Honest positioning — what this track is and isn't

Given the above, a naive "build a single-node NVML train-vs-infer classifier"
plan would have walked directly into a problem Rahman & Tajdari already
solved thoroughly, with a public paper and (per their claim) public code, on
hardware that already includes our exact target class. That would not be
useful work.

What this track actually does instead:

1. **Faithful-methodology reimplementation** (not literal reproduction — see
   limitations) of their feature/classifier design, trained on **our own**
   benign corpus (`train_ddp`, `infer_dp`, `infer_tp` — reusing this repo's
   existing workload implementations, which are methodologically different
   from whatever generated their 93 training / 40 inference workloads).
2. **External red-team** with two workloads this repo already has that don't
   obviously match any of their 20 documented families:
   - `kv_disguise` — chunks the gradient all-reduce into KV-cache-sized
     pieces specifically to disguise training as inference at the
     collective-op shape level. Closest to their "training-as-inference"
     bucket but a distinct mechanism (shape/size camouflage of a real op,
     not diluting/staggering/mixing update frequency).
   - `diloco` — genuine communication-sparse local-SGD training (real
     DiLoCo, Douillard et al. 2023, arXiv:2311.08105), syncing only every
     `inner_steps`. Mechanistically different from "staggered dilution"
     (which spreads *disguised* traffic across time) — this changes the
     actual temporal signature of the whole run, not just a single op.
3. **Set realistic expectations, not a foregone conclusion**: their own
   Table 5 shows near-100% detection on every multi-GPU evasion family they
   tested. The honest prior is that our two workloads probably also get
   caught by a competently hardened classifier — that would be a legitimate,
   worth-reporting negative/confirmatory result, not a failure. Report
   whatever the real 8-GPU run actually shows; do not go looking for a way
   to claim an evasion "win."

Separately, `Robi Rahman, "Does Distributed Training Undermine Compute
Governance?"` (arXiv:2605.29359, MIRI, 2026-05-28) is relevant background for
*why* `diloco`-style evasion matters at all, even though it's not about
NVML telemetry: under Scher et al. (2025)'s proposed 16-H100-equivalent
node-registration threshold and consumer-grade internet (100 Mbps / 100 ms
latency), hierarchical DiLoCo can still reach Llama-3.1-405B-equivalent
training compute (3.8×10²⁴ FLOP) for ~$441M using 625 small nodes — i.e.
distributed/low-comm training is a real, quantified incentive to evade
node-count-based governance, which is the motivating reason `diloco` belongs
in this red-team corpus at all.

## Pipeline design

```
src/redteam/
  telemetry.py    9-signal NVML poller (real: pynvml; fake: SyntheticTelemetrySource
                  for GPU-less local dev). Posts aggregated (mean+std across
                  GPUs) samples to the *existing, unmodified* collector's
                  /event endpoint as {"type": "nvml9_sample", ...} — reuses
                  src/monitor/collector.py as-is rather than inventing new
                  transport.
  features.py     30s window / 15s stride (matches the paper). Structural +
                  temporal + physics-based features. Reuses
                  src/detect/features.py:iter_windows (import, not edit) to
                  find each workload's [start,end] marker span.
  classifier.py   RandomForest(400, class_weight="balanced"), matching their
                  reported best model.
src/run_redteam.py   3-phase orchestrator:
  Phase A: run benign_workloads (train_ddp / infer_dp / infer_tp), telemetry
           running throughout, tagged train=1 / infer=0.
  Phase B: extract features, train the classifier on the benign corpus.
  Phase C: run adversarial_workloads (kv_disguise / diloco), score every
           window against the Phase-B classifier, report P(training) per
           workload — this is the red-team result.
```

Cross-GPU aggregation (mean + std of each signal across all visible GPUs per
1Hz tick) is **our own design choice** — the paper doesn't specify its exact
multi-GPU aggregation in the sections we could extract. Same for the exact
"time to memory plateau" formula (we use: first time a trailing 5s window's
memory range stays within 2% of its mean *and* stays that way for the rest
of the run). Both are documented in code comments (`src/redteam/telemetry.py`,
`src/redteam/features.py`) — treat them as reasonable-not-verified.

## How to run

```bash
# Local, no GPU, no cloud spend — validates the whole pipeline with fabricated telemetry:
python -m src.run_redteam --config configs/redteam_smoke.yaml

# Real 8-GPU Azure node, once quota lands (needs pynvml + real hardware):
python -m src.run_redteam --config configs/azure_redteam_single_node.yaml
```

Output: `outputs/<run_name>/{trace.jsonl, classifier.joblib, report.json}`.
`report.json` includes an explicit `limitations` field restating the caveats
above so a reader of just the JSON (not this doc) still sees them.

## Reproducing this — what's actually included, and what real reproduction means here

Everything is here except a GPU: all source code (`src/`), every config
actually run (`configs/azure_*.yaml`), and — unlike a typical run of this
project, where `outputs/` is gitignored as local scratch state — the raw
data behind every number in this document. `outputs/` in this repo
contains the real, non-synthetic result for every experiment cited above:
`azure_redteam_single_node` (baseline), `azure_redteam_round2` /
`shared_box_validation` (the two pilot runs), `azure_redteam_loop` +
`_continued` through `_continued5` (all 16 hardening rounds),
`azure_false_positive_check` (the original gap), `azure_redteam_fp_fix` /
`fp_fix2` (both fixes), `azure_false_positive_boundary_sweep`, and
`azure_fp_fragile_point_replication`. Each directory has the raw 1&nbsp;Hz
NVML trace (`trace.jsonl`), the trained classifier (`*.joblib`), and the
full evaluation report (`report.json` / `loop_report.json` /
`false_positive*.json`) — the same files this document's every number was
read from, not a summary of them.

**Two different things "reproduce" can mean here, and they need different
resources:**

- **Verify the numbers in this document are real and correctly computed**
  — needs no GPU at all. `src/redteam/features.py`'s
  `extract_redteam_features()` runs on the included `trace.jsonl` files on
  a laptop CPU; re-running it and re-evaluating the included classifiers
  against the included traces should reproduce every number in this
  document exactly, since nothing about that step is stochastic. This is
  literally how the round-2 power-band correction and the KV-cache
  correction elsewhere in this doc were found — by re-deriving numbers
  from these same raw files, not by re-running anything on a GPU.
- **Re-run the actual experiments from scratch on new hardware** — needs
  a real CUDA GPU with `pynvml` (any generation; doesn't have to be A100
  or Azure specifically) and will **not** reproduce bit-identical numbers.
  None of these workloads set a random seed (`src/workloads/dist_utils.py`'s
  `random_batch` uses whatever the ambient torch RNG state is), so even
  literally the same code on the same hardware twice gives different
  numbers each time — demonstrated directly by the statistical-replication
  section above (4 reruns of the identical config landed at 0.41/0.23/0.14/0.15,
  not four copies of 0.41). What should reproduce is the *qualitative*
  pattern: communication-shape disguises caught after one fold-in, memory
  reduction the only axis with real traction, extreme parameters producing
  out-of-band power readings, etc. — not the exact decimal values.

## Limitations (restated explicitly, not just in code comments)

- Not their trained classifier or weights — a reimplementation from the
  published methodology.
- Far smaller corpus than their 1,396 runs / 26,496 windows — any single
  8-GPU-node run here is directional, not a statistically powered
  replication.
- Single hardware generation per run (whatever the Azure quota approves —
  A100 or H100 class, not both).
- `kv_disguise` plausibly falls inside their already-covered
  "training-as-inference" evasion category — a caught result would not be
  surprising and should be reported as such, not spun.
- Synthetic-telemetry smoke runs (`configs/redteam_smoke.yaml`) prove the
  pipeline executes correctly; they say nothing about real evasion
  feasibility. Don't cite smoke-run numbers as findings.

## First real-hardware result (2026-08-22, `outputs/shared_box_validation`)

1000 steps/workload, GPUs 3-5 of the shared Italy North box, tiny synthetic
model (not HF). Classifier trained on 24 benign windows (6 `train_ddp`
positive, 18 `infer_dp`+`infer_tp` negative) reached **100% in-sample
accuracy** — consistent with Rahman & Tajdari's own finding that
non-adversarial classification is close to solved. Against the adversarial
corpus: **13/15 windows (86.7%) evaded** — all 9 `kv_disguise` windows
predicted not-training (P(training) 0.17-0.23), `diloco` mixed but mostly
evading (4/6).

**Read this correctly, don't oversell it:**
- This is our own from-scratch classifier trained on a *non-adversarial*
  benign corpus only — i.e. it's at the same hardening stage as Rahman &
  Tajdari's own **Round-1 baseline** (before any of their 5 adversarial
  co-evolution rounds), not their final hardened classifier. Their paper's
  own Table 5 shows baseline classifiers get beaten easily too (6-96%
  accuracy against Round-1 evasion) — a fresh, undefended classifier being
  evadable is the expected starting point, not a novel result.
- Small numbers (24 benign / 15 adversarial windows from one short run) —
  directional, not statistically powered. Do not read 86.7% as a precise
  evasion rate; it's what one run on this small corpus showed.
- Interesting anyway: feature importance is dominated by `power_mem_corr`
  (24.5%), `time_to_mem_plateau_s` (20.6%), and `first_30s_mem_delta_mb`
  (20.0%) — exactly the three "physics-based evasion-resistant" features
  Rahman & Tajdari added in their own Round 3+ hardening specifically to
  catch the hardest evasion cases. That they dominate *and* still didn't
  stop `kv_disguise`/`diloco` here is the genuinely interesting thread to
  pull on: does adversarial hardening (multiple rounds, like their
  methodology) close this gap, or does it persist even with those features
  weighted highest? That requires actually implementing a hardening loop
  (retrain on adversarial examples, repeat) — not done yet, next step if
  this track continues past the Aug 21-23 window.

## First hardening round (2026-08-22, `outputs/azure_redteam_round2`)

`src/run_redteam_harden.py` implements one round of Rahman & Tajdari's
actual methodology (§4.3): fold an evasion strategy's examples into
training as (correctly labeled) positive examples, retrain, then test
against a FRESH execution of the same strategy — held out, never seen in
training, so the test isn't circular. Same held-out set scored against
both classifiers, so any difference is attributable to hardening, not a
different test set.

Result: **round-1 (undefended) classifier: 0/15 held-out windows detected
(0.0 accuracy).** Every fresh `kv_disguise`/`diloco` window was missed
(P(training) ~0.19-0.24, confidently wrong, not borderline). **Round-2
(hardened on round-1's 15 adversarial examples): 15/15 (1.0 accuracy)** on
the identical held-out set.

**Read this correctly:**
- This is a real, clean demonstration that the hardening *mechanism*
  works — folding evasion examples into training measurably closes the
  gap, exactly as Rahman & Tajdari's methodology predicts.
- It is NOT evidence the hardened classifier generalizes to a genuinely
  *different* evasion strategy — the held-out set is a fresh execution of
  the *same* `kv_disguise`/`diloco` implementations with the same
  parameters, so this tests "does hardening catch a repeat of a trick it's
  seen," not "does hardening catch a novel trick." Rahman & Tajdari ran 5
  rounds against 20 *different* families for a reason; one round against
  the same two workloads is a much weaker claim.
- One round, small N (15 folded-in + 15 held-out windows) — directional,
  not the multi-round, many-family robustness curve their paper reports.
- Next real test if this continues: hold out a workload the hardened
  classifier has never seen an example of at all (e.g. a third disguise
  variant, or a different `kv_chunk_tokens`/`inner_steps` parameterization)
  — that would speak to generalization rather than memorization of the
  specific trick.

## Full 8-round hardening loop (2026-08-22, `outputs/azure_redteam_loop`)

`src/run_redteam_loop.py` chains real rounds (each a genuinely different
evasion parameterization, not a repeat) instead of the single round above.
Ran unattended overnight on GPUs 3-5 (~40 min total, all 8 rounds completed,
zero failures) via `configs/azure_redteam_hardening_loop.yaml`: round 0
(`kv_disguise`, chunk=2048) → round 1 (`diloco`, inner=25) → rounds 2-3
(`kv_disguise` at chunk=512/8192) → rounds 4-5 (`diloco` at inner=10/100) →
rounds 6-7 (the new `kv_diloco_composite` workload — both mechanisms
stacked — at two parameterizations). Each round's fresh, held-out windows
are scored against the classifier hardened on every PRIOR round only, then
folded in.

**Trajectory:**

| round | variant | pre-hardening accuracy |
|---|---|---|
| 0 | kv_disguise (chunk=2048) | **0.0** |
| 1 | diloco (inner=25) | 1.0 |
| 2 | kv_disguise (chunk=512) | 1.0 — mean power 170.8W, outside the 239-351W baseline band (flagged only later, see "Rounds 10-11") |
| 3 | kv_disguise (chunk=8192) | 1.0 |
| 4 | diloco (inner=10) | 1.0 |
| 5 | diloco (inner=100) | 1.0 |
| 6 | composite (chunk=1024, inner=20) | 1.0 |
| 7 | composite (chunk=4096, inner=50) | 1.0 |

Final classifier (hardened on all 8) re-scored against every round's
held-out set: 1.0 across the board — no catastrophic forgetting.

**Why round 0 alone made everything after it trivial — checked, not
assumed:** raw power draw does NOT cleanly separate train from infer in
this data (`infer_dp` actually shows *higher* mean power than `train_ddp`
in the collected traces — 317-351W vs 285-320W). The feature that
generalizes is memory: `first_30s_mem_delta_mb` (memory ramp in the first
30s of a run, driven by optimizer-state allocation) is 10,392 MB for
`train_ddp`, 5,924 MB for `diloco`, 5,480 MB for `kv_disguise`, vs. 3,366
MB (`infer_dp`) / 1,528 MB (`infer_tp`) for inference. **Every evasion
mechanism tested here reshapes communication — chunk size, sync
frequency, or both — but none of them touch memory allocation.** A real
backward pass + AdamW step always allocates gradient buffers and
optimizer momentum/variance state, regardless of how the resulting
gradients get communicated. Once the classifier has a single example
distinguishing "optimizer-state memory ramp present" from "absent," it
generalizes almost for free to every other communication-only disguise,
including one (`diloco`) and one workload (the composite) it had never
seen an example of.

**This is a real, mechanistically-grounded, honestly-scoped result, not a
free win — read the limitation precisely:** it shows communication-layer
disguises cannot beat memory/physics-based detection *because they never
address the thing being detected*. It says nothing about whether an
evasion that also touches the memory footprint — gradient checkpointing,
activation offloading, an optimizer with less state (plain SGD instead of
AdamW), or reduced-precision optimizer state — would be caught. That is
the natural next round if this continues, and would be the first round
against a genuinely different axis of evasion rather than a parametric
variant.

## Rounds 8-9: memory-touching evasion (2026-08-22, `outputs/azure_redteam_loop_continued`)

`src/workloads/low_mem_disguise.py` (new) swaps AdamW for plain SGD with
`momentum=0` — torch's SGD allocates a momentum buffer only when
`momentum != 0`, so this has **zero persistent optimizer state**, directly
targeting the feature (`first_30s_mem_delta_mb`, driven by AdamW's ~8
bytes/param fp32 momentum+variance) that explained why every prior round
generalized so cleanly. Resumed the completed 8-round loop
(`--resume-from`, reconstructing cumulative training data from saved
traces — no GPU time for rounds 0-7) and ran two new rounds: memory-only
(`low_mem_8`, still the original unchunked AllReduce) and memory +
communication combined (`low_mem_chunked_9`).

**Both got caught (pre-hardening accuracy 1.0 for each) — but the
*confidence* tells the real story, and it's not what a "hardening always
generalizes" narrative would predict:**

| round | mean P(training) | range |
|---|---|---|
| `low_mem_8` (memory-only) | **0.586** | 0.555 – 0.598 — barely above the 0.5 threshold |
| `low_mem_chunked_9` (memory + comm) | **0.999** | 0.9925 – 1.0 — maximally confident |

For comparison, every earlier communication-only round after round 0
scored 0.62–1.0 confidence, and `kv_disguise_2048` (round 0, before any
hardening) scored 0.075–0.128 — confidently *wrong*.

**The memory fix worked, partially — `first_30s_mem_delta_mb` for
`low_mem_8` is 3,968 MB, close to `infer_dp`'s 3,366 MB and far below
every AdamW-based training variant (5,480–10,392 MB).** That's real: one
feature moved from a clear tell to nearly camouflaged. It didn't fully
evade because the classifier uses all 12 features jointly, not a single
threshold — `power_mem_corr` (0.836) still sits closer to the training
cluster (0.898–0.966) than the disguise cluster (0.507–0.622), and that
plus residual signal elsewhere kept it barely on the "training" side.

**Adding chunked communication back on top made it WORSE, not better, for
the adversary — and here's why, checked against the loop's actual
confidence scores, not assumed:** every communication-based round after
round 0 was progressively caught with *escalating* confidence
(`kv_disguise_512`→0.799, `diloco_100`→0.958, the composites→0.998-1.0).
The classifier has learned "chunked/sparse communication pattern" itself
as a strong positive signal for training-in-disguise, because that's
exactly what rounds 0-7 taught it, one confirmed example at a time. So
layering chunking onto `low_mem_8` didn't add camouflage — it re-triggered
an already strongly-learned "this shape means training" fingerprint,
overwhelming the weaker residual memory signal and pushing confidence
back to 0.999. **The evasion mechanisms this repo implements may have
become counterproductive once caught once: the act of disguising
communication is itself now a tell, not a hiding strategy, against this
specific hardened classifier.**

Read carefully: this is not "the classifier catches communication
disguises broadly" as an a-priori fact — it's a claim about *this specific
classifier's learned decision boundary*, built from *this exact sequence*
of examples. A different round ordering, or an adversary who never
triggers the "chunked-therefore-training" association in the first place
(i.e. skips straight to memory-only evasion without ever having done
comm-based disguise the classifier could learn from), might see a
different outcome. Next round, if this continues: push the memory-only
axis further without adding communication disguise back (smaller
batch/seq to shrink activation memory too, not just optimizer state) —
`low_mem_8` at 0.586 is the closest anything has come to genuine evasion
so far, and it's worth finding out whether it can be pushed under 0.5.

## Rounds 10-11: pushing the memory axis further — a cautionary result (2026-08-22, `outputs/azure_redteam_loop_continued2`)

Two more `low_mem_disguise` variants, same SGD/momentum=0 fix, further
reducing `batch_size`/`seq_len` to shrink activation memory too (not just
optimizer state): `low_mem_min_11` (batch=2, seq=256) and `low_mem_min_10`
(batch=1, seq=128), vs. round 8's `low_mem_8` (batch=4, seq=512).

**Confidence went UP, not down, and non-monotonically:**

| round | batch/seq | mean P(training) | mean power |
|---|---|---|---|
| `low_mem_8` | 4 / 512 | 0.586 | 285.3 W |
| `low_mem_min_11` | 2 / 256 | 0.947 | 198.9 W |
| `low_mem_min_10` | 1 / 128 | 0.675 | 133.1 W |

`first_30s_mem_delta_mb` and `power_mem_corr` DID move further toward the
inference cluster as intended (3,968→2,080→1,904 MB;
0.836→0.585→0.614) — the memory-shrinking mechanism itself worked exactly
as designed. **But mean power dropped to 133-199 W, well below the
239-351 W range the original `azure_redteam_single_node` benign+adversarial
baseline categories established.** (Correction, added after building a
visualization of all 16 rounds: this specific 239-351 W band is that
*original baseline run's* range, not literally every round ever run in
this project — round 2, `kv_disguise_512`, is a separate, later round that
also reads at 170.8 W, likely because its very fine chunking made it
communication-bound enough to lower average power throughout its whole
run. It was never flagged as OOD at the time. The methodological point
below stands regardless — checking power against a real reference range
before trusting a confidence score — the reference range just needs
naming precisely, and round 2 should have been flagged the same way rounds
10-11 and 14 were.) That's very likely due to the
tiny batch/seq starving the GPU (small compute bursts separated by more
idle time), not a deliberate evasion property, and it's plausible this
pushed the input outside the region of feature space the classifier was
ever trained on. **A Random Forest's prediction on a genuinely
out-of-distribution input is not reliable evidence of anything — it can
land confidently on either side of a leaf boundary that was never
meaningfully trained on nearby data.** Reading "confidence went up" as
"smaller batch/seq makes evasion harder" would be over-interpreting: the
more honest reading is that this input left the region where the
classifier's judgments (in either direction) mean much at all.

**Practical implication if this continues**: testing evasion parameters
that stay within realistic training hyperparameter ranges (the batch/seq
combinations an actual pretraining run would plausibly use, not values
chosen purely to minimize a target feature) is more informative than
chasing a feature-space extreme — `low_mem_8`'s batch=4/seq=512 (mean
0.586, genuinely the closest call so far) is arguably the more meaningful
data point of the three, precisely because it's the one that looks like a
real training configuration, not an artificially starved one.

## Rounds 12-13: does "low sync frequency" generalize across mechanisms? (2026-08-22)

`src/workloads/grad_accum_disguise.py` (new) tests whether the classifier's
learned "reduced sync frequency = training" association (from `diloco`,
rounds 1/4/5) is specific to diloco's particular mechanism (local-SGD
inner steps + Nesterov outer-momentum average) or generalizes to ANY
mechanism producing the same externally-observable effect. Gradient
accumulation is a completely different, far more standard technique — K
micro-batches accumulate gradients locally with zero communication, then
one all_reduce + one optimizer step every K steps. No outer-loop momentum
state, no local-SGD phase.

**Caught with even higher confidence than diloco itself**: mean
P(training) 0.996 (accum every 4 steps) and 0.997 (every 25 steps) — both
above every diloco variant (0.775-0.958) and matching the composite
rounds' near-total certainty (0.998-1.0). This confirms the earlier
hypothesis directly: the classifier generalized a genuine, mechanism-
agnostic pattern ("training syncs infrequently, in bursts, with a
recognizable temporal signature") rather than overfitting to diloco's
specific code path. A structurally different way of achieving the same
communication-frequency reduction gets caught just as hard, if not harder.

(One operational note on this round: it had to be re-run once — the first
attempt died silently ~20s in when something external to this project
killed the orchestrating process, orphaning the GPU-bound worker
processes for ~3 minutes with no telemetry being collected; see
`/mnt/SHARED.md`'s 2026-08-22 16:31 UTC entry for the shared-box
diagnostic writeup. Not a bug in this code — flagged for completeness
since an unattended overnight/all-day loop needs to survive this class of
event, which the retry did.)

## Round 14: white-box combined adversary — a confound, not a clean result (2026-08-22)

`src/workloads/white_box_disguise.py` combined everything learned so
far — SGD/momentum=0 (round 8's partial win), realistic batch=4/seq=512
(avoiding the OOD risk from rounds 10-11), no communication-shape changes
(avoiding the backfire from rounds 1-9) — plus one genuinely new axis:
deliberate idle gaps between steps (`idle_frac=1.0`, sleeping roughly as
long as each step's compute took), targeting the temporal/duty-cycle
features (`cv_power`, `periodicity_power`) that no prior round had touched.

**Caught at mean P(training)=0.998 — worse than the memory-only round 8
(0.586), not better.** But the mechanism is diagnosable, not mysterious:
`cv_power` did rise as intended (0.269→0.392, more burstiness — the
temporal-shaping idea worked on its own terms) — but **mean power dropped
to 153.1 W**, again below the 239-351 W range the original baseline run
established (see the round 2 caveat under "Rounds 10-11" — that band isn't
a strict floor for every round ever run, but 153.1 W is low enough to
land well outside it by any reasonable reading). Sleeping for ~half the
wall-clock time pulls the *average* power
reading down substantially, since idle periods read as near-zero power —
an unaccounted-for side effect that likely pushed this into the same kind
of out-of-distribution territory as rounds 10-11's extreme batch/seq
reduction (see that section's caution about over-reading a Random
Forest's confidence outside its trained region), rather than genuinely
demonstrating that temporal/duty-cycle shaping doesn't help.

**Lesson, not a dead end**: naive interventions on one feature axis often
have unintended confounds on a DIFFERENT, more dominant feature (mean
power here) that swamp the intended effect. A cleaner test of the
temporal-shaping hypothesis would need to preserve realistic mean power
(stay in the 240-351 W band the classifier was actually trained on) while
varying only the burst *pattern* — e.g. shaping when a fixed total amount
of compute happens within a window, not adding net idle time on top of it.
Not attempted yet; flagging as the more carefully-designed follow-up to
this specific idea, distinct from concluding the idea itself failed.

## False-positive check: a real limitation, not an artifact (2026-08-22, `outputs/azure_false_positive_check`)

Every round so far tested one direction of error (does disguised training
evade detection?). `src/run_false_positive_check.py` tests the direction
that actually determines real deployment viability: does the classifier
(hardened through round 14) misclassify heavier-than-baseline but entirely
**legitimate** inference — bigger batch, longer context, the kind of load
a busy real inference server actually serves — as training?

**Yes, confidently: `infer_dp_bigbatch` (batch=32 vs baseline's 8) — 9/9
windows misclassified, mean P(training)=0.812. `infer_dp_longctx` (seq=2048
vs baseline's 512) — 11/11 windows, mean P(training)=0.825.**
(`infer_tp_heavy` only produced 1 usable window — a monitoring-script race
condition where the tmux session closed normally right as the run finished
made it look like a crash; not enough data there to read anything into,
unlike the other two.)

**This is not another out-of-distribution artifact like rounds 10-11/14 —
checked directly, not assumed:** mean power for both misclassified
workloads (328.3 W, 317.5 W) sits squarely in the normal 240-351 W range
every legitimate category has shown throughout this project — nothing
anomalous there. The real story is memory: `infer_dp_bigbatch`'s
`first_30s_mem_delta_mb` is **10,042 MB — essentially identical to
`train_ddp`'s 10,392 MB.** `infer_dp_longctx`'s is **11,387 MB — higher
than train_ddp.** `power_mem_corr` also climbed to 0.878/0.839, close to
train_ddp's 0.966 and well above baseline infer's 0.804.

**Why, mechanistically**: inference's memory footprint scales with
batch×context just like training's activation memory does — there's
nothing about inference *per se* that caps its memory ramp low. The
benign training corpus for this whole project only ever ran inference at
modest batch=8/seq=512 while training explored a wider range, so
`first_30s_mem_delta_mb` distinguishing them was **partly a confound of
the corpus's own experimental design, not a property of training vs.
inference as such.** A real inference deployment serving many concurrent
requests or long conversations would plausibly trip this classifier
today.

**Correction (2026-08-24), important for external validity, not just
precision**: an earlier draft of this section attributed part of
inference's memory growth to KV-cache. Checked against the actual code
while answering a question about it — wrong. `TinyGPT.generate()`
(`src/model/tiny_gpt.py`) recomputes a full forward pass over the whole
context on every generation step (`self(idx[:, -block_size:])`); there is
no KV-cache anywhere in this codebase (`grep -rn "cache\|kv_cache\|past_key"`
across `src/model/` and `src/workloads/` returns nothing). So the actual
mechanism here is that `infer_dp`/`infer_tp`'s memory growth comes
entirely from the *same* activation-memory scaling law training uses —
both are running the identical B×T×C×layers forward-pass computation, and
inference here just never adds training's *extra* gradient+optimizer-state
memory on top. This makes the false-positive finding *more* robust, not
less — it isn't a coincidental resemblance between two different memory
mechanisms (KV-cache vs. activations), it's the same shared mechanism
being large enough at scale to swamp the smaller training-only increment.
**But it also narrows what this specific finding can claim**: a real
inference server with actual KV-caching (vLLM, TGI, etc.) would show a
substantially cheaper, differently-shaped memory profile than our
uncached `generate()` loop — cache reads instead of full recomputation
per step — so the exact false-positive boundary measured in this project
should not be assumed to transfer to a real production inference stack
without re-testing against one. Not attempted here; flagged as an
external-validity gap alongside the "no real HF model" one below.

**This is the most consequential finding of the day, not a footnote**:
every prior round asked "can an adversary hide training as inference" —
this asks "does the detector even work correctly on ordinary heavy
inference," and the answer is currently no. Any real deployment claim for
this line of detection needs to include benign workloads across the FULL
realistic range of scale (batch, context length) in the training corpus,
not just a fixed small baseline — the fact that the redteam/loop pipeline
already supports adding non-training examples the same way it added
training-disguise examples means this is fixable, but it hasn't been done
yet and should be treated as required, not optional, before this result
means anything for a real system.

## Fixing the false-positive gap (2026-08-22, `outputs/azure_redteam_fp_fix`)

`src/run_redteam_fix_false_positives.py` folds the false positives found
above into the training corpus as correctly-labeled negative
(is_training=False) examples — the same mechanism the hardening loop uses
for adversarial positives, opposite class, kept as a separate script since
`run_redteam_loop.py`'s `validate_rounds()` requires every round resolve
True. 21 negative windows folded in (reconstructed cumulative training set
went from 269 → 290 examples, spanning all 15 prior rounds — reuses
`run_redteam_loop._load_prior_loop`'s chain-walking, no re-running old
rounds).

**Clean result, both halves:**
- **Generalizes, doesn't just memorize**: tested against FRESH
  heavy-inference runs at *different* batch/seq than what got folded in
  (batch=24/seq=768 and batch=16/seq=1536, vs. the folded-in 32/512 and
  8/2048) — mean P(training) dropped to **0.369** and **0.295**,
  correctly below the 0.5 threshold, down from 0.812/0.825 before the fix.
- **Zero regression**: all 15 prior adversarial rounds (every
  communication-shape and memory-touching disguise tested so far) still
  score ~1.0 against the fixed classifier — fixing the false-positive gap
  didn't reopen any earlier evasion.

**What this does and doesn't establish**: it shows the false-positive
problem is fixable by the obvious mechanism (put realistic-scale benign
examples in the training data), and that doing so doesn't trade away
prior detection capability — for the batch/seq ranges tested. It does
NOT establish where the boundary now sits (some large-enough batch/context
would presumably still trip it — this only tested moderately-larger
values, not a sweep to find where false positives resume) or that this
generalizes to inference scaled well beyond what's been tried. The honest
takeaway: the underlying methodology (fold in realistic negatives the same
way you fold in adversarial positives) works and is cheap — a real
deployment would need this done systematically across the full realistic
range of legitimate traffic shapes, not as a one-off patch after finding
one gap.

## Round 15: gradient checkpointing — a cleaner memory test, still caught (2026-08-22)

`src/workloads/grad_checkpoint_disguise.py` (new) is the more careful
continuation of the memory axis after round 14's confound: real
large-model training routinely uses activation checkpointing (recompute
each transformer block's activations during backward instead of storing
them) to fit more in memory — trading ~30-40% more compute, not touching
batch/seq at all. Same SGD/momentum=0 fix, same realistic batch=4/seq=512,
no communication changes.

**Caught (accuracy 1.0), mean P(training)=0.777** — worse for the
adversary than round 8 (0.586) but far better than the communication-based
and composite rounds (0.9-1.0). The comparison is clean this time, not
confounded: mean power was 291.0 W, squarely in the normal 240-351 W range
(unlike rounds 10-11/14's OOD dips) — checkpointing achieved its memory
reduction without the side effect that undermined the earlier attempts.
And it worked *better* than round 8 on the targeted feature itself:
`first_30s_mem_delta_mb` = **2,432 MB, lower than round 8's 3,968 MB**,
closer to `infer_tp`'s 1,528 MB than to any training variant.

**Why "better on the target feature" didn't mean "more evasive" — likely
explanation, not directly measured**: round 8 tested the memory axis when
it was still novel to the classifier (one prior round folded in). By
round 15, the classifier has been hardened against five prior memory-
focused attempts (`low_mem_8`, `low_mem_min_10/11`, `grad_accum` variants
sharing similar memory characteristics, `white_box_14`) — a further
reduction in one feature doesn't help as much once the classifier has
already learned to weight memory-adjacent signal more robustly from
repeated exposure to that general strategy. Consistent with the broader
pattern across all 15 rounds: novelty of *axis*, not just degree of
change on one feature, seems to be what determines how much a given round
challenges the current classifier.

## False-positive boundary sweep (2026-08-22, `outputs/azure_false_positive_boundary_sweep`)

The false-positive fix (previous section) validated only two points —
`infer_dp` at batch24/seq768 (mean P(training)=0.369) and batch16/seq1536
(0.295) — both below the 0.5 threshold, but not by a wide margin, and both
on the data-parallel axis only. Two gaps this leaves: (a) whether that's a
sharp cliff right around those values or a gradual gradient with real
margin, and (b) `infer_tp` (tensor-parallel) inference was folded into
training as a negative (1 window, from the original false-positive check)
but the fix was **never freshly retested on the tp axis at all** — the
"generalizes" claim so far only actually covers infer_dp.

Config: `configs/azure_false_positive_boundary_sweep.yaml`, evaluated
against the already-fixed classifier
(`outputs/azure_redteam_fp_fix/classifier_fixed.joblib`, nothing retrained)
— pure evaluation, 12 points:
- **dp-batch axis** (seq=512 fixed): batch ∈ {8 (baseline sanity), 16, 24,
  32 (exact repeat of the originally-folded-in point — regression sanity),
  48 (extrapolation beyond anything tested)}
- **dp-seq axis** (batch=8 fixed): seq ∈ {1024, 2048 (repeat of
  folded-in point), 3072 (extrapolation)}
- **tp axis** (never freshly tested before this): batch/seq/tp_size ∈
  {(2,512,3) baseline sanity, (4,512,3), (8,512,3), (8,1536,3) — all
  distinct from the one tp point folded into training (8,1024,3)}

**First attempt failed silently (19:18-19:37 UTC), caught, root-caused,
fixed, rerun clean.** The 12 workload names above (`dp_baseline_sanity`,
`tp_b4_s512`, etc.) don't contain the substring `"infer"` or `"train"` —
`src/redteam/features.py`'s `_label_from_name()` keys off substrings in
the workload's `name` field (not its `kind` field, which correctly said
`infer_dp`/`infer_tp` throughout), so every one of the 12 real,
correctly-executing workloads (confirmed via `nvidia-smi`: 100% util,
325-360W on GPUs 3-5 for the full ~19 minutes) produced windows that
silently resolved `is_training=None` and got dropped by `to_matrix`
before ever reaching the classifier — `n_windows=0` for all 12 points in
the report, with no error or crash anywhere. The raw NVML trace itself
was completely fine (1001 real samples, correct marker spans); only the
label string was wrong. Recovered the run's real numbers by relabeling
the existing trace in place (confirmed the fix hypothesis, and incidentally
confirmed the whole sweep hypothesis directionally) rather than treating
the GPU time as wasted, then fixed the config (names now
`infer_dp_...`/`infer_tp_...`) and **recalibrated per-workload step counts
from this same failed run's own measured per-step wall-clock time** (which
varies ~7x across these batch/seq/tp combos — 0.02s/step for tiny
tensor-parallel batches up to 2.2s/step for batch=8/seq=3072) so the
rerun would land every point at roughly the same, adequately-windowed
(~9-16 windows) wall time instead of the first attempt's uncontrolled
5-263s range that left several points (worst: every tp point) with as
few as 1 window. Also caught and fixed the identical naming bug in
`configs/redteam_boundary_sweep_smoke.yaml` before rerunning — the smoke
test's `n=0, mean_p=nan` output had the exact same root cause, misread
the first time as "just too short to form a window" rather than checked.

**Rerun (19:42-20:12 UTC), properly powered — results:**

| workload | batch/seq/tp | n windows | false positives | mean P(training) |
|---|---|---|---|---|
| `infer_dp_baseline_sanity` | 8/512 | 9 | 0/9 | 0.123 |
| `infer_dp_b16_s512` | 16/512 | 9 | **9/9** | **0.696** |
| `infer_dp_b24_s512` | 24/512 | 9 | 1/9 | 0.106 |
| `infer_dp_b32_s512_regression` | 32/512 (= folded-in) | 9 | 1/9 | 0.255 |
| `infer_dp_b48_s512_extrapolate` | 48/512 | 9 | 0/9 | 0.322 |
| `infer_dp_b8_s1024` | 8/1024 | 9 | **9/9** | **0.721** |
| `infer_dp_b8_s2048_regression` | 8/2048 (= folded-in) | 9 | 0/9 | 0.192 |
| `infer_dp_b8_s3072_extrapolate` | 8/3072 | 10 | **10/10** | **0.639** |
| `infer_tp_baseline_sanity` | 2/512/tp3 (= true baseline) | 2 | **1/2** | 0.545 |
| `infer_tp_b4_s512` | 4/512/tp3 | 3 | 0/3 | 0.265 |
| `infer_tp_b8_s512` | 8/512/tp3 | 5 | **4/5** | 0.634 |
| `infer_tp_b8_s1536_fresh` | 8/1536/tp3 | 7 | **4/7** | 0.541 |

`any_false_positive: True`. Three findings, not one:

1. **The fix is real but narrow, not general.** The two exact points the
   classifier was actually retrained on (batch32/seq512, batch8/seq2048)
   read correctly low. Points one step away in either direction —
   including plain interpolation (batch16, between the untouched baseline
   at 8 and the folded-in point at 32) and extrapolation beyond anything
   folded in — flip to confidently, consistently false-positive. Per-window
   detail (not just the mean) rules out "startup transient": several of
   these workloads show the misclassification holding steady across their
   *entire* runtime, not just an initial spike (e.g. `b16_s512`'s 9 windows
   run 0.637-0.760 throughout; `b8_s1024`'s run 0.632-0.807 throughout).
   Others (`b24_s512`, `b32_s512_regression`, `b8_s2048_regression`) do
   show a startup-transient pattern — one elevated first window, then a
   sharp drop for the rest — consistent with CUDA/NCCL init and initial
   memory-allocation ramp genuinely looking more training-like for the
   first ~30s regardless of the steady-state workload.
2. **Root cause, confirmed by direct feature inspection, not just
   inference from the P(training) pattern:** raw `mean_power_w` (295-354W)
   and `mean_util_pct` (86-100%) are similar across every point here,
   flagged or not — the structural features alone don't explain the split.
   `first_30s_mem_delta_mb` is the standout physics feature but is
   **non-monotonic** with batch/seq (`b24_s512`=8849MB reads low;
   `b16_s512`=6567MB, lower, reads high) — inconsistent with "the
   classifier learned a smooth memory-scaling rule" and consistent
   instead with a 400-tree ensemble drawing an arbitrary, jagged partition
   around a small number of specific memorized anchor points, where being
   nearest to a positive-labeled tree split in 12-dimensional feature
   space doesn't track being nearest in batch/seq space at all.
3. **The training data explains why, precisely:** reconstructing the
   fixed classifier's actual training set shows **263 positive
   (training-like) windows across the 16 adversarial rounds vs. only 39
   negative (benign) windows across just 6 distinct configs** — and the
   entire tensor-parallel axis contributed **2 windows total** (1 from the
   original benign baseline, 1 from the one folded-in `infer_tp_heavy`
   point) across the *whole* campaign to this point. `class_weight=
   "balanced"` reweights by raw count, not by how well a region of feature
   space is sampled — it cannot manufacture negative-class diversity that
   was never collected. This is a properly diagnosed, mechanistic
   explanation, not a guess: it directly predicts (and matches) which
   axis broke hardest (tp, 2 windows) vs. least (the two exact folded-in
   dp points, which read correctly precisely because they're memorized).

## Second false-positive fix: broad negative corpus, blind test (2026-08-22, `outputs/azure_redteam_fp_fix2`)

Folded **all 12** boundary-sweep points in as negatives (all genuinely
benign inference regardless of what the narrow classifier said about
them — same "fold in what breaks it" discipline the whole campaign uses
for the *positive* class, applied to the negative class for the first
time here) — broadening the negative corpus from 6 configs/39 windows to
18 configs/~97 windows, crucially including real tensor-parallel
diversity (4 tp configs instead of 1). Then tested on **6 brand-new
points** (`configs/azure_redteam_false_positive_fix2.yaml`,
`fresh_benign_stress_workloads`) that don't repeat any batch/seq/tp_size
combination tested anywhere before this — a genuine blind generalization
test, not a repeat of anything already inspected when designing the fix:
`infer_dp_b12_s512_blind`, `infer_dp_b20_s512_blind`,
`infer_dp_b8_s768_blind` (interpolating the two dp axes), and
`infer_tp_b3_s512_blind`, `infer_tp_b6_s512_blind`,
`infer_tp_b8_s768_blind` (interpolating the tp axis on both batch and
seq). Also re-runs the full 16-round regression check.

**Result: clean.** Training set grew from 281 windows (263 positive / 18
negative — the original benign baseline only, since this branch's
cumulative reconstruction doesn't chain through the separate first-fix
branch) to 371 (263 positive / 108 negative across ~12 distinct
configs, real tp diversity included) after folding in the 90 windows from
all 12 sweep points.

| blind workload | batch/seq/tp | n windows | mean P(training) (want LOW) |
|---|---|---|---|
| `infer_dp_b12_s512_blind` | 12/512 | 9 | 0.409 |
| `infer_dp_b20_s512_blind` | 20/512 | 9 | 0.012 |
| `infer_dp_b8_s768_blind` | 8/768 | 9 | 0.151 |
| `infer_tp_b3_s512_blind` | 3/512/tp3 | 6 | 0.076 |
| `infer_tp_b6_s512_blind` | 6/512/tp3 | 7 | 0.393 |
| `infer_tp_b8_s768_blind` | 8/768/tp3 | 6 | 0.090 |

All 6 read below the 0.5 threshold on genuinely new points never executed
before this run, let alone trained on — real generalization, not
memorization repeated a second time. **Zero regression**: all 16 prior
adversarial rounds still read back at accuracy=1.000 (kv_disguise,
diloco, composite, low_mem, grad_accum, white_box, grad_checkpoint — every
mechanism tried across the campaign). Broadening the negative corpus's
*diversity* (not just adding more copies of the same 2-3 points) is what
worked, exactly as the root-cause analysis in the previous section
predicted.

One caveat, not swept away: `infer_dp_b12_s512_blind` (0.409) is
meaningfully closer to the 0.5 line than the other five (0.01-0.15,
0.08-0.39) — the point closest to the worst-offending earlier false
positive (`b16_s512`, batch16) is also the least confidently-correct blind
point here. Consistent with "broader coverage narrows the fragile region,
doesn't provably eliminate it" — a claim like "the false-positive gap is
closed" would still be overstating a 12-and-18-config negative corpus.
This is real, meaningful progress on a real problem, not a final,
swept-boundary answer — the honest version of that claim needs either
(a) many more diverse negative configs than 18, or (b) a fundamentally
different negative-sampling strategy (e.g. training on a continuous
random distribution over batch/seq rather than a discrete grid of
points), neither of which has been tried yet.

## Statistical replication of the one fragile blind point (2026-08-22, `outputs/azure_fp_fragile_point_replication`)

`infer_dp_b12_s512_blind` (0.409) was the one blind point close enough to
the 0.5 line to leave the "is the second fix actually solid" question
open. Since none of these workloads use a fixed random seed
(`src/workloads/dist_utils.py`'s `random_batch`), rerunning the same
batch/seq config produces genuine independent replicates, not duplicates
— ran 4 fresh reps of the fragile point (batch=12/seq=512) plus 3 reps of
a confidently-correct control point (batch=20/seq=512, read 0.012 in the
blind test) against the actual fix2 classifier, to see whether 0.409 was
the fragile point's typical behavior or an unlucky single draw.

| point | reps (mean P(training) per run) | mean | stdev |
|---|---|---|---|
| `b12/s512` (fragile) | 0.407, 0.231, 0.137, 0.154 | **0.232** | 0.123 |
| `b20/s512` (control) | 0.023, 0.019, 0.015 | 0.019 | 0.004 |

**The original 0.409 reading was the high tail of a real distribution, not
its center.** 3 of 4 fresh reps land well below 0.5 (0.137-0.231); the
mean (0.232) sits comfortably on the correct side of the threshold — this
point is not, on average, a residual false positive. But it genuinely is
~30x noisier than the control (stdev 0.123 vs 0.004), and one individual
30s window across the 36 total in this check *did* cross 0.5
(`any_false_positive: True`, 1/9 windows in rep1). The right characterization
isn't "the boundary still leaks here" — the run-level mean is fine — it's
"this specific region of batch/seq space produces noisier per-window
scores than deeper-in-distribution points, so a deployment that alarms on
a single 30s window (rather than aggregating several) would see occasional
spurious alarms near this point even though the classifier is right on
average." A smoothing/aggregation policy (e.g. require 2+ consecutive
alarming windows before flagging) would likely absorb this; not
implemented or tested here.

**Closing state of the whole false-positive investigation, in one line:**
found a real gap (bug) → root-caused it precisely (39 windows/6 configs
in the negative class, 2 of them from the whole tp axis) → fixed it in a
way that generalizes to genuinely new points with zero regression → then
verified the one remaining soft spot is noise around a correct mean, not
a second hidden gap. Every step checked against the previous one's
methodology (fresh execution, never re-testing on folded-in data) rather
than trusting a single encouraging number.

## Untested evasion vectors worth flagging (2026-08-24, threat-model note — not run)

Surfaced while explaining the memory-vs-activation mechanism in
conversation, not from a new experimental round. Recorded here precisely,
in priority order, rather than left as a vague "more evasions might
exist" — each of these is arguably *more realistic* than several of the
16 rounds actually tested, because each is standard, non-adversarial
practice in real large-scale training, not a bespoke disguise.

1. **Mixed-precision activations (bf16/fp8) — highest priority, most
   likely to matter in practice.** Every round in this campaign trained in
   pure fp32 (confirmed: no `autocast`/`.half()`/`bfloat16` anywhere in
   `src/model/` or `src/workloads/`). Real frontier training overwhelmingly
   uses bf16 or fp8 mixed precision for plain efficiency, unrelated to
   evasion. Doing so would roughly halve-to-quarter activation memory for
   free, with zero adversarial intent required — meaning the detection
   margin this whole campaign measured (activation memory dwarfing every
   other feature, §"how much memory" discussion) is plausibly an artifact
   of this project's own fp32 choice, not a property of what an adversary
   would actually face against a real training run already using standard
   efficient precision. Not tested — no round varied precision.

2. **Parameter-efficient fine-tuning (LoRA / adapters) — second priority,
   also standard practice, not exotic.** Freezing the base model and
   training only a small adapter shrinks gradient+optimizer-state memory
   to a tiny fraction of the full-model case — this campaign's whole
   gradient/optimizer accounting scales with *trainable* parameter count,
   and a LoRA-style setup could plausibly pull that memory down toward
   inference's own footprint without doing anything disguised, since it's
   just normal efficient fine-tuning. Directly relevant to the governance
   framing this track sits in, too: a lot of realistic "hidden training"
   concern is about fine-tuning an existing capable model, not pretraining
   from scratch, and LoRA-style fine-tuning is exactly the common real-world
   case for that. Not tested — every round here did full-parameter training.

3. **Activation offloading to host (CPU) memory — a feature-coverage
   question, not an obvious clean win for the adversary.** Techniques like
   DeepSpeed ZeRO-Offload move activations to CPU RAM between forward and
   backward instead of keeping them GPU-resident, directly suppressing the
   GPU-side memory-ramp signal this classifier leans on hardest. But it
   should substantially increase PCIe traffic — and `mean_pcie_tx_mbps`/
   `mean_pcie_rx_mbps` are two of the classifier's 12 features already.
   Plausible this evasion trades one detected signal for another rather
   than genuinely evading. This is a hypothesis from reading the feature
   list, not a tested result — flagged as such, not claimed as a finding.

4. **Sequence/activation-parallel sharding across more GPUs — attacks a
   structural assumption, not just a feature.** Megatron-style sequence
   parallelism (or similar activation-partitioning schemes) shards a
   training step's activation memory across multiple GPUs, so any single
   *monitored* GPU's activation footprint drops — not because total
   cluster memory shrank, but because more GPUs are splitting it. This
   targets the detection methodology's core premise (per-GPU telemetry,
   no cross-node coordination visibility) more directly than any mechanism
   actually tested here, all of which stayed within a single node's
   memory-reduction budget. Not tested — this project never varied the
   degree of model/activation parallelism.

None of these four were run. If this track continues, (1) and (2) are the
higher-value next rounds specifically because they require no adversarial
cleverness at all — they're what a real, non-adversarial efficient
training/fine-tuning setup already looks like, which makes them the more
honest test of whether this detection approach would actually hold up
against realistic modern practice, not just against bespoke disguises
built to fool it.

## Not built: same-box network-namespace fallback

Earlier in scoping this work we discussed a same-machine fallback for
preserving the *original* cross-node track's signal even without a second
physical node: Linux network namespaces + a veth pair to split the 8 GPUs
into two logically-separated groups, forcing their NCCL traffic over a real
network interface (`NCCL_P2P_DISABLE=1`, `NCCL_SHM_DISABLE=1`) so
`proc_net`-style byte counters see genuine cross-boundary traffic. This
would be a different signal axis from this track (network interface
byte/burst shape vs. GPU power/utilization) and wouldn't overlap with
Rahman & Tajdari's territory. **Not implemented** — repo owner scoped this
session to the NVML red-team track only. If it's wanted later: veth
bandwidth is pure software-forwarding speed, not representative of real
inter-machine latency/bandwidth even with `tc netem` shaping, and that
caveat would need to be stated as prominently as the ones above.

## Graduating back to 2 nodes

If a second node (any size, doesn't need to match the first) becomes
available: the original AWS 2-node track (`infra/terraform`,
`src/run_cluster.py`) still works unmodified. `src/run_cluster.py` now also
accepts an `ICTD_NPROC_PER_NODE` env var override (additive, defaults to
the old symmetric behavior) so an asymmetric pairing — e.g. 6 GPUs on the
real node + however many a small companion VM has — can run one DDP job
with genuine cross-machine traffic without needing a second node the same
size as the first. An Azure equivalent of the 2-node AWS Terraform hasn't
been built (`infra/azure/` is single-node-only by design, see that
directory's `main.tf` header comment) — build it as a new module if/when
this is actually needed, don't grow `infra/azure/terraform/main.tf` into it.

## References

- Rahman, R. & Tajdari, S. (2026). *Detecting Hidden ML Training With
  Zero-Overhead Telemetry.* TAIGR @ ICML 2026. arXiv:2606.19262.
- Rahman, R. (2026). *Does Distributed Training Undermine Compute
  Governance?* arXiv:2605.29359. MIRI.
- Seferis, E. & Fist, T. (2026). *Detecting Compute Structuring in AI
  Governance is Likely Feasible.* AAAI-26 Special Track on AI Alignment.
  doi:10.1609/aaai.v40i44.41127. (Already cited in `README.md`; note the
  repo's original framing of this paper as directly about "cross-node
  byte-shape separates train from infer" overstates it slightly — the
  paper's actual target is cross-account/cross-provider compute
  *structuring* detection, using cluster-level bandwidth + node-level
  utilization telemetry as inputs, not a train-vs-infer classifier itself.)
- Douillard, A. et al. (2023). *DiLoCo: Distributed Low-Communication
  Training of Language Models.* arXiv:2311.08105.
- Zhang, Y. et al. (2025). *NVBleed: Covert and Side-Channel Attacks on
  NVIDIA Multi-GPU Interconnect.* arXiv:2503.17847. (NVLink counters leak
  general application-identity signal, F1 up to 97.8% — but only validated
  through NVLink-V2/P100+V100; explicitly leaves NVLink-V3/NVSwitch, i.e.
  A100/H100-class hardware, for future work. Relevant context for the
  *original* cross-node/NVLink track, not this NVML track directly, but
  worth knowing NVSwitch-generation validation is still an open gap in that
  literature.)
- Zhang, Y. et al. (2024). *Beyond the Bridge: Contention-Based Covert and
  Side Channel Attacks on Multi-GPU Interconnect.* arXiv:2404.03877.
  (Precursor workshop paper to NVBleed, same group.)
