from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from research_dojo.config.spec import ExperimentSpec
from research_dojo.harness.agent import AgentHarness


def _tool_call(id_, name, arguments):
    return SimpleNamespace(id=id_, function=SimpleNamespace(name=name, arguments=arguments))


def test_agent_harness_bash_then_submit(monkeypatch):
    spec = ExperimentSpec.model_validate({
        "experiment_id": "x", "hypothesis": "h",
        "model": {"deployment": "d"}, "dataset": "d.jsonl",
        "budget": {"max_usd": 1.0},
        "harness": {"kind": "agent", "max_steps": 5, "timeout_seconds": 10},
    })
    harness = AgentHarness(spec)
    calls = {"n": 0}

    def fake_create(*, model, messages, tools, **kwargs):
        calls["n"] += 1
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
        if calls["n"] == 1:
            tc = _tool_call("1", "bash", '{"command": "echo hello"}')
        else:
            tc = _tool_call("2", "submit", '{"answer": "final answer"}')
        msg = SimpleNamespace(content=None, tool_calls=[tc])
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)

    client = MagicMock()
    client.chat.completions.create.side_effect = fake_create
    monkeypatch.setattr(
        "research_dojo.harness.agent.azure_openai_client_and_model",
        lambda: (client, "mock-model"),
    )

    result = harness.run("do something", sample_id="s1", arm="baseline")
    assert result.completion == "final answer"
    assert calls["n"] == 2
    tool_events = [e for e in result.transcript if e.get("role") == "tool"]
    assert any(e.get("name") == "bash" and "hello" in e.get("content", "") for e in tool_events)


def test_agent_harness_stops_at_max_steps_without_submit(monkeypatch):
    spec = ExperimentSpec.model_validate({
        "experiment_id": "x", "hypothesis": "h",
        "model": {"deployment": "d"}, "dataset": "d.jsonl",
        "budget": {"max_usd": 1.0},
        "harness": {"kind": "agent", "max_steps": 2, "timeout_seconds": 10},
    })
    harness = AgentHarness(spec)

    def fake_create(*, model, messages, tools, **kwargs):
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5)
        tc = _tool_call("1", "bash", '{"command": "echo loop"}')
        msg = SimpleNamespace(content=None, tool_calls=[tc])
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)

    client = MagicMock()
    client.chat.completions.create.side_effect = fake_create
    monkeypatch.setattr(
        "research_dojo.harness.agent.azure_openai_client_and_model",
        lambda: (client, "mock-model"),
    )

    result = harness.run("do something", sample_id="s1", arm="baseline")
    assert "max_steps reached" in result.completion
