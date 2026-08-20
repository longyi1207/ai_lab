"""`dojo` CLI — Typer app. See README.md for the full command surface."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import typer

from research_dojo.config.settings import PACKAGE_ROOT, get_settings
from research_dojo.db.models import RunStatus
from research_dojo.db.repositories import (
    AlertRepo,
    DLQRepo,
    ExperimentRepo,
    MetricRepo,
    RolloutRepo,
    RunRepo,
)
from research_dojo.db.session import new_session

app = typer.Typer(help="research-dojo: production self-research + eval platform", no_args_is_help=True)
experiment_app = typer.Typer(help="Experiment registry")
bundle_app = typer.Typer(help="Reproducibility bundles")
supervisor_app = typer.Typer(help="Self-healing supervisor daemon")
dlq_app = typer.Typer(help="Dead-letter queue")
metrics_app = typer.Typer(help="Metrics")
inspect_app = typer.Typer(help="Inspect AI interop")
alerts_app = typer.Typer(help="Alerts")
db_app = typer.Typer(help="Database")

app.add_typer(experiment_app, name="experiment")
app.add_typer(bundle_app, name="bundle")
app.add_typer(supervisor_app, name="supervisor")
app.add_typer(dlq_app, name="dlq")
app.add_typer(metrics_app, name="metrics")
app.add_typer(inspect_app, name="inspect")
app.add_typer(alerts_app, name="alerts")
app.add_typer(db_app, name="db")


# ---------------------------------------------------------------- lifecycle

@app.command("run")
def run_cmd(
    spec: str = typer.Option(..., "--spec", help="Path to experiment spec YAML"),
    run_id: str | None = typer.Option(None, "--run-id"),
    resume: bool = typer.Option(False, "--resume"),
    detach: bool = typer.Option(False, "--detach"),
) -> None:
    if detach:
        cmd = [sys.executable, "-m", "research_dojo.cli.main", "run", "--spec", spec]
        if run_id:
            cmd += ["--run-id", run_id]
        if resume:
            cmd += ["--resume"]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        typer.echo(f"detached run launching (pid={proc.pid})")
        return

    from research_dojo.engine.run_engine import run_experiment

    rid = run_experiment(spec, run_id=run_id, resume=resume)
    typer.echo(f"run_id={rid}")


@app.command("status")
def status_cmd(
    run_id: str | None = typer.Option(None, "--run-id"),
    watch: bool = typer.Option(False, "--watch"),
) -> None:
    def _print_once() -> None:
        session = new_session()
        try:
            runs = [r for r in [RunRepo.get(session, run_id)] if r] if run_id else RunRepo.list(session)
            if not runs:
                typer.echo("no runs found")
            for r in runs:
                counts = RolloutRepo.count_by_status(session, r.run_id)
                dlq = DLQRepo.count_unresolved(session, r.run_id)
                typer.echo(
                    f"{r.run_id}  status={r.status}  rollouts={counts}  dlq={dlq}  "
                    f"heartbeat={r.heartbeat_at}  error={r.error_summary or ''}"
                )
        finally:
            session.close()

    if not watch:
        _print_once()
        return
    try:
        while True:
            print("\033c", end="")  # ANSI clear
            _print_once()
            time.sleep(3)
    except KeyboardInterrupt:
        pass


@app.command("cancel")
def cancel_cmd(run_id: str) -> None:
    session = new_session()
    try:
        run = RunRepo.get(session, run_id)
        if run is None:
            typer.echo(f"run {run_id} not found", err=True)
            raise typer.Exit(1)
        RunRepo.set_status(session, run_id, RunStatus.CANCELLED)
        session.commit()
        typer.echo(f"run {run_id} marked CANCELLED")
    finally:
        session.close()


@app.command("resume")
def resume_cmd(run_id: str) -> None:
    session = new_session()
    try:
        run = RunRepo.get(session, run_id)
    finally:
        session.close()
    if run is None:
        typer.echo(f"run {run_id} not found", err=True)
        raise typer.Exit(1)
    spec_path = (run.spec_frozen_json or {}).get("_spec_path")
    if not spec_path:
        typer.echo("no recorded spec path on this run; use `dojo run --spec ... --resume --run-id ...`", err=True)
        raise typer.Exit(1)
    from research_dojo.engine.run_engine import run_experiment

    rid = run_experiment(spec_path, run_id=run_id, resume=True)
    typer.echo(f"resumed run_id={rid}")


# ------------------------------------------------------------- experiments

@experiment_app.command("list")
def experiment_list() -> None:
    session = new_session()
    try:
        for e in ExperimentRepo.list(session):
            typer.echo(f"{e.experiment_id}  {e.hypothesis[:70]}")
    finally:
        session.close()


@experiment_app.command("show")
def experiment_show(experiment_id: str) -> None:
    session = new_session()
    try:
        e = ExperimentRepo.get(session, experiment_id)
        if e is None:
            typer.echo("not found", err=True)
            raise typer.Exit(1)
        typer.echo(f"experiment_id={e.experiment_id}\nhypothesis={e.hypothesis}\ncreated_at={e.created_at}")
        for r in RunRepo.list(session, experiment_id):
            typer.echo(f"  run={r.run_id} status={r.status} started={r.started_at}")
    finally:
        session.close()


@experiment_app.command("compare")
def experiment_compare(experiment_id: str) -> None:
    session = new_session()
    try:
        for r in RunRepo.list(session, experiment_id):
            agg = MetricRepo.aggregate(session, r.run_id)
            cost = agg.get("cost_usd_est_total", {}).get("sum", 0.0)
            judge = agg.get("judge_score", {}).get("avg")
            judge_str = f"{judge:.3f}" if judge is not None else "n/a"
            typer.echo(f"{r.run_id}  status={r.status}  cost=${cost:.4f}  judge_avg={judge_str}")
    finally:
        session.close()


@app.command("diff")
def diff_cmd(run_a: str, run_b: str) -> None:
    session = new_session()
    try:
        a, b = RunRepo.get(session, run_a), RunRepo.get(session, run_b)
        if a is None or b is None:
            typer.echo("one or both runs not found", err=True)
            raise typer.Exit(1)
        typer.echo(f"spec_hash: {a.spec_hash} vs {b.spec_hash}")
        typer.echo(f"status:    {a.status} vs {b.status}")
        agg_a, agg_b = MetricRepo.aggregate(session, run_a), MetricRepo.aggregate(session, run_b)
        for key in sorted(set(agg_a) | set(agg_b)):
            va = agg_a.get(key, {})
            vb = agg_b.get(key, {})
            typer.echo(f"  {key}: sum={va.get('sum', 0):.4f} avg={va.get('avg', 0):.4f}"
                       f"  vs  sum={vb.get('sum', 0):.4f} avg={vb.get('avg', 0):.4f}")
    finally:
        session.close()


@app.command("lineage")
def lineage_cmd(run_id: str) -> None:
    from research_dojo.analysis.lineage import lineage_summary

    session = new_session()
    try:
        typer.echo(lineage_summary(session, run_id))
    finally:
        session.close()


@bundle_app.command("export")
def bundle_export_cmd(run_id: str, out: str = typer.Option("bundle.tar.gz", "-o", "--out")) -> None:
    from research_dojo.artifacts.bundle import export_bundle

    path = export_bundle(run_id, out)
    typer.echo(f"wrote {path}")


# ------------------------------------------------------------------ ops

@supervisor_app.command("start")
def supervisor_start(
    poll_interval: int = typer.Option(30, "--poll-interval"),
    detach: bool = typer.Option(False, "--detach"),
) -> None:
    from research_dojo.supervisor import daemon

    if daemon.running_pid():
        typer.echo(f"supervisor already running (pid={daemon.running_pid()})", err=True)
        raise typer.Exit(1)
    if detach:
        cmd = [sys.executable, "-m", "research_dojo.cli.main", "supervisor", "start",
               "--poll-interval", str(poll_interval)]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        typer.echo("supervisor launching in background")
        return
    daemon.loop(poll_interval=poll_interval)


@supervisor_app.command("stop")
def supervisor_stop() -> None:
    from research_dojo.supervisor import daemon

    pid = daemon.running_pid()
    if not pid:
        typer.echo("supervisor not running")
        return
    os.kill(pid, signal.SIGTERM)
    typer.echo(f"sent SIGTERM to supervisor pid={pid}")


@supervisor_app.command("status")
def supervisor_status() -> None:
    from research_dojo.supervisor import daemon

    pid = daemon.running_pid()
    typer.echo(f"running (pid={pid})" if pid else "not running")


@dlq_app.command("list")
def dlq_list_cmd(run_id: str | None = typer.Argument(None)) -> None:
    session = new_session()
    try:
        if run_id:
            entries = DLQRepo.list_for_run(session, run_id)
        else:
            entries = [e for r in RunRepo.list(session) for e in DLQRepo.list_for_run(session, r.run_id)]
        if not entries:
            typer.echo("DLQ empty")
        for e in entries:
            typer.echo(
                f"[{e.id}] run={e.run_id} sample={e.sample_id} arm={e.arm} rollout_idx={e.rollout_idx} "
                f"attempts={e.attempts} next_retry={e.next_retry_at} error={e.error[:80]}"
            )
    finally:
        session.close()


@dlq_app.command("retry")
def dlq_retry_cmd(run_id: str) -> None:
    session = new_session()
    try:
        entries = DLQRepo.list_for_run(session, run_id)
        for e in entries:
            DLQRepo.bump_attempt(session, e.id, retry_delay_seconds=0)
        session.commit()
        typer.echo(f"queued {len(entries)} DLQ entries for immediate retry; run `dojo resume {run_id}`")
    finally:
        session.close()


@metrics_app.command("show")
def metrics_show_cmd(run_id: str) -> None:
    session = new_session()
    try:
        agg = MetricRepo.aggregate(session, run_id)
        if not agg:
            typer.echo("no metrics recorded")
        for name, vals in sorted(agg.items()):
            typer.echo(
                f"{name:30s} count={vals['count']:<8.0f} sum={vals['sum']:<14.4f} "
                f"avg={vals['avg']:<14.4f} max={vals['max']:<14.4f}"
            )
    finally:
        session.close()


@app.command("serve")
def serve_cmd(port: int = typer.Option(9090, "--port"), host: str = typer.Option("127.0.0.1", "--host")) -> None:
    from research_dojo.api.server import serve

    serve(port=port, host=host)


# -------------------------------------------------------------------- inspect

@inspect_app.command("run")
def inspect_run_cmd(
    task: str,
    model: str | None = typer.Option(None, "--model"),
    log_dir: str | None = typer.Option(None, "--log-dir"),
) -> None:
    settings = get_settings()
    if model is None:
        deploy = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
        if not deploy:
            typer.echo("no --model given and AZURE_OPENAI_DEPLOYMENT unset in .env", err=True)
            raise typer.Exit(1)
        model = f"azure/{deploy}"
    if model.startswith("azure/"):
        model = f"openai/{model}"  # inspect_ai routes azure via the openai provider, see docs/AZURE.md

    log_dir = log_dir or str(settings.resolve_data_dir() / "inspect_logs")
    # relative, not absolute: inspect_ai's task-file glob (root_dir.glob(...))
    # rejects absolute patterns on Python 3.13's stricter pathlib.glob()
    task_file_abs = PACKAGE_ROOT / "src" / "research_dojo" / "inspect_tasks" / f"{task}.py"
    task_file = os.path.relpath(task_file_abs, Path.cwd())
    cmd = ["inspect", "eval", task_file, "--model", model, "--log-dir", log_dir]
    typer.echo(f"$ {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    typer.echo(f"view with: inspect view --log-dir {log_dir}")


@inspect_app.command("export")
def inspect_export_cmd(run_id: str) -> None:
    from research_dojo.inspect_tasks.bridge import export_run_to_inspect_log

    session = new_session()
    try:
        path = export_run_to_inspect_log(session, run_id)
        session.commit()
        if path is None:
            typer.echo("export failed or run not found — see logs", err=True)
            raise typer.Exit(1)
        typer.echo(f"wrote {path}")
    finally:
        session.close()


# -------------------------------------------------------------------- alerts

@alerts_app.command("test")
def alerts_test_cmd(rule: str = typer.Option(..., "--rule")) -> None:
    from research_dojo.alerts import dispatcher
    from research_dojo.alerts.rules import AlertTrigger

    session = new_session()
    try:
        trigger = AlertTrigger(rule=rule, severity="warning", message=f"dry-run test of rule={rule}")
        dispatcher.dispatch(session, trigger, run_id=None)
        session.commit()
        typer.echo(f"dispatched test alert for rule={rule}")
    finally:
        session.close()


@alerts_app.command("history")
def alerts_history_cmd(run_id: str | None = typer.Option(None, "--run-id")) -> None:
    session = new_session()
    try:
        events = AlertRepo.list(session, run_id=run_id)
        if not events:
            typer.echo("no alert history")
        for e in events:
            typer.echo(f"[{e.ts}] {e.severity:8s} {e.rule:22s} run={e.run_id} {e.message}")
    finally:
        session.close()


# ------------------------------------------------------------------------ db

@db_app.command("migrate")
def db_migrate_cmd() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(PACKAGE_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(PACKAGE_ROOT / "src" / "research_dojo" / "db" / "migrations"))
    command.upgrade(cfg, "head")
    typer.echo("migrated to head")


@db_app.command("reset")
def db_reset_cmd(i_understand: bool = typer.Option(False, "--i-understand")) -> None:
    if not i_understand:
        typer.echo("refusing: this drops all tables. Pass --i-understand to confirm (dev only).", err=True)
        raise typer.Exit(1)
    from research_dojo.db.models import Base
    from research_dojo.db.session import get_engine

    Base.metadata.drop_all(get_engine())
    db_migrate_cmd()
    typer.echo("DB reset complete")


if __name__ == "__main__":
    app()
