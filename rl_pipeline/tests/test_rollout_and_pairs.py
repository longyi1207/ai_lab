import json

from conftest import FakeChat, FakeSandbox, FakeTask, bash_call, entries_for, final_call

from rl_pipeline.pairs import build_pair, build_pairs, divergence, validate_example
from rl_pipeline.rollout import continue_episode, run_rollout


def test_agent_loop_runs_tools_nudges_and_stops(task):
    sb = FakeSandbox({"ls": "file"})
    chat = FakeChat([{"content": "hmm"}, {"content": None, "tool_calls": [bash_call("ls")]},
                     {"content": None, "tool_calls": [final_call("honest")]}])
    msgs = task.initial_messages({"scope": "none"})
    out = continue_episode(task, sb, {"scope": "none"}, msgs, chat, "m", start_step=5, max_new_steps=10,
                           temperature=1.0, max_tokens=100, purpose="t")
    assert out.end == "final_tool" and out.final_answer == "honest" and out.steps == 3
    assert [e["step"] for e in out.entries] == [5, 6, 6, 7]
    assert chat.calls[1][-1] == {"role": "user", "content": "keep going"}
    assert sb.ran == ["ls"]


def test_agent_loop_respects_step_budget(task):
    chat = FakeChat([{"content": "x"}] * 3)
    out = continue_episode(task, FakeSandbox(), {"scope": "none"}, task.initial_messages({"scope": "none"}),
                           chat, "m", start_step=1, max_new_steps=3, temperature=1.0, max_tokens=10, purpose="t")
    assert out.end == "max_steps" and out.steps == 3


def _rollout(final: str, first_cmd: str, key: str):
    sb = FakeSandbox({"a": "A", first_cmd: "R"})
    task = FakeTask(sb)
    episode = {"transcript": entries_for((1, None, [("bash", json.dumps({"cmd": "a"}))], ["A"]))}
    bp = {"branch_id": "ep@2", "episode_id": "ep", "branch_step": 2, "cell": {"scope": "none"}, "split": "train"}
    chat = FakeChat([{"content": None, "tool_calls": [bash_call(first_cmd)]},
                     {"content": None, "tool_calls": [final_call(final)]}])
    rec = run_rollout(task, episode, bp, chat=chat, model="m", policy_label="base", sample_idx=int(key),
                      max_new_steps=5, temperature=1.0, max_tokens=10, label_source="outcome_action",
                      intent_policy="pursuit", judge_model=None, phase="sample")
    return task, rec


def test_rollout_from_branch_point_is_graded():
    _, rec = _rollout("cheat", "cat conf", "0")
    assert rec["status"] == "ok" and rec["replay"]["ok"]
    assert rec["reward"]["reason"] == "action_cheat"
    assert rec["prefix_entries"][1]["tool_output"] == "A"


def test_pair_lands_on_first_divergent_turn():
    task, good = _rollout("honest", "cat spec", "0")
    _, bad = _rollout("cheat", "cat conf", "1")
    assert divergence(good, bad) == 0
    pair = build_pair(task, good, bad)
    ex = pair["example"]
    assert validate_example(ex) == []
    assert ex["input"]["messages"][-1]["role"] == "tool"          # context ends after the prefix
    assert "cat spec" in ex["preferred_output"][0]["tool_calls"][0]["function"]["arguments"]
    assert "cat conf" in ex["non_preferred_output"][0]["tool_calls"][0]["function"]["arguments"]


def test_shared_turns_extend_the_context():
    task, good = _rollout("honest", "cat same", "0")
    _, bad = _rollout("cheat", "cat same", "1")
    assert divergence(good, bad) == 1                              # first turn identical, second differs
    ex = build_pair(task, good, bad)["example"]
    assert ex["preferred_output"][0]["tool_calls"][0]["function"]["name"] == "submit"


def test_formatting_differences_are_not_a_divergence():
    from rl_pipeline.pairs import _same_turn
    a = ({"content": "Reading the note.", "tool_calls": [{"cmd": 'bash {"cmd": "cat ~/HANDOFF.md"}'}]}, ["out"])
    b = ({"content": None, "tool_calls": [{"cmd": 'bash {"cmd":"cat ~/HANDOFF.md"}'}]}, ["out"])
    c = ({"content": None, "tool_calls": [{"cmd": 'bash {"cmd":"curl /fetch"}'}]}, ["out"])
    assert _same_turn(a, b)                     # same command, different spacing and wording
    assert not _same_turn(a, c)                 # a different command is a real decision
    assert not _same_turn(a, (a[0], ["other output"]))


def test_build_pairs_needs_contrast_at_a_branch():
    task, good = _rollout("honest", "cat spec", "0")
    _, bad = _rollout("cheat", "cat conf", "1")
    for r in (good, bad):
        r["task"] = "fake"
    out = build_pairs({"fake": task}, [good, bad], max_pairs_per_branch=4, val_fraction=0.0)
    assert out["counts"]["train_pairs"] == 1
    only_bad = build_pairs({"fake": task}, [bad], max_pairs_per_branch=4, val_fraction=0.0)
    assert only_bad["counts"]["branches_without_contrast"] == 1


def test_recorded_continuation_can_be_the_preferred_side():
    from rl_pipeline.pairs import recorded_rollout
    task, bad = _rollout("cheat", "cat conf", "1")
    bad["task"] = "fake"
    episode = {"transcript": entries_for((1, None, [("bash", json.dumps({"cmd": "a"}))], ["A"]),
                                         (2, None, [("bash", json.dumps({"cmd": "cat spec"}))], ["S"]),
                                         (3, None, [("submit", json.dumps({"answer": "honest"}))], [])),
               "reward": {"reward": 1, "reason": "clean_completion"}}
    bp = {"branch_id": "ep@2", "task": "fake", "split": "train", "branch_step": 2, "cell": {"scope": "none"}}
    rec = recorded_rollout(bp, episode)
    assert [e["step"] for e in rec["prefix_entries"]] == [1, 1] and rec["entries"][0]["step"] == 2
    out = build_pairs({"fake": task}, [bad], max_pairs_per_branch=4, val_fraction=0.0, recorded=[rec])
    assert out["counts"]["train_pairs"] == 1
    assert out["meta"][0]["chosen_policy"] == "recorded" and out["meta"][0]["rejected_policy"] == "base"


def test_pairs_never_contain_null_content():
    task, good = _rollout("honest", "cat spec", "0")
    _, bad = _rollout("cheat", "cat conf", "1")
    ex = build_pair(task, good, bad)["example"]
    for m in ex["input"]["messages"] + ex["preferred_output"] + ex["non_preferred_output"]:
        assert m.get("content", "") is not None
    ex["input"]["messages"].append({"role": "assistant", "content": None})
    assert any("null content" in p for p in validate_example(ex))


def test_validate_catches_unanswered_tool_calls():
    ex = {"input": {"messages": [{"role": "system", "content": "s"},
                                 {"role": "assistant", "tool_calls": [{"id": "x"}]}]},
          "preferred_output": [{"role": "assistant", "content": "a"}],
          "non_preferred_output": [{"role": "assistant", "content": "b"}]}
    assert "context ends with unanswered tool calls" in validate_example(ex)
