from __future__ import annotations

import random

import pytest

from ai_scientist.domain import DomainMetricsError, load_domain, validate_metrics
from ai_scientist.schema import Axis, Candidate, EliteRecord, ExperimentPlan, Hypothesis, Metrics
from ai_scientist.search import (
    FakeMutator,
    MapElites,
    NoveltyArchive,
    SearchEngine,
    cosine_distance,
    pick_op,
)

AXES = [Axis(name="quality", edges=[0.0, 0.5, 1.0001]), Axis(name="cost", edges=[0.0, 0.5, 1.0001])]


def _record(fitness: float, descriptor: dict[str, float], *, behavior=None) -> EliteRecord:
    hyp = Hypothesis(statement="s", claim="c")
    plan = ExperimentPlan(
        hypothesis_id=hyp.hypothesis_id,
        domain="fake_toy",
        params={"alpha": fitness, "rounds": 2, "mode": "debate"},
    )
    candidate = Candidate(hypothesis=hyp, plan=plan)
    metrics = Metrics(fitness=fitness, descriptor=descriptor, behavior=behavior or [fitness])
    archive = MapElites(AXES)
    return EliteRecord(
        candidate=candidate,
        metrics=metrics,
        cell=archive.cell_for(descriptor),
        fitness=fitness,
    )


# --------------------------------------------------------------------- MAP-Elites
def test_insert_occupies_empty_cell_and_only_better_replaces():
    archive = MapElites(AXES)
    assert archive.insert(_record(0.4, {"quality": 0.2, "cost": 0.2})) is True
    assert archive.insert(_record(0.3, {"quality": 0.2, "cost": 0.2})) is False
    assert archive.insert(_record(0.9, {"quality": 0.2, "cost": 0.2})) is True
    assert archive.cells[(0, 0)].fitness == 0.9
    assert len(archive.cells) == 1
    assert archive.insert(_record(0.1, {"quality": 0.9, "cost": 0.9})) is True
    assert len(archive.cells) == 2
    assert archive.total_cells == 4
    assert archive.occupancy == 0.5


def test_equal_fitness_does_not_replace():
    archive = MapElites(AXES)
    archive.insert(_record(0.5, {"quality": 0.2, "cost": 0.2}))
    assert archive.insert(_record(0.5, {"quality": 0.2, "cost": 0.2})) is False


def test_pinned_elite_is_immortal():
    archive = MapElites(AXES)
    weak = _record(0.2, {"quality": 0.2, "cost": 0.2})
    archive.insert(weak)
    archive.pin(weak.elite_id)
    assert archive.insert(_record(0.99, {"quality": 0.2, "cost": 0.2})) is False
    archive.pin(weak.elite_id, False)
    assert archive.insert(_record(0.99, {"quality": 0.2, "cost": 0.2})) is True


def test_descriptor_must_cover_all_axes():
    archive = MapElites(AXES)
    with pytest.raises(KeyError):
        archive.cell_for({"quality": 0.5})


def test_neighbors_and_empty_neighbor_count():
    archive = MapElites(AXES)
    archive.insert(_record(0.5, {"quality": 0.2, "cost": 0.2}))
    assert set(archive.neighbors((0, 0))) == {(1, 0), (0, 1)}
    assert archive.empty_neighbor_count((0, 0)) == 2


def test_archive_persists_and_rejects_axis_drift(tmp_path):
    archive = MapElites(AXES)
    archive.insert(_record(0.7, {"quality": 0.9, "cost": 0.1}))
    path = tmp_path / "map.json"
    archive.save(path)
    reloaded = MapElites.load(path, AXES)
    assert reloaded.cells.keys() == archive.cells.keys()
    assert reloaded.best().fitness == 0.7
    with pytest.raises(ValueError, match="axes differ"):
        MapElites.load(path, [Axis(name="quality", edges=[0.0, 1.0])])


# --------------------------------------------------------------------- novelty
def test_novelty_of_empty_archive_is_maximal_and_duplicates_are_not_novel():
    archive = NoveltyArchive(k=3, max_size=3)
    assert archive.novelty([1.0, 0.0]) == 1.0
    archive.consider("a", [1.0, 0.0])
    assert archive.novelty([1.0, 0.0]) == 0.0
    assert archive.novelty([0.0, 1.0]) == 1.0


def test_novelty_replaces_least_novel_when_full():
    archive = NoveltyArchive(k=2, max_size=2)
    archive.consider("a", [1.0, 0.0])
    archive.consider("b", [1.0, 0.001])  # near-duplicate of a
    assert len(archive) == 2
    assert archive.consider("c", [0.0, 1.0]) is not None
    assert len(archive) == 2
    assert "c" in {e.candidate_id for e in archive.entries}


def test_cosine_distance_edges():
    assert cosine_distance([1.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)
    assert cosine_distance([1.0, 0.0], [0.0, 1.0]) == pytest.approx(1.0)
    assert cosine_distance([0.0, 0.0], [0.0, 0.0]) == 0.0
    assert cosine_distance([0.0, 0.0], [1.0, 0.0]) == 1.0
    with pytest.raises(ValueError):
        cosine_distance([1.0], [1.0, 2.0])


def test_novelty_persists(tmp_path):
    archive = NoveltyArchive(k=2, max_size=5)
    archive.consider("a", [1.0, 0.0], fitness=0.5)
    path = tmp_path / "novelty.jsonl"
    archive.save(path)
    reloaded = NoveltyArchive.load(path, k=2, max_size=5)
    assert [e.candidate_id for e in reloaded.entries] == ["a"]


# --------------------------------------------------------------------- mutation
def test_pick_op_excludes_crossover_with_one_parent():
    rng = random.Random(0)
    weights = {"crossover": 1.0, "vary_params": 1.0}
    assert {pick_op(rng, weights, n_parents=1) for _ in range(20)} == {"vary_params"}
    assert "crossover" in {pick_op(rng, weights, n_parents=2) for _ in range(40)}


def test_fake_mutator_produces_valid_distinct_children(domain):
    rng = random.Random(1)
    parent = domain.seed_candidates()[0]
    mutator = FakeMutator()
    seen = set()
    for op in ("vary_params", "sharpen_claim", "change_seed", "broaden_scope"):
        child = mutator.mutate(op, [parent], domain=domain, rng=rng)
        domain.validate_plan(child.plan)
        assert child.generation == parent.generation + 1
        assert child.hypothesis.parent_ids == [parent.hypothesis.hypothesis_id]
        assert child.origin == f"mutation:{op}"
        seen.add(child.fingerprint())
    assert len(seen) >= 3


def test_mutated_params_stay_in_bounds(domain):
    rng = random.Random(7)
    parent = domain.seed_candidates()[0]
    mutator = FakeMutator()
    child = parent
    for _ in range(40):
        child = mutator.mutate("vary_params", [child], domain=domain, rng=rng)
        domain.validate_plan(child.plan)  # raises if out of bounds
        assert 0.0 <= child.plan.params["alpha"] <= 1.0
        assert 1 <= child.plan.params["rounds"] <= 6


def test_crossover_mixes_parents(domain):
    rng = random.Random(3)
    a, b = domain.seed_candidates()[0], domain.seed_candidates()[2]
    b.plan.params["alpha"] = 0.9
    child = FakeMutator().mutate("crossover", [a, b], domain=domain, rng=rng)
    assert len(child.hypothesis.parent_ids) == 2
    domain.validate_plan(child.plan)


# --------------------------------------------------------------------- engine
def test_validate_metrics_requires_axis_coverage(domain):
    with pytest.raises(DomainMetricsError):
        validate_metrics(domain, Metrics(fitness=0.5, descriptor={"quality": 0.5}))


def test_engine_seeds_dedupe_and_persist(project):
    domain = load_domain("fake_toy")
    engine = SearchEngine(project, domain, project.read_config().search, rng=random.Random(0))
    seeds = engine.seed()
    assert len(seeds) == 3
    assert engine.seed() == []  # idempotent by fingerprint
    assert len(list(project.candidates_dir.glob("*.json"))) == 3


def test_engine_ingest_updates_archive_and_novelty(project):
    domain = load_domain("fake_toy")
    engine = SearchEngine(project, domain, project.read_config().search, rng=random.Random(0))
    candidate = engine.seed()[0]
    metrics = Metrics(
        fitness=0.6,
        descriptor={"quality": 0.6, "cost": 0.2},
        values={"quality": 0.6},
        behavior=[1.0, 0.0, 1.0],
    )
    outcome = engine.ingest(candidate, metrics, job_id="job_x")
    assert outcome.inserted and outcome.novel
    assert engine.summary()["cells_filled"] == 1
    assert project.map_path.exists() and project.novelty_path.exists()
    # reload from disk keeps the elite
    reloaded = SearchEngine(project, domain, project.read_config().search)
    assert reloaded.archive.best().elite_id == outcome.elite.elite_id


def test_engine_propose_needs_population_then_produces(project):
    domain = load_domain("fake_toy")
    engine = SearchEngine(project, domain, project.read_config().search, rng=random.Random(5))
    empty, stats = engine.propose(2)
    assert empty == [] and stats.produced == 0  # nothing to select from yet

    for candidate in engine.seed():
        engine.ingest(
            candidate,
            Metrics(
                fitness=0.5,
                descriptor={"quality": 0.5, "cost": 0.3},
                behavior=[1.0, 0.0],
            ),
        )
    children, stats = engine.propose(3)
    assert len(children) == 3 and stats.produced == 3
    for child in children:
        domain.validate_plan(child.plan)
        assert child.generation >= 1
