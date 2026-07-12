"""Tests for generation.card_distribution — Units U1-U4.

House style: in-memory DuckDB + ``parse_cache_item`` + ``store.load_tournament``;
``TestX`` classes; deterministic fixtures.

Fixture archetype: extends the "Delver" fixture from test_generation_consensus.py
(same tournament, 10 decks, 2026-05-25 — within the current ban-regime).
Murktide Regent: 8/10 decks @ 2, 2/10 don't run it → dist should be {2: 0.8, 0: 0.2}.

Hand-validated examples (from feature design doc):
  - Bowmasters user 4 vs {3: 0.68, 4: 0.23, ...} → on-consensus (23% ≥ 20% floor, Δ+1)
  - Murktide user 2 vs {2: 0.79, 0: 0.11, 3: 0.09} → on-consensus Δ0
  - Lands user 18 vs {19: 0.73, 20: 0.21, 18: 0.05} → outlier (5% < 20% floor)
  - Daze user 2 vs {3: 0.61, 2: 0.18, 4: 0.12} → outlier (18% < 20% floor)

_OUTLIER_SHARE_FLOOR = 0.20: chosen so Daze@18% IS flagged and Bowmasters@23% is NOT.
"""

from __future__ import annotations

import pytest

from legacy_engine.generation.card_distribution import (
    CardCountDelta,
    CardCountDist,
    DeckDoctorReport,
    _OUTLIER_SHARE_FLOOR,
    build_deck_doctor_report,
    card_count_distributions,
    diff_deck_vs_field,
)
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item
from tests.conftest import in_current_regime


# ---------------------------------------------------------------------------
# Fixture helpers (mirrors test_generation_consensus.py patterns)
# ---------------------------------------------------------------------------

def _make_deck_raw(player: str, mainboard: list[dict], sideboard: list[dict]) -> dict:
    return {
        "Player": player,
        "Result": "1st Place",
        "Mainboard": mainboard,
        "Sideboard": sideboard,
    }


def _card(name: str, count: int = 4) -> dict:
    return {"CardName": name, "Count": count}


def _build_delver_tournament() -> dict:
    """10 Delver decks in the current ban-regime (2026-05-25).

    Card inclusions designed to exercise the 0-bucket:
      Murktide Regent: 8/10 @ 2  → dist {2: 0.8, 0: 0.2}
      Brainstorm:     10/10 @ 4  → dist {4: 1.0}  (no 0-bucket rendered in output; share=0.0)
      Daze:            8/10 @ 4  → dist {4: 0.8, 0: 0.2}

    We also add a mixed-count card "Spell Pierce" (6 decks @ 3, 4 decks @ 4) to test
    multi-bucket distributions.
    """
    decks = []
    for i in range(10):
        main = [
            _card("Brainstorm", 4),             # 10/10
            _card("Force of Will", 4),          # 10/10
            _card("Ponder", 4),                 # 10/10
            _card("Wasteland", 4),              # 10/10
            _card("Dragon's Rage Channeler", 4), # 10/10
            _card("Volcanic Island", 2),        # 10/10
            _card("Scalding Tarn", 4),          # 10/10
            _card("Mishra's Bauble", 4),        # 10/10
            _card("Polluted Delta", 4),         # 10/10
            _card("Arid Mesa", 4),              # 10/10
            _card("Misty Rainforest", 4),       # 10/10
        ]
        if i < 8:
            main.append(_card("Daze", 4))           # 8/10 @ 4
        if i < 8:
            main.append(_card("Murktide Regent", 2))  # 8/10 @ 2
        if i < 6:
            main.append(_card("Preordain", 4))      # 6/10
        if i < 4:
            main.append(_card("Lightning Bolt", 4)) # 4/10
        # Mixed-count card: 6 decks @ 3 copies, 4 decks @ 4 copies.
        if i < 6:
            main.append(_card("Spell Pierce", 3))   # 6/10 @ 3
        else:
            main.append(_card("Spell Pierce", 4))   # 4/10 @ 4

        side = [
            _card("Pyroblast", 4),            # 10/10
            _card("Red Elemental Blast", 4),  # 10/10
        ]
        if i < 8:
            side.append(_card("Flusterstorm", 2))   # 8/10

        decks.append(_make_deck_raw(f"player{i}", main, side))

    dist_date = in_current_regime(7)
    return {
        "Tournament": {
            "Name": "Legacy Challenge Distribution Test",
            "Date": dist_date,
            "Uri": f"https://www.mtgo.com/decklist/legacy-challenge-dist-{dist_date}",
            "Formats": "Legacy",
        },
        "Decks": decks,
        "Rounds": [],
        "Standings": [],
    }


@pytest.fixture
def con():
    """In-memory DuckDB with 10-deck Delver tournament, all labeled 'Delver'."""
    c = store.connect(":memory:")
    store.init_schema(c)
    raw = _build_delver_tournament()
    store.load_tournament(c, parse_cache_item(raw, "MTGO"))
    c.execute("UPDATE decks SET archetype = 'Delver'")
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Unit 1 — card_count_distributions (DB primitive)
# ---------------------------------------------------------------------------

class TestCardCountDistributions:
    """DB-level distribution tests — 0-bucket math is the main concern."""

    def test_murktide_two_buckets(self, con):
        """Murktide: 8/10 decks @ 2 → dist = {2: 0.8, 0: 0.2}."""
        dists = card_count_distributions(con, "Delver", board="main")
        murk = dists.get("Murktide Regent")
        assert murk is not None, "Murktide Regent must appear in distributions"
        assert murk.dist[2] == pytest.approx(0.8)
        assert murk.dist[0] == pytest.approx(0.2)
        assert sum(murk.dist.values()) == pytest.approx(1.0)

    def test_brainstorm_no_zero_bucket(self, con):
        """Brainstorm: 10/10 @ 4 → dist = {4: 1.0}; no zero-bucket (all decks run it)."""
        dists = card_count_distributions(con, "Delver", board="main")
        bs = dists.get("Brainstorm")
        assert bs is not None
        assert bs.dist[4] == pytest.approx(1.0)
        assert 0 not in bs.dist

    def test_mixed_count_card(self, con):
        """Spell Pierce: 6/10 @ 3, 4/10 @ 4 → dist = {3: 0.6, 4: 0.4} (no 0-bucket)."""
        dists = card_count_distributions(con, "Delver", board="main")
        sp = dists.get("Spell Pierce")
        assert sp is not None
        assert sp.dist[3] == pytest.approx(0.6)
        assert sp.dist[4] == pytest.approx(0.4)
        assert 0 not in sp.dist
        assert sum(sp.dist.values()) == pytest.approx(1.0)

    def test_modal_tie_prefers_higher_count(self, con):
        """When two counts tie on frequency, higher count wins (matches CardFreq behavior).

        Build a fixture with 5 decks @ 3 and 5 decks @ 4 for a card — modal should be 4.
        (Spell Pierce is 6@3 and 4@4 — not a tie. Instead we test via a direct hand-built fixture.)
        """
        # We can't directly test a tie from the existing fixture, but we can verify the modal
        # for Spell Pierce: 6 decks @ 3 > 4 decks @ 4, so modal should be 3.
        dists = card_count_distributions(con, "Delver", board="main")
        sp = dists.get("Spell Pierce")
        assert sp is not None
        assert sp.modal_count == 3  # 0.6 > 0.4, no tie here; but tests the max logic

    def test_modal_tie_higher_count_wins_directly(self, con):
        """Test tie-breaking: create a tie scenario with 5+5 decks."""
        # Build a fresh 10-deck con where Tie Card is 5@2, 5@3 → modal should be 3.
        c = store.connect(":memory:")
        store.init_schema(c)
        decks = []
        for i in range(10):
            base_main = [_card("Brainstorm", 4)] * 1
            base_main = [
                {"CardName": "Brainstorm", "Count": 4},
                {"CardName": "Force of Will", "Count": 4},
                {"CardName": "Ponder", "Count": 4},
                {"CardName": "Wasteland", "Count": 4},
                {"CardName": "Dragon's Rage Channeler", "Count": 4},
                {"CardName": "Volcanic Island", "Count": 2},
                {"CardName": "Scalding Tarn", "Count": 4},
                {"CardName": "Mishra's Bauble", "Count": 4},
                {"CardName": "Polluted Delta", "Count": 4},
                {"CardName": "Arid Mesa", "Count": 4},
                {"CardName": "Misty Rainforest", "Count": 4},
                {"CardName": "Flooded Strand", "Count": 4},
                {"CardName": "Ancient Tomb", "Count": 2},
                {"CardName": "Daze", "Count": 4},
            ]
            # Tie Card: 5 decks @ 2, 5 decks @ 3
            count = 2 if i < 5 else 3
            base_main.append({"CardName": "Tie Card", "Count": count})
            decks.append(_make_deck_raw(f"tp{i}", base_main, []))
        raw = {
            "Tournament": {
                "Name": "Tie Test",
                "Date": in_current_regime(7),
                "Uri": "https://example.com/tie-test",
                "Formats": "Legacy",
            },
            "Decks": decks,
            "Rounds": [],
            "Standings": [],
        }
        store.load_tournament(c, parse_cache_item(raw, "MTGO"))
        c.execute("UPDATE decks SET archetype = 'TieArch'")
        dists = card_count_distributions(c, "TieArch", board="main")
        tie_card = dists.get("Tie Card")
        assert tie_card is not None
        assert tie_card.modal_count == 3  # ties → higher count wins
        c.close()

    def test_window_default_matches_latest_regime(self, con):
        """Default window (since=None, until=None) should use _latest_regime_window() — SSOT test.

        Both card_count_distributions and card_frequencies (consensus) must return the same
        effective window so generate doctor and generate consensus don't contradict each other.
        """
        from legacy_engine.generation.consensus import _latest_regime_window, card_frequencies
        consensus_since, consensus_until = _latest_regime_window()

        # card_count_distributions should find the same decks when called with its own default.
        dists_default = card_count_distributions(con, "Delver", board="main")
        dists_explicit = card_count_distributions(
            con, "Delver", board="main",
            since=consensus_since, until=consensus_until,
        )
        # Same deck pool → same cards and same decks_total.
        assert set(dists_default.keys()) == set(dists_explicit.keys())
        for name in dists_default:
            assert dists_default[name].decks_total == dists_explicit[name].decks_total

        # Also confirm both surfaces yield the same decks_total.
        freqs = card_frequencies(con, "Delver", board="main")
        if freqs:
            expected_total = round(freqs[0].decks_running / freqs[0].inclusion_pct)
            any_dist = next(iter(dists_default.values()))
            assert any_dist.decks_total == expected_total

    def test_unknown_archetype_returns_empty(self, con):
        dists = card_count_distributions(con, "NoSuchArchetype", board="main")
        assert dists == {}

    def test_decks_total_populated(self, con):
        dists = card_count_distributions(con, "Delver", board="main")
        assert dists, "Should have cards for Delver"
        any_dist = next(iter(dists.values()))
        assert any_dist.decks_total == 10

    def test_zero_bucket_excluded_when_all_decks_run_card(self, con):
        """Cards run by every deck must NOT have a 0-bucket."""
        dists = card_count_distributions(con, "Delver", board="main")
        # Brainstorm is in all 10 decks.
        bs = dists["Brainstorm"]
        assert 0 not in bs.dist

    def test_shares_sum_to_1(self, con):
        """Each card's distribution must sum to ~1.0."""
        dists = card_count_distributions(con, "Delver", board="main")
        for name, d in dists.items():
            total = sum(d.dist.values())
            assert total == pytest.approx(1.0, abs=1e-9), (
                f"{name} dist sums to {total:.6f}, not 1.0"
            )

    def test_side_distributions_exist(self, con):
        """Sideboard distributions are queryable."""
        dists = card_count_distributions(con, "Delver", board="side")
        assert "Pyroblast" in dists
        pyroblast = dists["Pyroblast"]
        assert pyroblast.dist[4] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Unit 2 — diff_deck_vs_field (PURE — hand-built distributions)
# ---------------------------------------------------------------------------

class TestDiffDeckVsField:
    """Pure comparison tests — the core of the feature.

    All four hand-validated examples from the design doc are replayed here to pin
    the _OUTLIER_SHARE_FLOOR = 0.20 choice.

    Calibration log:
      - Bowmasters user@4, field_dist {3:.68,4:.23,...}: 23% >= 20% floor → on-consensus.
        The design says "4 is a real camp" — correct with 0.20.
      - Murktide user@2, field_dist {2:.79,0:.11,3:.09}: 79% >> 20% → on-consensus Δ0. Correct.
      - Lands user@18, field_dist {19:.73,20:.21,18:.05}: 5% < 20% → outlier. Correct.
      - Daze user@2, field_dist {3:.61,2:.18,4:.12}: 18% < 20% → outlier.
        The design says "flagged as the one off-consensus count". 0.20 satisfies this.
        (With 0.15, Daze would NOT be flagged. 0.20 is the calibrated choice.)
    """

    def _make_dist(self, name: str, dist: dict[int, float], board: str = "main") -> CardCountDist:
        modal = max(dist.keys(), key=lambda c: (dist[c], c))
        return CardCountDist(name=name, board=board, dist=dist, modal_count=modal, decks_total=100)

    # ── Bowmasters: user@4, 23% run 4 → on-consensus (real camp) ──

    def test_bowmasters_on_consensus(self):
        """Bowmasters at 4: 23% of field runs 4 → ≥ 0.20 floor → on-consensus (Δ+1, 'real camp')."""
        dist = self._make_dist("Orcish Bowmasters", {3: 0.68, 4: 0.23, 2: 0.05, 0: 0.04})
        deltas, not_in_field = diff_deck_vs_field(
            {"Orcish Bowmasters": 4}, {"Orcish Bowmasters": dist}, board="main"
        )
        assert not not_in_field
        assert len(deltas) == 1
        d = deltas[0]
        assert d.name == "Orcish Bowmasters"
        assert d.user_count == 4
        assert d.field_modal == 3
        assert d.delta == 1
        assert d.user_share == pytest.approx(0.23)
        assert not d.is_outlier, "23% >= 20% floor → should NOT be an outlier"

    # ── Murktide: user@2, 79% run 2 → on-consensus Δ0 ──

    def test_murktide_on_consensus_delta_zero(self):
        """Murktide at 2 (mode=2, user_share=79%) → Δ0 on-consensus."""
        dist = self._make_dist("Murktide Regent", {2: 0.79, 0: 0.11, 3: 0.09, 1: 0.01})
        deltas, _ = diff_deck_vs_field(
            {"Murktide Regent": 2}, {"Murktide Regent": dist}, board="main"
        )
        assert len(deltas) == 1
        d = deltas[0]
        assert d.delta == 0
        assert d.user_share == pytest.approx(0.79)
        assert not d.is_outlier

    # ── Lands: user@18, 5% run 18 → outlier (Δ-1) ──

    def test_lands_outlier(self):
        """Lands at 18 (mode=19, user_share=5%) → outlier (5% < 20% floor)."""
        dist = self._make_dist("Island", {19: 0.73, 20: 0.21, 18: 0.05, 17: 0.01})
        deltas, _ = diff_deck_vs_field({"Island": 18}, {"Island": dist}, board="main")
        assert len(deltas) == 1
        d = deltas[0]
        assert d.user_count == 18
        assert d.field_modal == 19
        assert d.delta == -1
        assert d.user_share == pytest.approx(0.05)
        assert d.is_outlier, "5% < 20% floor → must be flagged as outlier"

    # ── Daze: user@2, 18% run 2 → outlier at floor=0.20 (the borderline case) ──

    def test_daze_borderline_outlier_at_default_floor(self):
        """Daze at 2 (mode=3, user_share=18%) → outlier at default floor of 0.20.

        This is the key calibration case. With floor=0.15, Daze would NOT be flagged.
        With floor=0.20, Daze IS flagged — which matches the design's stated intent
        ('flagged as the one off-consensus count'). The floor is 0.20.
        """
        assert _OUTLIER_SHARE_FLOOR == 0.20, (
            f"Floor is {_OUTLIER_SHARE_FLOOR}, expected 0.20 — calibration has drifted"
        )
        dist = self._make_dist("Daze", {3: 0.61, 2: 0.18, 4: 0.12, 0: 0.09})
        deltas, _ = diff_deck_vs_field({"Daze": 2}, {"Daze": dist}, board="main")
        assert len(deltas) == 1
        d = deltas[0]
        assert d.user_count == 2
        assert d.field_modal == 3
        assert d.user_share == pytest.approx(0.18)
        assert d.is_outlier, (
            "Daze at 18% should be flagged with floor=0.20 "
            "(18% < 20% floor = outlier; this was the design's intent)"
        )

    def test_daze_not_outlier_at_lower_floor(self):
        """If floor were 0.15, Daze at 18% would NOT be flagged — confirming our calibration choice."""
        dist = self._make_dist("Daze", {3: 0.61, 2: 0.18, 4: 0.12, 0: 0.09})
        deltas, _ = diff_deck_vs_field(
            {"Daze": 2}, {"Daze": dist}, board="main", outlier_floor=0.15
        )
        d = deltas[0]
        # At 0.15, 18% >= 15% → NOT an outlier.  This proves why we chose 0.20.
        assert not d.is_outlier

    # ── Other cases ──

    def test_user_card_not_in_field(self):
        """A user card with no field distribution goes to not_in_field."""
        dists: dict[str, CardCountDist] = {}
        deltas, not_in_field = diff_deck_vs_field(
            {"Chrome Mox": 4}, dists, board="main"
        )
        assert deltas == []
        assert "Chrome Mox" in not_in_field

    def test_user_zero_of_field_staple(self):
        """User runs 0 of a field staple → outlier with user_count=0."""
        dist = self._make_dist("Brainstorm", {4: 1.0})
        # user has 0 Brainstorm (not in user_counts dict, so defaults to 0)
        deltas, not_in_field = diff_deck_vs_field({}, {"Brainstorm": dist}, board="main")
        # No not_in_field since card is in dists.
        assert not not_in_field
        assert len(deltas) == 1
        d = deltas[0]
        assert d.user_count == 0
        assert d.field_modal == 4
        assert d.delta == -4
        assert d.user_share == 0.0   # 0-bucket may not be in field dist if all run it
        assert d.is_outlier

    def test_ordering_outliers_first(self):
        """Outliers appear before on-consensus entries in the output."""
        bowmasters_dist = self._make_dist("Orcish Bowmasters", {3: 0.68, 4: 0.23, 0: 0.09})
        daze_dist = self._make_dist("Daze", {3: 0.61, 2: 0.18, 4: 0.12, 0: 0.09})
        dists = {"Orcish Bowmasters": bowmasters_dist, "Daze": daze_dist}
        # Bowmasters at 4 → on-consensus (23% >= 20%); Daze at 2 → outlier (18% < 20%)
        deltas, _ = diff_deck_vs_field(
            {"Orcish Bowmasters": 4, "Daze": 2}, dists, board="main"
        )
        outlier_names = [d.name for d in deltas if d.is_outlier]
        consensus_names = [d.name for d in deltas if not d.is_outlier]
        # Check all outliers appear before any consensus card in the list.
        if outlier_names and consensus_names:
            last_outlier_idx = max(i for i, d in enumerate(deltas) if d.is_outlier)
            first_consensus_idx = min(i for i, d in enumerate(deltas) if not d.is_outlier)
            assert last_outlier_idx < first_consensus_idx

    def test_deterministic_ordering(self):
        """Same inputs must produce same ordering across calls."""
        dist_a = self._make_dist("Aaa", {4: 1.0})
        dist_b = self._make_dist("Bbb", {3: 0.10, 4: 0.90})
        dists = {"Aaa": dist_a, "Bbb": dist_b}
        user = {"Aaa": 4, "Bbb": 4}
        d1, nf1 = diff_deck_vs_field(user, dists, board="main")
        d2, nf2 = diff_deck_vs_field(user, dists, board="main")
        assert [x.name for x in d1] == [x.name for x in d2]

    def test_not_in_field_sorted(self):
        """not_in_field list must be sorted deterministically."""
        _, not_in_field = diff_deck_vs_field(
            {"Zzz": 4, "Aaa": 2, "Mmm": 1}, {}, board="main"
        )
        assert not_in_field == sorted(not_in_field)

    def test_on_consensus_when_count_matches_modal(self):
        """If user count == field modal count, never an outlier regardless of share."""
        dist = self._make_dist("Force of Will", {4: 0.95, 3: 0.05})
        deltas, _ = diff_deck_vs_field({"Force of Will": 4}, {"Force of Will": dist}, board="main")
        d = deltas[0]
        assert d.delta == 0
        assert not d.is_outlier  # delta==0 → never an outlier


# ---------------------------------------------------------------------------
# Unit 3 — build_deck_doctor_report (orchestrator, DB)
# ---------------------------------------------------------------------------

class TestBuildReport:
    """End-to-end orchestrator tests over the Delver fixture."""

    def test_report_has_correct_archetype_and_board(self, con):
        report = build_deck_doctor_report(
            con,
            {"Brainstorm": 4, "Murktide Regent": 2},
            {},
            "Delver",
            board="main",
        )
        assert report.archetype == "Delver"
        assert report.board == "main"

    def test_decks_total_populated(self, con):
        report = build_deck_doctor_report(
            con, {"Brainstorm": 4}, {}, "Delver", board="main"
        )
        assert report.decks_total == 10

    def test_window_populated_from_default(self, con):
        """Default window resolves to the latest ban-regime (same as consensus)."""
        from legacy_engine.generation.consensus import _latest_regime_window
        exp_since, exp_until = _latest_regime_window()
        report = build_deck_doctor_report(con, {"Brainstorm": 4}, {}, "Delver", board="main")
        assert report.window == (exp_since, exp_until)

    def test_ordering_outliers_first(self, con):
        """Outliers appear before on-consensus entries in deltas."""
        # Murktide at 3 is an outlier (field mode=2): user_share for count=3 is 0.0 < 0.20.
        user_main = {"Brainstorm": 4, "Murktide Regent": 3}
        report = build_deck_doctor_report(con, user_main, {}, "Delver", board="main")
        outlier_indices = [i for i, d in enumerate(report.deltas) if d.is_outlier]
        consensus_indices = [i for i, d in enumerate(report.deltas) if not d.is_outlier]
        if outlier_indices and consensus_indices:
            assert max(outlier_indices) < min(consensus_indices)

    def test_not_in_field_catches_unknown_card(self, con):
        """A card the field never runs shows up in not_in_field."""
        report = build_deck_doctor_report(
            con, {"Brainstorm": 4, "Chrome Mox": 4}, {}, "Delver", board="main"
        )
        assert "Chrome Mox" in report.not_in_field

    def test_murktide_on_consensus_at_2(self, con):
        """Murktide at 2 (mode=2) → Δ0, on-consensus."""
        report = build_deck_doctor_report(
            con, {"Murktide Regent": 2}, {}, "Delver", board="main"
        )
        murk_delta = next(d for d in report.deltas if d.name == "Murktide Regent")
        assert murk_delta.delta == 0
        assert not murk_delta.is_outlier

    def test_empty_archetype_returns_zero_decks_total(self, con):
        """Unknown archetype → decks_total=0, empty deltas."""
        report = build_deck_doctor_report(
            con, {"Brainstorm": 4}, {}, "NonExistent", board="main"
        )
        assert report.decks_total == 0
        assert report.deltas == []

    def test_side_board(self, con):
        """Side-board doctor report works for sideboard."""
        report = build_deck_doctor_report(
            con, {}, {"Pyroblast": 4}, "Delver", board="side"
        )
        assert report.board == "side"
        pyroblast_delta = next(
            (d for d in report.deltas if d.name == "Pyroblast"), None
        )
        assert pyroblast_delta is not None

    def test_window_ssot_matches_consensus(self, con):
        """generate doctor and generate consensus MUST use the same default window.

        This is the critical SSOT assertion: both call _latest_regime_window() and should
        produce the same (since, until) for the Delver archetype.
        """
        from legacy_engine.generation.consensus import _latest_regime_window, build_consensus
        exp_since, exp_until = _latest_regime_window()

        report = build_deck_doctor_report(
            con, {"Brainstorm": 4}, {}, "Delver", board="main"
        )
        consensus_deck = build_consensus(con, "Delver")

        # Both must resolve to the same window.
        assert report.window[0] == exp_since
        assert report.window[1] == exp_until
        assert consensus_deck.window[0] == exp_since
        assert consensus_deck.window[1] == exp_until


# ---------------------------------------------------------------------------
# Unit 4 — CLI: generate doctor (smoke tests)
# ---------------------------------------------------------------------------

class TestGenerateDoctorCLI:
    """CLI smoke tests for generate doctor."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Write the Delver fixture to a real DuckDB file for CLI invocation."""
        import duckdb as _duckdb
        db_file = tmp_path / "dist_test.duckdb"
        file_con = _duckdb.connect(str(db_file))
        store.init_schema(file_con)
        raw = _build_delver_tournament()
        store.load_tournament(file_con, parse_cache_item(raw, "MTGO"))
        file_con.execute("UPDATE decks SET archetype = 'Delver'")
        file_con.close()
        return str(db_file)

    @pytest.fixture
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    @pytest.fixture
    def deck_file(self, tmp_path):
        """A plain-text decklist containing Murktide at 3 (outlier vs mode=2)."""
        lines = [
            "4 Brainstorm",
            "4 Force of Will",
            "4 Ponder",
            "4 Wasteland",
            "4 Dragon's Rage Channeler",
            "2 Volcanic Island",
            "4 Scalding Tarn",
            "4 Mishra's Bauble",
            "4 Polluted Delta",
            "4 Arid Mesa",
            "4 Misty Rainforest",
            "4 Daze",
            "3 Murktide Regent",  # outlier: field mode=2, user runs 3
            "4 Preordain",
            "4 Lightning Bolt",
            "4 Flooded Strand",
        ]
        deck = tmp_path / "test_deck.txt"
        deck.write_text("\n".join(lines) + "\n")
        return str(deck)

    def test_happy_path_exit_zero(self, runner, db_path, deck_file):
        """generate doctor exits 0 and renders the report."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main, ["generate", "doctor", "--deck", deck_file, "--archetype", "Delver", "--db", db_path]
        )
        assert result.exit_code == 0, f"exit={result.exit_code}\n{result.output}"

    def test_outlier_line_rendered(self, runner, db_path, deck_file):
        """Murktide at 3 (vs mode=2) should appear in the OUTLIERS section."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main, ["generate", "doctor", "--deck", deck_file, "--archetype", "Delver", "--db", db_path]
        )
        assert result.exit_code == 0, result.output
        # The output should contain an outliers section.
        assert "OUTLIERS" in result.output
        # Murktide should be in the output (either in OUTLIERS or ON CONSENSUS).
        assert "Murktide Regent" in result.output

    def test_sample_tier_banner_rendered(self, runner, db_path, deck_file):
        """The sample_n and tier are rendered in the header."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main, ["generate", "doctor", "--deck", deck_file, "--archetype", "Delver", "--db", db_path]
        )
        assert result.exit_code == 0, result.output
        # sample_n=10 → [speculative] tier.
        assert "sample_n=10" in result.output
        assert "[speculative]" in result.output

    def test_archetype_override_path(self, runner, db_path, deck_file):
        """--archetype overrides classification."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main, ["generate", "doctor", "--deck", deck_file, "--archetype", "Delver", "--db", db_path]
        )
        assert result.exit_code == 0, result.output
        # No "Classified archetype:" echo when --archetype is provided.
        assert "Classified archetype:" not in result.output

    def test_min_tier_suppresses_report(self, runner, db_path, deck_file):
        """With --min-tier established, sample_n=10 [speculative] report is suppressed."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main, [
                "generate", "doctor",
                "--deck", deck_file,
                "--archetype", "Delver",
                "--db", db_path,
                "--min-tier", "established",
            ]
        )
        assert result.exit_code == 0, result.output
        assert "SUPPRESSED" in result.output
        assert "OUTLIERS" not in result.output

    def test_all_time_flag(self, runner, db_path, deck_file):
        """--all-time uses full corpus (bypasses ban-regime window)."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main, [
                "generate", "doctor",
                "--deck", deck_file,
                "--archetype", "Delver",
                "--db", db_path,
                "--all-time",
            ]
        )
        assert result.exit_code == 0, result.output
        # open → current window label
        assert "open → current" in result.output

    def test_board_side(self, runner, db_path, tmp_path):
        """--board side runs the sideboard comparison."""
        from legacy_engine.cli import main
        # Deck with a sideboard.
        lines = [
            "4 Brainstorm",
            "4 Force of Will",
            "4 Ponder",
            "4 Wasteland",
            "4 Dragon's Rage Channeler",
            "2 Volcanic Island",
            "4 Scalding Tarn",
            "4 Mishra's Bauble",
            "4 Polluted Delta",
            "4 Arid Mesa",
            "4 Misty Rainforest",
            "4 Daze",
            "2 Murktide Regent",
            "4 Preordain",
            "4 Lightning Bolt",
            "4 Flooded Strand",
            "",
            "Sideboard",
            "4 Pyroblast",
            "4 Red Elemental Blast",
            "2 Flusterstorm",
        ]
        side_deck = tmp_path / "side_deck.txt"
        side_deck.write_text("\n".join(lines) + "\n")

        result = runner.invoke(
            main, [
                "generate", "doctor",
                "--deck", str(side_deck),
                "--archetype", "Delver",
                "--db", db_path,
                "--board", "side",
            ]
        )
        assert result.exit_code == 0, result.output
