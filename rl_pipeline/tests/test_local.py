"""Pure-function tests for the self-hosted trainers (no model download). Skipped without torch."""
import json
import math

import pytest

torch = pytest.importorskip("torch")

from rl_pipeline.local.dpo import dpo_loss  # noqa: E402
from rl_pipeline.local.grpo import group_advantages  # noqa: E402
from rl_pipeline.local.model import parse_tool_calls, template_messages  # noqa: E402
from rl_pipeline.local.toy_env import ToySandbox, ToyShortcutTask  # noqa: E402


def test_parse_tool_calls_with_and_without_closing_tag():
    text = 'thinking\n<tool_call>\n{"name": "bash", "arguments": {"cmd": "ls"}}\n</tool_call>'
    content, calls = parse_tool_calls(text)
    assert content == "thinking"
    assert calls[0]["function"]["name"] == "bash"
    assert json.loads(calls[0]["function"]["arguments"]) == {"cmd": "ls"}
    _, calls = parse_tool_calls('<tool_call>\n{"name": "release", "arguments": {"build_id": "7.2"}}')
    assert calls and calls[0]["function"]["name"] == "release"


def test_template_messages_converts_argument_strings_and_null_content():
    msgs = [{"role": "assistant", "content": None, "tool_calls": [
        {"id": "x", "type": "function", "function": {"name": "bash", "arguments": '{"cmd": "ls"}'}}]}]
    out = template_messages(msgs)
    assert out[0]["content"] == ""
    assert out[0]["tool_calls"][0]["function"]["arguments"] == {"cmd": "ls"}


def test_group_advantages():
    assert group_advantages([1, 1, 1, 1]) == [0.0] * 4          # no contrast -> no gradient
    adv = group_advantages([1, 0, 0, 1])
    assert sum(adv) == pytest.approx(0.0) and adv[0] > 0 > adv[1]
    assert group_advantages([1]) == [0.0]


def test_dpo_loss_matches_the_formula():
    pi_w, pi_l = torch.tensor(-10.0), torch.tensor(-12.0)
    loss, acc, margin = dpo_loss(pi_w, pi_l, ref_w=-11.0, ref_l=-11.0, beta=0.1)
    expected_margin = 0.1 * ((-10 + 11) - (-12 + 11))
    assert margin == pytest.approx(expected_margin)
    assert loss.item() == pytest.approx(-math.log(1 / (1 + math.exp(-expected_margin))))
    assert acc == 1.0
    loss0, _, _ = dpo_loss(torch.tensor(-5.0), torch.tensor(-7.0), ref_w=-5.0, ref_l=-7.0, beta=0.1)
    assert loss0.item() == pytest.approx(math.log(2))              # policy == reference


def test_toy_task_grades_honest_shortcut_and_nothing():
    task = ToyShortcutTask()
    honest, cheat, idle = ToySandbox(), ToySandbox(), ToySandbox()
    honest.exec("make check"); cheat.exec("make force-pass")
    assert task.grade(honest, "7.2", [], {})["label"] == "honest_solve"
    assert task.grade(cheat, "7.2", [], {})["label"] == "score_seek_success"
    assert task.grade(idle, "7.2", [], {})["label"] == "fail"
