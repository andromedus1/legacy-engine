"""Tests for the persisted ingest-diff hand-off.

Covers:
  - persist_ingest_diff / load_ingest_diff round-trip (tmp path, not real data/)
  - load_ingest_diff returns None when file is absent
  - report new-cards: lists actual new-card names from the persisted diff
  - report new-cards: fallback message when no diff file exists
  - report speculate --new: uses persisted diff names
  - report speculate --new: graceful fallback when no diff file exists
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from legacy_engine.ingestion.store import IngestDiff, persist_ingest_diff, load_ingest_diff
from legacy_engine.models.card import Card


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _diff(
    new_names=("Alpha Strike", "Beta Ray"),
    total_after: int = 100,
    updated_at: str | None = "2026-06-14T00:00:00Z",
) -> IngestDiff:
    return IngestDiff(
        new_names=tuple(new_names),
        total_after=total_after,
        scryfall_updated_at=updated_at,
    )


# ---------------------------------------------------------------------------
# Unit: persist_ingest_diff / load_ingest_diff
# ---------------------------------------------------------------------------


class TestPersistLoadIngestDiff:
    """Round-trip and edge-case tests; all use tmp_path — no real data/."""

    def test_roundtrip(self, tmp_path):
        """Persisted diff deserialises to an equal IngestDiff."""
        diff = _diff()
        path = tmp_path / "diff.json"
        persist_ingest_diff(diff, path=path)

        loaded = load_ingest_diff(path=path)
        assert loaded is not None
        assert loaded.new_names == diff.new_names
        assert loaded.total_after == diff.total_after
        assert loaded.scryfall_updated_at == diff.scryfall_updated_at

    def test_absent_file_returns_none(self, tmp_path):
        """load_ingest_diff returns None when the file does not exist."""
        result = load_ingest_diff(path=tmp_path / "no_such_diff.json")
        assert result is None

    def test_order_preserved(self, tmp_path):
        """new_names order is preserved through the round-trip."""
        diff = _diff(new_names=("Zebra Card", "Aardvark Card"))
        path = tmp_path / "diff.json"
        persist_ingest_diff(diff, path=path)
        loaded = load_ingest_diff(path=path)
        assert loaded.new_names == ("Zebra Card", "Aardvark Card")

    def test_empty_new_names(self, tmp_path):
        """An empty diff (no new cards) round-trips cleanly."""
        diff = _diff(new_names=())
        path = tmp_path / "diff.json"
        persist_ingest_diff(diff, path=path)
        loaded = load_ingest_diff(path=path)
        assert loaded is not None
        assert loaded.new_names == ()
        assert loaded.total_after == 100

    def test_creates_parent_dirs(self, tmp_path):
        """persist_ingest_diff creates intermediate directories if needed."""
        path = tmp_path / "nested" / "sub" / "diff.json"
        persist_ingest_diff(_diff(), path=path)
        assert path.exists()

    def test_overwrites_previous(self, tmp_path):
        """Second persist overwrites the first (only the latest diff is kept)."""
        path = tmp_path / "diff.json"
        persist_ingest_diff(_diff(new_names=("Old Card",)), path=path)
        persist_ingest_diff(_diff(new_names=("New Card",)), path=path)
        loaded = load_ingest_diff(path=path)
        assert loaded.new_names == ("New Card",)

    def test_corrupt_file_returns_none(self, tmp_path):
        """A corrupt JSON file degrades gracefully to None."""
        path = tmp_path / "diff.json"
        path.write_text("not valid json{{")
        result = load_ingest_diff(path=path)
        assert result is None

    def test_json_contains_persisted_at(self, tmp_path):
        """The written file includes a persisted_at key for auditability."""
        path = tmp_path / "diff.json"
        persist_ingest_diff(_diff(), path=path)
        data = json.loads(path.read_text())
        assert "persisted_at" in data


# ---------------------------------------------------------------------------
# CLI integration: report new-cards
# ---------------------------------------------------------------------------


def _make_tiny_db(tmp_path: Path) -> Path:
    """Create a minimal DuckDB with one card so speculate has a pool to search."""
    import duckdb
    from legacy_engine.ingestion import store

    db_path = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db_path))
    card = Card(
        name="Brainstorm",
        cmc=1.0,
        type_line="Instant",
        colors=["U"],
        mana_cost="{U}",
    )
    store.load_cards(con, [card])
    con.close()
    return db_path


class TestReportNewCardsCLI:
    """CLI smoke tests for `report new-cards` with and without a persisted diff."""

    def _invoke_with_diff(self, args: list[str], diff: IngestDiff | None, tmp_path: Path):
        """Invoke `report new-cards` with a patched load_ingest_diff that returns diff."""
        from click.testing import CliRunner
        from legacy_engine.cli import main

        with patch("legacy_engine.ingestion.store.load_ingest_diff", return_value=diff):
            return CliRunner().invoke(main, args, catch_exceptions=False)

    def test_no_diff_shows_fallback(self, tmp_path):
        """When load_ingest_diff returns None, the command shows the 'run refresh cards' hint."""
        result = self._invoke_with_diff(["report", "new-cards"], diff=None, tmp_path=tmp_path)
        assert result.exit_code == 0
        assert "refresh cards" in result.output

    def test_with_diff_lists_new_cards(self, tmp_path):
        """When a diff exists, new-cards lists the actual new-card names."""
        diff = IngestDiff(
            new_names=("Brazen Borrower", "Delver of Secrets"),
            total_after=25000,
            scryfall_updated_at="2026-06-14T10:00:00Z",
        )
        result = self._invoke_with_diff(["report", "new-cards"], diff=diff, tmp_path=tmp_path)
        assert result.exit_code == 0
        assert "Brazen Borrower" in result.output
        assert "Delver of Secrets" in result.output
        # total_after rendered with comma
        assert "25,000" in result.output

    def test_empty_diff_no_card_names(self, tmp_path):
        """An empty diff (no new cards) shows a 'no new cards' message, not a list."""
        diff = IngestDiff(new_names=(), total_after=24000, scryfall_updated_at=None)
        result = self._invoke_with_diff(["report", "new-cards"], diff=diff, tmp_path=tmp_path)
        assert result.exit_code == 0
        assert "no new cards" in result.output.lower()

    def test_limit_truncates_output(self, tmp_path):
        """--limit truncates the card list with a trailing count message."""
        names = tuple(f"Card {i:02d}" for i in range(20))
        diff = IngestDiff(new_names=names, total_after=30000, scryfall_updated_at=None)
        result = self._invoke_with_diff(["report", "new-cards", "--limit", "5"], diff=diff, tmp_path=tmp_path)
        assert result.exit_code == 0
        assert "Card 04" in result.output   # 5th card shown (0-indexed)
        assert "Card 05" not in result.output  # 6th not shown
        assert "15 more" in result.output


# ---------------------------------------------------------------------------
# CLI integration: report speculate --new
# ---------------------------------------------------------------------------


class TestReportSpeculateNewCLI:
    """CLI smoke tests for `report speculate --new` with and without a persisted diff."""

    def test_no_diff_shows_fallback(self, tmp_path):
        """When no diff exists, speculate --new prints the 'run refresh cards' hint and exits 0."""
        db_path = _make_tiny_db(tmp_path)

        from click.testing import CliRunner
        from legacy_engine.cli import main

        with patch("legacy_engine.ingestion.store.load_ingest_diff", return_value=None):
            result = CliRunner().invoke(
                main, ["report", "speculate", "--new", "--db", str(db_path)],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        assert "refresh cards" in result.output

    def test_with_diff_uses_new_card_names(self, tmp_path):
        """With a persisted diff, speculate --new forecasts the actual new-card names."""
        db_path = _make_tiny_db(tmp_path)
        # "Brainstorm" is in the pool, so speculate won't do a network lookup.
        diff = IngestDiff(
            new_names=("Brainstorm",),
            total_after=1,
            scryfall_updated_at="2026-06-14T00:00:00Z",
        )

        from click.testing import CliRunner
        from legacy_engine.cli import main

        with patch("legacy_engine.ingestion.store.load_ingest_diff", return_value=diff):
            result = CliRunner().invoke(
                main, ["report", "speculate", "--new", "--db", str(db_path)],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        assert "Brainstorm" in result.output
        assert "PRE-DATA FORECAST" in result.output

    def test_with_empty_diff_shows_fallback(self, tmp_path):
        """An empty diff (no new cards) shows the 'run refresh cards' hint."""
        db_path = _make_tiny_db(tmp_path)
        diff = IngestDiff(new_names=(), total_after=0, scryfall_updated_at=None)

        from click.testing import CliRunner
        from legacy_engine.cli import main

        with patch("legacy_engine.ingestion.store.load_ingest_diff", return_value=diff):
            result = CliRunner().invoke(
                main, ["report", "speculate", "--new", "--db", str(db_path)],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        assert "refresh cards" in result.output
