from __future__ import annotations

from pathlib import Path


def test_export_run_to_inspect_log(dojo_env, mock_llm):
    from research_dojo.db.session import new_session
    from research_dojo.engine.run_engine import run_experiment
    from research_dojo.inspect_tasks.bridge import export_run_to_inspect_log

    fixtures = Path(__file__).resolve().parent.parent / "fixtures"
    run_id = run_experiment(str(fixtures / "mini_spec.yaml"), run_id="mini_inspect")

    session = new_session()
    path = export_run_to_inspect_log(session, run_id)
    session.commit()
    session.close()

    assert path is not None
    assert path.exists()
    assert path.suffix == ".eval"


def test_tom_smoke_task_loads():
    from research_dojo.inspect_tasks.tom_smoke import tom_smoke

    task = tom_smoke()
    assert task.dataset is not None
    assert len(task.dataset) == 20
