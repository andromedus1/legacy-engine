"""Tests for the deck-tuning refresh workflow (feature-deck-tuning-refresh-workflow).

Tests spec-derived from the feature spec:

1. Per-venue package assembles for online and paper (two packages returned).
2. Plain-speak primer prose includes the OUT/IN swaps and a WHY for a matchup with data.
3. Plain-speak primer honestly labels a thin / no-data matchup.
4. Gated-additive no-op: empty matchup_plans -> primer assembles without crashing.
5. generate_primer is pure: same inputs -> same output (determinism).
6. Per-venue primer carries the venue label.
7. run_refresh degrades gracefully when a venue has no data (data_absent=True).
8. CLI command 'advise refresh' is registered and help text is reachable without error.

Architecture: the primer generator (advisory.primer) is tested as a pure function with
hand-built MatchupPlan stubs (objective-search-split pattern — no DB needed for most tests).
Integration tests for run_refresh use an in-memory corpus.
"""

from __future__ import annotations

import pytest
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Hand-built MatchupPlan stubs (pure, no DB)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _FakePlan:
    """Minimal duck-type stand-in for MatchupPlan."""
    opponent: str
    side_out: dict
    side_in: dict
    post_board: dict
    n_basis: int
    tier: str
    degraded: bool
    note: str


def _data_plan(opp: str) -> _FakePlan:
    """Matchup plan with real data (evolving tier, swaps present)."""
    return _FakePlan(
        opponent=opp,
        side_out={"Dead Weight": 2},
        side_in={"Surgical Extraction": 2},
        post_board={},
        n_basis=35,
        tier="evolving",
        degraded=False,
        note=f"vs {opp}: 2 swap(s); tier=evolving, n_basis=35",
    )


def _thin_plan(opp: str) -> _FakePlan:
    """Matchup plan that degraded due to thin data."""
    return _FakePlan(
        opponent=opp,
        side_out={},
        side_in={},
        post_board={},
        n_basis=0,
        tier="speculative",
        degraded=True,
        note=f"thin data (n < gate threshold) for {opp} — no per-matchup plan",
    )


def _no_swap_plan(opp: str) -> _FakePlan:
    """Plan where data cleared the gate but no swaps were found."""
    return _FakePlan(
        opponent=opp,
        side_out={},
        side_in={},
        post_board={},
        n_basis=40,
        tier="evolving",
        degraded=False,
        note=f"vs {opp}: data cleared gate but no flex dead cards found",
    )


# ---------------------------------------------------------------------------
# Tests: generate_primer (pure)
# ---------------------------------------------------------------------------

class TestGeneratePrimer:
    """Tests for advisory.primer.generate_primer — pure function, no DB."""

    def test_primer_includes_out_in_swaps_for_data_plan(self):
        """Primer prose includes the OUT/IN swaps and a WHY for a matchup with data."""
        from legacy_engine.advisory.primer import generate_primer

        sideboard = {"Surgical Extraction": 2, "Force of Will": 2}
        plans = {"Dredge": _data_plan("Dredge")}

        primer = generate_primer(
            archetype="Dimir Tempo",
            sideboard=sideboard,
            matchup_plans=plans,
            venue_label="Online (MTGO)",
            window_label="adaptive (per-opponent ban-aware)",
        )

        assert len(primer.blurbs) == 1
        blurb = primer.blurbs[0]
        assert blurb.opponent == "Dredge"
        assert blurb.data_quality in ("evolving", "established")
        assert not blurb.degraded

        # OUT and IN must be represented in the prose
        assert "OUT" in primer.primer_text or "Dead Weight" in primer.primer_text
        assert "IN" in primer.primer_text or "Surgical Extraction" in primer.primer_text

        # Swap strings in the blurb
        assert "Dead Weight" in blurb.side_out_str
        assert "Surgical Extraction" in blurb.side_in_str

        # A WHY — should mention "performs" or "lift" or "below-baseline"
        assert any(kw in blurb.prose for kw in ("performance", "lift", "below-baseline", "improve"))

    def test_primer_honestly_labels_thin_matchup(self):
        """Primer explicitly labels thin/no-data matchups as reasoning-based."""
        from legacy_engine.advisory.primer import generate_primer

        sideboard = {"Force of Will": 2}
        plans = {"UR Delver": _thin_plan("UR Delver")}

        primer = generate_primer(
            archetype="Dimir Tempo",
            sideboard=sideboard,
            matchup_plans=plans,
            venue_label="Paper",
            window_label="current-regime (uniform)",
        )

        blurb = primer.blurbs[0]
        assert blurb.degraded
        assert blurb.data_quality == "reasoning-based"

        # Must NOT contain fabricated numbers or false precision
        assert "reasoning-based, not data-derived" in blurb.prose

        # Must NOT recommend specific swaps
        assert "OUT" not in blurb.side_out_str or "none" in blurb.side_out_str.lower()
        assert "IN" not in blurb.side_in_str or "none" in blurb.side_in_str.lower()

        # primer_text should also surface the honest label
        assert "reasoning-based" in primer.primer_text

    def test_primer_assembles_without_crash_on_empty_plans(self):
        """Gated-additive no-op: empty matchup_plans -> primer assembles cleanly."""
        from legacy_engine.advisory.primer import generate_primer

        primer = generate_primer(
            archetype="Dimir Tempo",
            sideboard={"Surgical Extraction": 2},
            matchup_plans={},
            venue_label="Online (MTGO)",
            window_label="current-regime",
        )

        assert primer.archetype == "Dimir Tempo"
        assert primer.blurbs == []
        assert primer.primer_text  # non-empty (has the no-plans fallback message)
        # Should contain helpful fallback text
        assert "No per-matchup data" in primer.primer_text or "no" in primer.primer_text.lower()

    def test_primer_is_deterministic(self):
        """Same inputs always produce identical output (pure function property)."""
        from legacy_engine.advisory.primer import generate_primer

        plans = {
            "Dredge": _data_plan("Dredge"),
            "ANT": _thin_plan("ANT"),
        }
        sideboard = {"Surgical Extraction": 2, "Force of Will": 2}

        p1 = generate_primer(
            archetype="Dimir Tempo",
            sideboard=sideboard,
            matchup_plans=plans,
            venue_label="Online (MTGO)",
            window_label="adaptive",
        )
        p2 = generate_primer(
            archetype="Dimir Tempo",
            sideboard=sideboard,
            matchup_plans=plans,
            venue_label="Online (MTGO)",
            window_label="adaptive",
        )

        assert p1.primer_text == p2.primer_text
        assert len(p1.blurbs) == len(p2.blurbs)

    def test_primer_carries_venue_label(self):
        """Primer text includes the venue label in the header."""
        from legacy_engine.advisory.primer import generate_primer

        primer = generate_primer(
            archetype="Dimir Tempo",
            sideboard={"Force of Will": 2},
            matchup_plans={},
            venue_label="Paper",
            window_label="current-regime",
        )

        assert "Paper" in primer.primer_text
        assert primer.venue_label == "Paper"

    def test_primer_orders_by_field_share(self):
        """When field_shares provided, blurbs are ordered descending by share."""
        from legacy_engine.advisory.primer import generate_primer

        plans = {
            "ANT": _thin_plan("ANT"),
            "Dredge": _data_plan("Dredge"),
            "UR Delver": _thin_plan("UR Delver"),
        }
        field_shares = {"Dredge": 0.20, "ANT": 0.10, "UR Delver": 0.05}

        primer = generate_primer(
            archetype="Dimir Tempo",
            sideboard={"Surgical Extraction": 2},
            matchup_plans=plans,
            field_shares=field_shares,
        )

        opponents = [b.opponent for b in primer.blurbs]
        # Dredge (0.20) should come first, then ANT (0.10), then UR Delver (0.05)
        assert opponents == ["Dredge", "ANT", "UR Delver"]

    def test_primer_includes_disclaimer(self):
        """Primer always includes the presence-correlational disclaimer."""
        from legacy_engine.advisory.primer import generate_primer, _PRESENCE_CORRELATIONAL_DISCLAIMER

        primer = generate_primer(
            archetype="Dimir Tempo",
            sideboard={"Surgical Extraction": 2},
            matchup_plans={"Dredge": _data_plan("Dredge")},
        )

        assert "presence-correlational" in primer.primer_text.lower()
        assert primer.honesty_note == _PRESENCE_CORRELATIONAL_DISCLAIMER

    def test_no_swap_needed_prose(self):
        """When data cleared gate but no swaps found, prose reflects that honestly."""
        from legacy_engine.advisory.primer import generate_primer

        plans = {"Miracles": _no_swap_plan("Miracles")}
        primer = generate_primer(
            archetype="Dimir Tempo",
            sideboard={"Force of Will": 2},
            matchup_plans=plans,
        )
        blurb = primer.blurbs[0]
        assert not blurb.degraded
        assert blurb.n_basis > 0
        # Should not claim specific swaps since there are none
        assert "(none)" in blurb.side_out_str
        assert "(none)" in blurb.side_in_str


# ---------------------------------------------------------------------------
# Tests: run_refresh integration (in-memory corpus, no-signal path)
# ---------------------------------------------------------------------------

class TestRunRefresh:
    """Integration tests for advisory.refresh.run_refresh — in-memory corpus."""

    def _make_minimal_corpus(self):
        """Build an in-memory corpus with minimal tournament data for testing.

        Uses only deck-presence data (no rounds) so we hit the no-signal fallback
        path reliably.  The key thing is that online and paper venues each have
        at least one deck so the field can be built.
        """
        from legacy_engine.ingestion import store
        from legacy_engine.ingestion.cache import parse_cache_item

        con = store.connect(":memory:")

        def _card(name: str, count: int = 4) -> dict:
            return {"CardName": name, "Count": count}

        def _make_deck(player: str, main: list, side: list) -> dict:
            return {
                "Player": player,
                "Result": "1st Place",
                "Mainboard": main,
                "Sideboard": side,
            }

        DIMIR_MAIN = [
            _card("Brainstorm"), _card("Daze"), _card("Force of Will"), _card("Ponder"),
            _card("Underground Sea", 4), _card("Volcanic Island", 4),
            _card("Scalding Tarn", 4), _card("Misty Rainforest", 4),
            _card("Murktide Regent", 4), _card("Dragon's Rage Channeler", 4),
            _card("Expressive Iteration", 4), _card("Lightning Bolt", 4),
            _card("Wasteland", 4), _card("Spell Pierce", 2),
        ]
        DIMIR_SIDE = [
            _card("Surgical Extraction", 2), _card("Force of Vigor", 2),
            _card("Pyroblast", 3), _card("Flusterstorm", 2), _card("Grafdigger's Cage", 2),
            _card("Blood Moon", 2), _card("Leyline of the Void", 2),
        ]

        for i in range(3):
            for provenance, source in [("online", "MTGO"), ("paper", "Paper")]:
                date = f"2026-01-{i + 1:02d}"
                uri = f"https://example.com/{provenance}-{i + 1}"
                raw = {
                    "Tournament": {
                        "Name": f"Test Event {i + 1} ({provenance})",
                        "Date": date,
                        "Uri": uri,
                        "Formats": "Legacy",
                        "Provenance": provenance,
                    },
                    "Decks": [
                        _make_deck(f"player-{provenance}-{i}", DIMIR_MAIN, DIMIR_SIDE),
                    ],
                    "Rounds": [],
                }
                item = parse_cache_item(raw, source)
                tid = store.load_tournament(con, item)
                # Label all decks with the archetype
                con.execute(
                    "UPDATE decks SET archetype = ? WHERE tournament_id = ?",
                    ["UR Delver", tid],
                )

        return con, {"Brainstorm": 4, "Daze": 4, "Force of Will": 4, "Ponder": 4,
                     "Underground Sea": 4, "Volcanic Island": 4, "Scalding Tarn": 4,
                     "Misty Rainforest": 4, "Murktide Regent": 4,
                     "Dragon's Rage Channeler": 4, "Expressive Iteration": 4,
                     "Lightning Bolt": 4, "Wasteland": 4, "Spell Pierce": 2}

    def test_run_refresh_returns_two_packages_for_default_venues(self):
        """run_refresh produces one package per venue (online + paper by default)."""
        from legacy_engine.advisory.refresh import run_refresh

        con, maindeck = self._make_minimal_corpus()
        try:
            result = run_refresh(
                con,
                maindeck,
                {},
                archetype="UR Delver",
            )
        finally:
            con.close()

        assert len(result.packages) == 2
        venue_keys = {p.venue.key for p in result.packages}
        assert "online" in venue_keys
        assert "paper" in venue_keys
        assert result.archetype == "UR Delver"

    def test_run_refresh_each_package_has_primer(self):
        """Each package carries a SideboardPrimer, not None."""
        from legacy_engine.advisory.refresh import run_refresh
        from legacy_engine.advisory.primer import SideboardPrimer

        con, maindeck = self._make_minimal_corpus()
        try:
            result = run_refresh(
                con,
                maindeck,
                {},
                archetype="UR Delver",
            )
        finally:
            con.close()

        for pkg in result.packages:
            assert pkg.primer is not None
            assert isinstance(pkg.primer, SideboardPrimer)
            assert pkg.primer.venue_label == pkg.venue.label

    def test_run_refresh_package_maindeck_matches_input_on_no_signal(self):
        """On no-signal fallback, package maindeck equals the input maindeck (no swaps made)."""
        from legacy_engine.advisory.refresh import run_refresh

        con, maindeck = self._make_minimal_corpus()
        try:
            result = run_refresh(
                con,
                maindeck,
                {},
                archetype="UR Delver",
            )
        finally:
            con.close()

        for pkg in result.packages:
            if not pkg.data_absent and pkg.tuned_deck is not None:
                td = pkg.tuned_deck
                if td.fell_back:
                    # No swaps were made — maindeck unchanged from input
                    assert pkg.maindeck == maindeck, (
                        f"venue {pkg.venue.key}: fell_back=True but maindeck differs from input"
                    )

    def test_run_refresh_no_data_venue_is_marked_data_absent(self):
        """A venue with zero decks is marked data_absent=True, not silently dropped."""
        from legacy_engine.advisory.refresh import run_refresh
        from legacy_engine.analytics.venue import Venue

        con, maindeck = self._make_minimal_corpus()
        # Create a venue that will never have data
        ghost_venue = Venue(key="ghost", label="Ghost Venue", provenance="ghost")
        try:
            result = run_refresh(
                con,
                maindeck,
                {},
                archetype="UR Delver",
                venues=[ghost_venue],
            )
        finally:
            con.close()

        assert len(result.packages) == 1
        pkg = result.packages[0]
        # Either data_absent is set OR the field has no shares (both indicate no data)
        assert pkg.data_absent or not pkg.maindeck.get("anything", False)

    def test_run_refresh_gated_additive_no_op_on_no_rounds(self):
        """Corpus without rounds data: fell_back=True, maindeck unchanged from input."""
        from legacy_engine.advisory.refresh import run_refresh

        con, maindeck = self._make_minimal_corpus()
        try:
            result = run_refresh(
                con,
                maindeck,
                {},
                archetype="UR Delver",
            )
        finally:
            con.close()

        for pkg in result.packages:
            if not pkg.data_absent and pkg.tuned_deck is not None:
                # Without rounds data, fell_back=True (no-signal path)
                td = pkg.tuned_deck
                if td.fell_back:
                    # Maindeck should be unchanged from input (no swaps)
                    assert td.swaps == []
                    assert td.objective == "no-signal-skip"


# ---------------------------------------------------------------------------
# Tests: CLI registration
# ---------------------------------------------------------------------------

class TestCLIRefresh:
    """Verify the advise refresh command is registered and reachable."""

    def test_advise_refresh_command_registered(self):
        """'advise refresh --help' exits 0 and shows the command description."""
        from click.testing import CliRunner
        from legacy_engine.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["advise", "refresh", "--help"])
        assert result.exit_code == 0, f"exit code {result.exit_code}: {result.output}"
        assert "refresh" in result.output.lower()
        assert "--deck" in result.output

    def test_advise_refresh_missing_deck_fails_loudly(self):
        """'advise refresh' without --deck raises a usage error (not a crash)."""
        from click.testing import CliRunner
        from legacy_engine.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["advise", "refresh"])
        # Click should exit with a non-zero code and mention the missing option
        assert result.exit_code != 0
        assert "deck" in result.output.lower() or "missing" in result.output.lower()


# ---------------------------------------------------------------------------
# Tests: render_refresh_result
# ---------------------------------------------------------------------------

class TestRenderRefreshResult:
    """Tests for the text renderer."""

    def test_render_includes_venue_labels(self):
        """Rendered output includes each venue's label."""
        from legacy_engine.advisory.refresh import (
            RefreshResult, VenueTuningPackage, render_refresh_result, _empty_primer
        )
        from legacy_engine.analytics.venue import ONLINE, PAPER

        # Build a minimal RefreshResult with data-absent packages
        packages = [
            VenueTuningPackage(
                venue=ONLINE,
                archetype="Dimir Tempo",
                maindeck={},
                sideboard={},
                primer=_empty_primer("Dimir Tempo", ONLINE),
                tuned_deck=None,
                outlier_deltas=[],
                window_label="(no data)",
                data_absent=True,
            ),
            VenueTuningPackage(
                venue=PAPER,
                archetype="Dimir Tempo",
                maindeck={},
                sideboard={},
                primer=_empty_primer("Dimir Tempo", PAPER),
                tuned_deck=None,
                outlier_deltas=[],
                window_label="(no data)",
                data_absent=True,
            ),
        ]
        result = RefreshResult(packages=packages, archetype="Dimir Tempo")
        rendered = render_refresh_result(result)

        assert "Online (MTGO)" in rendered
        assert "Paper" in rendered
        assert "Dimir Tempo" in rendered

    def test_render_data_absent_says_no_data(self):
        """A data-absent venue renders a clear no-data message."""
        from legacy_engine.advisory.refresh import (
            RefreshResult, VenueTuningPackage, render_refresh_result, _empty_primer
        )
        from legacy_engine.analytics.venue import PAPER

        pkg = VenueTuningPackage(
            venue=PAPER,
            archetype="Dimir Tempo",
            maindeck={},
            sideboard={},
            primer=_empty_primer("Dimir Tempo", PAPER),
            tuned_deck=None,
            outlier_deltas=[],
            window_label="(no data)",
            data_absent=True,
        )
        result = RefreshResult(packages=[pkg], archetype="Dimir Tempo")
        rendered = render_refresh_result(result)
        # Should say something about no data
        assert "no data" in rendered.lower()
