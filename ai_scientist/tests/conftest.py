from __future__ import annotations

import os
from pathlib import Path

import pytest

from ai_scientist.domain import load_domain
from ai_scientist.fs_layout import Workspace
from ai_scientist.ops.state import StateStore
from ai_scientist.schema import Budget, EngineConfig, Metadata

os.environ.setdefault("AI_SCIENTIST_FAKE_LLM", "1")


@pytest.fixture
def project(tmp_path: Path) -> Workspace:
    ws = Workspace(tmp_path / "study")
    config = EngineConfig(domain="fake_toy")
    config.resources.api_slots = 2
    config.ops.concurrency = 2
    config.ops.heartbeat_interval_s = 0.1
    config.ops.heartbeat_timeout_s = 1.0
    config.ops.scheduler_tick_s = 0.05
    config.ops.health_tick_s = 0.1
    config.ops.ops_triage_tick_s = 0.05
    config.ops.ops_triage_enabled = True
    config.ops.job_timeout_s = 60.0
    config.search.offspring_per_tick = 2
    config.search.target_inflight = 3
    ws.init(
        metadata=Metadata(
            project_id="study",
            question="does the toy loop work?",
            budget=Budget(max_usd=1.0),
            credentials_refs=["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"],
        ),
        config=config,
    )
    return ws


@pytest.fixture
def store(project: Workspace) -> StateStore:
    store = StateStore(project.db_path)
    yield store
    store.close()


@pytest.fixture
def domain():
    return load_domain("fake_toy")
