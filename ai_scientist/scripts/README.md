# Lightweight mode (portable twin)

Same schemas, same `fs` layout, same skills as V1 — but **the host agent is the supervisor**.
Drop this repo (or just `skills/` plus these scripts) next to any agent and it can run science
without a daemon.

```bash
sci init -p runs/light -d fake_toy --budget-usd 1     # or use scripts + a hand-written config
python scripts/propose_next.py       --project runs/light --bootstrap
python scripts/run_one_experiment.py --project runs/light
python scripts/propose_next.py       --project runs/light      # ingest + propose again
python scripts/check_workers.py      --project runs/light      # best-effort health
sci report -p runs/light --no-narrative
```

## What you keep

- Hypothesis/plan schemas, MAP-Elites + novelty archive, deterministic grading
- The ten skills, loadable by whatever model the host provides
- The same `fs` artifacts, so a run can later be picked up by the V1 daemon

## What you give up (read this before an overnight run)

| | Lightweight | V1 daemon (`sci serve`) |
|---|---|---|
| Health checks | only while something calls `check_workers.py` | timer loop in its own process |
| Crashed worker recovery | next manual call, if any | detected within seconds, requeued |
| Concurrency | one job per script invocation | scheduler with resource locks |
| Survives the chat ending | no | yes |
| Model provider outage | host stalls, nothing supervises | supervision keeps running |

A wedged job in lightweight mode stays wedged until you notice. That is the trade for
portability, and the reason V1 exists.
