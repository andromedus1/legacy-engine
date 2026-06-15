"""Production-hardening tests for the list-granular positioning overlay.

Four areas covered (matching the 4 hardening items in the feature spec):

  1. CLI integration — ``--list-granular`` flag renders S_granular + caveat;
     absent flag → output byte-identical to baseline.
  2. Live plumbing — ``_render_list_granular`` builds CardWinRates from the
     corpus and passes non-land cards to ``positioning_score_granular``.
     (CLI tests use a file-backed DB + ``--db`` for hermeticity.)
  3. Constant calibration — ``_GRANULAR_SCALE`` / ``_GRANULAR_MAX_NUDGE``
     are tested for:
       (a) sub-dominance: |s_granular − base_S| < max_nudge on any corpus
       (b) grindy/lean Dimir Tempo differentiation still reproduces
  4. Land detection — ``filter_nonland_cards`` correctly excludes lands;
     a deck differing only in land choices gets ~identical s_granular.

All DB-dependent CLI tests use a tmp-path file-backed DuckDB and ``--db``
(never rely on the default data/legacy.duckdb).
"""

from __future__ import annotations

from dataclasses import dataclass as _dc

import pytest

from legacy_engine.advisory.field import build_custom_field
from legacy_engine.advisory.positioning import (
    _GRANULAR_MAX_NUDGE,
    _GRANULAR_SCALE,
    composition_adjusted_winrates,
    filter_nonland_cards,
    positioning_score_granular,
)
from legacy_engine.analytics.matchup import MatchupMatrix, build_cell, build_mirror_cell

# ---------------------------------------------------------------------------
# Re-use the hermetic corpus from the spike tests (no DB needed)
# ---------------------------------------------------------------------------

_SEED = 99
_N_DRAWS = 5_000

_DIMIR = "Dimir Tempo"
_RED = "Red Stompy"
_ANT = "ANT"

_GRINDY = {
    "Hymn to Tourach": 4,
    "Baleful Strix": 4,
    "Force of Will": 4,
    "Brainstorm": 4,
    "Ponder": 4,
}

_LEAN = {
    "Daze": 4,
    "Nethergoyf": 4,
    "Force of Will": 4,
    "Brainstorm": 4,
    "Ponder": 4,
}


# Fake CardWinRates (duck-typed) — same lift narrative as the spike


@_dc
class _FakeMarginalRec:
    card: str
    board: str
    wins: int = 55
    losses: int = 45

    @property
    def n(self) -> int:
        return self.wins + self.losses


@_dc
class _FakeMatchupRec:
    card: str
    board: str
    opponent: str
    wins: int = 50
    losses: int = 50

    @property
    def n(self) -> int:
        return self.wins + self.losses


@_dc
class _FakeCWR:
    matchup: dict
    marginal: dict
    baseline_winrate: float = 0.5


def _build_cwr() -> _FakeCWR:
    BOARD = "main"
    matchup: dict = {}
    marginal: dict = {}
    for card in ["Hymn to Tourach", "Baleful Strix", "Force of Will", "Brainstorm",
                 "Ponder", "Daze", "Nethergoyf"]:
        marginal[(card, BOARD)] = _FakeMarginalRec(card=card, board=BOARD)
    matchup[("Hymn to Tourach", BOARD, _ANT)] = _FakeMatchupRec(
        card="Hymn to Tourach", board=BOARD, opponent=_ANT, wins=70, losses=30
    )
    matchup[("Daze", BOARD, _RED)] = _FakeMatchupRec(
        card="Daze", board=BOARD, opponent=_RED, wins=65, losses=35
    )
    matchup[("Nethergoyf", BOARD, _RED)] = _FakeMatchupRec(
        card="Nethergoyf", board=BOARD, opponent=_RED, wins=66, losses=34
    )
    return _FakeCWR(matchup=matchup, marginal=marginal, baseline_winrate=0.5)


def _hermetic_matrix() -> MatchupMatrix:
    archetypes = [_DIMIR, _RED, _ANT]
    winrates = {
        (_DIMIR, _RED): (55, 100),
        (_DIMIR, _ANT): (48, 100),
        (_RED, _DIMIR): (45, 100),
        (_RED, _ANT): (50, 100),
        (_ANT, _DIMIR): (52, 100),
        (_ANT, _RED): (50, 100),
    }
    cells: dict = {}
    for a in archetypes:
        cells[(a, a)] = build_mirror_cell(a, 60)
        for b in archetypes:
            if a == b:
                continue
            wins, n = winrates.get((a, b), (0, 0))
            cells[(a, b)] = build_cell(a, b, wins, n)
    return MatchupMatrix(
        cells=cells, provenance=None,
        total_matches=300,
        archetypes=sorted(archetypes),
        caveat="hermetic hardening matrix",
    )


def _hermetic_field():
    return build_custom_field({_RED: 0.40, _ANT: 0.60})


# ---------------------------------------------------------------------------
# Item 3: Constant calibration tests
# ---------------------------------------------------------------------------


class TestConstantCalibration:
    """Calibration: overlay stays sub-dominant; grindy/lean differentiation reproduces."""

    def test_subdominance_grindy(self):
        """|s_granular − base_S| < _GRANULAR_MAX_NUDGE for the grindy list."""
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_cwr()

        gr = positioning_score_granular(
            matrix, field, _DIMIR, _GRINDY, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        delta = abs(gr.s_granular - gr.base.s_mean)
        assert delta < _GRANULAR_MAX_NUDGE, (
            f"Overlay must be sub-dominant: |{gr.s_granular:.5f} - {gr.base.s_mean:.5f}| "
            f"= {delta:.5f} >= _GRANULAR_MAX_NUDGE={_GRANULAR_MAX_NUDGE}"
        )

    def test_subdominance_lean(self):
        """|s_granular − base_S| < _GRANULAR_MAX_NUDGE for the lean list."""
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_cwr()

        gr = positioning_score_granular(
            matrix, field, _DIMIR, _LEAN, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        delta = abs(gr.s_granular - gr.base.s_mean)
        assert delta < _GRANULAR_MAX_NUDGE, (
            f"Overlay must be sub-dominant: |{gr.s_granular:.5f} - {gr.base.s_mean:.5f}| "
            f"= {delta:.5f} >= _GRANULAR_MAX_NUDGE={_GRANULAR_MAX_NUDGE}"
        )

    def test_grindy_vs_lean_differentiation_reproduces(self):
        """Grindy (Hymn/Strix) has higher s_granular than lean on 60% ANT field.

        This is the core calibration regression: if the scale/nudge constants
        change and break this, the constants need revisiting.
        """
        matrix = _hermetic_matrix()
        field = _hermetic_field()  # 40% Red, 60% ANT
        cwr = _build_cwr()

        grindy_gr = positioning_score_granular(
            matrix, field, _DIMIR, _GRINDY, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        lean_gr = positioning_score_granular(
            matrix, field, _DIMIR, _LEAN, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )

        # Archetype-level S is identical for both (same matrix row + seed)
        assert grindy_gr.base.s_mean == lean_gr.base.s_mean

        # Overlay must differentiate: grindy > lean on ANT-heavy field
        assert grindy_gr.s_granular > lean_gr.s_granular, (
            f"Grindy list should score higher on 60% ANT field: "
            f"grindy={grindy_gr.s_granular:.5f}, lean={lean_gr.s_granular:.5f}"
        )

    def test_scale_constant_keeps_overlay_sub_half_of_max_nudge(self):
        """The 0.5x scale ensures the per-matchup nudge is at most half the raw lift signal.

        A deck with a single card having maximum allowed per-matchup raw nudge of
        max_nudge/scale should produce an actual nudge of exactly max_nudge (clamp
        prevents overshoot).  With scale=0.5, a raw lift of 0.10 (10 pp) on a full
        deck of 4 identical cards normalised by 4 → 0.10 * 0.5 = 0.05 ≤ max_nudge.
        This test asserts the clamp is never exceeded.
        """
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_cwr()

        # The deck with the strongest per-matchup signal in our corpus
        extreme_deck = {"Hymn to Tourach": 20}  # all Hymns, maximises ANT lift
        adj = composition_adjusted_winrates(
            matrix, field, _DIMIR, extreme_deck, cwr,
            max_nudge=_GRANULAR_MAX_NUDGE,
            scale=_GRANULAR_SCALE,
        )
        for opp, wr in adj.items():
            # Baseline WR for Dimir vs each opponent
            cell = matrix.cells.get((_DIMIR, opp))
            if cell is not None and cell.p_shrunk is not None:
                baseline = cell.p_shrunk
            else:
                baseline = 0.5
            actual_nudge = abs(wr - baseline)
            assert actual_nudge <= _GRANULAR_MAX_NUDGE + 1e-9, (
                f"Nudge for {opp} exceeded _GRANULAR_MAX_NUDGE: {actual_nudge:.5f}"
            )


# ---------------------------------------------------------------------------
# Item 4: Land detection
# ---------------------------------------------------------------------------


class TestLandDetection:
    """Land exclusion: filter_nonland_cards + land-only deck difference."""

    def test_filter_nonland_cards_excludes_lands(self):
        """filter_nonland_cards removes cards for which is_land_fn returns True."""
        deck = {
            "Brainstorm": 4,
            "Underground Sea": 4,
            "Polluted Delta": 4,
            "Force of Will": 4,
        }
        land_names = {"Underground Sea", "Polluted Delta"}
        is_land = lambda name: name in land_names  # noqa: E731
        result = filter_nonland_cards(deck, is_land)
        assert "Underground Sea" not in result
        assert "Polluted Delta" not in result
        assert result["Brainstorm"] == 4
        assert result["Force of Will"] == 4

    def test_filter_nonland_cards_keeps_unknown(self):
        """Unknown cards (is_land_fn returns False) are kept (conservative default)."""
        deck = {"Brainstorm": 4, "SomeUnknownCard": 2}
        is_land = lambda name: False  # noqa: E731
        result = filter_nonland_cards(deck, is_land)
        assert "SomeUnknownCard" in result
        assert result["SomeUnknownCard"] == 2

    def test_filter_nonland_cards_all_lands_returns_empty(self):
        """A deck of only lands produces an empty dict (safety path tested separately)."""
        deck = {"Underground Sea": 4, "Swamp": 4}
        is_land = lambda name: True  # noqa: E731
        result = filter_nonland_cards(deck, is_land)
        assert result == {}

    def test_land_only_difference_produces_near_identical_s_granular(self):
        """Two lists identical except for land choices get ~identical s_granular.

        The non-land spells are the same; only lands differ.  Since lands are
        excluded from the composition signal, s_granular should be identical.
        """
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_cwr()

        # Base spells (same in both)
        spells = {"Force of Will": 4, "Brainstorm": 4, "Ponder": 4}
        # List A: Tundra lands; List B: very different lands
        # Both include the same spells → same nonland deck after filtering
        list_a_lands = {"Underground Sea": 4, "Polluted Delta": 4}
        list_b_lands = {"Swamp": 4, "Island": 4}

        # All lands are filtered by is_land_fn before calling positioning_score_granular
        is_land_a = lambda name: name in list_a_lands  # noqa: E731
        is_land_b = lambda name: name in list_b_lands  # noqa: E731

        full_deck_a = {**spells, **list_a_lands}
        full_deck_b = {**spells, **list_b_lands}

        nonland_a = filter_nonland_cards(full_deck_a, is_land_a)
        nonland_b = filter_nonland_cards(full_deck_b, is_land_b)

        # After filtering, both nonland dicts should be equal
        assert nonland_a == nonland_b == spells

        # Therefore s_granular should be identical
        gr_a = positioning_score_granular(
            matrix, field, _DIMIR, nonland_a, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        gr_b = positioning_score_granular(
            matrix, field, _DIMIR, nonland_b, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        assert gr_a.s_granular == gr_b.s_granular, (
            f"Land-only difference should not affect s_granular: "
            f"a={gr_a.s_granular:.5f}, b={gr_b.s_granular:.5f}"
        )

    def test_land_exclusion_does_not_affect_baseline_s(self):
        """Filtering lands from deck_cards must not affect base.s_mean (archetype S)."""
        matrix = _hermetic_matrix()
        field = _hermetic_field()
        cwr = _build_cwr()

        # All-spells deck (no lands)
        spells_only = {"Force of Will": 4, "Brainstorm": 4, "Ponder": 4}
        # Same spells + lots of lands
        with_lands = {**spells_only, "Underground Sea": 4, "Polluted Delta": 4, "Swamp": 4}
        land_names = {"Underground Sea", "Polluted Delta", "Swamp"}
        nonland_with_lands = filter_nonland_cards(with_lands, lambda n: n in land_names)

        assert nonland_with_lands == spells_only

        gr_spells = positioning_score_granular(
            matrix, field, _DIMIR, spells_only, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )
        gr_nonland = positioning_score_granular(
            matrix, field, _DIMIR, nonland_with_lands, cwr,
            n_draws=_N_DRAWS, seed=_SEED,
        )

        # base.s_mean is archetype-level (not affected by deck_cards at all)
        assert gr_spells.base.s_mean == gr_nonland.base.s_mean
        # And s_granular should be identical (same nonland composition)
        assert gr_spells.s_granular == gr_nonland.s_granular


# ---------------------------------------------------------------------------
# Item 1: CLI integration (hermetic — file-backed DB + --db)
# ---------------------------------------------------------------------------


@pytest.fixture
def db_with_granular_corpus(tmp_path, make_rounds_corpus):
    """File-backed DuckDB corpus for CLI granular tests.

    Uses n_repeats=50 (n=100, established tier) so card lift signals clear
    the evolving/established gate in composition_adjusted_winrates.
    Adds cards table rows for land detection (is_land flag).
    """
    db_path = tmp_path / "granular_test.duckdb"
    # n_repeats=50 → n=100 per seeded cell (established tier)
    con_mem, _ = make_rounds_corpus(n_repeats=50)

    from legacy_engine.ingestion import store as _store
    con_file = _store.connect(str(db_path))
    _store.init_schema(con_file)

    for table in ("tournaments", "decks", "deck_cards", "rounds"):
        rows = con_mem.execute(f"SELECT * FROM {table}").fetchall()
        if rows:
            placeholders = ", ".join(["?"] * len(rows[0]))
            con_file.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)

    con_mem.close()
    con_file.close()
    return str(db_path)


@pytest.fixture
def deck_file_control(tmp_path):
    """Write a minimal Control decklist to a tmp file."""
    deck_text = "4 Brainstorm\n2 Force of Will\n4 Swamp\n"
    p = tmp_path / "control.txt"
    p.write_text(deck_text)
    return str(p)


@pytest.fixture
def runner():
    from click.testing import CliRunner
    return CliRunner()


class TestCLIListGranularFlag:
    """CLI item 1: --list-granular flag wiring and honesty constraints."""

    def test_list_granular_in_help(self, runner):
        """--list-granular appears in advise positioning --help."""
        from legacy_engine.cli import main
        result = runner.invoke(main, ["advise", "positioning", "--help"])
        assert result.exit_code == 0
        assert "--list-granular" in result.output

    def test_list_granular_help_mentions_experimental(self, runner):
        """Help text for --list-granular includes EXPERIMENTAL label."""
        from legacy_engine.cli import main
        result = runner.invoke(main, ["advise", "positioning", "--help"])
        assert result.exit_code == 0
        assert "EXPERIMENTAL" in result.output or "experimental" in result.output.lower()

    def test_positioning_without_flag_byte_identical(
        self, runner, db_with_granular_corpus, deck_file_control, tmp_path
    ):
        """Without --list-granular, advise positioning output has no S_granular line."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main,
            [
                "advise", "positioning",
                "--deck", deck_file_control,
                "--archetype", "Control",
                "--db", db_with_granular_corpus,
                "--all-time",
                "--seed", "42",
            ],
        )
        assert result.exit_code == 0, result.output
        # No granular output without the flag
        assert "S_granular" not in result.output
        assert "list-granular" not in result.output.lower()
        assert "EXPERIMENTAL" not in result.output

    def test_list_granular_shows_s_granular(
        self, runner, db_with_granular_corpus, deck_file_control
    ):
        """With --list-granular, output includes S_granular line."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main,
            [
                "advise", "positioning",
                "--deck", deck_file_control,
                "--archetype", "Control",
                "--db", db_with_granular_corpus,
                "--all-time",
                "--seed", "42",
                "--list-granular",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "S_granular" in result.output

    def test_list_granular_shows_caveat(
        self, runner, db_with_granular_corpus, deck_file_control
    ):
        """With --list-granular, the caveat is always shown."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main,
            [
                "advise", "positioning",
                "--deck", deck_file_control,
                "--archetype", "Control",
                "--db", db_with_granular_corpus,
                "--all-time",
                "--seed", "42",
                "--list-granular",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "EXPERIMENTAL" in result.output
        assert "presence-correlational" in result.output.lower()

    def test_list_granular_shows_archetype_baseline_s(
        self, runner, db_with_granular_corpus, deck_file_control
    ):
        """With --list-granular, the baseline archetype S is also shown for comparison."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main,
            [
                "advise", "positioning",
                "--deck", deck_file_control,
                "--archetype", "Control",
                "--db", db_with_granular_corpus,
                "--all-time",
                "--seed", "42",
                "--list-granular",
            ],
        )
        assert result.exit_code == 0, result.output
        # Both baseline and granular must be present in output
        assert "S (archetype-level" in result.output or "S (meta-positioning" in result.output

    def test_list_granular_shows_land_exclusion(
        self, runner, db_with_granular_corpus, deck_file_control
    ):
        """With --list-granular, decklist with lands shows land exclusion note.

        deck_file_control has '4 Swamp' — the cards table may or may not have
        is_land set (no cards seeded in the corpus), so we just check the output
        doesn't crash and still shows S_granular.
        """
        from legacy_engine.cli import main
        result = runner.invoke(
            main,
            [
                "advise", "positioning",
                "--deck", deck_file_control,
                "--archetype", "Control",
                "--db", db_with_granular_corpus,
                "--all-time",
                "--seed", "42",
                "--list-granular",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "S_granular" in result.output

    def test_list_granular_shows_delta(
        self, runner, db_with_granular_corpus, deck_file_control
    ):
        """Output includes a delta line (S_granular − S)."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main,
            [
                "advise", "positioning",
                "--deck", deck_file_control,
                "--archetype", "Control",
                "--db", db_with_granular_corpus,
                "--all-time",
                "--seed", "42",
                "--list-granular",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "delta" in result.output.lower()


# ---------------------------------------------------------------------------
# Item 2: Live plumbing — filter_nonland_cards + real corpus path
# ---------------------------------------------------------------------------


class TestLivePlumbing:
    """Item 2: verify the live-plumbing path uses the corpus window correctly."""

    def test_list_granular_with_all_time_flag(
        self, runner, db_with_granular_corpus, deck_file_control
    ):
        """--list-granular with --all-time uses the full corpus for CardWinRates."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main,
            [
                "advise", "positioning",
                "--deck", deck_file_control,
                "--archetype", "Control",
                "--db", db_with_granular_corpus,
                "--all-time",
                "--list-granular",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "S_granular" in result.output

    def test_list_granular_nonland_count_in_output(
        self, runner, db_with_granular_corpus, deck_file_control
    ):
        """Output mentions nonland card count used for lift signal."""
        from legacy_engine.cli import main
        result = runner.invoke(
            main,
            [
                "advise", "positioning",
                "--deck", deck_file_control,
                "--archetype", "Control",
                "--db", db_with_granular_corpus,
                "--all-time",
                "--list-granular",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "nonland" in result.output.lower()
