from datetime import date

import duckdb
import pytest

from legacy_engine.analytics.eras.discovery import (
    DiscoveryDeck,
    load_discovery_calibration,
    load_outcome_free_corpus,
)
from legacy_engine.config import DISCOVERY_CALIBRATION_PATH


def _source_db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute("CREATE TABLE tournaments (id VARCHAR, date VARCHAR, source VARCHAR, provenance VARCHAR)")
    con.execute("CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, player VARCHAR, archetype VARCHAR)")
    con.execute("CREATE TABLE deck_cards (tournament_id VARCHAR, deck_idx INTEGER, board VARCHAR, name VARCHAR, count INTEGER)")
    con.execute("CREATE TABLE rounds (tournament_id VARCHAR, result VARCHAR)")
    con.execute("CREATE TABLE standings (tournament_id VARCHAR, wins INTEGER)")
    con.executemany("INSERT INTO tournaments VALUES (?, ?, ?, ?)", [
        ("old", "2026-01-01", "mtgo", "online"),
        ("cutoff", "2026-01-07", "paper", "paper"),
        ("future", "2026-01-08", "future", "online"),
    ])
    con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?)", [
        ("old", 1, " Alice ", "A"), ("cutoff", 0, "Bob", "A"),
        ("future", 0, "Eve", "A"),
    ])
    con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [
        ("old", 1, "Mainboard", "Brainstorm", 4),
        ("old", 1, "Sideboard", "Force of Will", 2),
        ("cutoff", 0, "main", "Brainstorm", 4),
        ("future", 0, "main", "Future Card", 4),
    ])
    return con


def test_calibration_is_checked_in_and_typed():
    calibration = load_discovery_calibration(DISCOVERY_CALIBRATION_PATH)
    assert calibration.calibration_id == "recurrent-segment-fingerprint-v2"
    assert calibration.weights.model_dump() == {
        "main": 0.4, "side": 0.25, "field": 0.2, "source": 0.1, "subject_share": 0.05,
    }


def test_cutoff_and_board_order_are_outcome_free():
    corpus = load_outcome_free_corpus(
        _source_db(), as_of=date(2026, 1, 7), taxonomy_version="tax-v1", legality_version="leg-v1"
    )
    assert [_deck.event_id for _deck in corpus.decks] == ["old", "cutoff"]
    assert corpus.decks[0].pilot_key == "old:alice"
    assert corpus.decks[0].sideboard[0].name == "Force of Will"
    assert "Future Card" not in {card.name for deck in corpus.decks for card in deck.mainboard}


def test_unknown_outcome_keys_are_rejected():
    with pytest.raises(Exception):
        DiscoveryDeck.model_validate({
            "event_id": "e", "event_date": date(2026, 1, 1), "deck_idx": 0,
            "pilot_key": None, "parent_archetype": "A", "source": "s", "provenance": "p",
            "mainboard": (), "sideboard": (), "wins": 2,
        })


def test_rounds_and_standings_are_not_required():
    con = _source_db()
    con.execute("DROP TABLE rounds")
    con.execute("DROP TABLE standings")
    corpus = load_outcome_free_corpus(
        con, as_of=date(2026, 1, 7), taxonomy_version="tax-v1", legality_version="leg-v1"
    )
    assert len(corpus.decks) == 2
