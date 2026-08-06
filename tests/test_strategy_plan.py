import json

import pytest

from legacy_engine.analytics.match_results import MatchCoverage, MatchResults, MatchupTally
from legacy_engine.analytics.strategy_plan import (
    PLAN_IDS,
    aggregate_archetype_vs_plan_results,
    aggregate_strategic_plan_results,
    load_strategic_plan_registry,
    validate_current_plan_coverage,
)


def _raw(assignments=None, plans=None):
    return {
        "schema_version": 1,
        "plans": plans or [
            {"id": token, "label": token.title(), "description": f"The {token} plan."}
            for token in sorted(PLAN_IDS)
        ],
        "assignments": assignments or [
            {"archetype": "A1", "primary": "disrupt-pressure", "secondary": ["go-off"]},
            {"archetype": "A2", "primary": "disrupt-pressure"},
            {"archetype": "B", "primary": "go-off"},
        ],
    }


@pytest.fixture
def registry_file(tmp_path):
    def _make(**updates):
        raw = _raw()
        raw.update(updates)
        path = tmp_path / "plans.json"
        path.write_text(json.dumps(raw))
        return path
    return _make


@pytest.fixture
def match_results():
    def _make():
        return MatchResults(
            matchups={
                ("A1", "A2"): MatchupTally("A1", "A2", 2, 1),
                ("A2", "A1"): MatchupTally("A2", "A1", 1, 2),
                ("A1", "B"): MatchupTally("A1", "B", 3, 1),
                ("B", "A1"): MatchupTally("B", "A1", 1, 3),
                ("A2", "B"): MatchupTally("A2", "B", 2, 2),
                ("B", "A2"): MatchupTally("B", "A2", 2, 2),
                ("A1", "Missing"): MatchupTally("A1", "Missing", 1, 1),
                ("Missing", "A1"): MatchupTally("Missing", "A1", 1, 1),
            },
            archetypes={}, coverage=MatchCoverage(), provenance="paper",
            mirror_n={"A1": 2, "Missing": 1},
        )
    return _make


def test_registry_load_is_deterministic_and_covers_vocabulary(registry_file):
    path = registry_file()
    first = load_strategic_plan_registry(path)
    assert first == load_strategic_plan_registry(path)
    assert {plan.id for plan in first.plans} == PLAN_IDS
    assert first.assignment_for("A1").secondary == ("go-off",)


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"schema_version": 2}, "schema_version"),
        ({"plans": _raw()["plans"] + [_raw()["plans"][0]]}, "duplicate strategic plan"),
        ({"plans": [{**p, "id": "wat"} if i == 0 else p for i, p in enumerate(_raw()["plans"])]}, "allowed"),
        ({"plans": [{**p, "label": ""} if i == 0 else p for i, p in enumerate(_raw()["plans"])]}, "nonblank"),
        ({"assignments": _raw()["assignments"] + [_raw()["assignments"][0]]}, "duplicate strategic-plan assignment"),
        ({"assignments": [{"archetype": "A", "primary": "wat"}]}, "allowed"),
        ({"assignments": [{"archetype": "A", "primary": "go-off", "secondary": ["go-off"]}]}, "repeat primary"),
        ({"assignments": [{"archetype": "A", "primary": "go-off", "secondary": ["go-over", "go-over"]}]}, "repeated secondary"),
    ],
)
def test_registry_rejects_malformed_contract(registry_file, updates, message):
    with pytest.raises(ValueError, match=message):
        load_strategic_plan_registry(registry_file(**updates))


def test_missing_current_assignments_are_named_together(registry_file):
    registry = load_strategic_plan_registry(registry_file())
    with pytest.raises(ValueError, match="Missing, Zed"):
        validate_current_plan_coverage(registry, ["A1", "Zed", "Missing"])


def test_match_level_aggregation_is_complementary_and_honest(registry_file, match_results):
    registry = load_strategic_plan_registry(registry_file())
    result = aggregate_strategic_plan_results(
        match_results(), registry, current_archetypes=["A1", "A2", "B"],
        ground_n=8, since="2026-01-01", until="2026-02-01",
    )
    ab = result.cells[("disrupt-pressure", "go-off")]
    ba = result.cells[("go-off", "disrupt-pressure")]
    assert (ab.wins, ab.losses, ab.n) == (5, 3, 8)
    assert (ba.wins, ba.losses, ba.n) == (3, 5, 8)
    assert ab.measured and ba.measured
    assert ab.shrunk + ba.shrunk == pytest.approx(1)
    same = result.cells[("disrupt-pressure", "disrupt-pressure")]
    assert same.structural_same_plan and same.raw == same.shrunk == 0.5
    assert (same.wins, same.losses, same.n) == (0, 0, 0)
    assert (same.observed_n, same.mirror_n) == (3, 2)
    assert result.same_plan_matches == 5
    assert result.omitted_matches == 3
    assert result.provenance == "paper"
    assert (result.since, result.until) == ("2026-01-01", "2026-02-01")


def test_absent_external_cells_are_null_and_ground_n_is_inclusive(registry_file, match_results):
    registry = load_strategic_plan_registry(registry_file())
    result = aggregate_strategic_plan_results(
        match_results(), registry, current_archetypes=["A1", "A2", "B"],
        ground_n=9, since=None,
    )
    thin = result.cells[("disrupt-pressure", "go-off")]
    absent = result.cells[("go-over", "go-wide")]
    assert not thin.measured and thin.n == 8
    assert (absent.raw, absent.shrunk, absent.n, absent.measured) == (None, None, 0, False)


def test_archetype_vs_plan_uses_direct_tallies_and_structural_mirrors(
    registry_file, match_results,
):
    registry = load_strategic_plan_registry(registry_file())
    cells = aggregate_archetype_vs_plan_results(
        match_results(), registry, current_archetypes=["A1", "A2", "B"], ground_n=4,
    )
    external = cells[("A1", "go-off")]
    assert (external.wins, external.losses, external.mirror_n, external.n) == (3, 1, 0, 4)
    assert external.raw == .75 and external.measured
    same = cells[("A1", "disrupt-pressure")]
    assert (same.wins, same.losses, same.mirror_n, same.n) == (2, 1, 2, 3)
    assert same.raw == pytest.approx(2 / 3)
    assert not same.measured


def test_archetype_mirrors_never_ground_an_observation_free_plan_cell(registry_file):
    registry = load_strategic_plan_registry(registry_file())
    results = MatchResults(
        matchups={}, archetypes={}, coverage=MatchCoverage(), provenance=None,
        mirror_n={"A1": 20},
    )
    cell = aggregate_archetype_vs_plan_results(
        results, registry, current_archetypes=["A1"], ground_n=8,
    )[("A1", "disrupt-pressure")]
    assert (cell.n, cell.mirror_n) == (0, 20)
    assert cell.raw is None and cell.shrunk is None and not cell.measured
