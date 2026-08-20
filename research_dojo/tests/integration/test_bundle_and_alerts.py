from __future__ import annotations

import tarfile
from pathlib import Path


def test_bundle_export_contains_db_slice_and_artifacts(dojo_env, mock_llm, tmp_path):
    from research_dojo.artifacts.bundle import export_bundle
    from research_dojo.engine.run_engine import run_experiment

    fixtures = Path(__file__).resolve().parent.parent / "fixtures"
    run_id = run_experiment(str(fixtures / "mini_spec.yaml"), run_id="mini_bundle")

    out = tmp_path / "bundle.tar.gz"
    path = export_bundle(run_id, out)
    assert path.exists()

    with tarfile.open(path, "r:gz") as tar:
        names = tar.getnames()
        assert any(n.endswith("db_slice.json") for n in names)
        assert any("artifacts" in n and n.endswith("REPORT.md") for n in names)


def test_alert_dispatch_writes_file_notifier_and_db_row(dojo_env, tmp_path):
    from research_dojo.alerts import dispatcher
    from research_dojo.alerts.rules import AlertTrigger
    from research_dojo.db.repositories import AlertRepo
    from research_dojo.db.session import new_session

    session = new_session()
    trigger = AlertTrigger(rule="run_failed", severity="critical", message="test failure")
    dispatcher.dispatch(session, trigger, run_id=None)
    session.commit()

    events = AlertRepo.list(session)
    assert any(e.rule == "run_failed" for e in events)

    alerts_file = dojo_env.resolve_data_dir() / "alerts.jsonl"
    assert alerts_file.exists()
    assert "run_failed" in alerts_file.read_text()
    session.close()


def test_alert_below_min_severity_is_suppressed(dojo_env):
    from research_dojo.alerts import dispatcher
    from research_dojo.alerts.rules import AlertTrigger
    from research_dojo.db.repositories import AlertRepo
    from research_dojo.db.session import new_session

    session = new_session()
    trigger = AlertTrigger(rule="quiet_info", severity="info", message="should be suppressed")
    dispatcher.dispatch(session, trigger, run_id=None, min_severity="warning")
    session.commit()

    events = AlertRepo.list(session)
    assert not any(e.rule == "quiet_info" for e in events)
    session.close()
