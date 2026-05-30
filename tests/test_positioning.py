"""Tests for advisory/positioning.py — Bayesian Monte-Carlo meta-positioning score.

House style:
- Direct MatchupCell/MatchupMatrix construction for arithmetic / worked-example assertions.
- Corpus-backed (build_matrix over :memory:) for seam tests.
- All MC tests pin ``seed`` for determinism.
- Tolerances are sized to n_draws (5000 draws → ±0.02 on means).
"""

from __future__ import annotations

import pytest
import numpy as np

from legacy_engine.advisory import (
    DeckRanking,
    FieldDistribution,
    PositioningResult,
    build_custom_field,
    build_global_field,
    delta_var_S,
    positioning_score,
    rank_decks,
)
from legacy_engine.advisory.positioning import (
    _DEFAULT_DRAWS,
    _row_winrate_inputs,
    _sample_S,
)
from legacy_engine.analytics import build_matrix
from legacy_engine.analytics.matchup import MatchupMatrix
from legacy_engine.models import MatchupCell
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item

# ---------------------------------------------------------------------------
# n_draws used in tests — small enough to be fast, big enough for ±0.02
# ---------------------------------------------------------------------------

_TEST_DRAWS = 5_000
_TOL_MEAN = 0.025    # ±0.025 on posterior means (conservative for 5000 draws)
_TOL_PROB = 0.03     # ±0.03 on probabilities (p_best, pairwise)

# ---------------------------------------------------------------------------
# Helpers: build MatchupMatrix and FieldDistribution directly (no DB)
# ---------------------------------------------------------------------------

SEED = 42


def _make_cell(a: str, b: str, wins: int, n: int) -> MatchupCell:
    """Build a MatchupCell the same way build_cell does."""
    from legacy_engine.analytics.matchup import build_cell
    return build_cell(a, b, wins, n)


def _make_mirror(a: str, n: int) -> MatchupCell:
    from legacy_engine.analytics.matchup import build_mirror_cell
    return build_mirror_cell(a, n)


def _simple_matrix(
    archetypes: list[str],
    winrates: dict[tuple[str, str], tuple[int, int]],  # (wins, n)
    mirror_n: dict[str, int] | None = None,
) -> MatchupMatrix:
    """Build a MatchupMatrix directly from archetype/winrate specs.

    ``winrates`` is keyed (deck, opp) → (wins, n).  Missing pairs become n=0 cells.
    ``mirror_n`` sets each archetype's mirror match count (default 0).
    """
    if mirror_n is None:
        mirror_n = {}

    cells: dict[tuple[str, str], MatchupCell] = {}
    for a in archetypes:
        cells[(a, a)] = _make_mirror(a, mirror_n.get(a, 0))
        for b in archetypes:
            if a == b:
                continue
            wins, n = winrates.get((a, b), (0, 0))
            cells[(a, b)] = _make_cell(a, b, wins, n)

    return MatchupMatrix(
        cells=cells,
        provenance=None,
        total_matches=sum(n for wins, n in winrates.values()) // 2,
        archetypes=sorted(archetypes),
        caveat="test matrix",
    )


def _custom_field(shares: dict[str, float]) -> FieldDistribution:
    return build_custom_field(shares)


# ---------------------------------------------------------------------------
# The brief's worked example
# ---------------------------------------------------------------------------
# Field: A:50%, B:30%, C:20%
# Deck X vs A=62/100 (WR=0.62), vs B=60/100 (0.60), vs C=20/100 (0.20)
#   S = 0.5*0.62 + 0.3*0.60 + 0.2*0.20 = 0.530
#   Ū = (0.62+0.60+0.20)/3 ≈ 0.473
# Deck Y vs A=42/100 (0.42), vs B=45/100 (0.45), vs C=85/100 (0.85)
#   S = 0.5*0.42 + 0.3*0.45 + 0.2*0.85 = 0.515
#   Ū = (0.42+0.45+0.85)/3 ≈ 0.573

_WORKED_ARCHETYPES = ["A", "B", "C", "X", "Y"]
_WORKED_WINRATES = {
    # Deck X rows
    ("X", "A"): (62, 100),
    ("X", "B"): (60, 100),
    ("X", "C"): (20, 100),
    # Deck Y rows
    ("Y", "A"): (42, 100),
    ("Y", "B"): (45, 100),
    ("Y", "C"): (85, 100),
    # Opponent rows (arbitrary — not used for scoring X/Y, but matrix must be rectangular)
    ("A", "X"): (38, 100),
    ("A", "Y"): (58, 100),
    ("A", "B"): (50, 100),
    ("A", "C"): (50, 100),
    ("B", "X"): (40, 100),
    ("B", "Y"): (55, 100),
    ("B", "A"): (50, 100),
    ("B", "C"): (50, 100),
    ("C", "X"): (80, 100),
    ("C", "Y"): (15, 100),
    ("C", "A"): (50, 100),
    ("C", "B"): (50, 100),
}
_WORKED_FIELD_SHARES = {"A": 0.50, "B": 0.30, "C": 0.20}


def _worked_matrix() -> MatchupMatrix:
    return _simple_matrix(_WORKED_ARCHETYPES, _WORKED_WINRATES)


def _worked_field() -> FieldDistribution:
    return _custom_field(_WORKED_FIELD_SHARES)


# ---------------------------------------------------------------------------
# Corpus fixtures (house style: :memory: DB, labels via SQL UPDATE)
# ---------------------------------------------------------------------------

_CORPUS_RAW = {
    "Tournament": {
        "Name": "Positioning Test Challenge",
        "Date": "2026-05-30",
        "Uri": "https://www.mtgo.com/decklist/positioning-test-2026-05-30",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": f"p{i}",
            "Result": f"{i+1}",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [],
        }
        for i in range(4)
    ],
    "Rounds": [
        # p0 (Delver) beats p1 (Lands) 60 times
        *[{"Player1": "p0", "Player2": "p1", "Result": "2-1"} for _ in range(60)],
        # p1 (Lands) beats p0 (Delver) 40 times
        *[{"Player1": "p1", "Player2": "p0", "Result": "2-1"} for _ in range(40)],
        # p2 (Reanimator) beats p3 (Show) 50 times
        *[{"Player1": "p2", "Player2": "p3", "Result": "2-1"} for _ in range(50)],
        # p3 (Show) beats p2 (Reanimator) 50 times
        *[{"Player1": "p3", "Player2": "p2", "Result": "2-1"} for _ in range(50)],
    ],
    "Standings": [],
}


def _con():
    return store.connect(":memory:")


def _build_corpus_matrix():
    """Build a MatchupMatrix from a labeled :memory: corpus (integration seam)."""
    con = _con()
    tid = store.load_tournament(con, parse_cache_item(_CORPUS_RAW, "MTGO"))
    con.execute("UPDATE decks SET archetype = 'Delver' WHERE tournament_id = ? AND player = 'p0'", [tid])
    con.execute("UPDATE decks SET archetype = 'Lands' WHERE tournament_id = ? AND player = 'p1'", [tid])
    con.execute("UPDATE decks SET archetype = 'Reanimator' WHERE tournament_id = ? AND player = 'p2'", [tid])
    con.execute("UPDATE decks SET archetype = 'Show' WHERE tournament_id = ? AND player = 'p3'", [tid])
    matrix = build_matrix(con)
    return matrix, con


# ===========================================================================
# TestSampleS
# ===========================================================================


class TestSampleS:
    """Unit 1 — _sample_S core behaviour."""

    def test_known_winrate_convergence(self):
        """A deck with all 60% cells vs a uniform 2-archetype field → S_mean ≈ 0.60."""
        archetypes = ["X", "A", "B"]
        winrates = {
            ("X", "A"): (60, 100),
            ("X", "B"): (60, 100),
            ("A", "X"): (40, 100),
            ("A", "B"): (50, 100),
            ("B", "X"): (40, 100),
            ("B", "A"): (50, 100),
        }
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 0.5, "B": 0.5})

        rng = np.random.default_rng(SEED)
        samples = _sample_S(matrix, field, "X", n_draws=_TEST_DRAWS, rng=rng)
        assert abs(samples.mean() - 0.60) < _TOL_MEAN

    def test_mirror_column_fixed_zero_variance(self):
        """Mirror column contributes exactly 0.5 * w_mirror — zero variance for that column."""
        # Deck X vs X is mirror: fixed 0.5
        # Field has only X (degenerate — full mirror)
        archetypes = ["X"]
        matrix = _simple_matrix(archetypes, {}, mirror_n={"X": 50})
        field = _custom_field({"X": 1.0})

        rng = np.random.default_rng(SEED)
        samples = _sample_S(matrix, field, "X", n_draws=_TEST_DRAWS, rng=rng)
        # All samples should be exactly 0.5 (mirror only field)
        assert np.allclose(samples, 0.5)

    def test_custom_field_share_variance_zero(self):
        """Custom field (counts=None): no share variance → S variance comes only from cells."""
        archetypes = ["X", "A", "B"]
        winrates = {
            ("X", "A"): (60, 100),
            ("X", "B"): (60, 100),
            ("A", "X"): (40, 100),
            ("A", "B"): (50, 100),
            ("B", "X"): (40, 100),
            ("B", "A"): (50, 100),
        }
        matrix = _simple_matrix(archetypes, winrates)
        # Custom field: point shares, no Dirichlet
        custom_field = _custom_field({"A": 0.5, "B": 0.5})
        assert custom_field.counts is None  # confirm point shares path

        rng_custom = np.random.default_rng(SEED)
        samples_custom = _sample_S(matrix, custom_field, "X", n_draws=_TEST_DRAWS, rng=rng_custom)

        # Build a global field with counts → higher variance due to Dirichlet
        global_field = FieldDistribution(
            shares={"A": 0.5, "B": 0.5},
            field_source="global",
            counts={"A": 5, "B": 5},  # low counts → high Dirichlet variance
            no_data=frozenset(),
            warnings=(),
        )
        rng_global = np.random.default_rng(SEED)
        samples_global = _sample_S(matrix, global_field, "X", n_draws=_TEST_DRAWS, rng=rng_global)

        # Custom should have lower variance than low-count global
        assert samples_custom.var() < samples_global.var()

    def test_no_data_imputation_no_error(self):
        """A no-data opponent is imputed without error; NaN must not appear."""
        archetypes = ["X", "A", "B"]
        # Only X vs A has data; X vs B is missing (n=0 cell)
        winrates = {
            ("X", "A"): (60, 100),
            ("A", "X"): (40, 100),
            ("A", "B"): (50, 100),
            ("B", "A"): (50, 100),
            # X vs B absent → n=0 cell
        }
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 0.5, "B": 0.5})

        rng = np.random.default_rng(SEED)
        samples = _sample_S(matrix, field, "X", n_draws=_TEST_DRAWS, rng=rng)
        assert not np.any(np.isnan(samples))
        assert not np.any(np.isinf(samples))

    def test_robust_lowers_s_mean_vs_default(self):
        """robust=True uses worst observed WR for no-data → lower S_mean than default."""
        # X vs A=70%, X vs B=40% (worst), X vs C=no data
        archetypes = ["X", "A", "B", "C"]
        winrates = {
            ("X", "A"): (70, 100),
            ("X", "B"): (40, 100),
            ("A", "X"): (30, 100), ("A", "B"): (50, 100), ("A", "C"): (50, 100),
            ("B", "X"): (60, 100), ("B", "A"): (50, 100), ("B", "C"): (50, 100),
            ("C", "A"): (50, 100), ("C", "B"): (50, 100),
            # X vs C absent
        }
        matrix = _simple_matrix(archetypes, winrates)
        # Give C a non-trivial share so imputation matters
        field = _custom_field({"A": 0.4, "B": 0.3, "C": 0.3})

        rng_default = np.random.default_rng(SEED)
        samples_default = _sample_S(
            matrix, field, "X", n_draws=_TEST_DRAWS, rng=rng_default, robust=False
        )

        rng_robust = np.random.default_rng(SEED)
        samples_robust = _sample_S(
            matrix, field, "X", n_draws=_TEST_DRAWS, rng=rng_robust, robust=True
        )

        # robust imputes worst WR=0.40; default imputes mean WR=(0.70+0.40)/2=0.55
        # So robust should give a lower S mean
        assert samples_robust.mean() < samples_default.mean()

    def test_include_mirror_false_renormalizes(self):
        """include_mirror=False zeros mirror column and renormalizes W."""
        # 2-archetype field: X (self) + A
        archetypes = ["X", "A"]
        winrates = {
            ("X", "A"): (60, 100),
            ("A", "X"): (40, 100),
        }
        matrix = _simple_matrix(archetypes, winrates, mirror_n={"X": 50})
        # Field gives X 50% share, A 50% share
        field = _custom_field({"X": 0.5, "A": 0.5})

        rng_with = np.random.default_rng(SEED)
        s_with = _sample_S(
            matrix, field, "X", n_draws=_TEST_DRAWS, rng=rng_with, include_mirror=True
        )

        rng_without = np.random.default_rng(SEED)
        s_without = _sample_S(
            matrix, field, "X", n_draws=_TEST_DRAWS, rng=rng_without, include_mirror=False
        )

        # With mirror: S ≈ 0.5*0.5 + 0.5*0.60 = 0.55
        # Without mirror (X column zeroed, renorm → full weight on A): S ≈ 0.60
        assert s_with.mean() < s_without.mean()
        assert abs(s_without.mean() - 0.60) < _TOL_MEAN

    def test_no_data_listed_in_row_winrate_inputs(self):
        """_row_winrate_inputs correctly identifies no-data archetypes."""
        archetypes = ["X", "A", "B", "C"]
        winrates = {
            ("X", "A"): (60, 100),  # has data
            ("X", "B"): (0, 0),      # n=0 → no data
            # X vs C completely absent from matrix
            ("A", "X"): (40, 100), ("A", "B"): (50, 100), ("A", "C"): (50, 100),
            ("B", "X"): (50, 100), ("B", "A"): (50, 100), ("B", "C"): (50, 100),
            ("C", "X"): (50, 100), ("C", "A"): (50, 100), ("C", "B"): (50, 100),
        }
        matrix = _simple_matrix(archetypes, winrates)
        field_archetypes = ["A", "B", "C"]
        wins, n, is_mirror, no_data = _row_winrate_inputs(matrix, "X", field_archetypes)

        assert "B" in no_data, "n=0 cell should be in no_data"
        assert "A" not in no_data, "n>0 cell should not be in no_data"


# ===========================================================================
# TestPositioningResult
# ===========================================================================


class TestPositioningResult:
    """Unit 2 — PositioningResult invariants."""

    def test_field_source_always_set(self):
        matrix = _worked_matrix()
        field = _worked_field()
        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert result.field_source is not None
        assert result.field_source == field.field_source

    def test_ci_brackets_mean(self):
        matrix = _worked_matrix()
        field = _worked_field()
        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert result.s_ci[0] <= result.s_mean <= result.s_ci[1]

    def test_s_samples_none_by_default(self):
        matrix = _worked_matrix()
        field = _worked_field()
        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert result.s_samples is None

    def test_s_samples_retained_when_keep_samples(self):
        matrix = _worked_matrix()
        field = _worked_field()
        result = positioning_score(
            matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED, keep_samples=True
        )
        assert result.s_samples is not None
        assert result.s_samples.shape == (_TEST_DRAWS,)

    def test_n_draws_recorded(self):
        matrix = _worked_matrix()
        field = _worked_field()
        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert result.n_draws == _TEST_DRAWS

    def test_warnings_is_tuple(self):
        matrix = _worked_matrix()
        field = _worked_field()
        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert isinstance(result.warnings, tuple)

    def test_imputed_is_frozenset(self):
        matrix = _worked_matrix()
        field = _worked_field()
        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert isinstance(result.imputed, frozenset)


# ===========================================================================
# TestPositioningScore
# ===========================================================================


class TestPositioningScore:
    """Unit 3 — positioning_score arithmetic and the worked example."""

    def test_worked_example_deck_x_s_approx(self):
        """Deck X: S ≈ 0.530 on the brief's worked field."""
        matrix = _worked_matrix()
        field = _worked_field()
        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        # Custom field → point shares → no Dirichlet variance; tight CI around 0.530
        assert abs(result.s_mean - 0.530) < _TOL_MEAN, (
            f"Expected S≈0.530 for Deck X, got {result.s_mean:.4f}"
        )

    def test_worked_example_deck_y_s_approx(self):
        """Deck Y: S ≈ 0.515 on the brief's worked field."""
        matrix = _worked_matrix()
        field = _worked_field()
        result = positioning_score(matrix, field, "Y", n_draws=_TEST_DRAWS, seed=SEED)
        assert abs(result.s_mean - 0.515) < _TOL_MEAN, (
            f"Expected S≈0.515 for Deck Y, got {result.s_mean:.4f}"
        )

    def test_worked_example_x_higher_s_than_y(self):
        """Deck X has higher S (better call) than Deck Y on the A:50/B:30/C:20 field."""
        matrix = _worked_matrix()
        field = _worked_field()
        x = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        y = positioning_score(matrix, field, "Y", n_draws=_TEST_DRAWS, seed=SEED + 1)
        assert x.s_mean > y.s_mean, (
            f"Deck X should be the better call (S_X={x.s_mean:.4f} > S_Y={y.s_mean:.4f})"
        )

    def test_worked_example_y_higher_u_bar_than_x(self):
        """Deck Y has higher Ū (better overall deck) than Deck X."""
        matrix = _worked_matrix()
        field = _worked_field()
        x = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        y = positioning_score(matrix, field, "Y", n_draws=_TEST_DRAWS, seed=SEED + 1)
        assert y.u_bar > x.u_bar, (
            f"Deck Y should be the better deck (Ū_Y={y.u_bar:.4f} > Ū_X={x.u_bar:.4f})"
        )

    def test_u_bar_approx_worked_example(self):
        """Deck X: Ū ≈ (0.62+0.60+0.20)/3 ≈ 0.473."""
        matrix = _worked_matrix()
        field = _worked_field()
        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        expected_u_bar = (0.62 + 0.60 + 0.20) / 3.0  # ≈ 0.4733
        assert abs(result.u_bar - expected_u_bar) < 0.01

    def test_determinism_with_seed(self):
        """Same seed → identical results."""
        matrix = _worked_matrix()
        field = _worked_field()
        r1 = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        r2 = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert r1.s_mean == r2.s_mean
        assert r1.s_ci == r2.s_ci

    def test_different_seeds_differ(self):
        """Different seeds → (very likely) different results."""
        matrix = _worked_matrix()
        field = _worked_field()
        r1 = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        r2 = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED + 99)
        # Extremely unlikely to be exactly equal with different seeds
        assert r1.s_mean != r2.s_mean

    def test_no_data_opponent_listed_in_imputed(self):
        """Archetypes with no matchup data are listed in result.imputed."""
        # X has data vs A but not vs B
        archetypes = ["X", "A", "B"]
        winrates = {
            ("X", "A"): (60, 100),
            ("A", "X"): (40, 100),
            ("A", "B"): (50, 100),
            ("B", "A"): (50, 100),
        }
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 0.5, "B": 0.5})
        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert "B" in result.imputed

    def test_dirichlet_shares_global_field(self):
        """Global field (counts!=None) → Dirichlet share sampling → wider CI than custom."""
        matrix = _worked_matrix()
        custom = _worked_field()  # counts=None

        # Global field with low counts → high Dirichlet variance
        global_field = FieldDistribution(
            shares={"A": 0.50, "B": 0.30, "C": 0.20},
            field_source="global",
            counts={"A": 4, "B": 3, "C": 2},
            no_data=frozenset(),
            warnings=(),
        )

        r_custom = positioning_score(matrix, custom, "X", n_draws=_TEST_DRAWS, seed=SEED)
        r_global = positioning_score(matrix, global_field, "X", n_draws=_TEST_DRAWS, seed=SEED)

        # Global has wider CI due to Dirichlet uncertainty
        ci_width_custom = r_custom.s_ci[1] - r_custom.s_ci[0]
        ci_width_global = r_global.s_ci[1] - r_global.s_ci[0]
        assert ci_width_global > ci_width_custom

    # ── Corpus-backed seam test ──────────────────────────────────────────────

    def test_corpus_seam_delver_vs_lands_field(self):
        """Integration: build_matrix from corpus, score Delver vs a custom field.

        Proves MatchupCell.wins/n feed the Beta sampler end-to-end.
        Delver wins 60% vs Lands in the corpus → S for Delver on a Lands-heavy
        field should be above 0.5.
        """
        matrix, con = _build_corpus_matrix()
        con.close()

        # Delver-dominant field: mostly Lands
        field = build_custom_field({"Lands": 0.6, "Reanimator": 0.2, "Show": 0.2})
        result = positioning_score(matrix, field, "Delver", n_draws=_TEST_DRAWS, seed=SEED)

        # Delver beats Lands 60% of the time; Lands is 60% of the field → S > 0.5
        assert result.s_mean > 0.5, (
            f"Delver on Lands-heavy field should be > 0.5, got {result.s_mean:.4f}"
        )
        assert result.field_source == "custom"

    def test_corpus_seam_global_field(self):
        """Integration: build_global_field from corpus → Dirichlet sampling path."""
        matrix, con = _build_corpus_matrix()
        field = build_global_field(con)
        con.close()

        result = positioning_score(matrix, field, "Delver", n_draws=_TEST_DRAWS, seed=SEED)
        assert result.field_source == "global"
        # Should be a valid probability
        assert 0.0 < result.s_mean < 1.0
        assert result.s_ci[0] <= result.s_mean <= result.s_ci[1]


# ===========================================================================
# TestRankDecks
# ===========================================================================


class TestRankDecks:
    """Unit 4 — rank_decks shared-field MC."""

    def test_p_best_sums_to_one(self):
        """Σ p_best ≈ 1.0."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(
            matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED
        )
        total = sum(ranking.p_best.values())
        assert abs(total - 1.0) < _TOL_PROB

    def test_best_call_deck_has_higher_p_best(self):
        """On the worked example, Deck X (better call) has higher p_best than Deck Y."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(
            matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED
        )
        assert ranking.p_best["X"] > ranking.p_best["Y"], (
            f"Deck X should have higher p_best: X={ranking.p_best['X']:.3f}, "
            f"Y={ranking.p_best['Y']:.3f}"
        )

    def test_decks_sorted_by_p_best(self):
        """Default sort is p_best descending."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(
            matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED
        )
        assert ranking.decks[0] == "X", "X (best call) should rank first"

    def test_pairwise_symmetry(self):
        """P(A>B) + P(B>A) ≈ 1.0 (ties are negligible in continuous MC)."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(
            matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED
        )
        p_xy = ranking.pairwise.get(("X", "Y"), 0.0)
        p_yx = ranking.pairwise.get(("Y", "X"), 0.0)
        assert abs(p_xy + p_yx - 1.0) < _TOL_PROB, (
            f"pairwise should be complementary: P(X>Y)={p_xy:.3f} + P(Y>X)={p_yx:.3f} ≈ 1"
        )

    def test_pairwise_all_pairs_present(self):
        """Every ordered pair (a, b) with a!=b is present."""
        matrix = _worked_matrix()
        field = _worked_field()
        candidates = ["X", "Y"]
        ranking = rank_decks(matrix, field, candidates, n_draws=_TEST_DRAWS, seed=SEED)
        for a in candidates:
            for b in candidates:
                if a != b:
                    assert (a, b) in ranking.pairwise

    def test_s_mean_ci_all_decks(self):
        """All candidates have s_mean and s_ci in the result."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(
            matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED
        )
        for deck in ["X", "Y"]:
            assert deck in ranking.s_mean
            assert deck in ranking.s_ci
            lo, hi = ranking.s_ci[deck]
            assert lo <= ranking.s_mean[deck] <= hi

    def test_risk_averse_can_reorder(self):
        """risk_averse=True may produce a different order to the default ranking."""
        # Build a setup where one deck has higher S_mean but more variance.
        # Use large disparity in opponent n to achieve this.
        archetypes = ["X", "Y", "A", "B"]
        winrates = {
            # X: high expected S but volatile (sparse n)
            ("X", "A"): (17, 20),  # 85% — sparse, high variance
            ("X", "B"): (3, 20),   # 15% — sparse, high variance
            # Y: moderate S, stable (dense n)
            ("Y", "A"): (60, 100),  # 60% — dense, lower variance
            ("Y", "B"): (55, 100),  # 55% — dense, lower variance
            ("A", "X"): (3, 20), ("A", "Y"): (40, 100), ("A", "B"): (50, 100),
            ("B", "X"): (17, 20), ("B", "Y"): (45, 100), ("B", "A"): (50, 100),
        }
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 0.5, "B": 0.5})

        ranking_default = rank_decks(matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED)
        ranking_risk = rank_decks(
            matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED, risk_averse=True
        )

        # Both results should be valid (decks present, p_best sums to 1)
        assert set(ranking_default.decks) == {"X", "Y"}
        assert set(ranking_risk.decks) == {"X", "Y"}
        total_risk = sum(ranking_risk.p_best.values())
        assert abs(total_risk - 1.0) < _TOL_PROB

    def test_empty_candidates_returns_empty_ranking(self):
        """Empty candidate list returns an empty DeckRanking without error."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(matrix, field, [], n_draws=_TEST_DRAWS, seed=SEED)
        assert ranking.decks == []
        assert ranking.p_best == {}

    def test_single_candidate_p_best_is_one(self):
        """With one candidate, p_best should be 1.0."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(matrix, field, ["X"], n_draws=_TEST_DRAWS, seed=SEED)
        assert abs(ranking.p_best["X"] - 1.0) < _TOL_PROB

    def test_field_source_propagated(self):
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED)
        assert ranking.field_source == field.field_source


# ===========================================================================
# TestDeltaVar
# ===========================================================================


class TestDeltaVar:
    """Unit 5 — delta_var_S sanity check."""

    def test_delta_var_in_ballpark_of_mc_variance(self):
        """delta_var_S should be in the same order of magnitude as the MC sample variance."""
        matrix = _worked_matrix()
        field = _worked_field()

        dv = delta_var_S(matrix, field, "X")

        result = positioning_score(
            matrix, field, "X", n_draws=20_000, seed=SEED, keep_samples=True
        )
        mc_var = float(result.s_samples.var())

        # delta-method is an approximation; check within 2 orders of magnitude
        # (not zero, not wildly off)
        assert dv > 0.0
        # For a custom field (point shares), delta_var_S uses point w_a — it's a lower
        # bound on true variance. Allow a generous factor.
        assert dv < mc_var * 100 and dv > mc_var / 100, (
            f"delta_var_S={dv:.6f} should be in ballpark of MC var={mc_var:.6f}"
        )

    def test_delta_var_zero_when_no_known_cells(self):
        """No known (n>0, non-mirror) cells → delta_var_S returns 0.0."""
        archetypes = ["X", "A"]
        winrates = {}  # no data at all
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 1.0})

        dv = delta_var_S(matrix, field, "X")
        assert dv == 0.0

    def test_delta_var_nonzero_with_known_cells(self):
        """With known cells, delta_var_S is positive."""
        matrix = _worked_matrix()
        field = _worked_field()
        dv = delta_var_S(matrix, field, "X")
        assert dv > 0.0

    def test_delta_var_decreases_with_larger_n(self):
        """More match data → lower variance (1/n term shrinks)."""
        archetypes = ["X", "A"]
        field = _custom_field({"A": 1.0})

        # Small n
        winrates_small = {("X", "A"): (60, 100), ("A", "X"): (40, 100)}
        matrix_small = _simple_matrix(archetypes, winrates_small)
        dv_small = delta_var_S(matrix_small, field, "X")

        # Large n
        winrates_large = {("X", "A"): (600, 1000), ("A", "X"): (400, 1000)}
        matrix_large = _simple_matrix(archetypes, winrates_large)
        dv_large = delta_var_S(matrix_large, field, "X")

        assert dv_large < dv_small
