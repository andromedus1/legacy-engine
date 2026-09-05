"""Real snapshot-to-publication contracts for the served ranking experiment."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from legacy_engine.advisory.ranking_benchmark import BenchmarkFold
from legacy_engine.analytics.eras.store import ENTITY_ERAS_DDL
from legacy_engine.ingestion import store
from legacy_engine.workflows import deck_ranking_evaluation as evaluation
from legacy_engine.workflows import ranking_benchmark as snapshots


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    rules = tmp_path / "rules" / "Formats" / "Legacy" / "Archetypes"
    rules.mkdir(parents=True)
    for label, card in (("Alpha", "Brainstorm"), ("Beta", "Ponder"), ("Energy", "Guide of Souls")):
        (rules / f"{label}.json").write_text(json.dumps({
            "Name": label, "Conditions": [{"Type": "InMainboard", "Cards": [card]}],
        }))
    monkeypatch.setattr(snapshots, "RULES_DIR", tmp_path / "rules")
    colors = tmp_path / "colors.json"
    colors.write_bytes(evaluation.COLOR_SPLITS_REGISTRY_PATH.read_bytes())
    monkeypatch.setattr(evaluation, "COLOR_SPLITS_REGISTRY_PATH", colors)
    source = tmp_path / "source.duckdb"
    con = store.connect(source)
    store.init_schema(con)
    con.executemany("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        (name, "{1}", 1.0, "Creature", color, "", "", "normal", False, None, None)
        for name, color in (("Brainstorm", "U"), ("Ponder", "U"), ("Guide of Souls", "W"),
                            ("Orcish Bowmasters", "B"), ("Late Card", "R"))
    ])
    for event, date in (("old", "2026-07-01"), ("recent", "2026-07-07"), ("cutoff", "2026-07-13")):
        con.execute("INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [event, event, date, event, "Legacy", "fixture", "online"])
        con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", [
            (event, index, player, "", "Wrong live label", "Future camp")
            for index, player in enumerate(("alice", "bob", "carol", "dave"))
        ])
        con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [
            (event, 0, "main", "Brainstorm", 4), (event, 1, "main", "Ponder", 4),
            (event, 2, "main", "Guide of Souls", 4), (event, 3, "main", "Guide of Souls", 4),
            (event, 3, "main", "Orcish Bowmasters", 4),
        ])
        con.executemany("INSERT INTO rounds VALUES (?, ?, ?, ?, ?)", [
            (event, 0, "alice", "bob", "2-0"),
            (event, 1, "carol", "dave", "2-0"),
            (event, 2, "alice", "carol", "0-2"),
        ])
    con.execute("INSERT INTO deck_cards VALUES ('cutoff', 0, 'side', 'Late Card', 1)")
    con.execute(ENTITY_ERAS_DDL)
    con.close()
    return source, colors


def freeze(source: Path, destination: Path):
    return evaluation.freeze_ranking_origin(
        source, destination, cutoff="2026-07-13", evaluation_until="2026-07-20",
        regime_start="2026-06-29", draws=64,
    )


def test_real_freeze_matches_published_parent_points_and_preserves_color_splits(corpus, tmp_path):
    source, _colors = corpus
    frozen = freeze(source, tmp_path / "origin")
    snapshot = Path(frozen["paths"]["snapshot"])
    with duckdb.connect(str(snapshot), read_only=True) as con:
        assert set(con.execute("SELECT DISTINCT archetype FROM decks").fetchall()) == {
            ("Alpha",), ("Beta",), ("Boros Energy",), ("Mardu Energy",),
        }
        assert con.execute("SELECT DISTINCT variant FROM decks").fetchall() == [(None,)]
        assert con.execute("SELECT count(*) FROM tournaments WHERE date >= '2026-07-13'").fetchone()[0] == 0
        assert con.execute("SELECT count(*) FROM cards WHERE name='Late Card'").fetchone()[0] == 0
    fold = BenchmarkFold.model_validate(frozen["metadata"]["fold"])
    blob, *_rest = evaluation._production_inputs(snapshot, fold, draws=64)
    baseline = frozen["forecasts"]["1"]["rows"]
    for published in blob["arch"]:
        projected = baseline[published["subject"]]
        decision = published["decision"]
        assert projected["performance"] == pytest.approx(decision["performance"])
        assert projected["floor"] == pytest.approx(decision["floor"])
        # The page omits structural mirrors from its visible opponent ledger.
        cells = {cell["opponent"]: cell for cell in projected["cells"] if not cell["is_mirror"]}
        shown = {cell["opponent"]: cell for cell in decision["cells"]}
        assert cells.keys() == shown.keys()
        for opponent, cell in cells.items():
            served = shown[opponent]
            assert (cell["wins"], cell["n"]) == (served["wins"], served["n"])
            assert cell["mean"] == pytest.approx(served["mean"])
            assert cell["prior_strength"] == served["prior_strength"]
    direct = [cell for cell in frozen["forecasts"]["1"]["cells"]
              if cell["support_n"] > 0 and not cell["is_mirror"]]
    assert direct
    for cell in direct:
        identity = cell["source_identity"]["selected_view"]
        assert identity["match_n"] == cell["support_n"]
        assert len(identity["match_ids_sha256"]) == 64
        assert identity["windows"] and identity["pair_component_ids"]
        assert identity["clock"]["data_until"] == "2026-07-13"


def test_cutoff_day_raw_and_live_cache_mutations_cannot_change_forecasts(corpus, tmp_path):
    source, _colors = corpus
    first = freeze(source, tmp_path / "first")
    with duckdb.connect(str(source)) as con:
        con.execute("UPDATE rounds SET result='0-2' WHERE tournament_id='cutoff'")
        con.execute("UPDATE deck_cards SET count=60 WHERE tournament_id='cutoff'")
        con.execute("UPDATE decks SET archetype='Future label', variant='Future camp'")
        con.execute("INSERT INTO entity_eras VALUES ('Alpha','Alpha','2026-07-19',false,999,'[]',false,NULL,NULL,NULL,.05,'2026-07-19')")
        con.execute("INSERT INTO player_aliases VALUES ('alice','future-alias')")
    second = freeze(source, tmp_path / "second")
    assert first["metadata"]["training_facts_sha256"] == second["metadata"]["training_facts_sha256"]
    assert first["forecasts"] == second["forecasts"]


def test_heldout_replay_rejects_changed_parent_color_registry(corpus, tmp_path):
    source, colors = corpus
    frozen = freeze(source, tmp_path / "origin")
    fold = BenchmarkFold.model_validate(frozen["metadata"]["fold"])
    expected = frozen["metadata"]["color_splits_sha256"]
    colors.write_text(colors.read_text().replace("Boros Energy", "Changed Energy"))
    with pytest.raises(ValueError, match="color"):
        snapshots.load_heldout_outcomes(
            source, fold, expected_rules_sha256=frozen["metadata"]["rules_sha256"],
            color_splits_path=colors, expected_color_splits_sha256=expected,
            card_metadata_policy=evaluation.DEFAULT_CARD_METADATA_POLICY,
        )


def test_public_phases_reuse_frozen_forecasts_and_reject_changed_config(corpus, tmp_path, monkeypatch):
    source, _colors = corpus
    root = tmp_path / "experiment"
    origin = ("2026-07-13", "2026-07-20", "2026-06-29")
    frozen = freeze(source, root / "2026-07-13--2026-07-20")

    def unexpected_rebuild(*args, **kwargs):
        pytest.fail("a sealed origin must be reused, not rebuilt between experiment phases")

    monkeypatch.setattr(evaluation, "build_origin_snapshot", unexpected_rebuild)
    sealed = evaluation.run_served_model_evaluation(
        source, root, origins=(origin,), draws=64, phase="freeze",
    )
    assert sealed["prediction_artifacts"] == [frozen["artifact_sha256"]]
    result = evaluation.run_served_model_evaluation(
        source, root, origins=(origin,), draws=64, phase="development",
    )
    assert result["origins"][0]["total_support_matches"] == 3
    assert (root / "development-summary.json").is_file()
    assert not (root / "development-selection.json").exists()
    with pytest.raises(ValueError, match="configuration"):
        evaluation.run_served_model_evaluation(
            source, root, origins=(origin,), draws=65, phase="freeze",
        )
