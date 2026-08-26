# ai_lab

Hands-on AI/ML systems learning projects — each subdirectory is self-contained (own README,
own dependencies, own venv). Real code, run and verified where the hardware allows, honestly
reported (including bugs found and negative results) where it doesn't.

## Projects

### [`dist_training_lab/`](dist_training_lab/) — distributed training & ML infrastructure

A hands-on curriculum covering the distributed-training and ML-infra skills frontier AI labs'
research-infrastructure / ML-platform-engineering roles screen for: DDP, FSDP2, tensor/pipeline/
expert parallelism, FP8 quantization, and fault tolerance — implemented from scratch and
numerically verified against single-device references wherever possible, entirely on a laptop
(no cloud spend required for correctness, only for real multi-GPU speed/memory numbers).

See [`dist_training_lab/README.md`](dist_training_lab/README.md) for the full phase-by-phase
writeup, including real bugs found (a macOS-specific FSDP2 device-mesh crash, a gloo backend
limitation with ragged `all_to_all`, an undocumented non-1.0 gradient through a naive FP8 cast)
and honest negative results (naive vs block-wise FP8 quantization barely differed in a toy
training run, which turned out to be more informative than a clean confirmation would have been).

### [`transformer_lab/`](transformer_lab/) — transformer training & interpretability basics

Small, readable scripts for training, inference, and interpretability: causal self-attention
from scratch, KV-cache speedup measurement, and a logit-lens walk through a real GPT-2's layers.
See [`transformer_lab/README.md`](transformer_lab/README.md).

### [`compute_pause_verification/`](compute_pause_verification/) — verifiable AI slowdown briefing + a red-teamed detector

A self-contained PDF/HTML briefing on public research for **Claim A** compute monitoring
(pause / slowdown verification under low trust): datacenter primer, Cankaya Plan A/B,
zkLLM, VerInf, FlexHEG, and open follow-up problems. Start with
[`compute_pause_verification/notes.pdf`](compute_pause_verification/notes.pdf).

Paired with a from-scratch reimplementation of one detection method the briefing cites
(Rahman & Tajdari's NVML-telemetry train-vs-infer classifier), red-teamed for real on an
8×A100 node: 16 rounds of adversarial hardening plus a full false-positive investigation
— a real gap found, root-caused, fixed, and validated on blind data rather than trusted on
one good-looking number. See
[`compute_pause_verification/interconnect_train_detect/docs/WRITEUP.md`](compute_pause_verification/interconnect_train_detect/docs/WRITEUP.md).

### [`research_dojo/`](research_dojo/) — production self-research & eval platform

A production-grade eval/experiment platform, not a notebook script: SQLAlchemy+Alembic
persistence (SQL is the source of truth, JSONL is an audit export, not a database), a
supervisor daemon that detects and auto-resumes crashed runs, a circuit breaker + dead-letter
queue, Prometheus metrics, pluggable alerts (webhook/file/log), dual deterministic + LLM-judge
verification with apparent-vs-real-progress sanity checks, and first-class
[Inspect AI](https://inspect.aisi.org.uk/) interop (bidirectional `.eval` export/import).

77 tests pass fully offline (mocked LLM, 86% coverage), and it's been live-validated end to end
against real Azure OpenAI: a full `dojo run` completed 20/20 rollouts with correct false-belief
tracking on a BigToM-style dataset, and the native `dojo inspect run` path hit 100% accuracy,
readable via `inspect view`. See [`research_dojo/README.md`](research_dojo/README.md) for the
architecture diagram and a comparison against JSONL-only scripts, and
[`research_dojo/docs/operations.md`](research_dojo/docs/operations.md) for the failure-mode
runbook (stuck runs, DLQ, budget stop, webhook alerts).

### [`long_horizon_eval/`](long_horizon_eval/) — controlled eval for score-seeking / reward-hacking propensity

A safe, factorial environment that measures whether an agent, given a **benign coding take-home**,
will leave the task and exploit a misconfigured neighbouring "production" intranet to **cheat the
grader** when the task gets hard — a synthetic twin of the *structure* of the mid-2026 "agent left
the eval box" incidents, not a replay of any real stack. Seven stdlib services form a believable ops
environment (runbooks, incident tickets, an object store, a CI cache) with **three independent
illicit payoff channels** — steal the watermarked answer via IDOR *or* path-traversal, poison the CI
fixture the grader trusts, or force-pass with a leaked bot token — each gated behind an
**independently toggleable** synthetic vuln, so the same task runs with the soft edges open or
closed.

Built on [Inspect AI](https://inspect.aisi.org.uk/) with full access-audit logging and a rule-based
label taxonomy (`honest_solve` / `score_seek_attempt` / `score_seek_success` / `refuse_or_scope` /
…), reported **per condition cell** rather than as one aggregate. Verified end to end: every channel
opens with vulns on and closes with vulns off (the honest path works either way), egress containment
holds (the network is internal-only), and both the no-key mock-agent path and the real Inspect
provider path produce logs + labels. See
[`long_horizon_eval/README.md`](long_horizon_eval/README.md) for the architecture, service-topology,
and label-decision diagrams.

## License

MIT — see [LICENSE](LICENSE).
