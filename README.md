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

### [`ai_scientist/`](ai_scientist/) — evolutionary AI research harness

An IDE-primary evolutionary harness: Phase 1 intake → Phase 2 MAP-Elites / novelty search over
`{hypothesis, plan}` → Phase 3 report. Deterministic daemon substrate (queue, locks, kickoff,
heartbeat, resume, spend accounting) plus agent skills for cognition; Cursor / Claude Code drive
it via local skills + MCP `sci_*` tools (CLI / `sci ask` are the headless twin).

First real domain pack is `oversight_debate` (solo / consultancy / debate under an evidence-poor
judge, paired `delta_vs_solo`); `fake_toy` is the offline reference. Offline test suite is green
(~130 tests, FakeLLM / scripted seats — no API spend required for CI). Sibling patterns from
[`research_dojo/`](research_dojo/) (durable eval platform) are reused, not reimplemented. Start at
[`ai_scientist/README.md`](ai_scientist/README.md); design source of truth is
[`ai_scientist/DESIGN.md`](ai_scientist/DESIGN.md).

### [`cyber_ai_fundamentals/`](cyber_ai_fundamentals/) — cyber → AI x cyber, a from-zero primer

Not a hands-on project like the others above — a sourced reading/orientation deck for going
from zero cybersecurity background to literacy: CIA triad, OWASP/CWE, the CVE→CVSS→NVD→KEV
vulnerability lifecycle, MITRE ATT&CK, NIST incident-response — then two real 2025–2026 cases
where AI and cyber actually intersected, framed as two structurally opposite failure modes: a
human weaponizing a jailbroken model (Anthropic's disclosed AI-orchestrated espionage campaign,
GTG-1002) vs. a model's own eval-time reward hacking spilling into real infrastructure
(ExploitGym/OpenAI×Hugging Face). Every factual claim cites an English-language primary source
(NIST/MITRE/CISA/FIRST.org/RAND/Anthropic/OpenAI/Hugging Face/UK AISI) inline. Published in
parallel English and Chinese editions — start with
[`cyber_ai_fundamentals/notes.pdf`](cyber_ai_fundamentals/notes.pdf) (English) or
[`notes_zh.pdf`](cyber_ai_fundamentals/notes_zh.pdf) (Chinese).

The GTG-1002 case gets a full standalone deep-dive beyond what either deck has room for —
Anthropic's complete six-phase task breakdown, the AI-hallucination-in-offensive-ops caveat,
independent security researchers' skepticism (the report published no IoCs), and a September
2026 follow-up showing the same operating model has since spread to at least five more named
threat groups. See
[`cyber_ai_fundamentals/deep_reads/01_GTG-1002_Anthropic_2025-11_案例深读.md`](cyber_ai_fundamentals/deep_reads/01_GTG-1002_Anthropic_2025-11_案例深读.md)
(Chinese prose, English-language sources linked throughout).

And where the decks stay at literacy level, [`cyber_ai_fundamentals/labs/ssrf_killchain/`](cyber_ai_fundamentals/labs/ssrf_killchain/)
turns that abstract Task 1-5 table into a runnable, reproducible lab: a self-built three-service
Docker target (public SSRF app + internal-only admin API + fake cloud-metadata endpoint) that
reproduces the Capital One 2019 pattern — SSRF → internal enumeration → cloud IAM credential
theft — with real tooling, an out-of-band callback verifier, and captured run output, each step
mapped back to GTG-1002. Sandboxed, self-authored, authorized learning environment; all
credentials fake.

## License

MIT — see [LICENSE](LICENSE).
