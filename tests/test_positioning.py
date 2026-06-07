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

    def test_decks_sorted_by_risk_quantile(self):
        """Default sort is lower-quantile (risk-adjusted) descending, not p_best."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(
            matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED
        )
        # X has higher S mean/quantile than Y on the worked example
        assert ranking.decks[0] == "X", "X (better call) should rank first by lower-quantile"
        # Sort key is s_quantile, not p_best
        assert ranking.s_quantile["X"] >= ranking.s_quantile["Y"], (
            f"X should have higher or equal lower-quantile: "
            f"X={ranking.s_quantile['X']:.4f}, Y={ranking.s_quantile['Y']:.4f}"
        )

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

    def test_risk_averse_uses_lower_quantile(self):
        """risk_averse=True uses a more conservative quantile (0.05) than default (0.25)."""
        matrix = _worked_matrix()
        field = _worked_field()

        ranking_default = rank_decks(matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED)
        ranking_risk = rank_decks(
            matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED, risk_averse=True
        )

        # Both results should be valid (decks present, p_best sums to 1)
        assert set(ranking_default.decks) == {"X", "Y"}
        assert set(ranking_risk.decks) == {"X", "Y"}
        total_risk = sum(ranking_risk.p_best.values())
        assert abs(total_risk - 1.0) < _TOL_PROB

        # risk_averse=True uses q=0.05; default uses q=0.25
        assert ranking_default.quantile_level == 0.25
        assert ranking_risk.quantile_level == 0.05

        # risk_averse s_quantile ≤ default s_quantile (more conservative → lower floor)
        for deck in ["X", "Y"]:
            assert ranking_risk.s_quantile[deck] <= ranking_default.s_quantile[deck] + _TOL_MEAN, (
                f"{deck}: risk_averse quantile should be ≤ default quantile "
                f"(got risk={ranking_risk.s_quantile[deck]:.4f}, default={ranking_default.s_quantile[deck]:.4f})"
            )

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


# ===========================================================================
# Regression tests for peer-review bug fixes
# ===========================================================================


class TestRegressionPeerReviewFixes:
    """One regression test per finding from the cross-model peer review (2026-05-30)."""

    # --- Fix 1: No-data imputation centred on `center` ---

    def test_fix1_nodata_imputation_centered_on_mean(self):
        """Bug: a=(2c+0.5), b=(2(1-c)+0.5) → mean=(2c+0.5)/3, NOT c.
        Fix: concentration-only params a=strength*c, b=strength*(1-c) → mean=c.
        A row with known mean 0.8 must impute ≈0.8, not ≈0.70.

        Setup: field contains BOTH A (known, 80%) AND B (no data).  A is in the field
        so the known_mask fires; we weight A at ε so the S mean is dominated by the
        imputed B cell, and check that it is centred on 0.8, not ~0.70.
        """
        _TOL = 0.05  # 5 000 draws, generous tolerance

        # X vs A = 80% (known); X vs B = no data (imputed from A's mean)
        archetypes = ["X", "A", "B"]
        winrates = {
            ("X", "A"): (80, 100),  # known 80%
            ("A", "X"): (20, 100),
            ("A", "B"): (50, 100),
            ("B", "A"): (50, 100),
            # X vs B: no data → imputed from known mean=0.80
        }
        matrix = _simple_matrix(archetypes, winrates)
        # Give A a tiny share and B almost all the weight so S ≈ imputed(B)
        field = _custom_field({"A": 0.01, "B": 0.99})

        rng = np.random.default_rng(SEED)
        samples = _sample_S(matrix, field, "X", n_draws=10_000, rng=rng)
        # With B's weight at 0.99 and imputed from mean=0.80, S_mean should be ≈0.80
        assert abs(samples.mean() - 0.80) < _TOL, (
            f"Imputation should be centred on known mean 0.80, got {samples.mean():.4f}"
        )

    # --- Fix 2: rank_decks tie handling ---

    def test_fix2_rank_decks_exact_tie_splits_pbest_exactly(self):
        """NIT: old test used identical Beta inputs that still produce independent samples,
        so argmax ≈50/50 even without the fix — it didn't prove anything.

        Fix: monkeypatch _sample_S to return IDENTICAL arrays for both candidates so
        every draw is an exact tie.  The tie-credit logic must award each deck exactly 0.5.

        Without the fix (argmax → lowest index wins all ties) P(best) for index-0 candidate
        would be 1.0 and index-1 would be 0.0.  With the fix both get exactly 0.5.
        """
        import legacy_engine.advisory.positioning as _pos_mod

        n_draws = 200
        # Both X and Y return the SAME array (all draws are exact ties).
        _shared_samples = np.linspace(0.4, 0.6, n_draws)

        def _patched_sample_S(matrix, field, deck_archetype, *, n_draws, **kwargs):
            return _shared_samples.copy()

        archetypes = ["X", "Y", "A"]
        winrates = {
            ("X", "A"): (60, 100),
            ("Y", "A"): (60, 100),
            ("A", "X"): (40, 100),
            ("A", "Y"): (40, 100),
        }
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 1.0})

        original = _pos_mod._sample_S
        try:
            _pos_mod._sample_S = _patched_sample_S
            ranking = rank_decks(matrix, field, ["X", "Y"], n_draws=n_draws, seed=SEED)
        finally:
            _pos_mod._sample_S = original

        p_x = ranking.p_best["X"]
        p_y = ranking.p_best["Y"]

        # With exact ties every draw, the credit must be split exactly 50/50.
        assert abs(p_x - 0.5) < 1e-9, (
            f"Exact-tie: X must get P(best)=0.5 exactly; got {p_x}"
        )
        assert abs(p_y - 0.5) < 1e-9, (
            f"Exact-tie: Y must get P(best)=0.5 exactly; got {p_y}"
        )

    # --- Fix 3: include_mirror=False on mirror-only field → 0.5 + warning ---

    def test_fix3_include_mirror_false_mirror_only_field_returns_half(self):
        """Bug: zeroing all mirror columns → safe_sums=1 → S=0 (misleading).
        Fix: detect all-mirror case, warn via log.warning, return 0.5 (undefined view sentinel).
        """
        # Deck X in a field that is ONLY X (mirror-only)
        archetypes = ["X"]
        matrix = _simple_matrix(archetypes, {}, mirror_n={"X": 50})
        field = _custom_field({"X": 1.0})  # field is entirely X's mirror

        rng = np.random.default_rng(SEED)
        samples = _sample_S(
            matrix, field, "X", n_draws=100, rng=rng, include_mirror=False
        )
        # The fix returns 0.5 (not 0.0) when all columns are mirror columns
        assert abs(samples.mean() - 0.5) < 1e-9, (
            f"Mirror-only field with include_mirror=False should return S=0.5, got {samples.mean()}"
        )


# ===========================================================================
# TestDataCoverage
# ===========================================================================


class TestDataCoverage:
    """Tests for data_coverage in PositioningResult and DeckRanking."""

    def test_full_coverage_all_cells_measured(self):
        """A deck with n>=30 cells against all field opponents → data_coverage=1.0."""
        # All cells have n=60 >= 30 (display=True)
        archetypes = ["X", "A", "B", "C"]
        winrates = {
            ("X", "A"): (35, 60),
            ("X", "B"): (30, 60),
            ("X", "C"): (32, 60),
            ("A", "X"): (25, 60), ("A", "B"): (30, 60), ("A", "C"): (30, 60),
            ("B", "X"): (30, 60), ("B", "A"): (30, 60), ("B", "C"): (30, 60),
            ("C", "X"): (28, 60), ("C", "A"): (30, 60), ("C", "B"): (30, 60),
        }
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 0.4, "B": 0.35, "C": 0.25})

        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert result.data_coverage == pytest.approx(1.0, abs=1e-9), (
            f"All-measured deck should have data_coverage=1.0, got {result.data_coverage}"
        )

    def test_zero_coverage_all_cells_sparse(self):
        """A deck with n=0 against all field opponents → data_coverage=0.0."""
        archetypes = ["X", "A", "B"]
        # No data at all for X vs opponents
        winrates = {
            ("A", "B"): (30, 60),
            ("B", "A"): (30, 60),
        }
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 0.6, "B": 0.4})

        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert result.data_coverage == pytest.approx(0.0, abs=1e-9), (
            f"All-sparse deck should have data_coverage=0.0, got {result.data_coverage}"
        )

    def test_partial_coverage_share_mass_weighted(self):
        """Partial coverage is the share-mass fraction of measured opponents."""
        # Field: A=0.6 (measured n=60), B=0.4 (sparse n=0)
        # Expected coverage = 0.6 / (0.6 + 0.4) = 0.6
        archetypes = ["X", "A", "B"]
        winrates = {
            ("X", "A"): (35, 60),   # n=60 → display=True → measured
            # X vs B: no data (n=0)
            ("A", "X"): (25, 60), ("A", "B"): (30, 60),
            ("B", "A"): (30, 60),
        }
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 0.6, "B": 0.4})

        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert result.data_coverage == pytest.approx(0.6, abs=1e-9), (
            f"Expected data_coverage=0.6, got {result.data_coverage}"
        )

    def test_sparse_cell_n_lt_30_not_counted_as_measured(self):
        """A cell with n=10 (display=False) does not count toward coverage."""
        # X vs A: n=10 → display=False (speculative), not measured
        # X vs B: n=60 → display=True, measured
        # Field: A=0.5, B=0.5 → coverage = 0.5
        archetypes = ["X", "A", "B"]
        winrates = {
            ("X", "A"): (5, 10),    # n=10 < 30 → display=False
            ("X", "B"): (30, 60),   # n=60 >= 30 → display=True
            ("A", "X"): (5, 10), ("A", "B"): (30, 60),
            ("B", "X"): (30, 60), ("B", "A"): (30, 60),
        }
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 0.5, "B": 0.5})

        result = positioning_score(matrix, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        # A has n=10 (display=False), B has n=60 (display=True)
        assert result.data_coverage == pytest.approx(0.5, abs=1e-9), (
            f"Cell n<30 should not count as measured; expected coverage=0.5, got {result.data_coverage}"
        )

    def test_rank_decks_data_coverage_present(self):
        """DeckRanking carries data_coverage dict for all candidates."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED)
        assert "X" in ranking.data_coverage
        assert "Y" in ranking.data_coverage
        for v in ranking.data_coverage.values():
            assert 0.0 <= v <= 1.0

    def test_min_coverage_flags_low_data_deck(self):
        """Deck with data_coverage below min_coverage appears in low_coverage set."""
        # X vs A: n=60 (measured), X vs B: n=0 (sparse)
        # Field: A=0.6, B=0.4 → coverage(X)=0.6; coverage(Y)=1.0 (all measured)
        archetypes = ["X", "Y", "A", "B"]
        winrates = {
            ("X", "A"): (35, 60),                # measured
            # X vs B: no data
            ("Y", "A"): (30, 60), ("Y", "B"): (30, 60),  # both measured
            ("A", "X"): (25, 60), ("A", "Y"): (30, 60), ("A", "B"): (30, 60),
            ("B", "Y"): (30, 60), ("B", "A"): (30, 60),
        }
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 0.6, "B": 0.4})

        ranking = rank_decks(
            matrix, field, ["X", "Y"],
            n_draws=_TEST_DRAWS, seed=SEED,
            min_coverage=0.7,
        )
        # X has coverage ~0.6 → flagged; Y has coverage 1.0 → not flagged
        assert "X" in ranking.low_coverage, (
            f"X (coverage≈0.6) should be in low_coverage when min_coverage=0.7"
        )
        assert "Y" not in ranking.low_coverage, (
            f"Y (coverage=1.0) should not be in low_coverage"
        )
        # X is NOT dropped — still in decks
        assert "X" in ranking.decks

    def test_min_coverage_zero_no_flagging(self):
        """min_coverage=0.0 (default) never flags anything."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED)
        assert ranking.low_coverage == set()


# ===========================================================================
# TestRiskAdjustedRanking
# ===========================================================================


class TestRiskAdjustedRanking:
    """Tests for the risk-adjusted lower-quantile headline ranking."""

    def test_well_measured_deck_outranks_sparse_spiker(self):
        """A well-measured ~52% deck outranks a sparse high-variance deck by default ranking.

        This is the Death-&-Taxes artifact: a deck with few measured cells has
        high-variance S — imputed from mean ~0.5, giving a wide Beta that spikes
        to the max across many argmax draws, inflating P(best).  The risk-adjusted
        lower-quantile ranking (q=0.25) penalises this: the sparse deck's lower
        tail is pulled down by its variance, even if its mean is similar or higher.

        Setup:
          W (well-measured): n=60 against A, B, C; ~52% WR → tight posterior near 0.52.
          SP (sparse):       only 1 measured cell (n=10 vs A, 50%), rest n=0 → imputed
                             from ~0.5 with wide Beta (NODATA_STRENGTH=2.0).
        The wide imputation Beta on SP gives high variance and long tails in both
        directions; the lower-quantile floor is well below W's tight ~0.52.
        """
        archetypes = ["W", "SP", "A", "B", "C"]
        winrates = {
            # W: fully measured, tight 52% posterior
            ("W", "A"): (32, 60),   # 53%
            ("W", "B"): (31, 60),   # 52%
            ("W", "C"): (31, 60),   # 52%
            # SP: only one thin cell; everything else imputed from ~50% center
            ("SP", "A"): (5, 10),   # 50% but n=10 (speculative, display=False)
            # SP vs B, SP vs C: completely absent → n=0
            # Opponent rows
            ("A", "W"): (28, 60), ("A", "SP"): (5, 10), ("A", "B"): (30, 60), ("A", "C"): (30, 60),
            ("B", "W"): (29, 60), ("B", "A"): (30, 60), ("B", "C"): (30, 60),
            ("C", "W"): (29, 60), ("C", "A"): (30, 60), ("C", "B"): (30, 60),
        }
        matrix = _simple_matrix(archetypes, winrates)
        field = _custom_field({"A": 0.4, "B": 0.3, "C": 0.3})

        ranking = rank_decks(
            matrix, field, ["W", "SP"], n_draws=10_000, seed=SEED
        )

        # Under the default risk-adjusted ranking (q=0.25):
        # W's tight posterior keeps its lower tail near its mean (~0.52)
        # SP's wide imputed posterior has a lower tail well below 0.52
        assert ranking.decks[0] == "W", (
            f"Well-measured W should outrank sparse-spiker SP; "
            f"ranking={ranking.decks}, "
            f"q(W)={ranking.s_quantile['W']:.4f}, q(SP)={ranking.s_quantile['SP']:.4f}"
        )
        assert ranking.s_quantile["W"] >= ranking.s_quantile["SP"], (
            f"W lower-quantile should be >= SP's: W={ranking.s_quantile['W']:.4f}, "
            f"SP={ranking.s_quantile['SP']:.4f}"
        )

    def test_p_best_still_present_as_secondary(self):
        """p_best is still computed and present in the ranking, even though it's not the sort key."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED)

        assert "X" in ranking.p_best
        assert "Y" in ranking.p_best
        total = sum(ranking.p_best.values())
        assert abs(total - 1.0) < _TOL_PROB, (
            f"p_best should still sum to 1.0 as a secondary field: sum={total:.4f}"
        )

    def test_s_quantile_present_for_all_decks(self):
        """s_quantile dict is populated for every candidate."""
        matrix = _worked_matrix()
        field = _worked_field()
        ranking = rank_decks(matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED)

        assert "X" in ranking.s_quantile
        assert "Y" in ranking.s_quantile
        assert ranking.quantile_level == 0.25  # default

    def test_ranking_determinism_with_seed(self):
        """Same seed → identical DeckRanking results."""
        matrix = _worked_matrix()
        field = _worked_field()
        r1 = rank_decks(matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED)
        r2 = rank_decks(matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED)
        assert r1.decks == r2.decks
        assert r1.s_quantile == r2.s_quantile
        assert r1.p_best == r2.p_best

    def test_custom_risk_quantile(self):
        """risk_quantile=0.10 sets quantile_level correctly and s_quantile ≤ q=0.25."""
        matrix = _worked_matrix()
        field = _worked_field()
        r_default = rank_decks(matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED)
        r_custom = rank_decks(
            matrix, field, ["X", "Y"], n_draws=_TEST_DRAWS, seed=SEED, risk_quantile=0.10
        )
        assert r_custom.quantile_level == 0.10
        # Lower quantile → more conservative floor
        for deck in ["X", "Y"]:
            assert r_custom.s_quantile[deck] <= r_default.s_quantile[deck] + _TOL_MEAN


# ---------------------------------------------------------------------------
# Coverage-aware positioning — epic-advisory-output-honesty-positioning-coverage
# ---------------------------------------------------------------------------

from legacy_engine.advisory.positioning import (  # noqa: E402
    _COVERAGE_RESTRICT_THRESHOLD,
    _is_covered_cell,
    covered_field_archetypes,
)


class TestCoveredPredicate:
    """_is_covered_cell + covered_field_archetypes — the coverage SSOT."""

    def test_mirror_is_covered(self):
        m = _simple_matrix(["X", "A"], {("X", "A"): (50, 100)}, mirror_n={"X": 0})
        assert _is_covered_cell(m, "X", "X") is True  # mirror, even at mirror_n=0

    def test_displayed_cell_is_covered(self):
        m = _simple_matrix(["X", "A"], {("X", "A"): (50, 100)})
        assert _is_covered_cell(m, "X", "A") is True

    def test_thin_cell_not_covered(self):
        m = _simple_matrix(["X", "A"], {("X", "A"): (5, 10)})  # n<30 → not display
        assert _is_covered_cell(m, "X", "A") is False

    def test_absent_cell_not_covered(self):
        m = _simple_matrix(["X", "A", "B"], {("X", "A"): (50, 100)})  # X vs B absent (n=0)
        assert _is_covered_cell(m, "X", "B") is False

    def test_covered_set_includes_mirror_and_displayed(self):
        m = _simple_matrix(["X", "A", "B"], {("X", "A"): (50, 100)})
        field = _custom_field({"X": 0.2, "A": 0.5, "B": 0.3})
        covered = covered_field_archetypes(m, field, "X")
        assert covered == frozenset({"X", "A"})  # mirror X + displayed A; B uncovered


class TestPositioningCoverageRestrict:
    """positioning_score restrict-to-covered behavior across coverage bands."""

    def test_full_coverage_is_byte_identical(self):
        # coverage==1.0 → restrict is a no-op; restrict_to_covered True vs False match exactly.
        m = _simple_matrix(["X", "A", "B"], {("X", "A"): (60, 100), ("X", "B"): (40, 100)})
        field = _custom_field({"A": 0.6, "B": 0.4})
        on = positioning_score(m, field, "X", n_draws=_TEST_DRAWS, seed=SEED, restrict_to_covered=True)
        off = positioning_score(m, field, "X", n_draws=_TEST_DRAWS, seed=SEED, restrict_to_covered=False)
        assert on.restricted is False
        assert on.s_mean == off.s_mean
        assert on.s_ci == off.s_ci
        assert pytest.approx(on.data_coverage) == 1.0

    def test_low_coverage_restricts(self):
        # X covered vs A (share .5), uncovered vs B (share .5) → coverage 0.5 < 0.85 → restrict.
        m = _simple_matrix(["X", "A", "B"], {("X", "A"): (70, 100)})
        field = _custom_field({"A": 0.5, "B": 0.5})
        r = positioning_score(m, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert r.restricted is True
        assert pytest.approx(r.data_coverage) == 0.5
        assert pytest.approx(r.excluded_share) == 0.5
        assert r.excluded_archetypes == frozenset({"B"})
        # S now scored on {A:1.0} → ~0.70 (the measured A cell), not pulled toward 0.5 by B.
        assert r.s_mean == pytest.approx(0.70, abs=_TOL_MEAN)

    def test_threshold_respected(self):
        # coverage 0.9 ≥ 0.85 → NOT restricted (trivial uncovered tail left alone).
        m = _simple_matrix(["X", "A", "B"], {("X", "A"): (60, 100)})
        field = _custom_field({"A": 0.9, "B": 0.1})
        r = positioning_score(m, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert r.restricted is False
        assert pytest.approx(r.data_coverage) == 0.9

    def test_zero_coverage_not_computable(self):
        # X has no displayed non-mirror cell → S not computable, NaN, no exception.
        m = _simple_matrix(["X", "A", "B"], {("X", "A"): (5, 10)})  # thin only
        field = _custom_field({"A": 0.5, "B": 0.5})
        r = positioning_score(m, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        assert r.s_computable is False
        assert np.isnan(r.s_mean)
        assert any("not computable" in w for w in r.warnings)

    def test_restricted_suppresses_thin_row_warning(self):
        m = _simple_matrix(["X", "A", "B"], {("X", "A"): (70, 100)})
        field = _custom_field({"A": 0.5, "B": 0.5})
        r = positioning_score(m, field, "X", n_draws=_TEST_DRAWS, seed=SEED)
        # The "dominated by the imputation prior" framing must NOT appear once restricted.
        assert not any("dominated by the imputation prior" in w for w in r.warnings)
        assert any("restricted S to the covered sub-field" in w for w in r.warnings)

    def test_restrict_can_be_disabled(self):
        m = _simple_matrix(["X", "A", "B"], {("X", "A"): (70, 100)})
        field = _custom_field({"A": 0.5, "B": 0.5})
        r = positioning_score(m, field, "X", n_draws=_TEST_DRAWS, seed=SEED, restrict_to_covered=False)
        assert r.restricted is False
        assert r.s_computable is True  # falls back to full-field imputed S
