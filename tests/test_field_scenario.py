from __future__ import annotations

import json

import pytest

from legacy_engine.advisory.field_scenario import (
    load_field_scenario,
    scenario_projection_inputs,
)
from legacy_engine.ingestion import store


@pytest.fixture
def con():
    connection = store.connect(":memory:")
    store.init_schema(connection)
    connection.execute(
        "INSERT INTO decks VALUES ('known', 0, 'p', '', 'Known Deck', NULL)"
    )
    connection.execute(
        "INSERT INTO tournaments VALUES ('known', 'known', '2026-01-01', '', 'Legacy', 'src', 'online')"
    )
    try:
        yield connection
    finally:
        connection.close()


def test_counted_scenario_preserves_supplied_total_and_unknown_mass(tmp_path, con):
    path = tmp_path / "room.txt"
    path.write_text("0.6 Known Deck 6\n0.4 Affinity Combo 4\n", encoding="utf-8")
    scenario = load_field_scenario(con, path, label="Saved room")

    assert scenario.label == "Saved room"
    assert scenario.count_basis == "supplied-observations"
    assert scenario.supplied_counts == {"Known Deck": 6, "Affinity Combo": 4}
    assert scenario.supplied_total == 10
    assert scenario.effective_count_total == 10
    assert scenario.unknown_opponents == ("Affinity Combo",)
    assert scenario.unknown_share == pytest.approx(0.4)
    assert scenario.field.field_source == "custom"
    assert json.loads(json.dumps(scenario.model_dump()))["source_sha256"] == scenario.source_sha256


def test_share_only_scenario_uses_fixed_weights_and_keeps_global_presence_separate(tmp_path, con):
    path = tmp_path / "share-only.txt"
    path.write_text("0.6 Known Deck\n0.4 Unknown Deck\n", encoding="utf-8")
    scenario = load_field_scenario(con, path)
    inputs = scenario_projection_inputs(scenario, global_presence={"Known Deck": 1.0, "Globally Present": 0.0})

    assert scenario.label == "share-only"
    assert scenario.count_basis == "share-only-fixed-weights"
    assert scenario.counts is None
    assert inputs["shares"] == {"Known Deck": 0.6, "Unknown Deck": 0.4}
    assert inputs["counts"] is None
    assert inputs["candidate_presence"] == {"Known Deck": 1.0, "Globally Present": 0.0}
    assert inputs["field_scenario"]["unknown_opponents"] == ["Unknown Deck"]


def test_effective_n_declared_total_is_retained_when_minimum_one_allocation_overshoots(tmp_path, con):
    path = tmp_path / "effective.txt"
    path.write_text("# effective_n: 2\n0.5 Known Deck\n0.3 A\n0.2 B\n", encoding="utf-8")
    scenario = load_field_scenario(con, path, known_archetypes=frozenset({"Known Deck", "A", "B"}))

    assert scenario.count_basis == "declared-effective-concentration"
    assert scenario.declared_effective_n == 2
    assert scenario.effective_count_total == 3
    assert scenario.supplied_total is None


def test_strict_scenario_rejects_synthetic_missing_counts_before_loading(tmp_path, con):
    path = tmp_path / "mixed.txt"
    path.write_text("0.6 Known Deck 6\n0.4 Affinity Combo\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mixes counted and share-only"):
        load_field_scenario(con, path)


def test_invalid_file_and_blank_label_fail_honestly(tmp_path, con):
    with pytest.raises(ValueError, match="does not exist"):
        load_field_scenario(con, tmp_path / "missing.txt")
    path = tmp_path / "named.txt"
    path.write_text("1.0 Known Deck\n", encoding="utf-8")
    assert load_field_scenario(con, path, label="   ").label == "named"
