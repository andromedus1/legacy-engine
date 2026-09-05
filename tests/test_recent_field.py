"""Focused contracts for the current recency weighted field ledger."""

from __future__ import annotations

import duckdb
import pytest

from legacy_engine.advisory.recent_field import build_recent_field


def _db() -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE tournaments (id VARCHAR, date VARCHAR, source VARCHAR, provenance VARCHAR)"
    )
    con.execute(
        "CREATE TABLE decks (tournament_id VARCHAR, deck_idx INTEGER, archetype VARCHAR, variant VARCHAR)"
    )
    return con


def test_recent_field_uses_half_open_cutoff_and_exact_counts() -> None:
    con = _db()
    con.executemany(
        "INSERT INTO tournaments VALUES (?, ?, ?, ?)",
        [
            ("old", "2025-12-31", "old-source", "online"),
            ("a", "2026-01-09", "published-a", "online"),
            ("b", "2026-01-10", "published-b", "online"),
            ("cutoff", "2026-01-11", "future", "online"),
        ],
    )
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?)",
        [("old", 0, "A", "old"), ("a", 0, "A", "x"), ("b", 0, "B", "y"), ("cutoff", 0, "C", "future")],
    )

    result = build_recent_field(con, since="2026-01-01", until="2026-01-11", half_life_days=2)
    assert result.exact_observed_decks == 2
    assert result.exact_counts == {"A": 1, "B": 1}
    assert "C" not in result.shares
    expected_a = 2 ** (-2 / 2)
    expected_b = 2 ** (-1 / 2)
    assert result.weighted_counts["A"] == pytest.approx(expected_a)
    assert result.weighted_counts["B"] == pytest.approx(expected_b)
    assert result.shares["B"] > result.shares["A"]
    assert result.until == "2026-01-11"


def test_effective_counts_preserve_share_and_report_kish_ess() -> None:
    con = _db()
    con.executemany(
        "INSERT INTO tournaments VALUES (?, ?, ?, ?)",
        [("new", "2026-01-10", "s", "online"), ("old", "2026-01-01", "s", "online")],
    )
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?)",
        [("new", 0, "A", None), ("old", 0, "B", None)],
    )
    result = build_recent_field(con, since="2026-01-01", until="2026-01-11", half_life_days=1)
    total = sum(result.effective_counts.values())
    assert total == pytest.approx(result.effective_sample_size)
    assert result.effective_sample_size > sum(result.weighted_counts.values())
    assert result.effective_counts["A"] / total == pytest.approx(result.shares["A"])


def test_source_denominator_and_camp_fractions_reconcile() -> None:
    con = _db()
    con.executemany(
        "INSERT INTO tournaments VALUES (?, ?, ?, ?)",
        [("a", "2026-01-10", "MTGO", "online"), ("b", "2026-01-09", "paper", "paper")],
    )
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?)",
        [("a", 0, "A", "x"), ("a", 1, "A", "y"), ("b", 0, "B", None)],
    )
    result = build_recent_field(con, since="2026-01-01", until="2026-01-11")
    assert result.source_denominator == "published-list"
    assert not result.coverage_verified
    assert set(result.source_breakdown) == {"MTGO", "paper"}
    assert sum(item.published_list_share for item in result.source_breakdown.values()) == pytest.approx(1)
    assert sum(result.camp_fractions["A"].values()) == pytest.approx(1)
    assert result.camp_fractions["B"] == {"unlabeled": 1.0}


def test_unknown_conflict_remain_in_shares_for_host_filtering() -> None:
    con = _db()
    con.execute("INSERT INTO tournaments VALUES ('e', '2026-01-10', 's', 'online')")
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?)",
        [("e", 0, "A", None), ("e", 1, "Unknown", None), ("e", 2, "Conflict(Card)", None)],
    )
    result = build_recent_field(con, since="2026-01-01", until="2026-01-11")
    assert set(result.shares) == {"A", "Unknown", "Conflict(Card)"}
    # Host recommendation code filters these labels while retaining their
    # contribution to the published-list field denominator.
    assert sum(result.shares.values()) == pytest.approx(1)
    assert result.shares["A"] == pytest.approx(1 / 3)


def test_movement_uses_equal_length_previous_period_and_is_deterministic() -> None:
    con = _db()
    con.executemany(
        "INSERT INTO tournaments VALUES (?, ?, ?, ?)",
        [("p", "2025-12-31", "s", "online"), ("n", "2026-01-10", "s", "online")],
    )
    con.executemany(
        "INSERT INTO decks VALUES (?, ?, ?, ?)",
        [("p", 0, "A", None), ("n", 0, "B", None)],
    )
    first = build_recent_field(con, since="2026-01-01", until="2026-01-11")
    second = build_recent_field(con, since="2026-01-01", until="2026-01-11")
    assert first.as_dict() == second.as_dict()
    assert first.previous_since == "2025-12-22"
    assert first.movement["B"].delta > 0
    assert first.movement["A"].previous_share == pytest.approx(1.0)


def test_rejects_invalid_window_and_half_life() -> None:
    con = _db()
    with pytest.raises(ValueError, match="until"):
        build_recent_field(con, since="2026-01-02", until="2026-01-01")
    with pytest.raises(ValueError, match="half_life"):
        build_recent_field(con, since="2026-01-01", until="2026-01-02", half_life_days=0)
