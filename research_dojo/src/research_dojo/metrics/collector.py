"""Application metrics -> `metrics` table (time-series, pillar 4.1). The
engine calls these right after a rollout completes/fails or a judgment is
recorded; the Prometheus exposition layer reads DB aggregates at scrape time.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from research_dojo.db.repositories import MetricRepo


def record_rollout_success(
    session: Session, run_id: str, arm: str, latency_ms: float,
    tokens_in: int, tokens_out: int, cost_usd_est: float,
) -> None:
    MetricRepo.record(session, run_id, "rollouts_total", 1.0, {"status": "success", "arm": arm})
    MetricRepo.record(session, run_id, "rollout_latency_ms", latency_ms, {"arm": arm})
    MetricRepo.record(session, run_id, "tokens_total", float(tokens_in), {"direction": "in", "arm": arm})
    MetricRepo.record(session, run_id, "tokens_total", float(tokens_out), {"direction": "out", "arm": arm})
    MetricRepo.record(session, run_id, "cost_usd_est_total", cost_usd_est, {"arm": arm})


def record_rollout_failure(session: Session, run_id: str, arm: str) -> None:
    MetricRepo.record(session, run_id, "rollouts_total", 1.0, {"status": "error", "arm": arm})


def record_judge_score(session: Session, run_id: str, score: float, task_type: str = "default") -> None:
    MetricRepo.record(session, run_id, "judge_score", score, {"task_type": task_type})


def record_verification_flag(session: Session, run_id: str, kind: str) -> None:
    MetricRepo.record(session, run_id, "verification_flags_total", 1.0, {"kind": kind})


def record_dlq_depth(session: Session, run_id: str, depth: int) -> None:
    MetricRepo.record(session, run_id, "dlq_depth", float(depth), {})
