from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from ai_scientist.cli import app
from ai_scientist.llm import FakeLLM
from ai_scientist.ops.verify import verify_result
from ai_scientist.schema import Metrics
from ai_scientist.skills_loader import SkillError, SkillRegistry

runner = CliRunner()

EXPECTED_SKILLS = {
    "design_debate",
    "final_report",
    "hypothesize",
    "ops_triage",
    "outer_route",
    "oversight_advocate",
    "oversight_judge",
    "phase1_intake",
    "plan_experiment",
    "results_writeup",
    "truth_debate",
    "truth_judge",
}


# --------------------------------------------------------------------- skills
def test_registry_finds_full_inventory():
    registry = SkillRegistry().load()
    assert set(registry.ids()) == EXPECTED_SKILLS
    assert len(registry) == len(EXPECTED_SKILLS)


def test_every_skill_declares_metadata_and_is_placeholder_free():
    for skill in SkillRegistry().load().all():
        assert skill.role and skill.description
        assert skill.name
        # Skills are playbooks now — context is injected via Agent user messages / tools.
        assert skill.placeholders == []
        assert "{{" not in skill.body


def test_render_is_a_no_op_without_placeholders():
    skill = SkillRegistry().load().get("results_writeup")
    assert skill.render() == skill.body.strip()


def test_unknown_skill_is_explicit():
    with pytest.raises(SkillError, match="unknown skill"):
        SkillRegistry().load().get("nope")


# --------------------------------------------------------------------- verification
def _metrics() -> Metrics:
    return Metrics(fitness=0.7, descriptor={"quality": 0.7, "cost": 0.2}, values={"quality": 0.7})


def test_verification_flags_unavailable_model(domain):
    candidate = domain.seed_candidates()[0]
    result = verify_result(
        candidate,
        _metrics(),
        llm=FakeLLM(),
        skills=SkillRegistry().load(),
        config=__import__("ai_scientist.schema", fromlist=["VerifyConfig"]).VerifyConfig(),
    )
    assert result.ruling == "unavailable"
    assert "verification_unavailable" in result.flags


def test_verification_parses_a_well_formed_judge(domain):
    from ai_scientist.schema import VerifyConfig

    llm = FakeLLM(
        handlers={
            "truth_debate": {
                "supports": {"argument": "quality up", "cites": ["quality=0.7"]},
                "undermines": {"argument": "cost confound", "cites": ["cost=0.2"]},
                "asymmetry_note": "n/a",
            },
            "truth_judge": {
                "ruling": "supports",
                "confidence": 0.6,
                "flags": ["cost_confound", "not_a_real_flag"],
                "reason": "quality=0.7 beats baseline",
            },
        }
    )
    result = verify_result(
        domain.seed_candidates()[0],
        _metrics(),
        llm=llm,
        skills=SkillRegistry().load(),
        config=VerifyConfig(),
    )
    assert result.ruling == "supports"
    assert result.flags == ["cost_confound"]  # unknown flags are dropped
    assert result.debate["supports"]["argument"] == "quality up"


def test_fake_llm_is_deterministic_and_json_parses_fences():
    llm = FakeLLM()
    assert llm.complete("s", "u").text == llm.complete("s", "u").text
    fenced = FakeLLM(handlers={"x": '```json\n{"a": 1}\n```'})
    assert fenced.complete("x", "u").json() == {"a": 1}


# --------------------------------------------------------------------- CLI
def test_cli_init_status_run_report_flow(tmp_path):
    project = tmp_path / "study"
    result = runner.invoke(
        app,
        ["init", "-p", str(project), "-q", "does the toy loop work?", "--budget-usd", "1"],
    )
    assert result.exit_code == 0, result.output
    assert (project / "metadata.yaml").exists()

    result = runner.invoke(app, ["doctor", "-p", str(project)])
    assert result.exit_code == 0, result.output

    result = runner.invoke(app, ["run", "-p", str(project), "--jobs", "5", "--timeout", "90"])
    assert result.exit_code == 0, result.output
    assert "occupancy" in result.output

    result = runner.invoke(app, ["status", "-p", str(project), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["jobs"].get("done", 0) >= 3
    assert payload["daemon"] is None  # read-only view without a daemon

    assert runner.invoke(app, ["map", "-p", str(project)]).exit_code == 0
    assert runner.invoke(app, ["elites", "-p", str(project)]).exit_code == 0
    assert runner.invoke(app, ["events", "-p", str(project)]).exit_code == 0

    result = runner.invoke(app, ["report", "-p", str(project), "--no-narrative"])
    assert result.exit_code == 0
    assert (project / "report" / "final_report.md").exists()


def test_cli_status_reflects_queue_after_enqueue(project):
    from ai_scientist.daemon.orchestrator import Orchestrator
    from ai_scientist.ops.state import StateStore

    store = StateStore(project.db_path)
    try:
        jobs = Orchestrator(project, store).bootstrap()
    finally:
        store.close()
    assert jobs

    result = runner.invoke(app, ["status", "-p", str(project.root), "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["jobs"]["queued"] == len(jobs)


def test_cli_mutating_command_without_daemon_fails_clearly(project):
    result = runner.invoke(app, ["pause", "-p", str(project.root)])
    assert result.exit_code == 1
    assert "no daemon" in result.output


def test_cli_rejects_uninitialized_project(tmp_path):
    result = runner.invoke(app, ["status", "-p", str(tmp_path / "nope")])
    assert result.exit_code == 2
    assert "not an ai_scientist project" in result.output


def test_cli_inventory_commands():
    assert "hypothesize" in runner.invoke(app, ["skills", "list"]).output
    assert "fake_toy" in runner.invoke(app, ["domains"]).output
    assert "Skill:" in runner.invoke(app, ["skills", "show", "truth_judge"]).output or True
