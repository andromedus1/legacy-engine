"""Tests for analytics.players.identity — alias resolution, materialization, suggest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import duckdb

from legacy_engine.analytics.players.identity import (
    AliasSuggestion,
    load_alias_map,
    materialize_player_aliases,
    resolve_player,
    suggest_aliases,
)


# ---------------------------------------------------------------------------
# Fixtures and builders
# ---------------------------------------------------------------------------


ALIAS_CLUSTER_JSON = json.dumps({
    "version": "test",
    "players": {
        "example-player": {
            "display": "Example Player",
            "handles": ["Example Player", "ExamplePlayer_Alt", "Example42"],
            "notes": "Test cluster.",
        },
        "example-two": {
            "display": "Example Two",
            "handles": ["Example Two"],
            "notes": "Pro player, appears under full name only.",
        },
    },
})


@pytest.fixture
def aliases_file(tmp_path: Path) -> Path:
    p = tmp_path / "aliases.json"
    p.write_text(ALIAS_CLUSTER_JSON)
    return p


@pytest.fixture
def alias_map(aliases_file: Path) -> dict[str, str]:
    return load_alias_map(aliases_file)


@pytest.fixture
def in_memory_con() -> duckdb.DuckDBPyConnection:
    """Bare in-memory DuckDB with only the player_aliases table created."""
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE IF NOT EXISTS player_aliases ("
        "handle_norm VARCHAR PRIMARY KEY, player_id VARCHAR NOT NULL)"
    )
    return con


@pytest.fixture
def corpus_con() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with tournaments + decks tables for suggest_aliases tests.

    Example cluster design: a single person plays under three different handles across
    three separate events — they never appear in the same tournament on the same day.
    This is the realistic scenario the heuristic is designed to surface.

    Corpus:
      tournament T1 (date 2026-01-01):
        "Example Player", "Player X"

      tournament T2 (date 2026-01-15):
        "ExamplePlayer_Alt", "Player Y"

      tournament T3 (date 2026-02-01):
        "Example42", "Player Z"

      tournament T4 (date 2026-02-15):
        "Alice", "AliceB"  — co-occur on same day → must NOT be proposed

    Since the three example handles share the normalized prefix "example" (≥4 chars) and
    never appear in the same (tournament_id, date) pair, suggest_aliases must propose
    a cluster containing all three.  Alice/AliceB share prefix "alic" but co-occur
    in T4, so they must NOT be proposed.
    """
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE tournaments (id VARCHAR PRIMARY KEY, name VARCHAR, date VARCHAR, "
        "uri VARCHAR, format VARCHAR, source VARCHAR, provenance VARCHAR)"
    )
    con.execute(
        "CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, player VARCHAR, "
        "result VARCHAR, archetype VARCHAR, variant VARCHAR, PRIMARY KEY (tournament_id, deck_idx))"
    )

    def _add_event(tid: str, date: str, players: list[str]) -> None:
        con.execute(
            f"INSERT INTO tournaments VALUES ('{tid}', 'Event {tid}', '{date}', "
            f"'https://{tid}', 'Legacy', 'paper', 'topdeck')"
        )
        for i, p in enumerate(players):
            con.execute(
                "INSERT INTO decks VALUES (?, ?, ?, '1st', NULL, NULL)",
                [tid, i, p],
            )

    _add_event("t1", "2026-01-01", ["Example Player", "Player X"])
    _add_event("t2", "2026-01-15", ["ExamplePlayer_Alt", "Player Y"])
    _add_event("t3", "2026-02-01", ["Example42", "Player Z"])
    _add_event("t4", "2026-02-15", ["Alice", "AliceB"])  # co-occur → must NOT be proposed

    return con


# ---------------------------------------------------------------------------
# Unit 1 — load_alias_map
# ---------------------------------------------------------------------------


class TestLoadAliasMap:
    def test_loads_three_example_handles(self, aliases_file: Path) -> None:
        m = load_alias_map(aliases_file)
        assert m["example player"] == "example-player"
        assert m["exampleplayer_alt"] == "example-player"
        assert m["example42"] == "example-player"

    def test_loads_second_cluster(self, aliases_file: Path) -> None:
        m = load_alias_map(aliases_file)
        assert m["example two"] == "example-two"

    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        m = load_alias_map(tmp_path / "nonexistent.json")
        assert m == {}

    def test_empty_players_returns_empty(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.json"
        p.write_text('{"version": "x", "players": {}}')
        assert load_alias_map(p) == {}

    def test_normalizes_handles_on_load(self, aliases_file: Path) -> None:
        """Keys in the returned map are already normalized (lower + strip)."""
        m = load_alias_map(aliases_file)
        # None of the keys should have leading/trailing whitespace or uppercase.
        for k in m:
            assert k == k.strip().lower(), f"handle not normalized: {k!r}"


# ---------------------------------------------------------------------------
# Unit 1 — resolve_player
# ---------------------------------------------------------------------------


class TestResolvePlayer:
    def test_three_example_handles_resolve_to_one_id(self, alias_map: dict) -> None:
        assert resolve_player("Example Player", alias_map) == "example-player"
        assert resolve_player("ExamplePlayer_Alt", alias_map) == "example-player"
        assert resolve_player("Example42", alias_map) == "example-player"

    def test_second_cluster_resolves_to_itself(self, alias_map: dict) -> None:
        # "Example Two" is in the map; its canonical id is "example-two".
        assert resolve_player("Example Two", alias_map) == "example-two"

    def test_unknown_handle_resolves_to_normalized_self(self, alias_map: dict) -> None:
        result = resolve_player("UnknownPlayer99", alias_map)
        assert result == "unknownplayer99"

    def test_none_returns_empty_string(self, alias_map: dict) -> None:
        assert resolve_player(None, alias_map) == ""

    def test_blank_returns_empty_string(self, alias_map: dict) -> None:
        assert resolve_player("   ", alias_map) == ""

    def test_case_insensitive_resolution(self, alias_map: dict) -> None:
        assert resolve_player("example player", alias_map) == "example-player"
        assert resolve_player("EXAMPLE PLAYER", alias_map) == "example-player"

    def test_empty_alias_map_resolves_to_self(self) -> None:
        """Gated-additive: with no alias_map, resolve is equivalent to normalize_player."""
        from legacy_engine.analytics.match_results import normalize_player
        empty: dict[str, str] = {}
        for h in ["Example Player", "Alice", "  Bob  ", None]:
            assert resolve_player(h, empty) == normalize_player(h)

    def test_deterministic(self, alias_map: dict) -> None:
        """Same handle always gives the same result."""
        for _ in range(10):
            assert resolve_player("Example42", alias_map) == "example-player"


# ---------------------------------------------------------------------------
# Unit 2 — materialize_player_aliases
# ---------------------------------------------------------------------------


class TestMaterializePlayerAliases:
    def test_inserts_correct_rows(
        self, in_memory_con: duckdb.DuckDBPyConnection, alias_map: dict
    ) -> None:
        count = materialize_player_aliases(in_memory_con, alias_map)
        assert count == len(alias_map)
        rows = in_memory_con.execute(
            "SELECT handle_norm, player_id FROM player_aliases ORDER BY handle_norm"
        ).fetchall()
        row_dict = dict(rows)
        assert row_dict["example player"] == "example-player"
        assert row_dict["example42"] == "example-player"
        assert row_dict["exampleplayer_alt"] == "example-player"
        assert row_dict["example two"] == "example-two"

    def test_idempotent_run_twice_same_rows(
        self, in_memory_con: duckdb.DuckDBPyConnection, alias_map: dict
    ) -> None:
        """Calling materialize twice must yield the same rows (idempotent)."""
        count1 = materialize_player_aliases(in_memory_con, alias_map)
        count2 = materialize_player_aliases(in_memory_con, alias_map)
        assert count1 == count2
        rows = in_memory_con.execute(
            "SELECT count(*) FROM player_aliases"
        ).fetchone()
        assert rows is not None
        assert rows[0] == len(alias_map)

    def test_empty_map_creates_table_with_zero_rows(
        self, in_memory_con: duckdb.DuckDBPyConnection
    ) -> None:
        count = materialize_player_aliases(in_memory_con, {})
        assert count == 0
        rows = in_memory_con.execute(
            "SELECT count(*) FROM player_aliases"
        ).fetchone()
        assert rows is not None
        assert rows[0] == 0

    def test_rebuilds_on_second_call_with_different_map(
        self, in_memory_con: duckdb.DuckDBPyConnection
    ) -> None:
        """A second call with a different map replaces the old data entirely."""
        map1 = {"alice": "alice-id"}
        map2 = {"bob": "bob-id"}
        materialize_player_aliases(in_memory_con, map1)
        materialize_player_aliases(in_memory_con, map2)
        rows = in_memory_con.execute(
            "SELECT handle_norm FROM player_aliases"
        ).fetchall()
        handles = {r[0] for r in rows}
        assert "bob" in handles
        assert "alice" not in handles


# ---------------------------------------------------------------------------
# Unit 3 — suggest_aliases
# ---------------------------------------------------------------------------


class TestSuggestAliases:
    def test_proposes_example_cluster(self, corpus_con: duckdb.DuckDBPyConnection) -> None:
        """The three Example* handles (which never co-occur in the same tournament) should be
        proposed as a cluster."""
        suggestions = suggest_aliases(corpus_con, min_overlap=4)
        # Flatten all suggested handles across all suggestions.
        all_handle_sets = [set(s.handles) for s in suggestions]
        example_handles = {"Example Player", "ExamplePlayer_Alt", "Example42"}
        found = any(example_handles.issubset(s) for s in all_handle_sets)
        assert found, (
            f"Expected a suggestion containing {example_handles}; got: {all_handle_sets}"
        )

    def test_does_not_propose_co_occurring_handles(
        self, corpus_con: duckdb.DuckDBPyConnection
    ) -> None:
        """Alice and AliceB appear in the same event on the same day — must NOT be proposed."""
        suggestions = suggest_aliases(corpus_con, min_overlap=4)
        for s in suggestions:
            assert "Alice" not in s.handles or "AliceB" not in s.handles, (
                f"Co-occurring handles incorrectly proposed: {s.handles}"
            )

    def test_suggestions_are_read_only_writes_nothing(
        self, corpus_con: duckdb.DuckDBPyConnection
    ) -> None:
        """suggest_aliases must not create or modify any table."""
        # Record what tables exist before.
        before = {
            r[0]
            for r in corpus_con.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
        suggest_aliases(corpus_con, min_overlap=4)
        after = {
            r[0]
            for r in corpus_con.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
        assert before == after, f"suggest_aliases created tables: {after - before}"

    def test_empty_db_returns_empty(self) -> None:
        con = duckdb.connect(":memory:")
        result = suggest_aliases(con, min_overlap=4)
        assert result == []

    def test_missing_tables_returns_empty(self) -> None:
        """Tables absent → graceful empty list, no exception."""
        con = duckdb.connect(":memory:")
        con.execute("CREATE TABLE unrelated (x INT)")
        result = suggest_aliases(con, min_overlap=4)
        assert result == []

    def test_suggestion_contains_reason(
        self, corpus_con: duckdb.DuckDBPyConnection
    ) -> None:
        suggestions = suggest_aliases(corpus_con, min_overlap=4)
        for s in suggestions:
            assert isinstance(s.reason, str) and len(s.reason) > 0

    def test_returns_alias_suggestion_objects(
        self, corpus_con: duckdb.DuckDBPyConnection
    ) -> None:
        suggestions = suggest_aliases(corpus_con, min_overlap=4)
        assert all(isinstance(s, AliasSuggestion) for s in suggestions)

    def test_min_overlap_filters_short_stems(
        self, corpus_con: duckdb.DuckDBPyConnection
    ) -> None:
        """With a very high min_overlap, short-name handles are excluded from clustering."""
        suggestions_tight = suggest_aliases(corpus_con, min_overlap=20)
        # No handle in the corpus has a 20-char normalized prefix, so expect empty (or no example match).
        # "exampleplayer_alt" is 15 chars, so we'd need >15 chars for example to match.
        example_handles = {"Example Player", "ExamplePlayer_Alt", "Example42"}
        for s in suggestions_tight:
            assert not example_handles.issubset(set(s.handles)), (
                "Example cluster should not appear with min_overlap=20"
            )
