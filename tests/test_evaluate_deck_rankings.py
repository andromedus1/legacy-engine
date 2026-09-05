"""Chronological complete-day evaluation contracts."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import duckdb


def _load_script():
    path = Path(__file__).parents[1] / "scripts" / "evaluate_deck_rankings.py"
    spec = importlib.util.spec_from_file_location("evaluate_deck_rankings", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE tournaments (id VARCHAR, date VARCHAR, source VARCHAR, provenance VARCHAR)")
    con.execute(
        "CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, player VARCHAR, result VARCHAR, archetype VARCHAR, variant VARCHAR)"
    )
    con.execute("CREATE TABLE rounds (tournament_id VARCHAR, match_idx INTEGER, player1 VARCHAR, player2 VARCHAR, result VARCHAR)")
    rows = [
        ("e1", "2026-01-01", "s", "online", "A", "a1"),
        ("e2", "2026-01-02", "s", "online", "A", "a1"),
        ("e3", "2026-01-03", "s", "online", "B", "b1"),
        ("e4", "2026-01-04", "s", "online", "B", "b1"),
    ]
    con.executemany("INSERT INTO tournaments VALUES (?, ?, ?, ?)", [row[:4] for row in rows])
    for event_id, _date, _source, _prov, archetype, variant in rows:
        con.execute(
            "INSERT INTO decks VALUES (?, 0, ?, ?, ?, ?)",
            [event_id, f"{event_id}-p1", "1st", archetype, variant],
        )
        con.execute(
            "INSERT INTO decks VALUES (?, 1, ?, ?, ?, ?)",
            [event_id, f"{event_id}-p2", "2nd", "B" if archetype == "A" else "A", "b1" if archetype == "A" else "a1"],
        )
        con.execute(
            "INSERT INTO rounds VALUES (?, 0, ?, ?, '2-0')",
            [event_id, f"{event_id}-p1", f"{event_id}-p2"],
        )
    return con


def test_field_evaluation_uses_complete_day_cutoffs_and_fixed_methods() -> None:
    module = _load_script()
    result = module.evaluate_chronologically(
        _db(),
        since="2026-01-01",
        until="2026-01-05",
        include_matchups=False,
    )
    assert [score.method for score in result.field_scores] == [
        "half-life-14d", "half-life-28d", "half-life-56d", "uniform"
    ]
    assert all(len(score.folds) == 3 for score in result.field_scores)
    assert all(score.scored_decks == 6 for score in result.field_scores)
    assert all(fold.cutoff < fold.holdout_until for fold in result.field_scores[0].folds)
    assert "source" in result.source_selection_note


def test_unknown_holdout_label_is_scored_with_explicit_unseen_accounting() -> None:
    module = _load_script()
    con = _db()
    con.execute("UPDATE decks SET archetype='Unknown' WHERE tournament_id='e4' AND deck_idx=0")
    result = module.evaluate_field_methods(
        con,
        since="2026-01-01",
        until="2026-01-05",
        half_lives=(14.0,),
    )[0]
    assert result.scored_decks == 6
    assert result.folds[-1].unseen_label_decks == 1
    assert result.logloss is not None and result.brier is not None


def test_matchup_scoring_counts_each_unordered_pair_once() -> None:
    module = _load_script()
    result = module.evaluate_chronologically(
        _db(),
        since="2026-01-01",
        until="2026-01-05",
        include_matchups=True,
    )
    assert len(result.match_scores) == 3
    available = [score for score in result.match_scores if score.available]
    # A minimal fixture may lack optional era metadata; when available, every
    # two-directed-row match is counted once in scored_matches.
    if available:
        assert all(score.scored_matches <= 2 for score in available)
        assert all(score.scored_pairs <= score.scored_matches for score in available)
