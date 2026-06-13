"""Tests for analytics/venue.py — Units 1 & 2 of feature-three-venue-meta-frame.

Pure-function tests for ``venue_divergence`` (Unit 2) and ``compute_venue_metashare``
(Unit 1) follow the objective-search-split pattern: Unit 2 is tested with hand-built
``VenueMetaShare`` inputs (no DB), Unit 1 with an in-memory DuckDB corpus.

House style: module-level raw dicts + ``parse_cache_item`` + ``store.load_tournament``
into ``:memory:``; labels pinned via direct SQL UPDATE; ``TestX`` classes; deterministic.
"""

from __future__ import annotations

import pytest

from legacy_engine.analytics.venue import (
    ONLINE,
    PAPER,
    DEFAULT_VENUES,
    Venue,
    VenueMetaShare,
    VenueDivergence,
    ArchetypeDivergence,
    resolve_venues,
    compute_venue_metashare,
    venue_divergence,
)
from legacy_engine.analytics.metashare import MetaShareEntry, MetaShareReport
from legacy_engine.confidence import tier_for_sample


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entry(archetype: str, share: float, n: int) -> MetaShareEntry:
    return MetaShareEntry(
        archetype=archetype,
        share=share,
        n=n,
        tier=tier_for_sample(n),
        fringe=share < 0.02,
    )


def _make_report(
    entries: list[MetaShareEntry],
    definition: str = "raw",
    provenance: str | None = None,
    total_decks: int = 100,
) -> MetaShareReport:
    return MetaShareReport(
        definition=definition,
        provenance=provenance,
        entries=entries,
        total_decks=total_decks,
        unlabeled=0,
        min_share=0.02,
    )


def _make_vms(venue: Venue, entries_or_none) -> VenueMetaShare:
    if entries_or_none is None:
        return VenueMetaShare(venue=venue, report=None)
    return VenueMetaShare(
        venue=venue,
        report=_make_report(entries_or_none, provenance=venue.provenance),
    )


# ---------------------------------------------------------------------------
# Test fixtures: provenance-split in-memory corpus
# ---------------------------------------------------------------------------

_ONLINE_TOURNAMENT = {
    "Tournament": {
        "Name": "MTGO Legacy Challenge 32",
        "Date": "2026-06-01",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-32-2026-06-01",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "alice",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Urza's Tower"}],
            "Sideboard": [],
        },
        {
            "Player": "bob",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Urza's Mine"}],
            "Sideboard": [],
        },
        {
            "Player": "carol",
            "Result": "3rd Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "dave",
            "Result": "4th Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "eve",
            "Result": "5th Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
        {
            "Player": "frank",
            "Result": "6th Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
        {
            "Player": "grace",
            "Result": "7th Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
        {
            "Player": "henry",
            "Result": "8th Place",
            "Mainboard": [{"Count": 4, "CardName": "Dark Ritual"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [],
}

_PAPER_TOURNAMENT = {
    "Tournament": {
        "Name": "Paper Legacy Open",
        "Date": "2026-06-02",
        "Uri": "https://melee.gg/Tournament/View/99999",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "ivan",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "judy",
            "Result": "2nd Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        },
        {
            "Player": "kurt",
            "Result": "3rd Place",
            "Mainboard": [{"Count": 4, "CardName": "Force of Will"}],
            "Sideboard": [],
        },
    ],
    "Rounds": [],
    "Standings": [],
}


def _build_split_corpus():
    """Build an in-memory DuckDB with both online and paper tournaments."""
    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.cache import parse_cache_item

    con = store.connect(":memory:")

    # Online tournament: alice=Tron, bob=Tron, carol/dave=Control, eve/frank/grace/henry=Combo
    tid_online = store.load_tournament(con, parse_cache_item(_ONLINE_TOURNAMENT, "MTGO"))
    con.execute(
        "UPDATE decks SET archetype = 'Tron' WHERE tournament_id = ? AND player IN ('alice', 'bob')",
        [tid_online],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ? AND player IN ('carol', 'dave')",
        [tid_online],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Combo' WHERE tournament_id = ? AND player IN ('eve', 'frank', 'grace', 'henry')",
        [tid_online],
    )

    # Paper tournament: ivan/judy=Control, kurt=Delver
    tid_paper = store.load_tournament(con, parse_cache_item(_PAPER_TOURNAMENT, "Melee"))
    con.execute(
        "UPDATE decks SET archetype = 'Control' WHERE tournament_id = ? AND player IN ('ivan', 'judy')",
        [tid_paper],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'kurt'",
        [tid_paper],
    )

    return con


# ---------------------------------------------------------------------------
# Tests: resolve_venues
# ---------------------------------------------------------------------------


class TestResolveVenues:
    """Tests for resolve_venues."""

    def test_default_returns_online_and_paper(self):
        # resolve_venues with None defaults to DEFAULT_VENUES — no DB needed for
        # this logic path (the con parameter is accepted for future use only).
        con = None  # type: ignore[assignment]
        result = resolve_venues(con, None)
        assert result == list(DEFAULT_VENUES)
        assert len(result) == 2
        assert result[0].key == "online"
        assert result[1].key == "paper"

    def test_explicit_keys_returned_in_order(self):
        result = resolve_venues(None, ["paper", "online"])  # type: ignore[arg-type]
        assert result[0].key == "paper"
        assert result[1].key == "online"

    def test_unknown_key_raises_value_error_listing_valid(self):
        with pytest.raises(ValueError) as exc_info:
            resolve_venues(None, ["online", "local:boulder"])  # type: ignore[arg-type]
        msg = str(exc_info.value)
        assert "local:boulder" in msg
        assert "online" in msg
        assert "paper" in msg

    def test_empty_list_returns_empty(self):
        result = resolve_venues(None, [])  # type: ignore[arg-type]
        assert result == []


# ---------------------------------------------------------------------------
# Tests: venue_divergence (Unit 2, pure / no DB)
# ---------------------------------------------------------------------------


class TestVenueDivergence:
    """Tests for venue_divergence over hand-built inputs (objective-search-split)."""

    def test_basic_spread_and_sort(self):
        """Spread is computed and rows sorted descending."""
        online_entries = [
            _make_entry("Tron", 0.40, 40),
            _make_entry("Control", 0.60, 60),
        ]
        paper_entries = [
            _make_entry("Tron", 0.10, 10),
            _make_entry("Control", 0.90, 90),
        ]
        vms = [
            _make_vms(ONLINE, online_entries),
            _make_vms(PAPER, paper_entries),
        ]
        div = venue_divergence(vms)
        assert isinstance(div, VenueDivergence)
        assert len(div.rows) == 2
        # Tron spread = 0.40 - 0.10 = 0.30; Control spread = 0.90 - 0.60 = 0.30
        # equal spreads → order stable; both present
        archetypes = {r.archetype for r in div.rows}
        assert archetypes == {"Tron", "Control"}
        # Verify spreads are correct
        tron_row = next(r for r in div.rows if r.archetype == "Tron")
        assert abs(tron_row.spread - 0.30) < 1e-9

    def test_archetype_present_in_one_venue_only(self):
        """Archetype in only one venue → share 0.0 on the other, spread = its share."""
        online_entries = [
            _make_entry("OnlineOnly", 0.20, 20),
            _make_entry("Both", 0.80, 80),
        ]
        paper_entries = [
            _make_entry("Both", 0.80, 80),
            # OnlineOnly not present in paper
        ]
        vms = [
            _make_vms(ONLINE, online_entries),
            _make_vms(PAPER, paper_entries),
        ]
        div = venue_divergence(vms)
        online_only_row = next((r for r in div.rows if r.archetype == "OnlineOnly"), None)
        assert online_only_row is not None
        assert online_only_row.shares["online"] == pytest.approx(0.20)
        assert online_only_row.shares["paper"] == pytest.approx(0.0)
        assert online_only_row.spread == pytest.approx(0.20)
        assert online_only_row.max_venue == "online"
        assert online_only_row.min_venue == "paper"

    def test_high_spread_backed_by_speculative_tier_annotated_in_notes(self):
        """A high-spread row with speculative tier on the max side → note emitted."""
        # n=5 → speculative tier
        online_entries = [
            _make_entry("Tron", 0.50, 5),  # speculative (n=5 < 30)
        ]
        paper_entries = [
            _make_entry("Tron", 0.01, 100),  # established on paper
        ]
        vms = [
            _make_vms(ONLINE, online_entries),
            _make_vms(PAPER, paper_entries),
        ]
        div = venue_divergence(vms)
        # There should be a note about the speculative tier
        assert any("speculative" in note or "Tron" in note for note in div.notes)

    def test_empty_venue_report_emits_note_not_crash(self):
        """A None-report venue (zero decks) emits a note and does not crash."""
        online_entries = [
            _make_entry("Control", 1.0, 50),
        ]
        vms = [
            _make_vms(ONLINE, online_entries),
            _make_vms(PAPER, None),  # no paper data
        ]
        div = venue_divergence(vms)
        # Should not crash; should emit a note about paper having 0 decks
        assert any("0 decks" in note or "paper" in note.lower() for note in div.notes)
        # Control row should still be present with paper share = 0.0
        assert len(div.rows) >= 1
        control_row = next((r for r in div.rows if r.archetype == "Control"), None)
        assert control_row is not None
        assert control_row.shares["paper"] == pytest.approx(0.0)

    def test_min_spread_filters_below_threshold(self):
        """Rows below min_spread are excluded from results."""
        online_entries = [
            _make_entry("Tron", 0.50, 50),  # spread = 0.30 vs paper
            _make_entry("Control", 0.50, 50),  # spread near 0 vs paper
        ]
        paper_entries = [
            _make_entry("Tron", 0.20, 20),
            _make_entry("Control", 0.80, 80),  # same-ish as online → low spread
        ]
        vms = [
            _make_vms(ONLINE, online_entries),
            _make_vms(PAPER, paper_entries),
        ]
        # Filter with min_spread=0.25 → only Tron (spread=0.30) passes
        div = venue_divergence(vms, min_spread=0.25)
        assert all(r.spread >= 0.25 for r in div.rows)

    def test_2026_06_13_regression_tron_online_vs_paper(self):
        """Regression fixture from 2026-06-13: online Tron 12.9% vs paper Tron 2.2% → spread ~0.107.

        Evidence captured during the session that motivated this feature.
        online: Tron at 12.9% (established tier, n=129 assumed)
        paper: Tron at 2.2% (speculative/evolving tier, n=22)
        Expected: spread ≈ 0.107, max_venue = 'online'
        """
        online_entries = [
            _make_entry("Tron", 0.129, 129),
        ]
        paper_entries = [
            _make_entry("Tron", 0.022, 22),
        ]
        vms = [
            _make_vms(ONLINE, online_entries),
            _make_vms(PAPER, paper_entries),
        ]
        div = venue_divergence(vms)
        assert len(div.rows) == 1
        tron_row = div.rows[0]
        assert tron_row.archetype == "Tron"
        assert abs(tron_row.spread - (0.129 - 0.022)) < 1e-6, f"Expected spread ~0.107, got {tron_row.spread}"
        assert tron_row.max_venue == "online"
        assert tron_row.min_venue == "paper"
        assert tron_row.shares["online"] == pytest.approx(0.129)
        assert tron_row.shares["paper"] == pytest.approx(0.022)

    def test_both_venues_empty_returns_empty_rows(self):
        """Both venues empty → rows=[], notes about empty corpus."""
        vms = [
            _make_vms(ONLINE, None),
            _make_vms(PAPER, None),
        ]
        div = venue_divergence(vms)
        assert div.rows == []
        assert any("no archetypes" in note for note in div.notes)

    def test_rows_sorted_desc_by_spread(self):
        """Rows are always sorted descending by spread."""
        online_entries = [
            _make_entry("A", 0.10, 10),
            _make_entry("B", 0.50, 50),
            _make_entry("C", 0.40, 40),
        ]
        paper_entries = [
            _make_entry("A", 0.05, 5),   # spread=0.05
            _make_entry("B", 0.10, 10),  # spread=0.40
            _make_entry("C", 0.35, 35),  # spread=0.05
        ]
        vms = [
            _make_vms(ONLINE, online_entries),
            _make_vms(PAPER, paper_entries),
        ]
        div = venue_divergence(vms)
        spreads = [r.spread for r in div.rows]
        assert spreads == sorted(spreads, reverse=True)


# ---------------------------------------------------------------------------
# Tests: compute_venue_metashare (Unit 1, with in-memory DB)
# ---------------------------------------------------------------------------


class TestComputeVenueMetashare:
    """Tests for compute_venue_metashare over a provenance-split in-memory corpus."""

    @pytest.fixture
    def split_corpus(self):
        con = _build_split_corpus()
        yield con
        con.close()

    def test_returns_one_result_per_venue(self, split_corpus):
        venues = [ONLINE, PAPER]
        results = compute_venue_metashare(split_corpus, venues, definition="raw", min_share=0.0)
        assert len(results) == 2
        assert results[0].venue == ONLINE
        assert results[1].venue == PAPER

    def test_online_report_has_correct_deck_count(self, split_corpus):
        """Online corpus has 8 decks (alice through henry)."""
        results = compute_venue_metashare(split_corpus, [ONLINE], definition="raw", min_share=0.0)
        assert results[0].report is not None
        assert results[0].report.total_decks == 8

    def test_paper_report_has_correct_deck_count(self, split_corpus):
        """Paper corpus has 3 decks (ivan, judy, kurt)."""
        results = compute_venue_metashare(split_corpus, [PAPER], definition="raw", min_share=0.0)
        assert results[0].report is not None
        assert results[0].report.total_decks == 3

    def test_empty_venue_returns_report_none(self, split_corpus):
        """A venue key with no matching decks → report=None."""
        no_data_venue = Venue(key="online", label="Online (MTGO)", provenance="nonexistent_prov")
        results = compute_venue_metashare(split_corpus, [no_data_venue], definition="raw", min_share=0.0)
        assert results[0].report is None

    def test_tron_higher_in_online(self, split_corpus):
        """Tron is 2/8=25% online and 0/3=0% paper."""
        results = compute_venue_metashare(split_corpus, [ONLINE, PAPER], definition="raw", min_share=0.0)
        online_result = results[0]
        paper_result = results[1]

        assert online_result.report is not None
        online_shares = {e.archetype: e.share for e in online_result.report.entries}
        assert "Tron" in online_shares
        assert online_shares["Tron"] == pytest.approx(2 / 8)

        assert paper_result.report is not None
        paper_shares = {e.archetype: e.share for e in paper_result.report.entries}
        assert "Tron" not in paper_shares  # 0 decks → not in paper report

    def test_reports_use_group_other_false(self, split_corpus):
        """compute_venue_metashare uses group_other=False so all archetypes explicit."""
        results = compute_venue_metashare(split_corpus, [ONLINE], definition="raw", min_share=0.0)
        online_report = results[0].report
        assert online_report is not None
        # With group_other=False, "Other" should not appear (all archetypes explicit)
        archetype_names = [e.archetype for e in online_report.entries]
        assert "Other" not in archetype_names

    def test_divergence_from_computed_reports(self, split_corpus):
        """venue_divergence over compute_venue_metashare output runs without error."""
        results = compute_venue_metashare(
            split_corpus, [ONLINE, PAPER], definition="raw", min_share=0.0
        )
        div = venue_divergence(results)
        assert isinstance(div, VenueDivergence)
        # Tron should appear as a high-spread archetype (25% online, 0% paper)
        tron_rows = [r for r in div.rows if r.archetype == "Tron"]
        assert len(tron_rows) == 1
        assert tron_rows[0].max_venue == "online"
        assert tron_rows[0].spread == pytest.approx(2 / 8)
