"""Phase-1 intake driver, its spec wiring into Phase 2, and the MCP server."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from ai_scientist.cli import app
from ai_scientist.llm import FakeLLM
from ai_scientist.mcp import McpServer, ToolRegistry
from ai_scientist.mcp.server import PROTOCOL_VERSION
from ai_scientist.phase1 import IntakeSession, read_spec_candidate
from ai_scientist.skills_loader import SkillRegistry

runner = CliRunner()

INTAKE_REPLY = {
    "statement": "Higher alpha with a critique protocol improves toy quality.",
    "claim": "mode=critique at alpha=0.75 beats mode=direct at alpha=0.5 on graded quality.",
    "rationale": "The seed run left the high-quality region unexplored.",
    "params": {"alpha": 0.75, "rounds": 3, "mode": "critique", "verbose": False},
    "questions": [],
    "assumptions": ["budget: inherited $1 cap from metadata"],
    "metadata": {
        "audience": "LessWrong",
        "style": "rigorous",
        "topic_fidelity": "mixed",
        "credentials_refs": ["SHOULD_BE_IGNORED"],
        "api_key": "sk-leak",
    },
}


def _session(project, llm) -> IntakeSession:
    return IntakeSession(project, llm=llm, skills=SkillRegistry().load())


# --------------------------------------------------------------------- intake
def test_intake_uses_model_draft_and_commits_artifacts(project):
    llm = FakeLLM(
        handlers={
            "phase1_intake": INTAKE_REPLY,
            "design_debate": "Missing control arm.\nVERDICT: ready",
        }
    )
    session = _session(project, llm)
    draft = session.critique(session.draft("Does critique beat direct answering?"))

    assert draft.model_used == "fake"
    assert draft.hypothesis.claim == INTAKE_REPLY["claim"]
    assert draft.plan.params["alpha"] == 0.75
    assert draft.verdict == "ready"
    assert draft.ready is True

    written = session.commit(draft, brief="Does critique beat direct answering?")
    assert "Claim (falsifiable)" in written["hypothesis"].read_text()
    metadata = project.read_metadata()
    assert metadata.audience == "LessWrong"
    assert metadata.question == "Does critique beat direct answering?"
    # model-supplied metadata is filtered: no credential or secret fields get through
    assert "SHOULD_BE_IGNORED" not in json.dumps(metadata.model_dump(), default=str)
    assert "sk-leak" not in project.metadata_path.read_text()
    log = written["intake_log"].read_text()
    assert "Design-debate critique" in log and "VERDICT: ready" in log


def test_intake_without_a_usable_model_asks_blocking_questions(project):
    session = _session(project, FakeLLM())
    draft = session.critique(session.draft("Study something vague"))

    assert draft.model_used == "unavailable"
    assert draft.ready is False
    assert draft.questions  # budget / fidelity / audience are shape-changing
    assert any("model unavailable" in note or "No usable model" in note for note in draft.notes)
    assert draft.plan.params  # still a runnable seed-derived plan


def test_intake_answers_suppress_those_questions(project):
    session = _session(project, FakeLLM())
    answers = {"budget": "30", "topic_fidelity": "discovery", "audience": "self"}
    draft = session.draft("Study something vague", answers=answers)
    assert draft.questions == []
    assert draft.ready is True


def test_intake_rejects_model_params_outside_the_domain(project):
    bad = dict(INTAKE_REPLY, params={"alpha": 5.0, "rounds": 99, "mode": "telepathy"})
    session = _session(project, FakeLLM(handlers={"phase1_intake": bad}))
    draft = session.draft("anything")
    assert any("rejected by domain" in note for note in draft.notes)
    session.domain.validate_plan(draft.plan)  # fell back to a valid plan


def test_revise_verdict_blocks_readiness(project):
    llm = FakeLLM(
        handlers={
            "phase1_intake": INTAKE_REPLY,
            "design_debate": "The claim is unfalsifiable.\nVERDICT: revise",
        }
    )
    session = _session(project, llm)
    draft = session.critique(session.draft("brief"))
    assert draft.verdict == "revise" and draft.ready is False


def test_spec_is_picked_up_as_a_phase2_seed(project):
    llm = FakeLLM(
        handlers={
            "phase1_intake": INTAKE_REPLY,
            "design_debate": "ok\nVERDICT: ready",
        }
    )
    session = _session(project, llm)
    session.commit(session.critique(session.draft("brief")), brief="brief")

    candidate = read_spec_candidate(project, session.domain)
    assert candidate is not None
    assert candidate.origin == "phase1"
    assert candidate.plan.params["mode"] == "critique"

    from ai_scientist.daemon.orchestrator import Orchestrator
    from ai_scientist.ops.state import StateStore

    store = StateStore(project.db_path)
    try:
        jobs = Orchestrator(project, store).bootstrap()
        # phase-1 spec candidate plus the three domain seeds
        assert len(jobs) == 4
        priorities = sorted(j.priority for j in store.list_jobs("queued", limit=10))
        assert priorities[-1] == 2.0  # the Phase-1 spec runs first
    finally:
        store.close()


def test_malformed_spec_does_not_block_seeds(project):
    project.write_text(project.spec_path, "hypothesis: {}\nplan: {}\n")
    from ai_scientist.daemon.orchestrator import Orchestrator
    from ai_scientist.ops.state import StateStore

    store = StateStore(project.db_path)
    try:
        jobs = Orchestrator(project, store).bootstrap()
        assert len(jobs) == 3  # seeds only
    finally:
        store.close()


def test_cli_intake_blocks_then_accepts(project, monkeypatch):
    result = runner.invoke(app, ["intake", "-p", str(project.root), "-b", "vague brief"])
    assert result.exit_code == 1
    assert "open questions" in result.output
    assert not project.spec_path.exists()

    result = runner.invoke(
        app,
        [
            "intake",
            "-p",
            str(project.root),
            "-b",
            "vague brief",
            "--answer",
            "budget=1",
            "--answer",
            "topic_fidelity=stuck",
            "--answer",
            "audience=self",
        ],
    )
    assert result.exit_code == 0, result.output
    assert project.spec_path.exists() and project.hypothesis_path.exists()


# --------------------------------------------------------------------- MCP
def test_initialize_and_tools_list():
    server = McpServer()
    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert response["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert response["result"]["serverInfo"]["name"] == "ai-scientist"

    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None

    tools = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]
    names = {t["name"] for t in tools}
    assert {"sci_status", "sci_start_run", "sci_elites", "sci_report", "sci_pause"} <= names
    for tool in tools:
        assert tool["description"] and tool["inputSchema"]["type"] == "object"


def test_unknown_method_and_tool_errors():
    server = McpServer()
    err = server.handle({"jsonrpc": "2.0", "id": 3, "method": "nope/nope"})
    assert err["error"]["code"] == -32601
    assert server.handle({"jsonrpc": "2.0", "method": "nope/nope"}) is None  # notification

    result = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "sci_not_a_tool", "arguments": {}},
        }
    )["result"]
    assert result["isError"] is True
    assert "unknown tool" in result["content"][0]["text"]


def test_tool_call_status_works_without_daemon(project):
    server = McpServer(default_project=str(project.root))
    result = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "sci_status", "arguments": {}},
        }
    )["result"]
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload["domain"] == "fake_toy" and payload["daemon"] is None


def test_tool_requires_initialized_project(tmp_path):
    server = McpServer()
    result = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "sci_status", "arguments": {"project": str(tmp_path / "nope")}},
        }
    )["result"]
    assert result["isError"] is True
    assert "not an ai_scientist project" in result["content"][0]["text"]


def test_missing_project_is_an_error_not_a_crash():
    result = McpServer().handle(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "sci_status", "arguments": {}},
        }
    )["result"]
    assert result["isError"] is True
    assert "no project" in result["content"][0]["text"]


def test_run_sync_and_report_tools(project):
    registry = ToolRegistry(str(project.root))
    outcome = registry.call("sci_run_sync", {"jobs": 4, "timeout_s": 90})
    assert outcome["jobs"].get("done", 0) >= 3
    assert outcome["search"]["cells_filled"] >= 1

    elites = registry.call("sci_elites", {"n": 2})
    assert elites and "fitness" in elites[0]

    grid = registry.call("sci_map", {})
    assert grid["cells_total"] == 12 and grid["cells"]

    report = registry.call("sci_report", {"narrative": False})
    assert "Archive coverage" in report["text"]

    events = registry.call("sci_events", {"limit": 5})
    assert isinstance(events, list) and events


def test_inventory_tools_need_no_project():
    registry = ToolRegistry()
    assert {s["id"] for s in registry.call("sci_skills", {})} >= {"hypothesize", "truth_judge"}
    domains = {d["domain"] for d in registry.call("sci_domains", {})}
    assert {"fake_toy", "oversight_debate"} <= domains


def test_serve_stdio_roundtrip(project):
    import io

    stdin = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        + "\n"
        + json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
        + "\n"
        + "not json\n"
        + json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        + "\n"
    )
    stdout = io.StringIO()
    McpServer(str(project.root)).serve_stdio(stdin=stdin, stdout=stdout)

    lines = [json.loads(line) for line in stdout.getvalue().splitlines() if line.strip()]
    assert lines[0]["result"]["protocolVersion"] == PROTOCOL_VERSION
    assert lines[1]["error"]["code"] == -32700  # the bad line, not a crash
    assert lines[2]["result"]["tools"]
