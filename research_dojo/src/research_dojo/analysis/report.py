"""Human-readable REPORT.md generator (pillar 4.3), written as an artifact
at the end of every run and also available via `dojo metrics show`.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from research_dojo.db.repositories import DLQRepo, JudgmentRepo, MetricRepo, RolloutRepo, RunRepo


def generate_report(session: Session, run_id: str) -> str:
    run = RunRepo.get(session, run_id)
    if run is None:
        raise ValueError(f"run {run_id} not found")
    counts = RolloutRepo.count_by_status(session, run_id)
    agg = MetricRepo.aggregate(session, run_id)
    judgments = JudgmentRepo.list_for_run(session, run_id)
    dlq_count = DLQRepo.count_unresolved(session, run_id)

    scores = [j.score for j in judgments if j.score is not None]
    avg_score = sum(scores) / len(scores) if scores else None
    flagged = sum(1 for j in judgments if j.flags_json.get("flags"))

    lines = [
        f"# Run Report — {run_id}",
        "",
        f"- Experiment: `{run.experiment_id}`",
        f"- Status: **{run.status}**",
        f"- Spec hash: `{run.spec_hash}`",
        f"- Git commit: `{run.git_commit or 'unknown'}`",
        f"- Started: {run.started_at}",
        f"- Finished: {run.finished_at}",
        f"- Error summary: {run.error_summary or 'none'}",
        "",
        "## Rollouts",
        "",
        "| Status | Count |",
        "|---|---|",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"| {status} | {count} |")
    lines += [
        "",
        "## Cost / latency",
        "",
        f"- Estimated cost: ${agg.get('cost_usd_est_total', {}).get('sum', 0.0):.4f}",
        f"- Avg latency: {agg.get('rollout_latency_ms', {}).get('avg', 0.0):.0f} ms",
        f"- Tokens (sum across in+out rows): {agg.get('tokens_total', {}).get('sum', 0.0):.0f}",
        "",
        "## Verification",
        "",
        f"- Judgments recorded: {len(judgments)}",
        f"- Avg judge score: {avg_score:.3f}" if avg_score is not None else "- Avg judge score: n/a",
        f"- Rollouts with sanity flags: {flagged}",
        f"- Unresolved DLQ entries: {dlq_count}",
        "",
        "## Next steps",
        "",
        f"- `dojo metrics show {run_id}` for full metric breakdown",
        f"- `dojo dlq list {run_id}` if DLQ entries are non-zero",
        f"- `dojo bundle export {run_id} -o bundle.tar.gz` for a reproducibility pack",
        "",
    ]
    return "\n".join(lines)
