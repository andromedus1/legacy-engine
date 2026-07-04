"""Tests for advisory.backtest — the sideboard-scorer backtest validation surface.

Uses the file-backed-cli-test-db-builder pattern: every test that touches a DuckDB
connection builds its own tmp DB (never the default DB — the green-local/red-CI trap).
"""

from __future__ import annotations

import duckdb
import pytest

from legacy_engine.advisory import backtest as backtest_mod
from legacy_engine.advisory.backtest import (
    _FIELD_OVERLAP_MIN,
    _OBSERVED_THRESHOLD,
    _TOP_FINISHER_QUANTILE,
    BoardBacktest,
    _apply_field_scope,
    backtest_board,
)
from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.advisory.sideboard import SideboardPackage
from legacy_engine.cli import main
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item


# ---------------------------------------------------------------------------
# Hermetic corpus builder (file-backed-cli-test-db-builder pattern)
# ---------------------------------------------------------------------------


def _deck(player: str, archetype: str, main: list[str], side: list[str], result: str) -> dict:
    return {
        "Player": player,
        "Result": result,
        "Mainboard": [{"Count": 4, "CardName": c} for c in main] or [
            {"Count": 60, "CardName": "Island"}
        ],
        "Sideboard": [{"Count": 1, "CardName": c} for c in side],
    }


def _standing(rank: int, player: str) -> dict:
    return {"Rank": rank, "Player": player, "Points": 100 - rank, "Wins": 5, "Losses": 1, "Draws": 0}


def _build_backtest_db(tmp_path) -> str:
    """A tmp DuckDB with three 8-player tournaments seeding a known Boulder top-finisher sample.

    Top-finisher threshold at `_TOP_FINISHER_QUANTILE=0.25` over an 8-player field is
    `ceil(0.25 * 8) = 2` — ranks 1-2 qualify in each tournament.

    Qualifying (top-finisher) Boulder decks in T1+T2: alice (T1 rank1), bob (T1 rank2),
    erin (T2 rank1), frank (T2 rank2) — 4 decks total.

    Known sideboard signal across those 4 decks:
      Surgical Extraction: alice, bob, erin, frank  -> 4/4 = 100%
      Ravenous Trap:       alice, bob,       frank  -> 3/4 = 75%
      Rest in Peace:             bob               -> 1/4 = 25%

    Non-qualifying decks are seeded with a DISTINCT sideboard card ("Wear // Tear" /
    "Pyroblast") that must NOT leak into observed_frequency if the rank/tournament
    filtering is correct:
      dave  (T1 rank4, Boulder) -> Wear // Tear
      grace (T2 rank5, Boulder) -> Pyroblast

    T3 is an OFF-FIELD tournament for feature-sfv-backtest-scoped's field-scoping tests:
    6/8 decks are Reanimator (a graveyard strategy), only 2/8 are Boulder. Its qualifying
    Boulder top-finishers (holly rank1, ivan rank2) run a DISTINCT card ("Grafdigger's
    Cage") that must NOT appear in observed_frequency under the default field-scoped
    backtest against a {Boulder, Doomsday} field (T3's Boulder-or-Doomsday share is
    2/8=0.25, below `_FIELD_OVERLAP_MIN=0.5`) — but MUST appear when field-scoping is
    disabled (`field_scope=False`), proving the toggle actually gates the filter.
    """
    db_path = str(tmp_path / "test_backtest.duckdb")
    con = store.connect(db_path)
    try:
        # --- Tournament 1 (8 players) ---
        raw1 = {
            "Tournament": {
                "Name": "Backtest Corpus 1",
                "Date": "2026-01-01",
                "Uri": "https://www.mtgo.com/decklist/backtest-corpus-1",
                "Formats": "Legacy",
            },
            "Decks": [
                _deck("alice", "Boulder", ["Brainstorm"], ["Surgical Extraction", "Ravenous Trap"], "1st"),
                _deck("bob", "Boulder", ["Brainstorm"],
                      ["Surgical Extraction", "Ravenous Trap", "Rest in Peace"], "2nd"),
                _deck("carol", "Doomsday", ["Dark Ritual"], ["Rest in Peace"], "3rd"),
                _deck("dave", "Boulder", ["Brainstorm"], ["Wear // Tear"], "4th"),
                _deck("p5", "Doomsday", ["Dark Ritual"], [], "5th"),
                _deck("p6", "Doomsday", ["Dark Ritual"], [], "6th"),
                _deck("p7", "Doomsday", ["Dark Ritual"], [], "7th"),
                _deck("p8", "Doomsday", ["Dark Ritual"], [], "8th"),
            ],
            "Rounds": [],
            "Standings": [
                _standing(1, "alice"), _standing(2, "bob"), _standing(3, "carol"),
                _standing(4, "dave"), _standing(5, "p5"), _standing(6, "p6"),
                _standing(7, "p7"), _standing(8, "p8"),
            ],
        }
        tid1 = store.load_tournament(con, parse_cache_item(raw1, "MTGO"))
        _label_archetypes(con, tid1, {
            "alice": "Boulder", "bob": "Boulder", "carol": "Doomsday", "dave": "Boulder",
            "p5": "Doomsday", "p6": "Doomsday", "p7": "Doomsday", "p8": "Doomsday",
        })

        # --- Tournament 2 (8 players) ---
        raw2 = {
            "Tournament": {
                "Name": "Backtest Corpus 2",
                "Date": "2026-01-08",
                "Uri": "https://www.mtgo.com/decklist/backtest-corpus-2",
                "Formats": "Legacy",
            },
            "Decks": [
                _deck("erin", "Boulder", ["Brainstorm"], ["Surgical Extraction"], "1st"),
                _deck("frank", "Boulder", ["Brainstorm"], ["Surgical Extraction", "Ravenous Trap"], "2nd"),
                _deck("q3", "Doomsday", ["Dark Ritual"], [], "3rd"),
                _deck("q4", "Doomsday", ["Dark Ritual"], [], "4th"),
                _deck("grace", "Boulder", ["Brainstorm"], ["Pyroblast"], "5th"),
                _deck("q6", "Doomsday", ["Dark Ritual"], [], "6th"),
                _deck("q7", "Doomsday", ["Dark Ritual"], [], "7th"),
                _deck("q8", "Doomsday", ["Dark Ritual"], [], "8th"),
            ],
            "Rounds": [],
            "Standings": [
                _standing(1, "erin"), _standing(2, "frank"), _standing(3, "q3"),
                _standing(4, "q4"), _standing(5, "grace"), _standing(6, "q6"),
                _standing(7, "q7"), _standing(8, "q8"),
            ],
        }
        tid2 = store.load_tournament(con, parse_cache_item(raw2, "MTGO"))
        _label_archetypes(con, tid2, {
            "erin": "Boulder", "frank": "Boulder", "q3": "Doomsday", "q4": "Doomsday",
            "grace": "Boulder", "q6": "Doomsday", "q7": "Doomsday", "q8": "Doomsday",
        })

        # --- Tournament 3 (8 players) — OFF-FIELD: 6/8 Reanimator, 2/8 Boulder ---
        raw3 = {
            "Tournament": {
                "Name": "Backtest Corpus 3 (graveyard-heavy, off-field)",
                "Date": "2026-01-15",
                "Uri": "https://www.mtgo.com/decklist/backtest-corpus-3",
                "Formats": "Legacy",
            },
            "Decks": [
                _deck("holly", "Boulder", ["Brainstorm"], ["Grafdigger's Cage"], "1st"),
                _deck("ivan", "Boulder", ["Brainstorm"], ["Grafdigger's Cage"], "2nd"),
                _deck("r3", "Reanimator", ["Entomb"], [], "3rd"),
                _deck("r4", "Reanimator", ["Entomb"], [], "4th"),
                _deck("r5", "Reanimator", ["Entomb"], [], "5th"),
                _deck("r6", "Reanimator", ["Entomb"], [], "6th"),
                _deck("r7", "Reanimator", ["Entomb"], [], "7th"),
                _deck("r8", "Reanimator", ["Entomb"], [], "8th"),
            ],
            "Rounds": [],
            "Standings": [
                _standing(1, "holly"), _standing(2, "ivan"), _standing(3, "r3"),
                _standing(4, "r4"), _standing(5, "r5"), _standing(6, "r6"),
                _standing(7, "r7"), _standing(8, "r8"),
            ],
        }
        tid3 = store.load_tournament(con, parse_cache_item(raw3, "MTGO"))
        _label_archetypes(con, tid3, {
            "holly": "Boulder", "ivan": "Boulder", "r3": "Reanimator", "r4": "Reanimator",
            "r5": "Reanimator", "r6": "Reanimator", "r7": "Reanimator", "r8": "Reanimator",
        })
    finally:
        con.close()
    return db_path


def _label_archetypes(con: duckdb.DuckDBPyConnection, tournament_id: str, by_player: dict[str, str]) -> None:
    """Set `decks.archetype` post-ingestion (archetype labeling is a separate step from
    raw decklist parsing — `parse_cache_item`/`load_tournament` leave it NULL)."""
    for player, archetype in by_player.items():
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND player = ?",
            [archetype, tournament_id, player],
        )


def _fake_field() -> FieldDistribution:
    return FieldDistribution(
        shares={"Boulder": 0.6, "Doomsday": 0.4},
        field_source="custom",
        counts=None,
        no_data=frozenset(),
        warnings=(),
    )


def _fake_package(cards: dict[str, int]) -> SideboardPackage:
    return SideboardPackage(
        cards=cards,
        trace=[],
        covered_weight=0.0,
        budget=15,
        reserved=0,
        solver_used="ilp",
        field_source="custom",
        heuristic_note="",
        warnings=(),
    )


# ---------------------------------------------------------------------------
# Unit tests: backtest_board classification
# ---------------------------------------------------------------------------


class TestBacktestBoardClassification:
    def test_top_finisher_filter_and_classification(self, tmp_path, monkeypatch):
        """Only rank<=threshold Boulder decks feed observed_frequency; classification
        correctly buckets overlap / scorer_only / winners_only."""
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)

        monkeypatch.setattr(
            backtest_mod,
            "recommend_sideboard",
            lambda *a, **k: _fake_package(
                {"Surgical Extraction": 1, "Toxic Deluge": 1, "Chalice of the Void": 1}
            ),
        )

        try:
            result = backtest_board(con, "Boulder", _fake_field())
        finally:
            con.close()

        assert isinstance(result, BoardBacktest)
        assert result.archetype == "Boulder"

        # Exactly 4 qualifying top-finisher Boulder decks (alice, bob, erin, frank).
        assert result.n_winning_decks == 4

        # Observed frequency: exact fractions from the 4 qualifying decks only —
        # dave/grace's off-signal cards must not leak in.
        assert result.observed_frequency["Surgical Extraction"] == pytest.approx(1.0)
        assert result.observed_frequency["Ravenous Trap"] == pytest.approx(0.75)
        assert result.observed_frequency["Rest in Peace"] == pytest.approx(0.25)
        assert "Wear // Tear" not in result.observed_frequency
        assert "Pyroblast" not in result.observed_frequency

        # Classification against the monkeypatched recommended board.
        assert result.recommended == ("Chalice of the Void", "Surgical Extraction", "Toxic Deluge")
        assert result.overlap == ("Surgical Extraction",)
        assert result.scorer_only == ("Chalice of the Void", "Toxic Deluge")
        assert result.winners_only == ("Ravenous Trap", "Rest in Peace")

        # overlap ∪ scorer_only == recommended (a partition).
        assert set(result.overlap) | set(result.scorer_only) == set(result.recommended)
        assert set(result.overlap) & set(result.scorer_only) == set()

        # 4 decks is below the evolving floor (30) -> honest-degrade "speculative" tier.
        assert result.confidence == "speculative"

    def test_observed_threshold_boundary(self, tmp_path, monkeypatch):
        """A card at exactly _OBSERVED_THRESHOLD counts as commonly played (>=, not >)."""
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)
        monkeypatch.setattr(
            backtest_mod, "recommend_sideboard", lambda *a, **k: _fake_package({})
        )
        try:
            result = backtest_board(con, "Boulder", _fake_field())
        finally:
            con.close()

        # Rest in Peace sits at exactly 1/4 == _OBSERVED_THRESHOLD (0.25 >= 0.20).
        assert result.observed_frequency["Rest in Peace"] == pytest.approx(_OBSERVED_THRESHOLD, rel=0.3)
        assert "Rest in Peace" in result.winners_only

    def test_empty_corpus_is_insufficient_data_not_a_crash(self, tmp_path):
        """A totally empty DB (no tournaments/decks/standings at all) never crashes;
        it degrades to an honest 'no data' result: n=0, confidence=None."""
        db_path = str(tmp_path / "empty.duckdb")
        con = store.connect(db_path)
        store.init_schema(con)

        try:
            result = backtest_board(con, "Boulder", _fake_field())
        finally:
            con.close()

        assert result.n_winning_decks == 0
        assert result.confidence is None
        assert result.observed_frequency == {}
        # No crash even though the scorer ran against a fully empty corpus; whatever it
        # recommends, every card must resolve to scorer_only (nothing was observed).
        assert set(result.overlap) == set()
        assert set(result.scorer_only) == set(result.recommended)
        assert set(result.winners_only) == set()

    def test_unknown_archetype_degrades_honestly(self, tmp_path, monkeypatch):
        """An archetype with corpus data but zero top-finisher decks (e.g. never places
        highly) also degrades to n=0/confidence=None, not a crash."""
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)
        monkeypatch.setattr(
            backtest_mod, "recommend_sideboard", lambda *a, **k: _fake_package({"Some Card": 1})
        )
        try:
            result = backtest_board(con, "Nonexistent Archetype", _fake_field())
        finally:
            con.close()

        assert result.n_winning_decks == 0
        assert result.confidence is None
        assert result.observed_frequency == {}
        assert result.winners_only == ()

    def test_scorer_failure_degrades_to_empty_recommended(self, tmp_path, monkeypatch):
        """A scorer exception must not propagate — it degrades to an empty recommended
        tuple (every observed card then honestly reads as winners_only)."""
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)

        def _boom(*a, **k):
            raise RuntimeError("scorer exploded")

        monkeypatch.setattr(backtest_mod, "recommend_sideboard", _boom)
        try:
            result = backtest_board(con, "Boulder", _fake_field())
        finally:
            con.close()

        assert result.recommended == ()
        assert result.overlap == ()
        assert result.scorer_only == ()
        assert set(result.winners_only) == {"Surgical Extraction", "Ravenous Trap", "Rest in Peace"}
        assert result.n_winning_decks == 4
        assert result.confidence == "speculative"


# ---------------------------------------------------------------------------
# Unit tests: _apply_field_scope — pure filter, no DB (feature-sfv-backtest-scoped)
# ---------------------------------------------------------------------------


class TestApplyFieldScopePure:
    """Exercises the pure half of the objective-search-split directly with hand-built
    dicts — no DuckDB connection needed."""

    def test_majority_in_field_tournament_is_kept(self):
        deck_keys = [("t1", 0), ("t1", 1)]
        archetype_counts = {"t1": {"Boulder": 6, "Doomsday": 2}}
        kept, considered, excluded = _apply_field_scope(
            deck_keys, archetype_counts, {"Boulder", "Doomsday"}
        )
        assert kept == deck_keys
        assert considered == 1
        assert excluded == 0

    def test_minority_in_field_tournament_is_excluded(self):
        """6/8 Reanimator, 2/8 Boulder: a {Boulder, Doomsday} field has only 25% overlap,
        below _FIELD_OVERLAP_MIN — the tournament's decks are dropped even though they
        pass the rank cut on their own."""
        deck_keys = [("t3", 0), ("t3", 1)]
        archetype_counts = {"t3": {"Boulder": 2, "Reanimator": 6}}
        kept, considered, excluded = _apply_field_scope(
            deck_keys, archetype_counts, {"Boulder", "Doomsday"}
        )
        assert kept == []
        assert considered == 1
        assert excluded == 1

    def test_boundary_at_exactly_min_overlap_is_kept(self):
        """Exactly _FIELD_OVERLAP_MIN (0.5) counts as in-field (>=, not >)."""
        deck_keys = [("t4", 0)]
        archetype_counts = {"t4": {"Boulder": 4, "Reanimator": 4}}
        kept, considered, excluded = _apply_field_scope(
            deck_keys, archetype_counts, {"Boulder"}, min_overlap=_FIELD_OVERLAP_MIN
        )
        assert kept == deck_keys
        assert excluded == 0

    def test_missing_or_all_null_tournament_is_conservatively_excluded(self):
        """A tournament absent from archetype_counts (e.g. a query failure, or a
        tournament with zero labeled decks) has zero evidence and is excluded — never
        fabricated as in-field."""
        deck_keys = [("t5", 0)]
        kept, considered, excluded = _apply_field_scope(deck_keys, {}, {"Boulder"})
        assert kept == []
        assert considered == 1
        assert excluded == 1

    def test_multi_tournament_mix_partitions_correctly(self):
        deck_keys = [("t1", 0), ("t2", 0), ("t3", 0), ("t3", 1)]
        archetype_counts = {
            "t1": {"Boulder": 8},                       # 100% in-field -> kept
            "t2": {"Doomsday": 8},                       # 100% in-field -> kept
            "t3": {"Boulder": 2, "Reanimator": 6},        # 25% in-field -> excluded
        }
        kept, considered, excluded = _apply_field_scope(
            deck_keys, archetype_counts, {"Boulder", "Doomsday"}
        )
        assert set(kept) == {("t1", 0), ("t2", 0)}
        assert considered == 3
        assert excluded == 1

    def test_empty_deck_keys_is_a_noop(self):
        kept, considered, excluded = _apply_field_scope([], {}, {"Boulder"})
        assert kept == []
        assert considered == 0
        assert excluded == 0


# ---------------------------------------------------------------------------
# Integration tests: backtest_board field scoping + window (feature-sfv-backtest-scoped)
# ---------------------------------------------------------------------------


class TestBacktestBoardFieldScope:
    def test_default_field_scope_excludes_off_field_tournament(self, tmp_path, monkeypatch):
        """Default field_scope=True: T3 (6/8 Reanimator) is excluded from a {Boulder,
        Doomsday} field backtest — its "Grafdigger's Cage" signal must not leak in, and
        the pre-existing T1+T2 sample (n=4) is unaffected."""
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)
        monkeypatch.setattr(
            backtest_mod, "recommend_sideboard", lambda *a, **k: _fake_package({})
        )
        try:
            result = backtest_board(con, "Boulder", _fake_field())
        finally:
            con.close()

        assert result.field_scope is True
        assert result.n_winning_decks == 4  # T1+T2 only; T3 excluded
        assert "Grafdigger's Cage" not in result.observed_frequency
        assert result.observed_frequency["Surgical Extraction"] == pytest.approx(1.0)
        assert result.n_tournaments_considered == 3  # T1, T2, T3 all had qualifying Boulder decks
        assert result.n_tournaments_excluded == 1  # only T3

    def test_no_field_scope_includes_off_field_tournament(self, tmp_path, monkeypatch):
        """--no-field-scope (field_scope=False) reproduces the prior global sample:
        T3's Grafdigger's Cage signal is now included, diluted across all 6 decks."""
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)
        monkeypatch.setattr(
            backtest_mod, "recommend_sideboard", lambda *a, **k: _fake_package({})
        )
        try:
            result = backtest_board(con, "Boulder", _fake_field(), field_scope=False)
        finally:
            con.close()

        assert result.field_scope is False
        assert result.n_winning_decks == 6  # T1+T2+T3
        assert result.observed_frequency["Grafdigger's Cage"] == pytest.approx(2 / 6)
        # field-scope did not run -> no exclusions counted, but "considered" still
        # reports every candidate tournament seen (honest, not silently 0).
        assert result.n_tournaments_considered == 3
        assert result.n_tournaments_excluded == 0

    def test_field_scope_thinning_sample_to_zero_is_honest_degrade_not_crash(
        self, tmp_path, monkeypatch
    ):
        """A field wholly disjoint from every candidate tournament's metagame excludes
        ALL candidates — degrades to n=0/confidence=None, never a crash, and the counts
        say exactly why (considered=excluded=3, not silently absent)."""
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)
        monkeypatch.setattr(
            backtest_mod, "recommend_sideboard", lambda *a, **k: _fake_package({})
        )
        disjoint_field = FieldDistribution(
            shares={"Some Unrelated Archetype": 1.0},
            field_source="custom",
            counts=None,
            no_data=frozenset(),
            warnings=(),
        )
        try:
            result = backtest_board(con, "Boulder", disjoint_field)
        finally:
            con.close()

        assert result.n_winning_decks == 0
        assert result.confidence is None
        assert result.observed_frequency == {}
        assert result.n_tournaments_considered == 3
        assert result.n_tournaments_excluded == 3

    def test_since_until_window_narrows_top_finisher_sample(self, tmp_path, monkeypatch):
        """--since/--until (already-partial support) correctly narrows the top-finisher
        sample to a sub-window — here, isolating T2 (2026-01-08) alone via a half-open
        [since, until) cut that excludes T1 (2026-01-01) and T3 (2026-01-15)."""
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)
        monkeypatch.setattr(
            backtest_mod, "recommend_sideboard", lambda *a, **k: _fake_package({})
        )
        try:
            result = backtest_board(
                con, "Boulder", _fake_field(), since="2026-01-08", until="2026-01-09"
            )
        finally:
            con.close()

        # Only T2's qualifying decks (erin, frank) survive the window cut.
        assert result.n_winning_decks == 2
        assert result.observed_frequency["Surgical Extraction"] == pytest.approx(1.0)
        assert result.observed_frequency["Ravenous Trap"] == pytest.approx(0.5)
        assert "Wear // Tear" not in result.observed_frequency
        assert "Grafdigger's Cage" not in result.observed_frequency
        assert result.n_tournaments_considered == 1

    def test_field_scope_and_window_compose(self, tmp_path, monkeypatch):
        """Field-scope and window filters compose: windowing to a range that includes
        only T3 (off-field), with field-scope on, must degrade to an honest empty
        result rather than silently falling back to some other tournament."""
        db_path = _build_backtest_db(tmp_path)
        con = store.connect(db_path)
        monkeypatch.setattr(
            backtest_mod, "recommend_sideboard", lambda *a, **k: _fake_package({})
        )
        try:
            result = backtest_board(
                con, "Boulder", _fake_field(), since="2026-01-15", until="2026-01-16"
            )
        finally:
            con.close()

        assert result.n_winning_decks == 0
        assert result.confidence is None
        assert result.n_tournaments_considered == 1
        assert result.n_tournaments_excluded == 1


# ---------------------------------------------------------------------------
# CLI test: `advise backtest`
# ---------------------------------------------------------------------------


class TestAdviseBacktestCLI:
    @pytest.fixture
    def runner(self):
        from click.testing import CliRunner
        return CliRunner()

    def test_advise_backtest_renders_groups_and_caveat(self, tmp_path, runner, monkeypatch):
        """`advise backtest` renders overlap/scorer-only/winners-only, the confidence
        tier, and the explicit non-negotiable caveat line — always, regardless of verdict."""
        db_path = _build_backtest_db(tmp_path)
        field_file = tmp_path / "field.txt"
        field_file.write_text("0.6 Boulder\n0.4 Doomsday\n")

        fake_result = BoardBacktest(
            archetype="Boulder",
            n_winning_decks=4,
            confidence="speculative",
            recommended=("Chalice of the Void", "Surgical Extraction", "Toxic Deluge"),
            observed_frequency={
                "Surgical Extraction": 1.0, "Ravenous Trap": 0.75, "Rest in Peace": 0.25,
            },
            overlap=("Surgical Extraction",),
            scorer_only=("Chalice of the Void", "Toxic Deluge"),
            winners_only=("Ravenous Trap", "Rest in Peace"),
        )
        monkeypatch.setattr(backtest_mod, "backtest_board", lambda *a, **k: fake_result)

        result = runner.invoke(
            main,
            ["advise", "backtest", "--archetype", "Boulder", "--field", str(field_file), "--db", db_path],
        )
        assert result.exit_code == 0, result.output

        out = result.output
        assert "// backtest: Boulder" in out
        assert "// confidence: speculative" in out
        assert "HONEST DEGRADE" in out
        assert "Overlap" in out
        assert "Scorer-only" in out
        assert "Winners-only" in out
        assert "Surgical Extraction" in out
        assert "Ravenous Trap" in out
        assert (
            "// divergence is a signal to investigate, not proof of error "
            "(winning boards are self-selected + metagame-lagged)" in out
        )

    def test_advise_backtest_no_data_shows_insufficient_data_banner(self, tmp_path, runner, monkeypatch):
        """When there is nothing to compare against, the CLI must say so plainly and
        still exit 0 — never a crash, never a fabricated verdict."""
        db_path = _build_backtest_db(tmp_path)
        field_file = tmp_path / "field.txt"
        field_file.write_text("1.0 Boulder\n")

        empty_result = BoardBacktest(
            archetype="Nonexistent",
            n_winning_decks=0,
            confidence=None,
            recommended=(),
            observed_frequency={},
            overlap=(),
            scorer_only=(),
            winners_only=(),
        )
        monkeypatch.setattr(backtest_mod, "backtest_board", lambda *a, **k: empty_result)

        result = runner.invoke(
            main,
            ["advise", "backtest", "--archetype", "Nonexistent", "--field", str(field_file), "--db", db_path],
        )
        assert result.exit_code == 0, result.output
        assert "insufficient data" in result.output.lower()
        assert (
            "// divergence is a signal to investigate, not proof of error "
            "(winning boards are self-selected + metagame-lagged)" in result.output
        )

    def test_advise_backtest_field_scope_on_by_default_excludes_off_field_tournament(
        self, tmp_path, runner, monkeypatch
    ):
        """End-to-end (real `backtest_board`, monkeypatched scorer only): the CLI's
        default run excludes T3 (off-field) and prints the field-scope banner with the
        correct considered/excluded counts."""
        db_path = _build_backtest_db(tmp_path)
        field_file = tmp_path / "field.txt"
        field_file.write_text("0.6 Boulder\n0.4 Doomsday\n")

        monkeypatch.setattr(
            backtest_mod, "recommend_sideboard", lambda *a, **k: _fake_package({})
        )

        result = runner.invoke(
            main,
            ["advise", "backtest", "--archetype", "Boulder", "--field", str(field_file), "--db", db_path],
        )
        assert result.exit_code == 0, result.output
        out = result.output
        assert "// field-scope: ON" in out
        assert "1/3 candidate tournaments excluded as off-field" in out
        assert "// top-finisher decks sampled: 4" in out
        assert "Grafdigger's Cage" not in out

    def test_advise_backtest_no_field_scope_flag_includes_off_field_tournament(
        self, tmp_path, runner, monkeypatch
    ):
        """`--no-field-scope` reproduces the prior global (unscoped) sample end-to-end."""
        db_path = _build_backtest_db(tmp_path)
        field_file = tmp_path / "field.txt"
        field_file.write_text("0.6 Boulder\n0.4 Doomsday\n")

        monkeypatch.setattr(
            backtest_mod, "recommend_sideboard", lambda *a, **k: _fake_package({})
        )

        result = runner.invoke(
            main,
            [
                "advise", "backtest", "--archetype", "Boulder", "--field", str(field_file),
                "--db", db_path, "--no-field-scope",
            ],
        )
        assert result.exit_code == 0, result.output
        out = result.output
        assert "// field-scope: OFF" in out
        assert "// top-finisher decks sampled: 6" in out
        assert "Grafdigger's Cage" in out

    def test_advise_backtest_field_scope_exhausts_sample_shows_specific_degrade(
        self, tmp_path, runner, monkeypatch
    ):
        """When field-scoping excludes every candidate tournament, the CLI names that
        specific reason (not the generic "no top-finisher decks" message) and still
        prints the unconditional caveat — never a crash, never a verdict."""
        db_path = _build_backtest_db(tmp_path)
        field_file = tmp_path / "field.txt"
        field_file.write_text("1.0 Some Unrelated Archetype\n")

        monkeypatch.setattr(
            backtest_mod, "recommend_sideboard", lambda *a, **k: _fake_package({})
        )

        result = runner.invoke(
            main,
            ["advise", "backtest", "--archetype", "Boulder", "--field", str(field_file), "--db", db_path],
        )
        assert result.exit_code == 0, result.output
        out = result.output
        assert "field-scope excluded all 3 candidate tournament(s) as off-field" in out
        assert (
            "// divergence is a signal to investigate, not proof of error "
            "(winning boards are self-selected + metagame-lagged)" in out
        )
