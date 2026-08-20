# Operations runbook

Single-machine deploy: SQLite at `<data_dir>/dojo.db` (default
`research_dojo/outputs/dojo.db`), artifacts under `<data_dir>/artifacts/`.
`v1: document single-worker per run_id` — two `dojo run` processes must never
target the same `run_id` concurrently (the unique constraint on `rollouts`
prevents duplicate rows, but two workers racing the same rollout will both
attempt it; the real fix is a lease-based queue, out of scope for v1).

## Starting things

```bash
dojo db migrate                                   # once, or after a schema change
dojo run --spec specs/tom_smoke.yaml               # foreground
dojo run --spec specs/tom_smoke.yaml --detach       # background, prints pid
dojo supervisor start --poll-interval 30 --detach   # watchdog, background
dojo serve --port 9090                              # /healthz, /metrics, /api/runs
```

## Failure mode: stuck / crashed run

**Symptom**: `dojo status --run-id <id>` shows `RUNNING` but `heartbeat` is
old (default staleness threshold 600s, `supervisor.stale_after_seconds` in
the spec).

**What happens automatically** (if `dojo supervisor start` is running):
1. `supervisor/daemon.py:check_once` finds the run, since
   `heartbeat_at` is stale past its configured threshold.
2. Marks it `STALE`, fires a `run_stale` alert.
3. If the run's frozen spec recorded a `_spec_path` that still exists on
   disk, flips it back to `RUNNING` and launches
   `dojo run --spec <path> --resume --run-id <id>` as a detached subprocess.
4. If no `_spec_path` (e.g. spec passed via a temp file that's since been
   deleted), the run stays `STALE` — recover manually (below).

**Manual recovery**:
```bash
dojo status --run-id <id>          # confirm it's STALE / stuck
dojo resume <id>                   # re-reads spec_frozen_json._spec_path, resumes
# or, if you know the spec file:
dojo run --spec specs/tom_smoke.yaml --resume --run-id <id>
```
Resume is always safe to re-run: `RolloutRepo.get_or_create_pending`'s
unique constraint on `(run_id, sample_id, arm, rollout_idx)` means a rollout
already `COMPLETE` is never re-attempted, and a `PENDING`/`RUNNING`/`FAILED`
row is reused rather than duplicated.

**Ctrl+C / SIGTERM mid-run**: the engine installs handlers that set a flag
instead of raising (`engine/run_engine.py:_GracefulStop`); the loop finishes
the in-flight rollout, commits, and exits leaving `status=RUNNING` (not a
terminal status) — so `dojo resume <id>` or the supervisor's stale detector
both pick it up correctly later. Force-kill (`kill -9`) is not graceful; the
in-flight rollout is simply lost and gets picked up fresh on resume (still
no duplicate — it was never marked COMPLETE).

## Failure mode: DLQ non-empty

**Symptom**: `dojo dlq list <run_id>` shows entries; `dlq_non_empty` alert
fired (checked once at the end of every run, in `engine/run_engine.py:_finalize`).

A DLQ entry is written when a rollout's `attempts` counter reaches
`DOJO_MAX_DLQ_ATTEMPTS` (default 5) and it fails again — i.e. it survived
several resume passes and is still failing. It is **not** written on the
first failure; a rollout failing once just sits `FAILED` and gets retried
automatically on the next `dojo resume`.

```bash
dojo dlq list <run_id>                  # see attempts, error, next_retry_at
dojo dlq retry <run_id>                 # reset next_retry_at to now
dojo resume <run_id>                    # actually re-attempt the FAILED rollouts
```
The supervisor also re-enqueues DLQ entries automatically once
`next_retry_at` elapses (exponential backoff, 60s base, capped at 3600s,
`supervisor/daemon.py:DLQ_BASE_RETRY_SECONDS`).

## Failure mode: circuit breaker / repeated API failures

After `DOJO_CIRCUIT_BREAKER_THRESHOLD` (default 5) consecutive rollout
failures, the run opens its circuit: pauses `DOJO_CIRCUIT_BREAKER_COOLDOWN_SECONDS`
(default 60s), fires a `consecutive_failures` alert, then resumes. If the
circuit opens more than 3 times in one run, the engine gives up and marks
the run `FAILED` with `error_summary` containing "circuit breaker" — this is
a hard stop, not auto-resumable by the supervisor (a human should look at
`error` on the failed rollouts first; this usually means the API endpoint or
deployment name is wrong, not a transient blip).

```bash
dojo status --run-id <id>                       # confirms FAILED + error_summary
dojo dlq list <id>                              # rollouts that hit max attempts
# fix the underlying issue (bad deployment name, expired key, etc.), then:
dojo run --spec specs/... --resume --run-id <id>
```

## Failure mode: budget stop

**Symptom**: `dojo status` shows `BUDGET_STOP`; a `budget_threshold`
(warning, 80%) and/or `budget_exceeded` (critical, 100%) alert fired.

This is not a bug — it's the budget gate working as designed
(`spec.budget.max_usd`, checked after every rollout via
`alerts/rules.py:budget_threshold`). To continue past it, either raise
`budget.max_usd` in the spec (or use a fresh spec with a new cap) and
`dojo run --resume --run-id <id>` — completed rollouts are not re-billed.

## Alerts: webhook wiring

```bash
export DOJO_ALERT_WEBHOOK_URL="https://your-endpoint/hook"
dojo alerts test --rule run_failed        # dry-run: dispatches through all
                                           # configured notifiers, including
                                           # the webhook, and records it
dojo alerts history                       # everything dispatched, from `alert_events`
```
Payload: `{"rule": ..., "severity": ..., "message": ..., "run_id": ...}`,
POSTed as JSON with a 10s timeout (`alerts/notifiers.py:WebhookNotifier`). A
failed webhook delivery is logged and recorded in `alert_events.delivered_to`
but never raises — alerting must not crash the run it's alerting about.
`DOJO_ALERT_MIN_SEVERITY` (default `warning`) filters what actually gets
dispatched; `info`-level triggers are suppressed by default.

## Prometheus scrape

```bash
dojo serve --port 9090
```
See `deploy/prometheus.yml` for a ready scrape config, or point any
Prometheus-compatible scraper at `GET /metrics` (`text/plain; version=0.0.4`).
Values are computed fresh from the DB on every scrape — safe to run
`dojo serve` on a different machine/process than the one running the
experiment, as long as they share the DB (Postgres, in that case; SQLite is
single-host only).

## Reproducing a run elsewhere

```bash
dojo bundle export <run_id> -o bundle.tar.gz
```
Tarball contains the frozen spec + a JSON slice of every DB row for that run
+ the full `artifacts/<run_id>/` tree (including any Inspect `.eval` export).
Nothing in it depends on the original machine's live DB.

## `docker compose --profile ops` (optional Postgres + Prometheus)

```bash
docker compose --profile ops up -d
export DOJO_DATABASE_URL=postgresql://dojo:dojo@localhost:5432/dojo
dojo db migrate
```
Not required for `pytest` or the default SQLite path — this profile exists
for a future "team production" story (multiple workers sharing one DB), not
for the v1 acceptance bar.
