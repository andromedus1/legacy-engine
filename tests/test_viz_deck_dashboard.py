"""Tests for viz/deck_dashboard.py — the per-deck Dashboard composer.

Covers:
- TestBuildDeckDashboard     — full build on rounds-bearing fixture DB; 5 tiles + primer;
                               attack-focused col_span order; matchup rows carry windows.
- TestPrimerSummary          — thin/no-data fixture: primer degrades, never fabricates.
- TestConsensusHtml          — two-column shading, sample_n, inclusion_pct shading.
- TestPrimerSummaryUnit      — unit tests for _primer_summary on hand-built inputs.
"""

from __future__ import annotations

import pytest

from legacy_engine.viz.deck_dashboard import _consensus_html, _primer_summary


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_meta_entry(archetype, share, tier="established", fringe=False):
    """Build a minimal meta entry dict-like object (duck-typed)."""
    class _Entry:
        pass
    e = _Entry()
    e.archetype = archetype
    e.share = share
    e.tier = tier
    e.fringe = fringe
    return e


def _make_meta(entries):
    class _Meta:
        pass
    m = _Meta()
    m.entries = entries
    m.total_decks = sum(int(e.share * 100) for e in entries)
    m.provenance = None
    m.definition = "raw"
    return m


def _make_ranking(decks, s_q_map=None, low_coverage=None):
    """Build a minimal DeckRanking for unit tests."""
    from legacy_engine.advisory.positioning import DeckRanking

    s_q_map = s_q_map or {d: 0.5 for d in decks}
    return DeckRanking(
        decks=decks,
        p_best={d: 1.0 / len(decks) for d in decks},
        s_mean={d: s_q_map.get(d, 0.5) + 0.01 for d in decks},
        s_ci={d: (s_q_map.get(d, 0.5) - 0.02, s_q_map.get(d, 0.5) + 0.05) for d in decks},
        s_quantile=s_q_map,
        quantile_level=0.05,
        data_coverage={d: 0.9 for d in decks},
        low_coverage=low_coverage or set(),
        pairwise={},
        field_source="global",
    )


def _make_subj(archetype, u_bar=0.52, data_coverage=0.8):
    class _Subj:
        pass
    s = _Subj()
    s.deck_archetype = archetype
    s.s_mean = 0.52
    s.s_ci = (0.49, 0.56)
    s.u_bar = u_bar
    s.data_coverage = data_coverage
    s.field_source = "global"
    s.n_draws = 20000
    s.imputed = frozenset()
    s.warnings = ()
    return s


# ---------------------------------------------------------------------------
# TestConsensusHtml
# ---------------------------------------------------------------------------

class TestConsensusHtml:
    def test_returns_string(self):
        from legacy_engine.generation.consensus import CardFreq
        main = [CardFreq(name="Brainstorm", inclusion_pct=0.95, modal_count=4, decks_running=19)]
        side = [CardFreq(name="Surgical Extraction", inclusion_pct=0.70, modal_count=2, decks_running=14)]
        html = _consensus_html("Control", main, side)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_card_name_in_output(self):
        from legacy_engine.generation.consensus import CardFreq
        main = [CardFreq(name="Brainstorm", inclusion_pct=0.95, modal_count=4, decks_running=19)]
        html = _consensus_html("Control", main, [])
        assert "Brainstorm" in html

    def test_two_columns_present(self):
        from legacy_engine.generation.consensus import CardFreq
        main = [CardFreq(name="Brainstorm", inclusion_pct=0.90, modal_count=4, decks_running=9)]
        side = [CardFreq(name="Force of Will", inclusion_pct=0.80, modal_count=1, decks_running=8)]
        html = _consensus_html("Control", main, side)
        # Should have two table sections
        assert "Maindeck" in html
        assert "Sideboard" in html

    def test_inclusion_pct_in_output(self):
        from legacy_engine.generation.consensus import CardFreq
        main = [CardFreq(name="Brainstorm", inclusion_pct=0.80, modal_count=4, decks_running=8)]
        html = _consensus_html("Control", main, [])
        assert "80%" in html

    def test_empty_side_shows_none(self):
        from legacy_engine.generation.consensus import CardFreq
        main = [CardFreq(name="Brainstorm", inclusion_pct=0.90, modal_count=4, decks_running=9)]
        html = _consensus_html("Control", main, [])
        assert "none" in html.lower()

    def test_lock_vs_flex_shading_different(self):
        from legacy_engine.generation.consensus import CardFreq
        main = [
            CardFreq(name="Brainstorm", inclusion_pct=0.90, modal_count=4, decks_running=9),  # lock
            CardFreq(name="Ponder", inclusion_pct=0.50, modal_count=4, decks_running=5),       # flex
        ]
        html = _consensus_html("Control", main, [])
        # Both cards present, shading should differ (different rgba values)
        assert "rgba(86,180,233,0.22)" in html  # lock alpha
        assert "rgba(86,180,233,0.08)" in html  # flex alpha

    # I1 regression: cons metadata (sample_n, window, legality_errors) must appear in tile

    def _make_cons(self, sample_n=20, since="2025-01-01", until="2025-06-01", legality_errors=None):
        """Build a minimal GeneratedDeck-like stub for _consensus_html tests."""
        from dataclasses import dataclass, field as dc_field

        @dataclass
        class _FakeCons:
            sample_n: int
            window: tuple
            legality_errors: list = dc_field(default_factory=list)

        return _FakeCons(
            sample_n=sample_n,
            window=(since, until),
            legality_errors=legality_errors or [],
        )

    def test_consensus_html_shows_sample_n(self):
        """cons.sample_n must appear in the rendered HTML."""
        from legacy_engine.generation.consensus import CardFreq
        main = [CardFreq(name="Brainstorm", inclusion_pct=0.80, modal_count=4, decks_running=16)]
        cons = self._make_cons(sample_n=42)
        html = _consensus_html("Control", main, [], cons=cons)
        assert "42" in html

    def test_consensus_html_shows_window(self):
        """cons.window (since, until) dates must appear in the rendered HTML."""
        from legacy_engine.generation.consensus import CardFreq
        main = [CardFreq(name="Brainstorm", inclusion_pct=0.80, modal_count=4, decks_running=8)]
        cons = self._make_cons(since="2025-03-15", until="2025-09-01")
        html = _consensus_html("Control", main, [], cons=cons)
        assert "2025-03-15" in html
        assert "2025-09-01" in html

    def test_consensus_html_shows_legality_errors_when_present(self):
        """legality_errors in cons must appear visibly in the rendered HTML."""
        from legacy_engine.generation.consensus import CardFreq
        main = [CardFreq(name="Brainstorm", inclusion_pct=0.80, modal_count=4, decks_running=8)]
        cons = self._make_cons(legality_errors=["maindeck has 58 cards (expected 60)"])
        html = _consensus_html("Control", main, [], cons=cons)
        assert "Legality" in html or "legality" in html.lower()
        assert "58 cards" in html

    def test_consensus_html_no_legality_section_when_empty(self):
        """When legality_errors is empty, no legality warning section should appear."""
        from legacy_engine.generation.consensus import CardFreq
        main = [CardFreq(name="Brainstorm", inclusion_pct=0.80, modal_count=4, decks_running=8)]
        cons = self._make_cons(legality_errors=[])
        html = _consensus_html("Control", main, [], cons=cons)
        assert "Legality warnings" not in html

    def test_consensus_html_without_cons_still_renders(self):
        """When cons=None (fallback path), HTML must still render correctly (no crash)."""
        from legacy_engine.generation.consensus import CardFreq
        main = [CardFreq(name="Brainstorm", inclusion_pct=0.80, modal_count=4, decks_running=8)]
        html = _consensus_html("Control", main, [], cons=None)
        assert "Brainstorm" in html
        assert "Maindeck" in html


# ---------------------------------------------------------------------------
# TestPrimerSummaryUnit — pure unit tests on _primer_summary
# ---------------------------------------------------------------------------

class TestPrimerSummaryUnit:
    def test_returns_html_string(self):
        meta = _make_meta([_make_meta_entry("Control", 0.30)])
        ranking = _make_ranking(["Control", "Combo"])
        subj = _make_subj("Control")
        rows = [{"opponent": "Combo", "p_shrunk": 0.62, "n": 50, "display": True}]
        html = _primer_summary("Control", meta, rows, ranking, subj)
        assert isinstance(html, str)
        assert "Control" in html

    def test_meta_share_mentioned(self):
        entries = [
            _make_meta_entry("Control", 0.30),
            _make_meta_entry("Combo", 0.20),
        ]
        meta = _make_meta(entries)
        ranking = _make_ranking(["Control", "Combo"])
        subj = _make_subj("Control")
        rows = []
        html = _primer_summary("Control", meta, rows, ranking, subj)
        assert "30" in html  # "30.0%" or "30%" depending on format

    def test_positioning_rank_mentioned(self):
        meta = _make_meta([_make_meta_entry("Control", 0.30)])
        ranking = _make_ranking(["Control", "Combo", "Aggro"])
        subj = _make_subj("Control")
        rows = []
        html = _primer_summary("Control", meta, rows, ranking, subj)
        assert "#1" in html  # Control is first in the ranking list

    def test_thin_data_no_matchup_data_degrades(self):
        """When all matchup rows are masked (display=False), must not fabricate rates."""
        meta = _make_meta([_make_meta_entry("Control", 0.30)])
        ranking = _make_ranking(["Control"])
        subj = _make_subj("Control", data_coverage=0.05)
        rows = [
            {"opponent": "Combo", "p_shrunk": None, "n": 5, "display": False},
            {"opponent": "Aggro", "p_shrunk": None, "n": 3, "display": False},
        ]
        html = _primer_summary("Control", meta, rows, ranking, subj)
        # Must say "insufficient" not a fabricated rate
        assert "insufficient" in html.lower()
        # Must NOT contain a fabricated explicit percentage for matchups
        assert "62%" not in html
        assert "0.62" not in html

    def test_archetype_absent_from_meta_degrades(self):
        """When archetype is not in meta entries, should say so, not crash."""
        meta = _make_meta([_make_meta_entry("OtherDeck", 0.50)])
        ranking = _make_ranking(["OtherDeck"])
        subj = _make_subj("Control", data_coverage=0.0)
        rows = []
        html = _primer_summary("Control", meta, rows, ranking, subj)
        assert "Control" in html
        assert "insufficient" in html.lower() or "absent" in html.lower()

    def test_archetype_absent_from_ranking_degrades(self):
        """When archetype not in ranking.decks, should say so."""
        meta = _make_meta([_make_meta_entry("Control", 0.30)])
        ranking = _make_ranking(["Combo", "Aggro"])  # Control not in ranking
        subj = _make_subj("Control")
        rows = []
        html = _primer_summary("Control", meta, rows, ranking, subj)
        assert "Control" in html
        # Should not fabricate a rank
        assert "ranking unavailable" in html.lower() or "absent" in html.lower()

    def test_best_worst_matchup_shown_when_established(self):
        meta = _make_meta([_make_meta_entry("Control", 0.30)])
        ranking = _make_ranking(["Control", "Combo", "Aggro"])
        subj = _make_subj("Control")
        rows = [
            {"opponent": "Combo", "p_shrunk": 0.70, "n": 50, "display": True},
            {"opponent": "Aggro", "p_shrunk": 0.45, "n": 35, "display": True},
        ]
        html = _primer_summary("Control", meta, rows, ranking, subj)
        assert "Combo" in html
        assert "Aggro" in html
        assert "70%" in html
        assert "45%" in html

    def test_no_fabrication_on_zero_data_coverage(self):
        """Zero data_coverage in subj + all masked rows → must not fabricate any S value."""
        meta = _make_meta([_make_meta_entry("Control", 0.10, tier="speculative")])
        ranking = _make_ranking(["Control"])
        # Override coverage to zero in the ranking
        from legacy_engine.advisory.positioning import DeckRanking
        r = DeckRanking(
            decks=["Control"],
            p_best={"Control": 1.0},
            s_mean={"Control": 0.5},
            s_ci={"Control": (0.4, 0.6)},
            s_quantile={"Control": 0.42},
            quantile_level=0.05,
            data_coverage={"Control": 0.0},
            low_coverage={"Control"},
            pairwise={},
            field_source="global",
        )
        subj = _make_subj("Control", data_coverage=0.0)
        rows = []
        html = _primer_summary("Control", meta, rows, r, subj)
        # Must mention low coverage — not pretend the number is reliable
        assert "low data coverage" in html.lower() or "coverage" in html.lower()


# ---------------------------------------------------------------------------
# TestBuildDeckDashboard — integration with rounds-bearing fixture DB
# ---------------------------------------------------------------------------

class TestBuildDeckDashboard:
    """Integration tests using the make_rounds_corpus fixture (n_repeats=50 for established tier)."""

    @pytest.fixture
    def con_and_facts(self, make_rounds_corpus):
        """Evolving-tier corpus: n_repeats=15 → Control vs Combo n=30 (≥30 evolving).

        We use n_repeats=15 to stay within valid January dates (1..15).
        n_repeats=50 would generate invalid dates like 2026-01-32 which break compute_trends.
        """
        con, facts = make_rounds_corpus(n_repeats=15)
        yield con, facts
        con.close()

    def test_returns_dashboard(self, con_and_facts):
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        con, _ = con_and_facts
        dash = build_deck_dashboard(con, "Control", regime="all-time", seed=42)
        from legacy_engine.viz.layout import Dashboard
        assert isinstance(dash, Dashboard)

    def test_six_tiles_with_primer(self, con_and_facts):
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        con, _ = con_and_facts
        dash = build_deck_dashboard(con, "Control", regime="all-time", seed=42)
        assert len(dash.tiles) == 6, f"expected 6 tiles, got {len(dash.tiles)}"

    def test_attack_focused_layout_order(self, con_and_facts):
        """
        Primer (html, 12) → Matchup (chart, 12) → Positioning (chart, 6) →
        Meta (chart, 6) → Trends (chart, 12) → Consensus (html, 12)
        """
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        con, _ = con_and_facts
        dash = build_deck_dashboard(con, "Control", regime="all-time", seed=42)
        expected = [
            ("html", 12),   # primer
            ("chart", 12),  # matchup spread
            ("chart", 6),   # positioning
            ("chart", 6),   # meta share
            ("chart", 12),  # trends
            ("html", 12),   # consensus
        ]
        actual = [(t.kind, t.col_span) for t in dash.tiles]
        assert actual == expected, f"layout mismatch: {actual}"

    def test_primer_tile_is_html_non_empty(self, con_and_facts):
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        con, _ = con_and_facts
        dash = build_deck_dashboard(con, "Control", regime="all-time", seed=42)
        primer = dash.tiles[0]
        assert primer.kind == "html"
        assert primer.html is not None and len(primer.html) > 50

    def test_matchup_tile_is_chart(self, con_and_facts):
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        con, _ = con_and_facts
        dash = build_deck_dashboard(con, "Control", regime="all-time", seed=42)
        matchup_tile = dash.tiles[1]
        assert matchup_tile.kind == "chart"
        assert matchup_tile.spec is not None
        assert "$schema" in matchup_tile.spec

    def test_matchup_rows_carry_window_field(self, con_and_facts):
        """Matchup row data values must include the 'window' field (adaptive cell window)."""
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        con, _ = con_and_facts
        dash = build_deck_dashboard(con, "Control", regime="all-time", seed=42)
        matchup_spec = dash.tiles[1].spec
        data_values = matchup_spec["data"]["values"]
        for row in data_values:
            assert "window" in row, f"row missing 'window': {row}"

    def test_positioning_tile_is_chart(self, con_and_facts):
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        con, _ = con_and_facts
        dash = build_deck_dashboard(con, "Control", regime="all-time", seed=42)
        pos_tile = dash.tiles[2]
        assert pos_tile.kind == "chart"
        assert pos_tile.spec is not None

    def test_consensus_tile_is_html(self, con_and_facts):
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        con, _ = con_and_facts
        dash = build_deck_dashboard(con, "Control", regime="all-time", seed=42)
        cons_tile = dash.tiles[5]
        assert cons_tile.kind == "html"
        assert cons_tile.html is not None

    def test_consensus_tile_renders_html_structure(self, make_rounds_corpus):
        """The consensus tile must render valid HTML structure (two column layout)."""
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        con, _ = make_rounds_corpus(n_repeats=50)
        try:
            dash = build_deck_dashboard(con, "Control", regime="all-time", seed=42)
        finally:
            con.close()
        cons_html = dash.tiles[5].html
        # Must contain two-column structure (Maindeck / Sideboard labels)
        assert "Maindeck" in cons_html
        assert "Sideboard" in cons_html
        # Shading description present in the template
        assert "lock" in cons_html

    def test_thin_deck_primer_degrades(self, make_rounds_corpus):
        """On a thin-data corpus (n_repeats=1), primer must mention insufficient data."""
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        con, _ = make_rounds_corpus(n_repeats=1)
        try:
            dash = build_deck_dashboard(con, "Control", regime="all-time", seed=42)
        finally:
            con.close()
        primer_html = dash.tiles[0].html
        # With n=2 matches, matchup data is speculative → primer should degrade
        # (no established cells → "insufficient matchup data" or similar)
        assert "insufficient" in primer_html.lower() or "masked" in primer_html.lower() or "withheld" in primer_html.lower()

    def test_all_chart_specs_have_schema(self, con_and_facts):
        """Every chart tile must have a $schema key (non-empty Vega-Lite spec)."""
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        from legacy_engine.config import VL_SCHEMA_URL
        con, _ = con_and_facts
        dash = build_deck_dashboard(con, "Control", regime="all-time", seed=42)
        for tile in dash.tiles:
            if tile.kind == "chart":
                assert tile.spec is not None
                assert "$schema" in tile.spec

    def test_unknown_archetype_does_not_crash(self, con_and_facts):
        """An archetype with no data in the corpus should produce a degraded dashboard, not crash."""
        from legacy_engine.viz.deck_dashboard import build_deck_dashboard
        con, _ = con_and_facts
        # "Unknown Archetype" is not in the fixture corpus
        dash = build_deck_dashboard(con, "Unknown Archetype", regime="all-time", seed=42)
        # Should still return a Dashboard with the right number of tiles
        assert len(dash.tiles) == 6
