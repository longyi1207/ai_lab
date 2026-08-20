"""Shared fixtures: isolated temp-dir settings/DB per test, and a scripted
mock OpenAI-SDK client so no test makes a real network call.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from research_dojo.config import settings as settings_module
from research_dojo.db import session as session_module
from research_dojo.db.models import Base


@pytest.fixture
def dojo_env(tmp_path, monkeypatch):
    """Point get_settings() + the DB engine at a throwaway temp dir/DB for
    the duration of one test, then reset the module-level caches."""
    monkeypatch.setenv("DOJO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("DOJO_DATABASE_URL", raising=False)
    settings_module.get_settings.cache_clear()
    session_module.reset_engine_cache()

    engine = session_module.get_engine()
    Base.metadata.create_all(engine)

    yield settings_module.get_settings()

    session_module.reset_engine_cache()
    settings_module.get_settings.cache_clear()


class ScriptedChatCompletions:
    """Mimics `client.chat.completions.create(...)`. `responder` maps the
    last user message content (or the whole message list) to a completion
    string; falls back to a default if no match."""

    def __init__(self, responder):
        self.responder = responder
        self.calls: list[dict] = []

    def create(self, *, model, messages, **kwargs):
        self.calls.append({"model": model, "messages": messages, **kwargs})
        content = self.responder(messages)
        usage = SimpleNamespace(prompt_tokens=17, completion_tokens=11)
        message = SimpleNamespace(content=content, tool_calls=None)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice], usage=usage)


def make_mock_client(responder) -> MagicMock:
    client = MagicMock()
    client.chat.completions = ScriptedChatCompletions(responder)
    return client


@pytest.fixture
def mock_llm(monkeypatch):
    """Patches the azure_openai_client_and_model() import site in every
    module that calls it, so harness + judge both hit the scripted client.
    Default behavior: echoes back a canned JSON judge score of 1.0, and for
    plain prompts returns the string "mock completion for: <first 40 chars>".
    Override via `mock_llm.responder = ...` in a test for custom behavior.
    """
    state = SimpleNamespace(responder=_default_responder)

    def responder(messages):
        return state.responder(messages)

    client = make_mock_client(responder)

    def fake_azure_client_and_model():
        return client, "mock-deployment"

    import research_dojo.harness.agent as agent_mod
    import research_dojo.harness.batch_chat as batch_chat_mod
    import research_dojo.verify.judge as judge_mod

    monkeypatch.setattr(batch_chat_mod, "azure_openai_client_and_model", fake_azure_client_and_model)
    monkeypatch.setattr(agent_mod, "azure_openai_client_and_model", fake_azure_client_and_model)
    monkeypatch.setattr(judge_mod, "azure_openai_client_and_model", fake_azure_client_and_model)

    state.client = client
    return state


def _default_responder(messages: list[dict]) -> str:
    system = (messages[0].get("content") or "") if messages else ""
    if "careful evaluator" in system:
        return '{"score": 0.9, "label": "ok", "rationale": "mock judge pass"}'
    last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "")
    return f"mock completion for: {last_user[:40]}"
