from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from research_dojo.verify.judge import _parse_json, judge_rollout


def test_parse_json_plain():
    assert _parse_json('{"score": 0.5}') == {"score": 0.5}


def test_parse_json_strips_markdown_fence():
    assert _parse_json('```json\n{"score": 1.0}\n```') == {"score": 1.0}


def test_parse_json_extracts_embedded_object():
    assert _parse_json('here is my answer: {"score": 0.7} thanks') == {"score": 0.7}


def test_parse_json_raises_on_garbage():
    with pytest.raises(ValueError):
        _parse_json("not json at all, no braces")


def _client_with_responses(responses: list[str]):
    client = MagicMock()
    it = iter(responses)

    def create(**kwargs):
        content = next(it)
        message = MagicMock(content=content)
        choice = MagicMock(message=message)
        return MagicMock(choices=[choice])

    client.chat.completions.create.side_effect = create
    return client


def test_judge_rollout_parses_first_response(monkeypatch):
    client = _client_with_responses(['{"score": 0.8, "label": "good", "rationale": "fine"}'])
    monkeypatch.setattr(
        "research_dojo.verify.judge.azure_openai_client_and_model", lambda: (client, "mock-model")
    )
    result = judge_rollout("rubric text", "prompt", "completion", "v1")
    assert result["score"] == 0.8
    assert result["label"] == "good"
    assert result["judge_version"] == "v1"
    assert client.chat.completions.create.call_count == 1


def test_judge_rollout_retries_once_on_bad_json(monkeypatch):
    client = _client_with_responses([
        "not valid json, sorry",
        '{"score": 0.3, "label": "meh", "rationale": "reformatted"}',
    ])
    monkeypatch.setattr(
        "research_dojo.verify.judge.azure_openai_client_and_model", lambda: (client, "mock-model")
    )
    result = judge_rollout("rubric text", "prompt", "completion", "v1")
    assert result["score"] == 0.3
    assert client.chat.completions.create.call_count == 2


def test_judge_rollout_raises_if_retry_also_fails(monkeypatch):
    client = _client_with_responses(["still not json", "still not json either"])
    monkeypatch.setattr(
        "research_dojo.verify.judge.azure_openai_client_and_model", lambda: (client, "mock-model")
    )
    with pytest.raises(ValueError):
        judge_rollout("rubric text", "prompt", "completion", "v1")
