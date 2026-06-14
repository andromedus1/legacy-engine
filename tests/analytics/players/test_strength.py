"""Tests for analytics.players.strength — PlayerRecord, compute_player_records, is_strong."""

from __future__ import annotations

import pytest
import duckdb

from legacy_engine.analytics.players.strength import (
    PlayerRecord,
    compute_player_records,
    is_strong,
    strong_player_set,
)
from legacy_engine.analytics.matchup import beta_binomial_shrink_to
from legacy_engine.confidence import tier_for_sample


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_con() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with tournaments + standings tables."""
    con = duckdb.connect(":memory:")
    con.execute(
        "CREATE TABLE tournaments ("
        "id VARCHAR PRIMARY KEY, name VARCHAR, date VARCHAR, "
        "uri VARCHAR, format VARCHAR, source VARCHAR, provenance VARCHAR)"
    )
    con.execute(
        "CREATE TABLE standings ("
        "tournament_id VARCHAR, rank INTEGER, player VARCHAR, "
        "points INTEGER, wins INTEGER, losses INTEGER, draws INTEGER)"
    )
    return con


def _add_tournament(con: duckdb.DuckDBPyConnection, tid: str, date: str, provenance: str = "paper") -> None:
    con.execute(
        "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
        [tid, f"Event {tid}", date, f"https://{tid}", "Legacy", "paper", provenance],
    )


def _add_standing(
    con: duckdb.DuckDBPyConnection,
    tid: str,
    player: str,
    rank: int,
    wins: int,
    losses: int,
    draws: int = 0,
    points: int = 0,
) -> None:
    con.execute(
        "INSERT INTO standings VALUES (?, ?, ?, ?, ?, ?, ?)",
        [tid, rank, player, points, wins, losses, draws],
    )


@pytest.fixture
def single_5_0_con() -> duckdb.DuckDBPyConnection:
    """One player with a single 5-0 finish: events=1, n≈7 decisive matches."""
    con = _make_con()
    _add_tournament(con, "t1", "2026-01-01")
    # A 5-0 finish in a Legacy challenge: ~7 matches rounds typical
    _add_standing(con, "t1", "HotNewPlayer", rank=1, wins=5, losses=0)
    return con


@pytest.fixture
def sustained_player_con() -> duckdb.DuckDBPyConnection:
    """One player with sustained results across 5 events: 25W-10L total."""
    con = _make_con()
    dates = ["2026-01-01", "2026-01-15", "2026-02-01", "2026-02-15", "2026-03-01"]
    for i, d in enumerate(dates):
        tid = f"t{i + 1}"
        _add_tournament(con, tid, d)
        # 5W-2L per event × 5 = 25W-10L total
        _add_standing(con, tid, "SustainedPlayer", rank=2, wins=5, losses=2)
    return con


@pytest.fixture
def two_event_player_con() -> duckdb.DuckDBPyConnection:
    """A 6-0 player across 2 events (12W-0L): beats min_win_rate but not min_events=3."""
    con = _make_con()
    for i in range(2):
        tid = f"t{i + 1}"
        _add_tournament(con, tid, f"2026-0{i + 1}-01")
        _add_standing(con, tid, "TwoEventStar", rank=1, wins=6, losses=0)
    return con


@pytest.fixture
def alias_bosh_map() -> dict[str, str]:
    """Bosh cluster alias map: three handles → 'bosh-n-roll'."""
    return {
        "bosh n roll": "bosh-n-roll",
        "boshnroll_brian": "bosh-n-roll",
        "bosh95": "bosh-n-roll",
    }


@pytest.fixture
def bosh_alias_con(alias_bosh_map: dict[str, str]) -> duckdb.DuckDBPyConnection:
    """Three Bosh* handles each appearing in separate events."""
    con = _make_con()
    handles = ["Bosh N Roll", "BoshNRoll_Brian", "Bosh95"]
    # Each handle appears in ~3 events: 5 events total = 15 events for 1 logical player
    # wins/losses: 7W-3L per event = 70W-30L total across all 10 events
    for i, handle in enumerate(handles):
        for j in range(4):
            tid = f"t{i * 4 + j}"
            date = f"2026-{(i + 1):02d}-{(j * 7 + 1):02d}"
            _add_tournament(con, tid, date)
            _add_standing(con, tid, handle, rank=2, wins=7, losses=3)
    return con


# ---------------------------------------------------------------------------
# Unit 1 — compute_player_records: basic aggregation
# ---------------------------------------------------------------------------


class TestComputePlayerRecords:
    def test_single_5_0_aggregation(self, single_5_0_con: duckdb.DuckDBPyConnection) -> None:
        records = compute_player_records(single_5_0_con, alias_map={})
        assert "hotnewplayer" in records
        rec = records["hotnewplayer"]
        assert rec.events == 1
        assert rec.match_wins == 5
        assert rec.match_losses == 0
        assert rec.match_draws == 0

    def test_sustained_player_aggregation(self, sustained_player_con: duckdb.DuckDBPyConnection) -> None:
        records = compute_player_records(sustained_player_con, alias_map={})
        assert "sustainedplayer" in records
        rec = records["sustainedplayer"]
        assert rec.events == 5
        assert rec.match_wins == 25
        assert rec.match_losses == 10

    def test_shrinkage_applied(self, sustained_player_con: duckdb.DuckDBPyConnection) -> None:
        """win_rate_shrunk is not the raw rate but the shrunk estimate."""
        records = compute_player_records(sustained_player_con, alias_map={})
        rec = records["sustainedplayer"]
        raw_rate = 25 / 35  # 0.714...
        expected_shrunk = beta_binomial_shrink_to(25, 35, prior_mean=0.5, strength=15.0)
        assert abs(rec.win_rate_shrunk - expected_shrunk) < 1e-9
        # Shrinkage pulls below raw rate
        assert rec.win_rate_shrunk < raw_rate

    def test_tier_computed_correctly(self, sustained_player_con: duckdb.DuckDBPyConnection) -> None:
        """Tier is derived from decisive matches (wins + losses)."""
        records = compute_player_records(sustained_player_con, alias_map={})
        rec = records["sustainedplayer"]
        expected_tier = tier_for_sample(35)  # 25+10 = 35 decisive
        assert rec.tier == expected_tier

    def test_single_5_0_tier_is_speculative(self, single_5_0_con: duckdb.DuckDBPyConnection) -> None:
        records = compute_player_records(single_5_0_con, alias_map={})
        rec = records["hotnewplayer"]
        # 5 decisive matches → speculative
        assert rec.tier == "speculative"

    def test_top_finishes_counted(self, single_5_0_con: duckdb.DuckDBPyConnection) -> None:
        records = compute_player_records(single_5_0_con, alias_map={})
        rec = records["hotnewplayer"]
        # rank=1 ≤ default cut_size=8 → 1 top finish
        assert rec.top_finishes == 1

    def test_custom_cut_size(self, sustained_player_con: duckdb.DuckDBPyConnection) -> None:
        """With cut_size=1 only rank=1 finishes count."""
        records = compute_player_records(sustained_player_con, alias_map={}, cut_size=1)
        rec = records["sustainedplayer"]
        # rank=2 in every event → 0 top finishes with cut_size=1
        assert rec.top_finishes == 0

    def test_window_since_filters_events(
        self, sustained_player_con: duckdb.DuckDBPyConnection
    ) -> None:
        """since filter excludes earlier events."""
        records_all = compute_player_records(sustained_player_con, alias_map={})
        records_windowed = compute_player_records(
            sustained_player_con, alias_map={}, since="2026-02-01"
        )
        rec_all = records_all["sustainedplayer"]
        rec_windowed = records_windowed["sustainedplayer"]
        # since=2026-02-01 includes events on 2026-02-01, 2026-02-15, 2026-03-01 → 3 events
        assert rec_windowed.events == 3
        assert rec_windowed.events < rec_all.events

    def test_window_until_filters_events(
        self, sustained_player_con: duckdb.DuckDBPyConnection
    ) -> None:
        """until filter excludes later events (half-open [since, until))."""
        records = compute_player_records(
            sustained_player_con, alias_map={}, until="2026-02-01"
        )
        rec = records["sustainedplayer"]
        # until=2026-02-01 excludes 2026-02-01+ → 2 events (2026-01-01, 2026-01-15)
        assert rec.events == 2

    def test_determinism(self, sustained_player_con: duckdb.DuckDBPyConnection) -> None:
        """Same corpus → identical PlayerRecord on repeated calls."""
        r1 = compute_player_records(sustained_player_con, alias_map={})
        r2 = compute_player_records(sustained_player_con, alias_map={})
        rec1 = r1["sustainedplayer"]
        rec2 = r2["sustainedplayer"]
        assert rec1.win_rate_shrunk == rec2.win_rate_shrunk
        assert rec1.tier == rec2.tier
        assert rec1.events == rec2.events

    def test_empty_standings_returns_empty(self) -> None:
        con = _make_con()
        records = compute_player_records(con, alias_map={})
        assert records == {}

    def test_provenance_filter(self, sustained_player_con: duckdb.DuckDBPyConnection) -> None:
        """provenance='online' returns no records when all events are 'paper'."""
        records = compute_player_records(sustained_player_con, alias_map={}, provenance="online")
        assert records == {}

    def test_provenance_paper_returns_records(
        self, sustained_player_con: duckdb.DuckDBPyConnection
    ) -> None:
        records = compute_player_records(sustained_player_con, alias_map={}, provenance="paper")
        assert "sustainedplayer" in records


# ---------------------------------------------------------------------------
# Unit 1 — alias pooling in compute_player_records
# ---------------------------------------------------------------------------


class TestAliasPooling:
    def test_bosh_aliases_pool_into_one_record(
        self,
        bosh_alias_con: duckdb.DuckDBPyConnection,
        alias_bosh_map: dict[str, str],
    ) -> None:
        """Three Bosh* handles should produce one PlayerRecord under 'bosh-n-roll'."""
        records = compute_player_records(bosh_alias_con, alias_map=alias_bosh_map)
        # Only one canonical player id
        assert "bosh-n-roll" in records
        # None of the raw normalized handles appear as separate keys
        assert "bosh n roll" not in records
        assert "boshnroll_brian" not in records
        assert "bosh95" not in records

    def test_alias_pooling_sums_stats(
        self,
        bosh_alias_con: duckdb.DuckDBPyConnection,
        alias_bosh_map: dict[str, str],
    ) -> None:
        """Stats from all three handles are summed into the single record."""
        records = compute_player_records(bosh_alias_con, alias_map=alias_bosh_map)
        rec = records["bosh-n-roll"]
        # 3 handles × 4 events each = 12 events; 7W-3L × 12 = 84W-36L
        assert rec.events == 12
        assert rec.match_wins == 84
        assert rec.match_losses == 36

    def test_alias_pooling_tier(
        self,
        bosh_alias_con: duckdb.DuckDBPyConnection,
        alias_bosh_map: dict[str, str],
    ) -> None:
        """Pooled record has enough volume to reach established tier."""
        records = compute_player_records(bosh_alias_con, alias_map=alias_bosh_map)
        rec = records["bosh-n-roll"]
        # 84+36 = 120 decisive matches → established
        assert rec.tier == "established"

    def test_no_alias_map_keeps_handles_separate(
        self, bosh_alias_con: duckdb.DuckDBPyConnection
    ) -> None:
        """With empty alias_map, each handle is its own record (gated-additive)."""
        records = compute_player_records(bosh_alias_con, alias_map={})
        assert "bosh n roll" in records
        assert "boshnroll_brian" in records
        assert "bosh95" in records
        # The canonical id should not appear as a key
        assert "bosh-n-roll" not in records


# ---------------------------------------------------------------------------
# Unit 2 — is_strong: the "single 5-0 isn't strong" guarantee
# ---------------------------------------------------------------------------


class TestIsStrong:
    def test_single_5_0_is_not_strong(self, single_5_0_con: duckdb.DuckDBPyConnection) -> None:
        """The spec's core requirement: a single hot finish never qualifies as strong."""
        records = compute_player_records(single_5_0_con, alias_map={})
        rec = records["hotnewplayer"]
        assert not is_strong(rec)

    def test_single_5_0_fails_event_floor(self, single_5_0_con: duckdb.DuckDBPyConnection) -> None:
        """events=1 fails min_events=3."""
        records = compute_player_records(single_5_0_con, alias_map={})
        rec = records["hotnewplayer"]
        assert rec.events == 1
        assert rec.events < 3

    def test_single_5_0_is_speculative_tier(
        self, single_5_0_con: duckdb.DuckDBPyConnection
    ) -> None:
        """n≈5 decisive matches → speculative tier."""
        records = compute_player_records(single_5_0_con, alias_map={})
        rec = records["hotnewplayer"]
        assert rec.tier == "speculative"

    def test_sustained_player_is_strong(
        self, sustained_player_con: duckdb.DuckDBPyConnection
    ) -> None:
        """25W-10L across 5 events satisfies all three gates."""
        records = compute_player_records(sustained_player_con, alias_map={})
        rec = records["sustainedplayer"]
        # Verify preconditions
        assert rec.events >= 3
        assert rec.tier in ("evolving", "established")
        assert rec.win_rate_shrunk >= 0.55
        assert is_strong(rec)

    def test_two_event_player_not_strong(
        self, two_event_player_con: duckdb.DuckDBPyConnection
    ) -> None:
        """6-0 across 2 events: fails events floor (min_events=3)."""
        records = compute_player_records(two_event_player_con, alias_map={})
        rec = records["twoeventstar"]
        assert rec.events == 2
        assert not is_strong(rec)

    def test_custom_min_events(self, two_event_player_con: duckdb.DuckDBPyConnection) -> None:
        """A player with 2 events clears the gate when min_events=2 and enough matches."""
        records = compute_player_records(two_event_player_con, alias_map={})
        rec = records["twoeventstar"]
        # 12W-0L → shrunk around 0.81; but n=12 → speculative tier
        # With min_tier="speculative" and min_events=2 they pass events+tier gates
        result = is_strong(rec, min_events=2, min_tier="speculative", min_win_rate=0.55)
        assert result

    def test_shrinkage_pulls_perfect_record_down(
        self, two_event_player_con: duckdb.DuckDBPyConnection
    ) -> None:
        """A 6-0/2-event player has shrunk rate < 1.0."""
        records = compute_player_records(two_event_player_con, alias_map={})
        rec = records["twoeventstar"]
        assert rec.win_rate_shrunk < 1.0

    def test_win_rate_gate(self) -> None:
        """A player with events+tier but low win-rate fails the win-rate gate."""
        # Build a .500 player across many events
        con = _make_con()
        for i in range(5):
            tid = f"t{i}"
            _add_tournament(con, tid, f"2026-0{i + 1}-01")
            _add_standing(con, tid, "MidPlayer", rank=5, wins=6, losses=6)
        records = compute_player_records(con, alias_map={})
        rec = records["midplayer"]
        assert rec.events == 5
        assert rec.tier in ("evolving", "established")  # 60 decisive matches → established
        assert not is_strong(rec)  # win_rate_shrunk < 0.55

    def test_is_strong_with_alias_pooling(
        self,
        bosh_alias_con: duckdb.DuckDBPyConnection,
        alias_bosh_map: dict[str, str],
    ) -> None:
        """Bosh cluster pooled record clears all gates."""
        records = compute_player_records(bosh_alias_con, alias_map=alias_bosh_map)
        rec = records["bosh-n-roll"]
        assert is_strong(rec)


# ---------------------------------------------------------------------------
# Unit 2 — strong_player_set
# ---------------------------------------------------------------------------


class TestStrongPlayerSet:
    def test_single_5_0_not_in_strong_set(
        self, single_5_0_con: duckdb.DuckDBPyConnection
    ) -> None:
        records = compute_player_records(single_5_0_con, alias_map={})
        strong = strong_player_set(records)
        assert "hotnewplayer" not in strong

    def test_sustained_player_in_strong_set(
        self, sustained_player_con: duckdb.DuckDBPyConnection
    ) -> None:
        records = compute_player_records(sustained_player_con, alias_map={})
        strong = strong_player_set(records)
        assert "sustainedplayer" in strong

    def test_mixed_corpus_filters_correctly(self) -> None:
        """In a corpus with one strong and one weak player, only strong appears."""
        con = _make_con()
        # Strong player: 5 events, 7W-2L each = 35W-10L total
        for i in range(5):
            tid = f"strong_{i}"
            _add_tournament(con, tid, f"2026-0{i + 1}-01")
            _add_standing(con, tid, "StrongPilot", rank=2, wins=7, losses=2)
        # Weak player: 1 event, 5W-0L (the single 5-0 case)
        _add_tournament(con, "weak_0", "2026-06-01")
        _add_standing(con, "weak_0", "OneTimeLucky", rank=1, wins=5, losses=0)

        records = compute_player_records(con, alias_map={})
        strong = strong_player_set(records)
        assert "strongpilot" in strong
        assert "onetimelucky" not in strong

    def test_empty_records_returns_empty_set(self) -> None:
        assert strong_player_set({}) == set()

    def test_returns_set_of_player_ids(
        self, sustained_player_con: duckdb.DuckDBPyConnection
    ) -> None:
        records = compute_player_records(sustained_player_con, alias_map={})
        strong = strong_player_set(records)
        assert isinstance(strong, set)
        for pid in strong:
            assert isinstance(pid, str)
