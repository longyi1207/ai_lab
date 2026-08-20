"""Prometheus text exposition for `GET /metrics` (pillar 4.2). Reads DB
aggregates fresh on each scrape — no long-lived process state, which keeps
`dojo serve` restart-safe and correct across multiple worker processes.
"""

from __future__ import annotations

from prometheus_client import CollectorRegistry, Gauge, generate_latest

from research_dojo.db.repositories import DLQRepo, MetricRepo, RunRepo
from research_dojo.db.session import session_scope


def render_metrics() -> bytes:
    registry = CollectorRegistry()
    rollouts_total = Gauge(
        "dojo_rollouts_total", "Rollouts by run and status", ["run_id", "status"], registry=registry
    )
    latency_avg = Gauge(
        "dojo_rollout_latency_ms_avg", "Average rollout latency (ms)", ["run_id"], registry=registry
    )
    tokens_total = Gauge(
        "dojo_tokens_total", "Tokens by run and direction", ["run_id", "direction"], registry=registry
    )
    cost_total = Gauge("dojo_cost_usd_est_total", "Estimated cost (USD) by run", ["run_id"], registry=registry)
    judge_score_avg = Gauge("dojo_judge_score_avg", "Average judge score by run", ["run_id"], registry=registry)
    verification_flags = Gauge(
        "dojo_verification_flags_total", "Verification sanity flags by run", ["run_id"], registry=registry
    )
    dlq_depth = Gauge("dojo_dlq_depth", "Unresolved DLQ entries by run", ["run_id"], registry=registry)
    runs_by_status = Gauge("dojo_runs_by_status", "Number of runs by status", ["status"], registry=registry)

    with session_scope() as session:
        runs = RunRepo.list(session)
        status_counts: dict[str, int] = {}
        for run in runs:
            status_counts[run.status] = status_counts.get(run.status, 0) + 1
            agg = MetricRepo.aggregate(session, run.run_id)

            if "rollout_latency_ms" in agg:
                latency_avg.labels(run_id=run.run_id).set(agg["rollout_latency_ms"]["avg"])
            if "cost_usd_est_total" in agg:
                cost_total.labels(run_id=run.run_id).set(agg["cost_usd_est_total"]["sum"])
            if "judge_score" in agg:
                judge_score_avg.labels(run_id=run.run_id).set(agg["judge_score"]["avg"])
            if "verification_flags_total" in agg:
                verification_flags.labels(run_id=run.run_id).set(agg["verification_flags_total"]["sum"])
            dlq_depth.labels(run_id=run.run_id).set(DLQRepo.count_unresolved(session, run.run_id))

            per_status: dict[str, float] = {}
            for m in MetricRepo.list_for_run(session, run.run_id, name="rollouts_total"):
                status = m.labels_json.get("status", "unknown")
                per_status[status] = per_status.get(status, 0.0) + m.value
            for status, total in per_status.items():
                rollouts_total.labels(run_id=run.run_id, status=status).set(total)

            per_direction: dict[str, float] = {}
            for m in MetricRepo.list_for_run(session, run.run_id, name="tokens_total"):
                direction = m.labels_json.get("direction", "unknown")
                per_direction[direction] = per_direction.get(direction, 0.0) + m.value
            for direction, total in per_direction.items():
                tokens_total.labels(run_id=run.run_id, direction=direction).set(total)

        for status, count in status_counts.items():
            runs_by_status.labels(status=status).set(count)

    return generate_latest(registry)
