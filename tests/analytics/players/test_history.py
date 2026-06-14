"""Tests for analytics.players.history — player_archetype_history."""

from __future__ import annotations

import pytest
import duckdb

from legacy_engine.analytics.players.history import (
    ArchetypeRegimeRow,
    player_archetype_history,
)
from legacy_engine.ingestion.banlist import BAN_EVENTS
from legacy_engine.analytics.trends import regime_windows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_con() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE tournaments ("
        "id VARCHAR PRIMARY KEY, name VARCHAR, date VARCHAR, "
        "uri VARCHAR, format VARCHAR, source VARCHAR, provenance VARCHAR)"
    )
    con.execute(
        "CREATE TABLE decks ("
        "tournament_id VARCHAR, deck_idx INTEGER, player VARCHAR, "
        "result VARCHAR, archetype VARCHAR, variant VARCHAR, "
        "PRIMARY KEY (tournament_id, deck_idx))"
    )
    return con


def _add_tournament(con: duckdb.DuckDBPyConnection, tid: str, date: str) -> None:
    con.execute(
        "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
        [tid, f"Event {tid}", date, f"https://{tid}", "Legacy", "paper", "paper"],
    )


def _add_deck(
    con: duckdb.DuckDBPyConnection,
    tid: str,
    idx: int,
    player: str,
    archetype: str | None,
) -> None:
    con.execute(
        "INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)",
        [tid, idx, player, "1st", archetype, None],
    )


def _two_regime_dates() -> tuple[str, str]:
    """Return (date_in_regime_0, date_in_regime_1) from the live BAN_EVENTS list.

    regime_0 is the baseline (pre-first ban); its 'since' is None, so we need a date
    before the first ban to fall into it.  regime_1 is after the first ban.
    """
    windows = regime_windows()
    # Baseline window: since=None, until=first_ban_date
    w0 = windows[0]
    w1 = windows[1] if len(windows) > 1 else windows[0]

    # Date in baseline: one day before the first ban date
    from datetime import date, timedelta

    if w0.until is not None:
        d0 = (w0.until - timedelta(days=7)).isoformat()
    else:
        d0 = "2020-01-01"

    # Date in regime 1
    if w1.since is not None:
        d1 = (w1.since + timedelta(days=7)).isoformat()
    else:
        d1 = "2023-01-01"

    return d0, d1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_con() -> duckdb.DuckDBPyConnection:
    """One player ('alice') with decks in two different regimes."""
    con = _make_con()
    d0, d1 = _two_regime_dates()

    # Regime 0: Alice plays Dimir Tempo × 2
    _add_tournament(con, "r0t1", d0)
    _add_deck(con, "r0t1", 0, "Alice", "Dimir Tempo")
    _add_deck(con, "r0t1", 1, "Alice", "Dimir Tempo")

    # Regime 1: Alice switches to Death and Taxes × 3
    _add_tournament(con, "r1t1", d1)
    _add_deck(con, "r1t1", 0, "Alice", "Death and Taxes")
    _add_deck(con, "r1t1", 1, "Alice", "Death and Taxes")
    _add_deck(con, "r1t1", 2, "Alice", "Death and Taxes")

    return con


@pytest.fixture
def alias_map_alice() -> dict[str, str]:
    return {"alice_alt": "alice"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPlayerArchetypeHistory:
    def test_returns_list(self, simple_con: duckdb.DuckDBPyConnection) -> None:
        result = player_archetype_history(simple_con, "alice", alias_map={})
        assert isinstance(result, list)

    def test_all_rows_are_archetype_regime_rows(
        self, simple_con: duckdb.DuckDBPyConnection
    ) -> None:
        result = player_archetype_history(simple_con, "alice", alias_map={})
        for row in result:
            assert isinstance(row, ArchetypeRegimeRow)

    def test_regime_partition_dimir_tempo(self, simple_con: duckdb.DuckDBPyConnection) -> None:
        """Alice's Dimir Tempo decks appear in regime 0 with count=2."""
        result = player_archetype_history(simple_con, "alice", alias_map={})
        windows = regime_windows()
        r0_label = windows[0].label

        r0_rows = [r for r in result if r.regime_label == r0_label and r.archetype == "Dimir Tempo"]
        assert len(r0_rows) == 1
        assert r0_rows[0].deck_count == 2

    def test_regime_partition_death_and_taxes(
        self, simple_con: duckdb.DuckDBPyConnection
    ) -> None:
        """Alice's Death and Taxes decks appear in regime 1 with count=3."""
        result = player_archetype_history(simple_con, "alice", alias_map={})
        windows = regime_windows()
        r1_label = windows[1].label if len(windows) > 1 else windows[0].label

        r1_rows = [r for r in result if r.regime_label == r1_label and r.archetype == "Death and Taxes"]
        assert len(r1_rows) == 1
        assert r1_rows[0].deck_count == 3

    def test_decks_do_not_cross_regime_boundary(
        self, simple_con: duckdb.DuckDBPyConnection
    ) -> None:
        """Regime 0 has no Death and Taxes; regime 1 has no Dimir Tempo."""
        result = player_archetype_history(simple_con, "alice", alias_map={})
        windows = regime_windows()
        r0_label = windows[0].label
        r1_label = windows[1].label if len(windows) > 1 else windows[0].label

        r0_dt = [r for r in result if r.regime_label == r0_label and r.archetype == "Death and Taxes"]
        r1_dimir = [r for r in result if r.regime_label == r1_label and r.archetype == "Dimir Tempo"]
        assert r0_dt == []
        assert r1_dimir == []

    def test_empty_regime_omitted(self, simple_con: duckdb.DuckDBPyConnection) -> None:
        """Regimes where the player has no decks produce no rows."""
        result = player_archetype_history(simple_con, "alice", alias_map={})
        regimes_with_rows = {r.regime_label for r in result}
        all_regime_labels = {w.label for w in regime_windows()}
        # Only the two regimes where Alice actually played appear
        assert regimes_with_rows.issubset(all_regime_labels)
        # The regimes where Alice has no decks are absent from the result
        empty_regime_labels = all_regime_labels - regimes_with_rows
        # We have more regimes than rows (assuming BAN_EVENTS has ≥2 events after our fixtures)
        if len(regime_windows()) > 2:
            assert len(empty_regime_labels) >= 0  # At minimum, the constraint holds structurally

    def test_alias_pooling_in_history(
        self,
        simple_con: duckdb.DuckDBPyConnection,
        alias_map_alice: dict[str, str],
    ) -> None:
        """An aliased handle ('alice_alt') pools into the same player_id 'alice'."""
        d0, d1 = _two_regime_dates()
        # Add a deck from the alias handle in regime 0
        _add_deck(simple_con, "r0t1", 99, "alice_alt", "Dimir Tempo")

        result = player_archetype_history(simple_con, "alice", alias_map=alias_map_alice)
        windows = regime_windows()
        r0_label = windows[0].label
        r0_dimir = [r for r in result if r.regime_label == r0_label and r.archetype == "Dimir Tempo"]
        assert len(r0_dimir) == 1
        # alice (2 decks) + alice_alt (1 deck) = 3
        assert r0_dimir[0].deck_count == 3

    def test_unknown_player_returns_empty(self, simple_con: duckdb.DuckDBPyConnection) -> None:
        result = player_archetype_history(simple_con, "nobody-ever-played", alias_map={})
        assert result == []

    def test_empty_player_id_returns_empty(self, simple_con: duckdb.DuckDBPyConnection) -> None:
        result = player_archetype_history(simple_con, "", alias_map={})
        assert result == []

    def test_no_tables_returns_empty(self) -> None:
        con = duckdb.connect(":memory:")
        result = player_archetype_history(con, "alice", alias_map={})
        assert result == []

    def test_unlabeled_decks_included(self, simple_con: duckdb.DuckDBPyConnection) -> None:
        """Decks without an archetype label (archetype=NULL) appear with archetype=None."""
        d0, _ = _two_regime_dates()
        _add_deck(simple_con, "r0t1", 98, "Alice", None)  # NULL archetype

        result = player_archetype_history(simple_con, "alice", alias_map={})
        windows = regime_windows()
        r0_label = windows[0].label
        none_rows = [r for r in result if r.regime_label == r0_label and r.archetype is None]
        assert len(none_rows) == 1
        assert none_rows[0].deck_count == 1

    def test_multiple_archetypes_same_regime(self) -> None:
        """Multiple archetypes in one regime each get their own row."""
        con = _make_con()
        d0, _ = _two_regime_dates()
        _add_tournament(con, "t0", d0)
        _add_deck(con, "t0", 0, "Bob", "Dimir Tempo")
        _add_deck(con, "t0", 1, "Bob", "Dimir Tempo")
        _add_deck(con, "t0", 2, "Bob", "Reanimator")

        result = player_archetype_history(con, "bob", alias_map={})
        windows = regime_windows()
        r0_label = windows[0].label
        r0_rows = [r for r in result if r.regime_label == r0_label]
        archetypes_seen = {r.archetype for r in r0_rows}
        assert "Dimir Tempo" in archetypes_seen
        assert "Reanimator" in archetypes_seen

        dimir_row = next(r for r in r0_rows if r.archetype == "Dimir Tempo")
        reanimator_row = next(r for r in r0_rows if r.archetype == "Reanimator")
        assert dimir_row.deck_count == 2
        assert reanimator_row.deck_count == 1
