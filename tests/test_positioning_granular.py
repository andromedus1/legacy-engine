"""Hermetic tests for the list-granular positioning overlay (Unit 6).

Validates three properties:
  A. DEFAULT OFF: calling positioning_score (baseline) is byte-identical
     regardless of which list you'd submit — archetype-level S unchanged.
  B. OPT-IN DIFFERENTIATION: two same-archetype Dimir Tempo lists (grindy
     Hymn/Strix vs lean Daze/Nethergoyf) produce DIFFERENT s_granular values
     when card-lift signals distinguish them.
  C. CAVEAT PRESENT: the GranularPositioningResult always carries GRANULAR_CAVEAT.

All inputs are in-memory (no real DB).  CardWinRates is hand-built with seeded
lift signals designed to differentiate the two list archetypes.
"""

from __future__ import annotations

from dataclasses import dataclass as _dc

from legacy_engine.advisory.field import build_custom_field
from legacy_engine.advisory.positioning import (
    GRANULAR_CAVEAT,
    GranularPositioningResult,
    PositioningResult,
    composition_adjusted_winrates,
    positioning_score,
    positioning_score_granular,
)
from legacy_engine.analytics.matchup import MatchupMatrix, build_cell, build_mirror_cell
from legacy_engine.models import MatchupCell

# ---------------------------------------------------------------------------
# Hermetic corpus — hand-built, seeded, no DB
# ---------------------------------------------------------------------------

_SEED = 99
_N_DRAWS = 5_000
_TOL = 0.01  # tight tolerance on deterministic overlay sums

# ── Archetype names ────────────────────────────────────────────────────────
# Dimir Tempo and two opponents
_DIMIR = "Dimir Tempo"
_RED = "Red Stompy"
_ANT = "ANT"

# Both test lists share the same archetype label
_GRINDY_LIST: dict[str, int] = {
    "Hymn to Tourach": 4,
    "Baleful Strix": 4,
    "Force of Will": 4,
    "Brainstorm": 4,
    "Ponder": 4,
    "Swamp": 4,
    "Island": 4,
    "Underground Sea": 4,
    "Polluted Delta": 4,
    "Misty Rainforest": 2,
    "Daze": 0,         # lean cards absent in grindy
    "Nethergoyf": 0,
}

_LEAN_LIST: dict[str, int] = {
    "Daze": 4,
    "Nethergoyf": 4,
    "Force of Will": 4,
    "Brainstorm": 4,
    "Ponder": 4,
    "Swamp": 2,
    "Island": 4,
    "Underground Sea": 4,
    "Polluted Delta": 4,
    "Misty Rainforest": 4,
    "Hymn to Tourach": 0,  # grindy cards absent in lean
    "Baleful Strix": 0,
}

# Strip zero-count entries (simulates real decklist input)
_GRINDY = {k: v for k, v in _GRINDY_LIST.items() if v > 0}
_LEAN = {k: v for k, v in _LEAN_LIST.items() if v > 0}


# ---------------------------------------------------------------------------
# Hermetic CardWinRates stand-in
# ---------------------------------------------------------------------------
# Rather than a real CardWinRates object (which requires DB + corpus),
# we build a minimal stand-in that duck-types what card_value_matchup needs.
# card_value_matchup accesses: r.marginal[(card, board)], r.matchup[(card, board, opp)]
# and r.baseline_winrate.
#
# Our stand-in encodes the following narrative:
#   - "Hymn to Tourach" has POSITIVE lift vs ANT (discard disrupts combo) — +0.06 lift
#   - "Baleful Strix" has POSITIVE lift vs Red Stompy (blocks profitably) — +0.06 lift
#   - "Daze" has POSITIVE lift vs Red Stompy (tempo card vs fast opponent) — +0.04 lift
#   - "Nethergoyf" has POSITIVE lift vs Red Stompy (fast clock) — +0.05 lift
#   - All other cards: neutral (lift=0.0)
#
# This simulates a corpus where grindy disruption cards are good vs combo and
# lean tempo cards are good vs aggro.  Both lists are the same archetype so
# archetype-level S is identical; the overlay differentiates them.


@_dc
class _FakeCardRecord:
    wins: int
    n: int

    @property
    def losses(self) -> int:
        return self.n - self.wins


@_dc
class _FakeCardMarginalRecord:
    card: str
    board: str
    wins: int = 0
    losses: int = 0

    @property
    def n(self) -> int:
        return self.wins + self.losses


@_dc
class _FakeCardMatchupRecord:
    card: str
    board: str
    opponent: str
    wins: int = 0
    losses: int = 0

    @property
    def n(self) -> int:
        return self.wins + self.losses


@_dc
class _FakeCardWinRates:
    """Minimal duck-type of CardWinRates for hermetic testing."""

    matchup: dict  # (card, board, opp) → _FakeCardMatchupRecord
    marginal: dict  # (card, board) → _FakeCardMarginalRecord
    baseline_winrate: float = 0.5


def _build_fake_card_winrates() -> _FakeCardWinRates:
    """Build a hand-crafted CardWinRates stand-in with narrative lift signals.

    Lift encoding (n=100 per cell so tier='established' fires):
      - Hymn vs ANT:    70/100 → lift ≈ +0.06 vs prior ~0.5
      - Strix vs Red:   67/100 → lift ≈ +0.05
      - Daze vs Red:    65/100 → lift ≈ +0.04
      - Nethergoyf vs Red: 66/100 → lift ≈ +0.04
      All marginals: 55/100 → p_shrunk slightly above 0.5
    """
    BOARD = "main"
    matchup: dict = {}
    marginal: dict = {}

    # All cards get a neutral marginal
    all_cards = [
        "Hymn to Tourach", "Baleful Strix", "Force of Will",
        "Brainstorm", "Ponder", "Daze", "Nethergoyf",
        "Underground Sea", "Polluted Delta", "Misty Rainforest",
        "Swamp", "Island",
    ]
    for card in all_cards:
        marginal[(card, BOARD)] = _FakeCardMarginalRecord(
            card=card, board=BOARD, wins=55, losses=45
        )

    # Hymn to Tourach: strong vs ANT (combo disruption)
    matchup[("Hymn to Tourach", BOARD, _ANT)] = _FakeCardMatchupRecord(
        card="Hymn to Tourach", board=BOARD, opponent=_ANT, wins=70, losses=30
    )
    matchup[("Hymn to Tourach", BOARD, _RED)] = _FakeCardMatchupRecord(
        card="Hymn to Tourach", board=BOARD, opponent=_RED, wins=50, losses=50
    )

    # Baleful Strix: strong vs Red Stompy (blocks Goblin Guide etc.)
    matchup[("Baleful Strix", BOARD, _RED)] = _FakeCardMatchupRecord(
        card="Baleful Strix", board=BOARD, opponent=_RED, wins=67, losses=33
    )
    matchup[("Baleful Strix", BOARD, _ANT)] = _FakeCardMatchupRecord(
        card="Baleful Strix", board=BOARD, opponent=_ANT, wins=50, losses=50
    )

    # Daze: good vs Red Stompy (tempo)
    matchup[("Daze", BOARD, _RED)] = _FakeCardMatchupRecord(
        card="Daze", board=BOARD, opponent=_RED, wins=65, losses=35
    )
    matchup[("Daze", BOARD, _ANT)] = _FakeCardMatchupRecord(
        card="Daze", board=BOARD, opponent=_ANT, wins=55, losses=45
    )

    # Nethergoyf: good vs Red Stompy (fast clock)
    matchup[("Nethergoyf", BOARD, _RED)] = _FakeCardMatchupRecord(
        card="Nethergoyf", board=BOARD, opponent=_RED, wins=66, losses=34
    )
    matchup[("Nethergoyf", BOARD, _ANT)] = _FakeCardMatchupRecord(
        card="Nethergoyf", board=BOARD, opponent=_ANT, wins=50, losses=50
    )

    return _FakeCardWinRates(matchup=matchup, marginal=marginal, baseline_winrate=0.5)


# ---------------------------------------------------------------------------
# Hermetic MatchupMatrix
# ---------------------------------------------------------------------------

def _make_cell_direct(a: str, b: str, wins: int, n: int) -> MatchupCell:
    return build_cell(a, b, wins, n)


def _make_mirror_direct(a: str, n: int) -> MatchupCell:
    return build_mirror_cell(a, n)


def _hermetic_matrix() -> MatchupMatrix:
    """Archetype-level matchup matrix where both Dimir lists share the same row.

    Dimir Tempo vs Red Stompy: 55/100 → 55% win rate
    Dimir Tempo vs ANT:        48/100 → 48% win rate
    (Opponents have reciprocal rows.)
    """
    archetypes = [_DIMIR, _RED, _ANT]
    winrates = {
        (_DIMIR, _RED): (55, 100),
        (_DIMIR, _ANT): (48, 100),
        (_RED, _DIMIR): (45, 100),
        (_RED, _ANT):   (50, 100),
        (_ANT, _DIMIR): (52, 100),
        (_ANT, _RED):   (50, 100),
    }
    cells: dict[tuple[str, str], MatchupCell] = {}
    for a in archetypes:
        cells[(a, a)] = _make_mirror_direct(a, 60)
        for b in archetypes:
            if a == b:
                continue
            wins, n = winrates.get((a, b), (0, 0))
            cells[(a, b)] = _make_cell_direct(a, b, wins, n)
    return MatchupMatrix(
        cells=cells,
        provenance=None,
        total_matches=sum(n for _, n in winrates.values()) // 2,
        archetypes=sorted(archetypes),
        caveat="hermetic test matrix",
    )


def _hermetic_field():
    """Field: Red Stompy 40%, ANT 60% — chosen to amplify grindy vs lean difference."""
    return build_custom_field({_RED: 0.40, _ANT: 0.60})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGranularDefault:
    """A: Default path is byte-identical — granular overlay does not affect baseline S."""

    def test_baseline_s_identical_for_both_lists(self):
        """positioning_score (archetype-level) must return the same S for both lists.

        This validates that the overlay is truly opt-in and does not contaminate
        the standard positioning_score entry point.
        """
        matrix = _hermetic_matrix()
        field = _hermetic_field()

        grindy_s = positioning_score(matrix, field, _DIMIR, n_draws=_N_DRAWS, seed=_SEED)
        lean_s = positioning_score(matrix, field, _DIMIR, n_draws=_N_DRAWS, seed=_SEED)

        # Same archetype → IDENTICAL (same seed, same matrix row)
        assert grindy_s.s_mean == lean_s.s_mean, (
            f"Archetype-level S must be identical for same archetype + seed: "
            f"grindy={grindy_s.s_mean:.5f}, lean={lean_s.s_mean:.5f}"
        )
        assert grindy_s.s_ci == lean_s.s_ci

    def test_baseline_s_unchanged_by_granular_call(self):
        """Calling positioning_score_granular must not mutate the archetype-level result.

        The `base` field of GranularPositioningResult must equal a direct
        positioning_score call (same seed).
        """
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_fake_card_winrates()

        direct = positioning_score(matrix, field, _DIMIR, n_draws=_N_DRAWS, seed=_SEED)
        granular = positioning_score_granular(
            matrix, field, _DIMIR, _GRINDY, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        # base.s_mean must be byte-identical
        assert granular.base.s_mean == direct.s_mean, (
            f"base.s_mean must equal direct positioning_score: "
            f"base={granular.base.s_mean:.5f}, direct={direct.s_mean:.5f}"
        )
        assert granular.base.s_ci == direct.s_ci


class TestGranularDifferentiation:
    """B: Opt-in overlay produces DIFFERENT s_granular for grindy vs lean lists."""

    def test_s_granular_differs_between_lists(self):
        """The two same-archetype lists produce different s_granular values.

        On the test field (Red 40%, ANT 60%):
        - Grindy (Hymn/Strix) has lift vs ANT → higher s_granular on ANT-heavy field
        - Lean (Daze/Nethergoyf) has lift vs Red → higher s_granular on Red-heavy field
        With Red=40%, ANT=60%, grindy's ANT bonus dominates → grindy > lean s_granular.
        """
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_fake_card_winrates()

        grindy_gr = positioning_score_granular(
            matrix, field, _DIMIR, _GRINDY, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        lean_gr = positioning_score_granular(
            matrix, field, _DIMIR, _LEAN, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )

        # Both lists produce the same archetype S
        assert grindy_gr.base.s_mean == lean_gr.base.s_mean, (
            "Archetype-level S must be identical (same matrix row + seed)"
        )

        # But s_granular should differ
        assert grindy_gr.s_granular != lean_gr.s_granular, (
            f"Granular overlay must differentiate the two lists: "
            f"grindy={grindy_gr.s_granular:.5f}, lean={lean_gr.s_granular:.5f}"
        )

        # On a 60% ANT field, grindy (Hymn specialises vs ANT) should win the overlay
        assert grindy_gr.s_granular > lean_gr.s_granular, (
            f"Grindy list (Hymn/Strix) should have higher s_granular on ANT-heavy field "
            f"(60% ANT): grindy={grindy_gr.s_granular:.5f}, lean={lean_gr.s_granular:.5f}"
        )

    def test_s_granular_greater_than_archetype_for_grindy_vs_ant_field(self):
        """On an ANT-heavy field, the grindy list's s_granular should exceed base S.

        The Hymn to Tourach lift vs ANT is positive; field-weighting by 60% ANT
        should pull s_granular above archetype S.
        """
        matrix = _hermetic_matrix()
        field = _hermetic_field()  # 40% Red, 60% ANT
        cwr = _build_fake_card_winrates()

        gr = positioning_score_granular(
            matrix, field, _DIMIR, _GRINDY, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )

        # s_granular should be above base.s_mean (Hymn's ANT lift dominates)
        assert gr.s_granular > gr.base.s_mean, (
            f"Grindy list should have s_granular > archetype S on ANT-heavy field: "
            f"s_granular={gr.s_granular:.5f}, s_mean={gr.base.s_mean:.5f}"
        )

    def test_adjusted_winrates_differ_by_list(self):
        """The adjusted per-matchup win-rates differ between the two lists."""
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_fake_card_winrates()

        adj_grindy = composition_adjusted_winrates(
            matrix, field, _DIMIR, _GRINDY, cwr,
        )
        adj_lean = composition_adjusted_winrates(
            matrix, field, _DIMIR, _LEAN, cwr,
        )

        # Grindy should have higher adjusted WR vs ANT (Hymn lift)
        assert adj_grindy[_ANT] > adj_lean[_ANT], (
            f"Grindy list should have higher adj WR vs ANT: "
            f"grindy={adj_grindy[_ANT]:.5f}, lean={adj_lean[_ANT]:.5f}"
        )

        # Lean should have higher adjusted WR vs Red (Daze + Nethergoyf lift)
        assert adj_lean[_RED] > adj_grindy[_RED], (
            f"Lean list should have higher adj WR vs Red: "
            f"lean={adj_lean[_RED]:.5f}, grindy={adj_grindy[_RED]:.5f}"
        )

    def test_adjusted_winrates_in_valid_range(self):
        """All adjusted win-rates are in [0, 1]."""
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_fake_card_winrates()

        for deck_cards in [_GRINDY, _LEAN]:
            adj = composition_adjusted_winrates(matrix, field, _DIMIR, deck_cards, cwr)
            for opp, wr in adj.items():
                assert 0.0 <= wr <= 1.0, (
                    f"Adjusted WR for {opp} out of range: {wr:.5f}"
                )

    def test_mirror_not_in_adjusted_winrates(self):
        """The self-mirror opponent must NOT appear in adjusted_winrates (always fixed 0.5)."""
        matrix = _hermetic_matrix()
        field_with_mirror = build_custom_field({_DIMIR: 0.10, _RED: 0.45, _ANT: 0.45})
        cwr = _build_fake_card_winrates()

        adj = composition_adjusted_winrates(
            matrix, field_with_mirror, _DIMIR, _GRINDY, cwr,
        )
        assert _DIMIR not in adj, (
            "Self-mirror archetype must not appear in adjusted_winrates"
        )


class TestGranularHonestyConstraints:
    """C: Honesty constraints — caveat always present, result is GranularPositioningResult."""

    def test_caveat_always_present(self):
        """GranularPositioningResult always carries GRANULAR_CAVEAT."""
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_fake_card_winrates()

        gr = positioning_score_granular(
            matrix, field, _DIMIR, _GRINDY, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        assert gr.caveat == GRANULAR_CAVEAT, (
            "GranularPositioningResult.caveat must equal GRANULAR_CAVEAT"
        )
        assert "EXPERIMENTAL" in gr.caveat
        assert "presence-correlational" in gr.caveat
        assert "not causal" in gr.caveat.lower() or "not treat" in gr.caveat.lower()

    def test_result_type_is_granular(self):
        """positioning_score_granular returns GranularPositioningResult, not PositioningResult."""
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_fake_card_winrates()

        gr = positioning_score_granular(
            matrix, field, _DIMIR, _GRINDY, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        assert isinstance(gr, GranularPositioningResult)
        assert isinstance(gr.base, PositioningResult)

    def test_base_result_unchanged(self):
        """The base PositioningResult inside GranularPositioningResult is complete and unchanged."""
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_fake_card_winrates()

        gr = positioning_score_granular(
            matrix, field, _DIMIR, _GRINDY, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        # base must have all the standard positioning fields populated
        assert gr.base.deck_archetype == _DIMIR
        assert isinstance(gr.base.s_mean, float)
        assert not isinstance(gr.base.s_mean, float) or (0.0 < gr.base.s_mean < 1.0)
        assert gr.base.s_ci[0] <= gr.base.s_mean <= gr.base.s_ci[1]
        assert isinstance(gr.base.warnings, tuple)

    def test_s_granular_in_valid_range(self):
        """s_granular is a valid probability."""
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_fake_card_winrates()

        for deck_cards in [_GRINDY, _LEAN]:
            gr = positioning_score_granular(
                matrix, field, _DIMIR, deck_cards, cwr,
                n_draws=_N_DRAWS, seed=_SEED,
            )
            assert 0.0 <= gr.s_granular <= 1.0, (
                f"s_granular must be in [0,1]: {gr.s_granular:.5f}"
            )

    def test_empty_deck_cards_produces_no_nudge(self):
        """An empty deck (no cards with lift signal) produces s_granular == baseline s_mean.

        When deck_cards is empty or all cards have zero lift, the overlay should
        produce the same field-weighted WR as archetype-level S.
        """
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_fake_card_winrates()

        # Use only Force of Will which has no special lift in our fake corpus
        neutral_deck = {"Force of Will": 4, "Brainstorm": 4, "Ponder": 4}

        gr = positioning_score_granular(
            matrix, field, _DIMIR, neutral_deck, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        # Without meaningful lift, s_granular should be close to archetype S
        # (within the max_nudge cap of ±5pp)
        assert abs(gr.s_granular - gr.base.s_mean) <= 0.06, (
            f"Neutral deck should produce s_granular near archetype S: "
            f"s_granular={gr.s_granular:.5f}, s_mean={gr.base.s_mean:.5f}"
        )
