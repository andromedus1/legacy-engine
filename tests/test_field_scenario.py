from __future__ import annotations

import json
import importlib.util
from pathlib import Path

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
    assert sum(scenario.posterior_counts.values()) == pytest.approx(2)
    assert sum(scenario.projection_field().counts.values()) == pytest.approx(2)


def test_per_line_counts_ignore_effective_n_header_without_rescaling(tmp_path, con):
    path = tmp_path / "counted-with-header.txt"
    path.write_text(
        "# effective_n: 2\n0.5 Known Deck 50\n0.5 Other Deck 50\n",
        encoding="utf-8",
    )
    scenario = load_field_scenario(
        con, path, known_archetypes=frozenset({"Known Deck", "Other Deck"}),
    )

    assert scenario.count_basis == "supplied-observations"
    assert scenario.declared_effective_n is None
    assert scenario.supplied_total == 100
    assert scenario.effective_count_total == 100
    assert sum(scenario.posterior_counts.values()) == pytest.approx(100)


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


def test_field_override_requires_a_private_output_path():
    """The public generator must reject custom scenarios before opening the DB."""
    script = Path(__file__).parents[1] / "scripts" / "refresh_best_call_ranking.py"
    spec = importlib.util.spec_from_file_location("refresh_best_call_ranking_private", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(ValueError, match="separate output path"):
        module.generate_ranking(
            db_path=Path("missing.duckdb"),
            out_path=module.DEFAULT_OUT,
            field_path=Path("missing-field.txt"),
        )


def test_invalid_custom_field_preserves_existing_output_before_compute(tmp_path, monkeypatch):
    from legacy_engine.ingestion import store

    script = Path(__file__).parents[1] / "scripts" / "refresh_best_call_ranking.py"
    spec = importlib.util.spec_from_file_location("refresh_ranking_invalid_field", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    db_path = tmp_path / "empty.duckdb"
    connection = store.connect(db_path)
    store.init_schema(connection)
    connection.close()
    field_path = tmp_path / "invalid.txt"
    field_path.write_text("not a field row\n", encoding="utf-8")
    output = tmp_path / "local.html"
    output.write_text("last good", encoding="utf-8")
    monkeypatch.setattr(module, "compute_blob", lambda *_args, **_kwargs: pytest.fail("computed before parsing"))

    with pytest.raises(ValueError, match="non-numeric share"):
        module.generate_ranking(
            db_path=db_path,
            out_path=output,
            field_path=field_path,
            field_since="2026-01-01",
        )
    assert output.read_text(encoding="utf-8") == "last good"
