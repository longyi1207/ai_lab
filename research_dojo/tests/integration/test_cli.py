from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from research_dojo.cli.main import app

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_cli_help():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0


def test_cli_status_no_runs(dojo_env):
    result = CliRunner().invoke(app, ["status"])
    assert result.exit_code == 0
    assert "no runs found" in result.output


def test_cli_run_then_status_metrics_lineage_experiment_alerts_dlq(dojo_env, mock_llm):
    runner = CliRunner()

    result = runner.invoke(app, ["run", "--spec", str(FIXTURES / "mini_spec.yaml"), "--run-id", "cli_run"])
    assert result.exit_code == 0, result.output
    assert "run_id=cli_run" in result.output

    result = runner.invoke(app, ["status", "--run-id", "cli_run"])
    assert result.exit_code == 0
    assert "COMPLETE" in result.output

    result = runner.invoke(app, ["metrics", "show", "cli_run"])
    assert result.exit_code == 0
    assert "cost_usd_est_total" in result.output

    result = runner.invoke(app, ["lineage", "cli_run"])
    assert result.exit_code == 0
    assert "spec_hash" in result.output

    result = runner.invoke(app, ["experiment", "list"])
    assert result.exit_code == 0
    assert "mini_test" in result.output

    result = runner.invoke(app, ["experiment", "compare", "mini_test"])
    assert result.exit_code == 0
    assert "cli_run" in result.output

    result = runner.invoke(app, ["alerts", "test", "--rule", "run_failed"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["alerts", "history"])
    assert result.exit_code == 0
    assert "run_failed" in result.output

    result = runner.invoke(app, ["dlq", "list"])
    assert result.exit_code == 0
    assert "DLQ empty" in result.output

    result = runner.invoke(app, ["cancel", "cli_run"])
    assert result.exit_code == 0
    assert "CANCELLED" in result.output


def test_db_migrate_creates_schema(tmp_path, monkeypatch):
    monkeypatch.setenv("DOJO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("DOJO_DATABASE_URL", raising=False)
    from research_dojo.config import settings as settings_module
    from research_dojo.db import session as session_module

    settings_module.get_settings.cache_clear()
    session_module.reset_engine_cache()
    try:
        result = CliRunner().invoke(app, ["db", "migrate"])
        assert result.exit_code == 0, result.output

        import sqlite3

        con = sqlite3.connect(str(tmp_path / "dojo.db"))
        tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
        con.close()
        assert "runs" in tables
        assert "rollouts" in tables
        assert "alembic_version" in tables
    finally:
        settings_module.get_settings.cache_clear()
        session_module.reset_engine_cache()


def test_db_reset_requires_confirmation(tmp_path, monkeypatch):
    monkeypatch.setenv("DOJO_DATA_DIR", str(tmp_path))
    from research_dojo.config import settings as settings_module
    from research_dojo.db import session as session_module

    settings_module.get_settings.cache_clear()
    session_module.reset_engine_cache()
    try:
        result = CliRunner().invoke(app, ["db", "reset"])
        assert result.exit_code != 0
        assert "--i-understand" in result.output
    finally:
        settings_module.get_settings.cache_clear()
        session_module.reset_engine_cache()
