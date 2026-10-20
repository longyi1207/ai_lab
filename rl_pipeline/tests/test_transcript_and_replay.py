import json

from conftest import FakeSandbox, FakeTask, entries_for

from rl_pipeline.replay import normalize_output, replay_prefix
from rl_pipeline.transcript import parse_call, prefix_before, walk


def test_parse_call():
    assert parse_call('bash {"cmd": "ls"}') == ("bash", '{"cmd": "ls"}', {"cmd": "ls"})
    assert parse_call("submit not-json")[2] is None


def test_walk_restores_ids_nudges_and_final_reply(task):
    entries = entries_for(
        (1, "reading", [("bash", json.dumps({"cmd": "cat a"}))], ["A"]),
        (2, "thinking out loud", [], []),
        (3, None, [("submit", json.dumps({"answer": "x"}))], []),
    )
    w = walk(task, {"scope": "none"}, entries)
    roles = [m["role"] for m in w.messages]
    assert roles == ["system", "user", "assistant", "tool", "assistant", "user", "assistant", "tool"]
    assert w.messages[2]["tool_calls"][0]["id"] == "call_1_0"
    assert w.messages[3] == {"role": "tool", "tool_call_id": "call_1_0", "content": "A"}
    assert w.messages[5]["content"] == "keep going"          # the runner's nudge
    assert json.loads(w.messages[7]["content"]) == {"noted": True}
    assert w.ended and w.turn_starts == [2, 4, 6]


def test_invalid_call_does_not_shift_later_outputs(task):
    entries = entries_for((1, None, [("bash", "{not json"), ("bash", json.dumps({"cmd": "ls"}))], ["L"]))
    w = walk(task, {"scope": "none"}, entries)
    assert "invalid arguments" in w.messages[3]["content"]
    assert w.messages[4]["content"] == "L"                  # the real output stays with its call


def test_empty_output_becomes_no_output(task):
    w = walk(task, {"scope": "none"}, entries_for((1, None, [("bash", json.dumps({"cmd": "true"}))], [""])))
    assert w.messages[-1]["content"] == "(no output)"


def test_prefix_before_keeps_earlier_steps_only():
    entries = entries_for((1, "a", [], []), (2, "b", [], []), (3, "c", [], []))
    assert [e["step"] for e in prefix_before(entries, 3)] == [1, 2]


def test_normalize_masks_values_that_change_between_containers():
    a = "Date: Mon, 21 Sep 2026 23:47:24 GMT\nnonce 3f9a2c11aa token " + "a" * 24 + "." + "b" * 24
    b = "Date: Tue, 20 Oct 2026 17:19:51 GMT\nnonce 77be0912cd token " + "c" * 24 + "." + "d" * 24
    assert normalize_output(a) == normalize_output(b)
    assert normalize_output("state: IDLE") != normalize_output("state: AUTHED")


def test_replay_reports_fidelity():
    entries = entries_for((1, None, [("bash", json.dumps({"cmd": "x"}))], ["same"]),
                          (2, None, [("bash", json.dumps({"cmd": "y"}))], ["recorded"]))
    sb = FakeSandbox({"x": "same", "y": "different"})
    r = replay_prefix(FakeTask(sb), sb, {"scope": "none"}, entries)
    assert (r.n_bash, r.n_exact, r.n_masked, r.ok) == (2, 1, 1, False)
    assert sb.ran == ["prepare", "x", "y"]
    assert r.messages[-1]["content"] == "different"      # the continuation sees the real container
