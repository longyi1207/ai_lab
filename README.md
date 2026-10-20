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

### [`rl_pipeline/`](rl_pipeline/) — training an agent away from shortcuts, one decision at a time

An end-to-end pipeline that turns recorded episodes of agents cheating on tasks into training
signal. It finds the step where each agent turned toward the shortcut, rebuilds the environment
at that step in a fresh container (re-running and verifying every recorded command), samples
alternative continuations, grades them, and fine-tunes on the difference: DPO on Azure OpenAI, plus
hand-written DPO and GRPO that run on a laptop, and the environments served through OpenEnv's
standard `reset` / `step` interface.

Everything ran for real (about $27): 78 of 80 branch points rebuilt faithfully, 228 graded
continuations, 92 preference pairs, a DPO job, and a paired evaluation on held-out branch points.
The honest result is negative: the tuned model did not take fewer shortcuts, and reading the
pairs shows why (only 4 of 92 put the exploit on the rejected side; the preference landed on
harmless early moves). The laptop trainers check out against TRL and learn a toy task. See
[`rl_pipeline/README.md`](rl_pipeline/README.md) and its
[`docs/concepts.md`](rl_pipeline/docs/concepts.md), written for people new to the area. It is the
training-side companion to `long_horizon_eval/` above.

### [`multi_agent_attack_exp/`](multi_agent_attack_exp/) — split multi-agent attacks vs AI-control monitors

A laptop-scale replication of Kitaoka et al. (2026), *Red-Teaming Multi-Agent Attacks for
Loss-of-Control Risks* ([arXiv:2610.24052](https://arxiv.org/abs/2610.24052)). Three AI agents
each do one ordinary-looking piece of work in a simulated AI lab, and an automated process combines
the pieces into a harmful outcome, such as restoring a held model's weights. A monitor model tries
to catch it reading each agent alone, the whole team, or a single agent doing everything.

**MiniLab-lite** is four Dockerised services with Linux-account permissions and hidden
deterministic graders. A scripted check (23/23 variants, no model calls) proves that every
attack fragment is necessary. The paper's executor and monitor prompts are used verbatim, with
the same models (DeepSeek-V4-Pro executors, GPT-5.6 Sol and Luna monitors) and the same scoring
(12 readings, median, 7.5 threshold).

Pilot result: per-agent monitoring flagged 1/12 split attacks, matching the paper's 7%. The solo
baseline flagged only 5/12, against the paper's 87%, once the solo plan was held to the same
commands as the team: most attacks hide by not printing the exposing record, and one agent can
do that too. A free Level 0 (play an operator account in the world) and about $1 for a full pilot
on the weak monitor. See [`multi_agent_attack_exp/README.md`](multi_agent_attack_exp/README.md).

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

### [`cyber_ai_fundamentals/`](cyber_ai_fundamentals/) — cyber → AI x cyber: beginner's map to extreme risk & safeguards

Not a hands-on engineering project like the others above — a sourced reading/orientation deck.
Part I goes from zero cybersecurity background to literacy: CIA triad, OWASP/CWE, the
CVE→CVSS→NVD→KEV vulnerability lifecycle, MITRE ATT&CK, NIST incident-response — then two real
2025–2026 cases where AI and cyber actually intersected, framed as two structurally opposite
failure modes: a human weaponizing a jailbroken model (Anthropic's disclosed AI-orchestrated
espionage campaign, GTG-1002) vs. a model's own eval-time reward hacking spilling into real
infrastructure (ExploitGym/OpenAI×Hugging Face). Part II adds an AI-safety lens on cyber misuse:
why AI x cyber is a class of "extreme risk," how cyber capability is measured, how frontier labs
handle cyber misuse (RSP/Preparedness/FSF comparison; the shift from "refuse cyber" to
"KYC/trusted-access + accelerate defenders"; why cyber is harder to safeguard than bio), and the
US/China/other governance map by force-of-law. Every factual claim cites an English-language
primary source (NIST/MITRE/CISA/FIRST.org/RAND/Anthropic/OpenAI/Hugging Face/UK AISI/CAISI) inline;
every claim carries its own inline primary source. Published in parallel English and Chinese
editions — start with
[`cyber_ai_fundamentals/notes.pdf`](cyber_ai_fundamentals/notes.pdf) (English) or
[`notes_zh.pdf`](cyber_ai_fundamentals/notes_zh.pdf) (Chinese). Anthropic's original GTG-1002 report
is kept alongside them at [`cyber_ai_fundamentals/reports/`](cyber_ai_fundamentals/reports/).

And where the decks stay at literacy level, [`cyber_ai_fundamentals/labs/`](cyber_ai_fundamentals/labs/)
holds three runnable, reproducible Docker labs, each focused on one core tool / vulnerability class,
each with real captured output and a self-built target on an isolated network (sandboxed, authorized,
fake credentials): **ssrf_killchain** (nmap/curl/Python — reproduces the Capital One 2019 SSRF →
internal enumeration → cloud IAM credential theft, mapped to GTG-1002's Task 1-5), **sqli_lab**
(sqlmap against a deliberately injectable app — detect, dump a hidden users table, auto-crack the
hashes), and **metasploit_cve_lab** (Metasploit against a real Apache Struts2 S2-045 / CVE-2017-5638
target — recon, hand-proven root RCE, then confirmed with the module's `check`).

### [`openai_math_explained/`](openai_math_explained/) — OpenAI's Oct-2026 AI-generated math release, explained from zero

A sourced reading deck in parallel English and Chinese editions, like `cyber_ai_fundamentals`.

**Part I (§0–§17): the release.** On 2026-10-06 OpenAI released 722 (now 719) AI-generated math
manuscripts. They claim results such as the quasi-Riemann hypothesis, the Unique Games Conjecture,
the matrix-multiplication exponent ω ≤ 9/4, the non-amenability of Thompson's group F and the
four-dimensional Kakeya conjecture. The deck takes 11 headline results, one section each. Each section builds the result up from basic concepts,
with hand-checkable examples and exercises. It then gives OpenAI's exact claim and how far it is
verified, reading each Lean statement line by line. Part I also summarizes a static audit of the
26M-line Lean library, studies the withdrawn papers, and asks what the release means for AI.

**Part II (§18–§24): what happens if AI solves mathematics at scale.**
- §18 calibrates with history: 14 cases of math becoming real-world impact, with their lag times.
  It explains when math is and is not the bottleneck, reviews the AI-for-science record so far, and
  sets out three capability curves.
- §19–§23 each pick the problems that matter most in one field: computing, cryptography and quantum;
  physics, chemistry and materials; biology, medicine and neuroscience; AI theory and alignment;
  economics, society and governance. For each problem they ask whether math is the bottleneck, what
  AI changes, what the deeper impacts are, and when.
- §24 gives the cross-field picture, a top 10 and a timeline to the 2030s.

Start with [`openai_math_explained/notes_en.pdf`](openai_math_explained/notes_en.pdf) (English) or
[`notes.pdf`](openai_math_explained/notes.pdf) (Chinese).

## License

MIT — see [LICENSE](LICENSE).
