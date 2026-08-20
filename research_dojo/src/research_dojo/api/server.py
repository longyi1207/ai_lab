"""`dojo serve [--port 9090]` — minimal FastAPI app: /healthz, /metrics
(Prometheus text exposition), /api/runs (JSON, for a future local dashboard).
"""

from __future__ import annotations

from fastapi import FastAPI, Response

from research_dojo.db.repositories import RunRepo
from research_dojo.db.session import new_session
from research_dojo.metrics.exposition import render_metrics

app = FastAPI(title="research-dojo", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(content=render_metrics(), media_type="text/plain; version=0.0.4")


@app.get("/api/runs")
def api_runs() -> list[dict]:
    session = new_session()
    try:
        runs = RunRepo.list(session)
        return [
            {
                "run_id": r.run_id,
                "experiment_id": r.experiment_id,
                "status": r.status,
                "started_at": str(r.started_at) if r.started_at else None,
                "finished_at": str(r.finished_at) if r.finished_at else None,
                "heartbeat_at": str(r.heartbeat_at) if r.heartbeat_at else None,
                "error_summary": r.error_summary,
            }
            for r in runs
        ]
    finally:
        session.close()


def serve(port: int = 9090, host: str = "127.0.0.1") -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port)
