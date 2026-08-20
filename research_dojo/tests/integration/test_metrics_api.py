from __future__ import annotations


def test_prometheus_exposition_renders(dojo_env):
    from research_dojo.db.repositories import ExperimentRepo, MetricRepo, RunRepo
    from research_dojo.db.session import new_session
    from research_dojo.metrics.exposition import render_metrics

    session = new_session()
    ExperimentRepo.get_or_create(session, "exp", "h")
    RunRepo.create(session, "r1", "exp", {"spec_hash": "x"}, "x")
    MetricRepo.record(session, "r1", "rollouts_total", 1.0, {"status": "success", "arm": "baseline"})
    MetricRepo.record(session, "r1", "cost_usd_est_total", 0.05, {"arm": "baseline"})
    session.commit()
    session.close()

    text = render_metrics().decode("utf-8")
    assert "dojo_rollouts_total" in text
    assert "dojo_cost_usd_est_total" in text
    assert 'run_id="r1"' in text


def test_api_server_healthz_and_runs(dojo_env):
    from fastapi.testclient import TestClient

    from research_dojo.api.server import app
    from research_dojo.db.repositories import ExperimentRepo, RunRepo
    from research_dojo.db.session import new_session

    session = new_session()
    ExperimentRepo.get_or_create(session, "exp", "h")
    RunRepo.create(session, "r1", "exp", {"spec_hash": "x"}, "x")
    session.commit()
    session.close()

    client = TestClient(app)
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

    r = client.get("/metrics")
    assert r.status_code == 200
    assert "dojo_runs_by_status" in r.text

    r = client.get("/api/runs")
    assert r.status_code == 200
    ids = [row["run_id"] for row in r.json()]
    assert "r1" in ids
