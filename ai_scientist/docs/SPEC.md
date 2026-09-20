# AI Scientist — V1 SPEC

**Status:** implementable contract · 2026-09-19  
**Parent:** [`../DESIGN.md`](../DESIGN.md)  
**Rule:** If DESIGN and SPEC disagree, amend DESIGN explicitly, then fix SPEC.

This is what to code against for **V1** (daemon). Lightweight mode reuses the same schemas/skills/`fs` where marked.

---

## 1. Package layout

```text
ai_scientist/
├── README.md
├── DESIGN.md
├── docs/
│   ├── SPEC.md              ← this file
│   └── RELATED.md
├── pyproject.toml
├── .env.example             # refs only; no secrets
├── skills/                  # agent skills (host + workers)
│   ├── phase1_intake/
│   ├── design_debate/
│   ├── hypothesize/
│   ├── plan_experiment/
│   ├── truth_debate/
│   ├── truth_judge/
│   ├── results_writeup/
│   ├── final_report/
│   ├── ops_triage/
│   └── outer_route/
├── scripts/                 # lightweight twin (host agent is supervisor)
│   ├── propose_next.py
│   ├── run_one_experiment.py
│   ├── check_workers.py     # best-effort only
│   └── README.md
├── src/ai_scientist/
│   ├── schema/
│   ├── fs_layout/
│   ├── search/              # MAP + novelty
│   ├── ops/                 # substrate + phase2_ops + experiment_agent
│   ├── daemon/              # scheduler/health/orch loops + ops_triage loop + RPC
│   ├── mcp/                 # stdio MCP over control API
│   ├── phase1.py            # Phase-1 intake driver (+ auto-research)
│   ├── outer.py             # Outer harness agent (`outer_route`)
│   ├── research.py          # Phase-1 web fetch / search notes
│   ├── skills_loader/
│   ├── domain/
│   │   ├── fake_toy.py
│   │   └── oversight_debate/  # first real pack
│   └── cli.py               # sci …
├── tests/
└── runs/                    # gitignored project workspaces
```

CLI entry: `sci`. Python ≥ 3.11.

---

## 2. Run workspace (`fs`)

Each study/project root (e.g. `runs/<project_id>/`):

```text
runs/<project_id>/
├── metadata.yaml
├── hypothesis.md            # or hypothesis.yaml
├── experiment_spec.yaml
├── intake_log.md
├── archive/
│   ├── map.json             # or sqlite
│   ├── novelty.jsonl
│   └── elites/<elite_id>/
│       ├── hypothesis…
│       ├── plan…
│       ├── results…
│       ├── metrics.json
│       └── results_writeup.md
├── queue/
│   └── jobs.jsonl           # or DB table mirrored to fs
├── jobs/<job_id>/
│   ├── spec_snapshot/
│   ├── logs/
│   ├── artifacts/
│   └── results_writeup.md
├── state/
│   ├── daemon.sqlite        # V1 source of truth for workers/heartbeats
│   └── …
├── report/
│   └── final_report.md
└── audit/
    └── …
```

**Credentials:** only env/vault **names** in `metadata.yaml` (e.g. `azure_openai_via: env:AZURE_OPENAI_*`). Never commit secrets.

---

## 3. Core schemas (logical)

### 3.1 `metadata.yaml` (Phase 1)

```yaml
project_id: ...
budget: { max_usd: 30, max_tokens: null }
time: { deadline: null, overnight_ok: true }
credentials_refs: [AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_DEPLOYMENT]
audience: self
style: rigorous   # rigorous | casual
topic_fidelity: stuck_or_discovery  # stuck | discovery | mixed
extensible: true
knowledge_sources: [web_default]
tools: [web, fs, basic]
assumptions: ["…"]
updated_at: ...
```

### 3.2 Hypothesis

Structured claim + plain-language statement. Must be mutable by `hypothesize` skill and addressable by id.

### 3.3 Experiment plan / spec

Runnable description: domain pack id, metrics, baselines, resource hints (`gpu: 0|1|…`, `api_concurrency`), seeds, train/heldout splits if any. Validated by code before enqueue.

### 3.4 Job

```json
{
  "job_id": "...",
  "elite_or_candidate_id": "...",
  "hypothesis_ref": "...",
  "plan_ref": "...",
  "priority": 0.0,
  "resources": {"gpu": 0, "api_slots": 1},
  "status": "queued|running|done|failed|stale",
  "worker_id": null,
  "created_at": "...",
  "heartbeat_at": null
}
```

### 3.5 Elite / archive record

`{hypothesis, plan, results, metrics, results_writeup, descriptor, fitness, lineage}` — exact fields in code models; MAP cell key derived from domain descriptors.

### 3.6 Metrics

Domain-defined. System requires at least: `fitness: float`, `descriptor: object`, optional `verification_flags: string[]`.

---

## 4. Daemon ops substrate (V1)

### 4.1 Processes

| Loop | Period | Responsibility |
|------|--------|----------------|
| Scheduler | event / ~100–500ms | Pop queue by priority; acquire locks; kickoff/assign workers; record state |
| Healthcheck | ~1–5s | Heartbeat timeout → STALE → kill/release → restart or requeue per policy |
| Orchestrator | ~scheduler | Ingest finished trials; propose/enqueue candidates; budget stop |
| Phase-2 ops | ~5s / on events | LLM `ops_triage` writes priorities / failure actions / concurrency into state |

Workers: separate processes or tasks; **must heartbeat**.

### 4.2 Scheduler pseudocode

```text
loop:
  slots = free_resources()
  while slots and queue.nonempty:
    job = pop_highest_priority()
    if not acquire_locks(job.resources):
      requeue(job); continue
    start_worker(job)
    record_state(...)
```

### 4.3 Healthcheck pseudocode

```text
loop:
  for worker in active:
    if now - heartbeat > timeout:
      mark_stale; kill; release_locks
      restart_or_requeue(policy)
```

### 4.4 Control API (CLI + MCP share)

| Method | Behavior |
|--------|----------|
| `serve(project)` | Start daemon for project root |
| `start_run(project)` | Ensure daemon up; load Phase-1 artifacts; begin search/enqueue |
| `status(project)` | Queue depth, workers, spend, top elites |
| `pause` / `resume` | Scheduler gate |
| `set_concurrency(n)` | Runtime cap |
| `pin` / `ban` | Archive intervention |
| `restart_worker(id)` | Substrate restart |
| `tail(job_id)` | Log / writeup paths |
| `ask(message)` / `sci ask` | Outer harness agent (`outer_route`) → control calls |
| `daemon_restart` | Reload after code change |

Idempotent where noted in implementation; all mutating calls audited to `audit/`.

---

## 5. Evolutionary search

- **Mutate:** `hypothesis` + `experiment_plan` via skills `hypothesize`, `plan_experiment`  
- **Select parents:** code (MAP cell mix + novelty) — see DESIGN §8  
- **Evaluate:** domain runner → metrics + results → optional truth-seeking skills → results_writeup skill  
- **Insert:** MAP + novelty update  
- **Descriptors / fitness:** domain pack  

Config lives in project or domain defaults (bins, k-NN, operator weights) — not hardcoded to oversight.

---

## 6. Skills inventory

| Skill ID | Role |
|----------|------|
| `phase1_intake` | Read, research, ask, draft H+spec+metadata |
| `design_debate` | Attack/improve H+spec |
| `hypothesize` | Propose/mutate hypotheses |
| `plan_experiment` | H → runnable plan |
| `truth_debate` / `truth_judge` | Phase-2 adversarial truth seeking |
| `results_writeup` | Per-job lab note (experiment agent) |
| `final_report` | Phase-3 report |
| `outer_route` | Anytime human NL — **IDE host + MCP**; headless twin `sci ask` / Agent |
| `ops_triage` | Soft fleet decisions — Agent loop + `get_queue`/`get_fleet` tools |

Each skill: `SKILL.md` (or host-native format) + declared tools. Loadable by IDE host and by daemon workers.

---

## 7. Lightweight mode

- Same `fs` layout and skills.  
- Host agent calls `scripts/*.py` instead of relying on daemon loops.  
- `check_workers.py` is **best-effort**; no unattended guarantee.  
- Documented as portable twin; README north star remains V1.

---

## 8. Domain pack interface

A domain pack provides:

| Hook | Purpose |
|------|---------|
| `validate_plan(plan)` | Schema + domain rules |
| `run(plan, job_dir) -> results` | Execute trial |
| `grade(results) -> metrics` | Fitness + descriptor features |
| `probe_descriptor(metrics) -> cell` | MAP axes |
| `seed_hypotheses()` / `seed_plans()` | Optional seeds |
| optional skills overlays | Domain-specific prompts |

First real pack: `src/ai_scientist/domain/oversight_debate/` — details owned by the pack, not this SPEC.
Offline reference pack: `fake_toy`.

---

## 9. LLM / Azure

Prefer Azure OpenAI when configured (`OPENAI_PREFER_AZURE`, repo `.env` / vault refs). Confirm with user before any single run `max_usd > 50`. Fake/deterministic LLM for offline tests.

---

## 10. Testing bar (V1)

| Area | Assert |
|------|--------|
| Schemas | Invalid plan rejected |
| MAP/novelty | Insert/replace rules under synthetic metrics |
| Scheduler | Lock prevents double kickoff |
| Healthcheck | Kill heartbeat → restart/requeue |
| Resume | Daemon kill mid-job → resume without corrupt archive |
| MCP/CLI | `status` reflects queue after `enqueue` |
| Skills | Loader finds inventory; dry-run prompts |
| Offline | Full tiny loop with FakeLLM + fake domain |

---

## 11. Implementation slices (toward V1)

| # | Slice | State |
|---|-------|-------|
| 1 | Schemas + `fs` layout + CLI | **done** |
| 2 | MAP/novelty + selection + mutators (+ tests) | **done** |
| 3 | Daemon scheduler + healthcheck + sqlite state | **done** |
| 4 | Skills inventory + loader; Phase-1 *driver* | **done** (`sci intake`, research, `phase1.IntakeSession`) |
| 5 | Fake domain end-to-end (incl. real subprocess path) | **done** |
| 6 | MCP server over the control API | **done** (`sci mcp` / `python -m ai_scientist.mcp`) |
| 7 | First real domain pack (`oversight_debate`) | **done** |
| 8 | Lightweight twin scripts + docs | **done** (`scripts/` + `scripts/README.md`) |
| 9 | Outer harness agent (`outer_route`) | **done** (`sci ask`, MCP `sci_ask`) |
| 10 | Phase-2 ops agent (`ops_triage`) | **done** (daemon loop + intent apply) |
| 11 | Experiment agent (worker body) | **done** (`ops/experiment_agent.py`) |

No product naming of these slices as v0/v0.5. V1 contract slices above are complete as of 2026-09-19.

### 11.1 Deviations from this spec, as built

| Spec text | As built | Why |
|---|---|---|
| `state/daemon.sqlite` via unspecified ORM | stdlib `sqlite3` (no SQLAlchemy) | the watchdog must run with zero optional deps |
| `queue/jobs.jsonl` | jobs live in the state db; `audit/events.jsonl` is the append-only trail | one writer for queue state, mirrored to audit instead of duplicated |
| engine knobs in `metadata.yaml` | `config.yaml` (engine) vs `metadata.yaml` (Phase-1 semantics) | Phase 1 is an agent/human contract; ops knobs churn separately |
| `domains/` at package root | packs live under `src/ai_scientist/domain/` | one import path; external packs still load via `module:factory` |
| truth-seeking placement unspecified | runs in the worker, flags fold into metrics before ingest | per-trial work parallelizes; archive stays single-writer |
| — | `settle()` after a synchronous run | otherwise `sci run` could return while finished jobs still held locks |
| MCP transport unspecified | newline-delimited JSON-RPC 2.0 on stdio, zero extra deps | matches Cursor / Claude Code hosts without pulling an MCP SDK |
| Phase-1 “auto-research” unspecified | `research.gather` fetches URLs + DuckDuckGo HTML; skips under `AI_SCIENTIST_NO_WEB` / FakeLLM | offline tests must not hang; notes still recorded |
| “experiment agents” | `ExperimentAgent` wraps domain.run + verify + writeup in worker process | domain owns `run`; agent owns epistemic hygiene around a trial |
