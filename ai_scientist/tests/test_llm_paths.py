"""Model-facing paths: skill-driven mutation, its fallback, and provider routing."""

from __future__ import annotations

import os
import random

import pytest

from ai_scientist.llm import (
    FakeLLM,
    MissingLLMDependency,
    OpenAICompatibleClient,
    get_llm,
)
from ai_scientist.search import LLMMutator
from ai_scientist.skills_loader import SkillRegistry

GOOD_HYPOTHESIS = {
    "statement": "Debate mode beats direct at high alpha.",
    "claim": "mode=debate yields higher quality than mode=direct at alpha=0.8.",
    "rationale": "Archive is empty in the high-quality region.",
    "tags": ["debate", "high-alpha"],
}
GOOD_PLAN = {
    "params": {"alpha": 0.8, "rounds": 3, "mode": "debate", "verbose": False},
    "metrics": ["quality", "cost"],
    "baselines": ["mode=direct"],
    "seed": 42,
    "notes": "falsified if quality <= direct baseline",
}


def _skills() -> SkillRegistry:
    return SkillRegistry().load()


def test_llm_mutator_uses_model_output_when_valid(domain):
    llm = FakeLLM(
        handlers={"hypothesize": GOOD_HYPOTHESIS, "plan_experiment": GOOD_PLAN}
    )
    mutator = LLMMutator(llm, _skills())
    child = mutator.mutate(
        "broaden_scope", [domain.seed_candidates()[0]], domain=domain, rng=random.Random(0)
    )

    assert mutator.fallbacks_used == 0
    assert child.hypothesis.claim == GOOD_HYPOTHESIS["claim"]
    assert child.plan.params["alpha"] == 0.8
    assert child.plan.seed == 42
    assert child.plan.baselines == ["mode=direct"]
    assert "broaden_scope" in child.hypothesis.tags
    domain.validate_plan(child.plan)


def test_llm_mutator_falls_back_when_model_is_unusable(domain):
    # bare FakeLLM returns {"fake": true, ...}: no statement, no params
    mutator = LLMMutator(FakeLLM(), _skills())
    child = mutator.mutate(
        "vary_params", [domain.seed_candidates()[0]], domain=domain, rng=random.Random(1)
    )

    assert mutator.fallbacks_used == 1
    assert mutator.last_error  # any model/parse failure is fine; child must still be valid
    domain.validate_plan(child.plan)  # fallback still produced a runnable child


def test_llm_mutator_falls_back_when_plan_violates_domain_bounds(domain):
    bad_plan = dict(GOOD_PLAN, params={"alpha": 9.0, "rounds": 99, "mode": "telepathy"})
    mutator = LLMMutator(
        FakeLLM(
            handlers={"hypothesize": GOOD_HYPOTHESIS, "plan_experiment": bad_plan}
        ),
        _skills(),
    )
    child = mutator.mutate(
        "vary_params", [domain.seed_candidates()[0]], domain=domain, rng=random.Random(2)
    )

    assert mutator.fallbacks_used == 1
    assert "rejected by domain" in (mutator.last_error or "")
    domain.validate_plan(child.plan)
    assert child.plan.params["alpha"] <= 1.0


def test_engine_with_llm_mutator_still_advances(project, domain):
    from ai_scientist.schema import Metrics
    from ai_scientist.search import SearchEngine

    llm = FakeLLM(
        handlers={"hypothesize": GOOD_HYPOTHESIS, "plan_experiment": GOOD_PLAN}
    )
    engine = SearchEngine(
        project,
        domain,
        project.read_config().search,
        mutator=LLMMutator(llm, _skills()),
        rng=random.Random(3),
    )
    for candidate in engine.seed():
        engine.ingest(
            candidate,
            Metrics(fitness=0.4, descriptor={"quality": 0.4, "cost": 0.2}, behavior=[1.0, 0.0]),
        )
    children, stats = engine.propose(2)
    # the model returns one fixed plan, so the second proposal is a duplicate by fingerprint
    assert stats.produced + stats.duplicates >= 2
    assert children, "expected at least one novel child from the model path"


# --------------------------------------------------------------------- routing
@pytest.fixture
def isolated_env(monkeypatch):
    """No ambient credentials and no `.env` discovery, so routing is what we set here."""
    from ai_scientist import llm as llm_module

    monkeypatch.setattr(llm_module, "load_env", lambda *a, **k: None)
    for key in (
        "AI_SCIENTIST_FAKE_LLM",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "OPENAI_API_KEY",
        "OPENAI_PREFER_AZURE",
    ):
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def test_fake_llm_forced_by_env(isolated_env):
    isolated_env.setenv("AI_SCIENTIST_FAKE_LLM", "1")
    isolated_env.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    isolated_env.setenv("AZURE_OPENAI_API_KEY", "placeholder")
    isolated_env.setenv("AZURE_OPENAI_DEPLOYMENT", "some-deployment")
    assert get_llm().name == "fake"


def test_no_credentials_degrades_to_fake(isolated_env):
    assert get_llm().name == "fake"
    assert get_llm(allow_network=False).name == "fake"


def _capture_client(monkeypatch) -> dict[str, object]:
    captured: dict[str, object] = {}

    def fake_init(self, *, provider, model, base_url=None):
        captured.update({"provider": provider, "model": model, "base_url": base_url})
        self.name = provider
        self.model = model

    monkeypatch.setattr(OpenAICompatibleClient, "__init__", fake_init)
    return captured


def test_azure_preferred_over_direct_openai(isolated_env):
    isolated_env.setenv("OPENAI_PREFER_AZURE", "true")
    isolated_env.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    isolated_env.setenv("AZURE_OPENAI_API_KEY", "placeholder")
    isolated_env.setenv("AZURE_OPENAI_DEPLOYMENT", "my-deployment")
    isolated_env.setenv("OPENAI_API_KEY", "placeholder")
    captured = _capture_client(isolated_env)

    assert get_llm().name == "azure"
    # deployment name is the model id, and the Azure v1 path is used
    assert captured["model"] == "my-deployment"
    assert captured["base_url"] == "https://example.openai.azure.com/openai/v1/"


def test_direct_openai_used_when_azure_disabled(isolated_env):
    isolated_env.setenv("OPENAI_PREFER_AZURE", "false")
    isolated_env.setenv("OPENAI_API_KEY", "placeholder")
    captured = _capture_client(isolated_env)
    assert get_llm().name == "openai"
    assert captured["base_url"] is None


def test_api_key_is_never_a_call_argument():
    """Regression: keys used to travel as a parameter and leaked into tracebacks."""
    import inspect

    params = set(inspect.signature(OpenAICompatibleClient.__init__).parameters)
    assert "api_key" not in params
    assert {"provider", "model"} <= params


def test_missing_sdk_raises_an_actionable_error(isolated_env):
    import builtins

    real_import = builtins.__import__

    def no_openai(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("No module named 'openai'")
        return real_import(name, *args, **kwargs)

    isolated_env.setenv("AZURE_OPENAI_API_KEY", "placeholder")
    isolated_env.setattr(builtins, "__import__", no_openai)
    with pytest.raises(MissingLLMDependency, match=r"pip install"):
        OpenAICompatibleClient(provider="azure", model="m", base_url="https://x/openai/v1/")


def test_response_json_requires_a_payload():
    with pytest.raises(ValueError, match="no JSON payload"):
        FakeLLM(handlers={"x": "no json here"}).complete("x", "u").json()


def test_load_env_finds_a_dotenv_upwards_without_overriding(tmp_path, monkeypatch):
    from ai_scientist.llm import load_env

    (tmp_path / ".env").write_text("AZURE_OPENAI_DEPLOYMENT=from-dotenv\nSCI_TEST_ONLY=yes\n")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "already-set")
    monkeypatch.delenv("SCI_TEST_ONLY", raising=False)

    load_env.cache_clear()
    found = load_env(str(nested))
    load_env.cache_clear()

    assert found == str(tmp_path / ".env")
    assert os.environ["AZURE_OPENAI_DEPLOYMENT"] == "already-set"  # real env wins
    assert os.environ["SCI_TEST_ONLY"] == "yes"  # missing value filled in


def test_load_env_returns_none_when_absent(tmp_path):
    """No `.env` anywhere up the chain must be a quiet None, not an exception."""
    from ai_scientist.llm import load_env

    load_env.cache_clear()
    try:
        assert load_env(str(tmp_path)) is None
    finally:
        load_env.cache_clear()
