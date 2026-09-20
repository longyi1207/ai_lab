# ai_scientist

Evolutionary **AI research harness**: Phase 1 intake → Phase 2 search/run loop → Phase 3 report.

- **UX:** IDE-primary (Cursor / Claude Code) via skills + MCP / CLI control API
- **Aim:** **V1** daemon ops substrate (healthcheck, queue, resource locks, kickoff, resume)
- **Twin:** the same skills + `scripts/` run in any agent host (portability), without unattended guarantees
- **Phenotype:** search mutates `{hypothesis, plan}`; the archive stores `{hypothesis, plan, results, metrics}`
- **Diversity:** MAP-Elites over domain descriptor axes + a novelty archive over behavior vectors
- **Domains:** `fake_toy` (offline reference) and `oversight_debate` (first real pack)

| Doc | Role |
|-----|------|
| [`DESIGN.md`](./DESIGN.md) | System design (source of truth) |
| [`docs/SPEC.md`](./docs/SPEC.md) | V1 contracts: schemas, `fs` layout, control API, domain interface |
| [`docs/RELATED.md`](./docs/RELATED.md) | Lineage / contrast (FunSearch, MAP-Elites, debate, Sakana) |
| [`docs/IDE.md`](./docs/IDE.md) | **How skills + MCP actually work in Cursor / Claude Code** |
| [`scripts/README.md`](./scripts/README.md) | Lightweight twin (no daemon) |

## Quickstart

```bash
python3.13 -m venv .venv && source .venv/bin/activate   # or: uv venv --python 3.13
pip install -e ".[dev]"
pytest                                                   # ~120 tests, fully offline

sci init -p runs/demo -q "does adversarial structure beat direct answering?" --budget-usd 1
sci intake -p runs/demo --brief "compare debate vs solo under a weak judge"   # Phase 1
sci run  -p runs/demo --jobs 12        # synchronous, bounded: seeds → mutate → run → archive
sci status -p runs/demo                # queue, locks, spend, top elites
sci map    -p runs/demo                # occupancy grid over descriptor axes
sci report -p runs/demo                # Phase-3 report into report/final_report.md
```

Long / unattended runs use the daemon instead of a bounded synchronous run:

```bash
sci serve -p runs/demo --detach   # scheduler + healthcheck + orchestrator + control plane
sci concurrency 3 -p runs/demo    # runtime policy, no code change
sci pin <elite_id> -p runs/demo   # taste injection: make an elite immortal
sci stop -p runs/demo
```

IDE hosts can drive the same control plane over MCP (stdio JSON-RPC):

```bash
sci mcp -p runs/demo              # or: python -m ai_scientist.mcp --project runs/demo
```

Tools include `sci_init`, `sci_status`, `sci_start_run`, `sci_run_sync`, pause/resume,
concurrency, elites/map/pin/ban, report, events, domains, skills, stop.

Lightweight twin (host agent is the supervisor — see [`scripts/README.md`](./scripts/README.md)):

```bash
python scripts/propose_next.py --project runs/demo --bootstrap
python scripts/run_one_experiment.py --project runs/demo
python scripts/check_workers.py --project runs/demo   # best-effort only
```

Sample output from a 13-job toy run: 3/12 cells filled, best fitness 0.52 at cell `[2,0]`,
spend $0.031, every elite flagged `verification_unavailable` because no real judge model was
configured — the harness reports that rather than treating unverified results as verified.

## What is code vs what is a skill

| Deterministic code | Agent skill |
|---|---|
| MAP-Elites, novelty archive, descriptor binning | `hypothesize`, `plan_experiment` |
| Queue, resource locks, kickoff, heartbeat, restart, resume | `design_debate`, `truth_debate`, `truth_judge` |
| State db, spend accounting, budget stop, audit log | `results_writeup`, `final_report` |
| Schema and plan validation; Phase-1 driver | `phase1_intake`, `ops_triage`, `outer_route` |

`sci skills list` shows the inventory; skills are plain markdown with frontmatter, so they load
in an IDE host or inside a daemon worker.

## Status

**V1 slices complete** (SPEC §11): schemas + `fs`, MAP/novelty, daemon ops substrate (scheduler /
health / orch / **ops_triage**), skills + Phase-1 intake **with auto-research**, Outer agent
(`sci ask` / MCP `sci_ask`), experiment agent workers, MCP stdio server, `fake_toy` +
`oversight_debate` packs, lightweight `scripts/` twin, CLI, verification, Phase-3 report.
Offline test suite is green.

```bash
sci ask -p runs/demo "pause the fleet and show top elites"
```

Adding a domain pack means implementing `axes`, `param_space`, `validate_plan`, `run`, `grade`,
`seed_candidates` — see [`src/ai_scientist/domain/fake_toy.py`](./src/ai_scientist/domain/fake_toy.py)
or the real pack under [`domain/oversight_debate/`](./src/ai_scientist/domain/oversight_debate/).

**Sibling:** [`research_dojo`](../research_dojo/) — durable eval platform; patterns reused here, not reimplemented.

## License

MIT (same as `ai_lab`).
