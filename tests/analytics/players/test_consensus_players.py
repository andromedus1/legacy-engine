"""Tests for player-filtered consensus / tune — story 3 of feature-strong-player-signal.

House style: in-memory DuckDB; hand-built fixtures; TestX classes; deterministic.

Coverage:
  - Gated-additive invariant: build_consensus(players=None) byte-identical to baseline.
  - Player filter narrows the pool and changes modal counts on a hand-built corpus.
  - Thin strong+windowed pool → sample_n low + speculative tier + banner in legality_errors;
    window NOT widened.
  - Regime-safety: a player's prior-regime list does NOT leak into the current-regime pool.
  - card_frequencies: players=None is byte-identical; player-filtered returns subset.
  - CLI smoke tests: identify suggest / strong / track exit 0 and emit expected headers.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.confidence import tier_for_sample
from legacy_engine.generation.consensus import (
    build_consensus,
    card_frequencies,
)
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item
from tests.conftest import in_current_regime


# ---------------------------------------------------------------------------
# Fixture helpers — minimal raw-dict builders
# ---------------------------------------------------------------------------

def _card(name: str, count: int = 4) -> dict:
    return {"CardName": name, "Count": count}


def _make_deck_raw(player: str, mainboard: list[dict], sideboard: list[dict] | None = None) -> dict:
    return {
        "Player": player,
        "Result": "1st Place",
        "Mainboard": mainboard,
        "Sideboard": sideboard or [],
    }


def _make_tournament(name: str, date: str, decks: list[dict]) -> dict:
    return {
        "Tournament": {
            "Name": name,
            "Date": date,
            "Uri": f"https://www.mtgo.com/decklist/{name.lower().replace(' ', '-')}-{date}",
            "Formats": "Legacy",
        },
        "Decks": decks,
        "Rounds": [],
        "Standings": [],
    }


# ---------------------------------------------------------------------------
# Corpus: two archetypes, two "strong" players running a distinct flex card.
#
# Archetype "ControlA":
#   - 8 "field" players run: [CounterA×4, WipeA×4, LandA×2] (×10 = 60 with pad)
#   - 2 "strong" players (example42, example-two) also run: [FlexStrong×4] instead of a filler
#
# This gives:
#   CounterA:   10/10 (inclusion=1.0) — appears in both field+strong
#   WipeA:      10/10 (inclusion=1.0)
#   LandA:      10/10 (inclusion=1.0)
#   FlexStrong: 2/10  (inclusion=0.2) in the unfiltered pool
#   FlexStrong: 2/2   (inclusion=1.0) in the strong-player filtered pool
#   FillerA:    8/10  (inclusion=0.8) in the unfiltered pool
#   FillerA:    0/2   (inclusion=0.0) in the strong-player filtered pool
# ---------------------------------------------------------------------------

# Cards that fill to exactly 60 slots (base core)
_CORE_CARDS = [
    ("CounterA", 4),   # 4
    ("WipeA", 4),      # 8
    ("LandA", 2),      # 10
    ("LandB", 2),      # 12
    ("LandC", 4),      # 16
    ("LandD", 4),      # 20
    ("LandE", 4),      # 24
    ("SpellA", 4),     # 28
    ("SpellB", 4),     # 32
    ("SpellC", 4),     # 36
    ("SpellD", 4),     # 40
    ("SpellE", 4),     # 44
    ("SpellF", 4),     # 48
    ("SpellG", 4),     # 52
    ("SpellH", 4),     # 56
]

_FLEX_FILLER = ("FillerA", 4)   # 60 (field players use this)
_FLEX_STRONG = ("FlexStrong", 4)  # 60 (strong players use this instead)


def _build_field_deck(player: str) -> dict:
    """Build a field player's deck: core + FillerA."""
    main = [_card(name, count) for name, count in _CORE_CARDS] + [_card(_FLEX_FILLER[0], _FLEX_FILLER[1])]
    return _make_deck_raw(player, main)


def _build_strong_deck(player: str) -> dict:
    """Build a strong player's deck: core + FlexStrong (instead of FillerA)."""
    main = [_card(name, count) for name, count in _CORE_CARDS] + [_card(_FLEX_STRONG[0], _FLEX_STRONG[1])]
    return _make_deck_raw(player, main)


def _build_corpus(date: str | None = None) -> dict:
    """Build 10-deck tournament: 8 field players + 2 strong players."""
    decks = [_build_field_deck(f"field{i}") for i in range(8)]
    decks += [_build_strong_deck("example42"), _build_strong_deck("example-two")]
    return _make_tournament("Test Challenge", date or in_current_regime(7), decks)


@pytest.fixture
def con():
    """In-memory DuckDB with the hand-built corpus."""
    c = store.connect(":memory:")
    store.init_schema(c)
    raw = _build_corpus()
    store.load_tournament(c, parse_cache_item(raw, "MTGO"))
    c.execute("UPDATE decks SET archetype = 'ControlA'")
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Test class 1 — gated-additive invariant
# ---------------------------------------------------------------------------

class TestGatedAdditiveInvariant:
    """build_consensus(players=None) must be byte-identical to the baseline call."""

    def test_players_none_maindeck_identical_to_baseline(self, con):
        baseline = build_consensus(con, "ControlA")
        filtered = build_consensus(con, "ControlA", players=None)
        assert baseline.maindeck == filtered.maindeck

    def test_players_none_sideboard_identical_to_baseline(self, con):
        baseline = build_consensus(con, "ControlA")
        filtered = build_consensus(con, "ControlA", players=None)
        assert baseline.sideboard == filtered.sideboard

    def test_players_none_sample_n_identical_to_baseline(self, con):
        baseline = build_consensus(con, "ControlA")
        filtered = build_consensus(con, "ControlA", players=None)
        assert baseline.sample_n == filtered.sample_n

    def test_card_frequencies_players_none_same_cards_and_stats(self, con):
        """card_frequencies(players=None) returns the same cards and stats as no-players."""
        baseline = card_frequencies(con, "ControlA", board="main")
        filtered = card_frequencies(con, "ControlA", board="main", players=None)
        # Both calls produce the same (name, inclusion_pct, modal_count) tuples.
        # Sort by name to compare independent of DuckDB ordering for ties.
        def _key(t):
            return t[0]
        assert sorted([(cf.name, cf.inclusion_pct, cf.modal_count) for cf in baseline], key=_key) == \
               sorted([(cf.name, cf.inclusion_pct, cf.modal_count) for cf in filtered], key=_key)

    def test_empty_alias_map_no_effect(self, con):
        """Passing an empty alias_map with players=None → byte-identical."""
        baseline = build_consensus(con, "ControlA")
        with_empty = build_consensus(con, "ControlA", players=None, alias_map={})
        assert baseline.maindeck == with_empty.maindeck
        assert baseline.sample_n == with_empty.sample_n


# ---------------------------------------------------------------------------
# Test class 2 — player filter narrows the pool
# ---------------------------------------------------------------------------

class TestPlayerFilterNarrowsPool:
    """Player filter restricts to strong-player decks; modal choices change."""

    def test_strong_players_pool_has_flex_strong(self, con):
        """FlexStrong appears in 100% of strong-player decks (2/2), not 20% overall."""
        freqs = card_frequencies(
            con, "ControlA", board="main",
            players={"example42", "example-two"},
        )
        flex_cf = next((cf for cf in freqs if cf.name == "FlexStrong"), None)
        assert flex_cf is not None, "FlexStrong must appear in strong-player pool"
        assert flex_cf.inclusion_pct == pytest.approx(1.0)

    def test_strong_players_pool_excludes_filler(self, con):
        """FillerA should not appear in the strong-player pool (0/2)."""
        freqs = card_frequencies(
            con, "ControlA", board="main",
            players={"example42", "example-two"},
        )
        filler_cf = next((cf for cf in freqs if cf.name == "FillerA"), None)
        assert filler_cf is None, "FillerA must not appear in the strong-player filtered pool"

    def test_sample_n_is_2_for_strong_players(self, con):
        """Filtered pool has exactly 2 decks (example42 + example-two)."""
        deck = build_consensus(con, "ControlA", players={"example42", "example-two"})
        assert deck.sample_n == 2

    def test_unfiltered_pool_has_filler(self, con):
        """Baseline (unfiltered) pool includes FillerA at 0.8 inclusion."""
        freqs = card_frequencies(con, "ControlA", board="main")
        filler_cf = next((cf for cf in freqs if cf.name == "FillerA"), None)
        assert filler_cf is not None
        assert filler_cf.inclusion_pct == pytest.approx(0.8)

    def test_unfiltered_pool_has_flex_strong_at_0_2(self, con):
        """Baseline pool includes FlexStrong at 0.2 inclusion (2/10)."""
        freqs = card_frequencies(con, "ControlA", board="main")
        flex_cf = next((cf for cf in freqs if cf.name == "FlexStrong"), None)
        assert flex_cf is not None
        assert flex_cf.inclusion_pct == pytest.approx(0.2)

    def test_single_player_filter(self, con):
        """A single-player filter produces a pool from that player's deck alone."""
        freqs = card_frequencies(con, "ControlA", board="main", players={"example42"})
        names = {cf.name for cf in freqs}
        # Must contain the strong-player card.
        assert "FlexStrong" in names
        # Must not contain the filler card (example42 doesn't run it).
        assert "FillerA" not in names

    def test_unknown_player_returns_empty(self, con):
        """A player with no decks in the corpus returns an empty freq list."""
        freqs = card_frequencies(con, "ControlA", board="main", players={"nobody_xyz"})
        assert freqs == []

    def test_unknown_player_returns_zero_sample_n(self, con):
        """build_consensus for an unknown player set returns sample_n=0."""
        deck = build_consensus(con, "ControlA", players={"nobody_xyz"})
        assert deck.sample_n == 0
        assert deck.legality_errors  # at least the "no decks" error


# ---------------------------------------------------------------------------
# Test class 3 — thin pool honest-degrade (no window widening)
# ---------------------------------------------------------------------------

class TestThinPoolHonestDegrade:
    """Thin strong+windowed pool → speculative tier + banner; window never widened."""

    def test_thin_pool_sample_n_below_floor(self, con):
        """2-deck strong-player pool is below the evolving floor (30)."""
        deck = build_consensus(con, "ControlA", players={"example42", "example-two"})
        # sample_n=2 → tier_for_sample(2) == "speculative"
        assert deck.sample_n == 2
        assert tier_for_sample(deck.sample_n) == "speculative"

    def test_thin_pool_banner_in_legality_errors(self, con):
        """A thin player-filtered pool attaches a loud banner to legality_errors."""
        deck = build_consensus(con, "ControlA", players={"example42", "example-two"})
        banners = [e for e in deck.legality_errors if "THIN" in e.upper()]
        assert banners, f"Expected thin-pool banner; got: {deck.legality_errors}"

    def test_thin_pool_banner_mentions_no_window_widening(self, con):
        """The banner must state the window was NOT widened."""
        deck = build_consensus(con, "ControlA", players={"example42", "example-two"})
        banners = [e for e in deck.legality_errors if "THIN" in e.upper()]
        assert banners
        assert "NOT widened" in banners[0] or "not widened" in banners[0].lower(), (
            f"Banner should state no window widening: {banners[0]}"
        )

    def test_no_banner_without_player_filter(self, con):
        """The thin-pool banner must NOT appear when no player filter is active."""
        # 10-deck unfiltered pool — well above 30 is not required; the point is
        # the banner should only fire when players is not None.
        deck = build_consensus(con, "ControlA")
        banners = [e for e in deck.legality_errors if "THIN PLAYER" in e.upper()]
        assert not banners, f"Unexpected thin-player banner on unfiltered pool: {banners}"

    def test_window_stays_at_latest_regime(self, con):
        """The filtered pool uses the latest-regime window, not a wider one."""
        from legacy_engine.generation.consensus import _latest_regime_window
        expected_since, expected_until = _latest_regime_window()
        deck = build_consensus(con, "ControlA", players={"example42", "example-two"})
        # Deck window must equal the regime window, not be widened.
        assert deck.window[0] == expected_since
        assert deck.window[1] == expected_until


# ---------------------------------------------------------------------------
# Test class 4 — regime-safety (prior-regime lists do NOT leak)
# ---------------------------------------------------------------------------

class TestRegimeSafety:
    """A strong player's prior-regime list must not contaminate the current-regime pool."""

    @pytest.fixture
    def con_two_regimes(self):
        """Corpus with two regimes:

        Regime 1 (2025-01-15 — pre current regime): example42 runs OldCard (4 copies).
        Regime 2 (ledger-derived current-regime date): example42 runs NewCard (4 copies).
        Other cards are shared core so 60-card constraint is met.
        """
        core_small = [
            ("CoreA", 4),
            ("CoreB", 4),
            ("CoreC", 4),
            ("CoreD", 4),
            ("CoreE", 4),
            ("CoreF", 4),
            ("CoreG", 4),
            ("CoreH", 4),
            ("CoreI", 4),
            ("CoreJ", 4),
            ("CoreK", 4),
            ("CoreL", 4),
            ("CoreM", 4),
            ("CoreN", 4),
        ]  # 14 × 4 = 56 cards

        def _make_regime_deck(player: str, signal_card: str) -> dict:
            main = [_card(n, c) for n, c in core_small] + [_card(signal_card, 4)]
            return _make_deck_raw(player, main)

        # Old regime (2025-01-15 — still within the full corpus but before current ban):
        old_decks = [_make_regime_deck("example42", "OldCard")] + [
            _make_regime_deck(f"other{i}", "OldCard") for i in range(4)
        ]
        old_t = _make_tournament("OldRegimeEvent", "2025-01-15", old_decks)

        # Current regime (post latest confirmed ban):
        new_decks = [_make_regime_deck("example42", "NewCard")] + [
            _make_regime_deck(f"current{i}", "NewCard") for i in range(4)
        ]
        new_t = _make_tournament("NewRegimeEvent", in_current_regime(7), new_decks)

        c = store.connect(":memory:")
        store.init_schema(c)
        store.load_tournament(c, parse_cache_item(old_t, "MTGO"))
        store.load_tournament(c, parse_cache_item(new_t, "MTGO"))
        c.execute("UPDATE decks SET archetype = 'RegimeArch'")
        yield c
        c.close()

    def test_current_regime_default_uses_latest_window(self, con_two_regimes):
        """Default call (since/until=None) queries only the current regime window."""
        from legacy_engine.generation.consensus import _latest_regime_window
        since, until = _latest_regime_window()
        freqs = card_frequencies(
            con_two_regimes, "RegimeArch", board="main",
            since=since, until=until,
        )
        names = {cf.name for cf in freqs}
        assert "NewCard" in names, "NewCard must be in current-regime pool"
        assert "OldCard" not in names, "OldCard must NOT be in current-regime pool"

    def test_prior_regime_card_excluded_from_default_pool(self, con_two_regimes):
        """OldCard is NOT in the player-filtered current-regime pool."""
        from legacy_engine.generation.consensus import _latest_regime_window
        since, until = _latest_regime_window()
        freqs = card_frequencies(
            con_two_regimes, "RegimeArch", board="main",
            since=since, until=until,
            players={"example42"},
        )
        names = {cf.name for cf in freqs}
        assert "NewCard" in names, "NewCard must appear for example42 in current regime"
        assert "OldCard" not in names, "OldCard must NOT leak from prior regime"

    def test_explicit_all_time_shows_both_cards(self, con_two_regimes):
        """Explicitly passing since=None/until=None with all-time → both cards visible."""
        # We simulate --all-time by passing since=None, until=None directly.
        # The default in card_frequencies triggers _latest_regime_window() so we must
        # pass the explicit window dates to override.  For "all-time" pass explicit
        # since="2000-01-01" to bypass the default.
        freqs = card_frequencies(
            con_two_regimes, "RegimeArch", board="main",
            since="2000-01-01", until=None,
        )
        names = {cf.name for cf in freqs}
        # Both cards exist in the full corpus.
        assert "NewCard" in names
        assert "OldCard" in names

    def test_strong_default_window_is_latest_regime(self, con_two_regimes):
        """build_consensus with players= defaults to the current regime (not widened)."""
        from legacy_engine.generation.consensus import _latest_regime_window
        since, until = _latest_regime_window()
        deck = build_consensus(
            con_two_regimes, "RegimeArch",
            players={"example42"},
        )
        # Window must equal the latest regime — not widened.
        assert deck.window[0] == since
        assert deck.window[1] == until

    def test_old_card_not_in_current_regime_filtered_deck(self, con_two_regimes):
        """The consensus maindeck for example42 in the current regime must not contain OldCard."""
        deck = build_consensus(
            con_two_regimes, "RegimeArch",
            players={"example42"},
        )
        assert "OldCard" not in deck.maindeck, (
            f"OldCard leaked from prior regime into filtered consensus: {deck.maindeck}"
        )


# ---------------------------------------------------------------------------
# Test class 5 — alias resolution in player filter
# ---------------------------------------------------------------------------

class TestAliasResolutionInFilter:
    """Player filter respects the alias_map to expand player_ids to handle variants."""

    def test_alias_map_expands_player_id_to_handles(self, con):
        """When alias_map maps 'example42' to 'example_canonical', filtering by
        'example_canonical' still finds example42's decks."""
        # Build alias_map: example42 (normalized: "example42") → "example_canonical"
        alias_map = {"example42": "example_canonical"}
        # Filter by the canonical id.
        freqs = card_frequencies(
            con, "ControlA", board="main",
            players={"example_canonical"},
            alias_map=alias_map,
        )
        names = {cf.name for cf in freqs}
        # example42 runs FlexStrong (the strong player's card).
        assert "FlexStrong" in names, (
            "Alias resolution should expand example_canonical → example42 handle"
        )

    def test_no_alias_map_still_resolves_by_player_id(self, con):
        """When alias_map is None or empty, player_id is matched directly as a handle."""
        # "example42" is already a normalized handle in the DB (player name).
        freqs = card_frequencies(
            con, "ControlA", board="main",
            players={"example42"},
            alias_map=None,
        )
        names = {cf.name for cf in freqs}
        assert "FlexStrong" in names


# ---------------------------------------------------------------------------
# Test class 6 — CLI smoke tests for identify group
# ---------------------------------------------------------------------------

class TestIdentifyCLI:
    """Smoke tests for the identify CLI group (suggest / strong / track)."""

    def _make_db(self, tmp_path):
        """Build a minimal file-backed DuckDB for CLI tests."""
        import duckdb as _duckdb
        db_path = tmp_path / "id_test.duckdb"
        fc = _duckdb.connect(str(db_path))
        store.init_schema(fc)
        raw = _build_corpus()
        store.load_tournament(fc, parse_cache_item(raw, "MTGO"))
        fc.execute("UPDATE decks SET archetype = 'ControlA'")
        fc.close()
        return db_path

    def test_identify_suggest_exits_zero(self, tmp_path):
        db_path = self._make_db(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["identify", "suggest", "--db", str(db_path)])
        assert result.exit_code == 0, f"exit={result.exit_code}\n{result.output}"

    def test_identify_suggest_output_is_readable(self, tmp_path):
        db_path = self._make_db(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["identify", "suggest", "--db", str(db_path)])
        assert result.exit_code == 0
        # Either "no alias clusters found" or a cluster header.
        assert "cluster" in result.output.lower() or "no alias" in result.output.lower()

    def test_identify_strong_exits_zero(self, tmp_path):
        db_path = self._make_db(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["identify", "strong", "--db", str(db_path)])
        assert result.exit_code == 0, f"exit={result.exit_code}\n{result.output}"

    def test_identify_strong_shows_header(self, tmp_path):
        db_path = self._make_db(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["identify", "strong", "--db", str(db_path)])
        assert result.exit_code == 0
        assert "Strong Players" in result.output

    def test_identify_track_exits_zero(self, tmp_path):
        db_path = self._make_db(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["identify", "track", "example42", "--db", str(db_path)])
        assert result.exit_code == 0, f"exit={result.exit_code}\n{result.output}"

    def test_identify_track_unknown_player(self, tmp_path):
        db_path = self._make_db(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["identify", "track", "nobody_xyz", "--db", str(db_path)])
        assert result.exit_code == 0
        assert "No archetype history" in result.output or "nobody" in result.output.lower()

    def test_identify_track_known_player_shows_archetype(self, tmp_path):
        db_path = self._make_db(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["identify", "track", "example42", "--db", str(db_path)])
        assert result.exit_code == 0
        # Should show "ControlA" in the history table.
        assert "ControlA" in result.output

    def test_generate_consensus_players_flag(self, tmp_path):
        """generate consensus --players exits 0 and shows a player-filtered label."""
        db_path = self._make_db(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["generate", "consensus", "--archetype", "ControlA",
             "--players", "example42,example-two", "--db", str(db_path)],
        )
        assert result.exit_code == 0, f"exit={result.exit_code}\n{result.output}"
        assert "player-filtered" in result.output.lower() or "Consensus deck" in result.output

    def test_generate_consensus_no_players_flag_unchanged(self, tmp_path):
        """generate consensus without --players behaves exactly as before."""
        db_path = self._make_db(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["generate", "consensus", "--archetype", "ControlA", "--db", str(db_path)],
        )
        assert result.exit_code == 0
        assert "Consensus deck: ControlA" in result.output
        assert "Maindeck: 60" in result.output
