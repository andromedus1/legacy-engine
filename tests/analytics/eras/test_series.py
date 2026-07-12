"""Tests for analytics.eras.series — build_entity_series.

House style: hermetic in-memory DuckDB, hand-built synthetic corpus (one tournament per ISO
week), TestX classes, deterministic. Never touches the default DB (`--db` convention doesn't
apply here — this module has no CLI surface — but the underlying DB is always ``:memory:``).

Synthetic corpus (8 consecutive Mondays starting 2026-01-05):
    Alpha : 15 decks/week (weeks 0-6), 3 decks/week (week 7, the trailing partial week).
            10/15 (2/3 in week 7) tagged ``variant="CampX"`` -> a qualifying camp entity.
            Runs "Filler Card" (100% inclusion, excluded from every flex band) always; CampX
            decks additionally run "Signature Card" (67% of Alpha's whole pool -> IN Alpha's
            flex band; 100% of CampX's own pool -> NOT in CampX's own flex band).
    Beta  : 3 decks/week, all 8 weeks (low density -> 4-week buckets). 2/3 tagged
            ``variant="ThinCamp"`` (below the camp floor -> never its own entity).
    Gamma : 7 decks/week, all 8 weeks (mid density -> 2-week buckets).
    Delta : 4 decks/week, weeks 0-1 ONLY (small total -> below the entity floor, always absent).
    Rounds: week 0 only, 3 decisive matches, each an Alpha deck beating a Beta deck 2-0.
    Provenance: every tournament is "paper" except week 7, which is "online".
"""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import pytest

from legacy_engine.analytics.eras.series import build_entity_series

_WEEK0 = date(2026, 1, 5)  # a Monday
assert _WEEK0.isoweekday() == 1


def _load_week(con: duckdb.DuckDBPyConnection, week_idx: int, monday: date) -> None:
    """Load one week's synthetic tournament (decks, cards, rounds) and label it."""
    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.cache import parse_cache_item

    alpha_n = 3 if week_idx == 7 else 15
    campx_n = 2 if week_idx == 7 else 10

    decks: list[dict] = []
    for j in range(alpha_n):
        mainboard = [{"Count": 4, "CardName": "Filler Card"}]
        if j < campx_n:
            mainboard.append({"Count": 2, "CardName": "Signature Card"})
        decks.append({"Player": f"alpha_{week_idx}_{j}", "Mainboard": mainboard, "Sideboard": []})
    for j in range(3):
        decks.append({
            "Player": f"beta_{week_idx}_{j}",
            "Mainboard": [{"Count": 4, "CardName": "Filler Card"}],
            "Sideboard": [],
        })
    for j in range(7):
        decks.append({
            "Player": f"gamma_{week_idx}_{j}",
            "Mainboard": [{"Count": 4, "CardName": "Filler Card"}],
            "Sideboard": [],
        })
    if week_idx < 2:
        for j in range(4):
            decks.append({
                "Player": f"delta_{week_idx}_{j}",
                "Mainboard": [{"Count": 4, "CardName": "Filler Card"}],
                "Sideboard": [],
            })

    rounds: list[dict] = []
    if week_idx == 0:
        # Only 3 Beta decks exist per week — one decisive match per Beta player.
        rounds = [
            {"Player1": f"alpha_0_{j}", "Player2": f"beta_0_{j}", "Result": "2-0"}
            for j in range(3)
        ]

    raw = {
        "Tournament": {
            "Name": f"Week {week_idx}",
            "Date": monday.isoformat(),
            "Uri": f"https://example.com/week-{week_idx}",
            "Formats": "Legacy",
        },
        "Decks": decks,
        "Rounds": rounds,
        "Standings": [],
    }
    tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))

    con.execute(
        "UPDATE decks SET archetype = 'Alpha' WHERE tournament_id = ? AND player LIKE ?",
        [tid, f"alpha_{week_idx}_%"],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Beta' WHERE tournament_id = ? AND player LIKE ?",
        [tid, f"beta_{week_idx}_%"],
    )
    con.execute(
        "UPDATE decks SET archetype = 'Gamma' WHERE tournament_id = ? AND player LIKE ?",
        [tid, f"gamma_{week_idx}_%"],
    )
    if week_idx < 2:
        con.execute(
            "UPDATE decks SET archetype = 'Delta' WHERE tournament_id = ? AND player LIKE ?",
            [tid, f"delta_{week_idx}_%"],
        )
    for j in range(campx_n):
        con.execute(
            "UPDATE decks SET variant = 'CampX' WHERE tournament_id = ? AND player = ?",
            [tid, f"alpha_{week_idx}_{j}"],
        )
    for j in range(2):
        con.execute(
            "UPDATE decks SET variant = 'ThinCamp' WHERE tournament_id = ? AND player = ?",
            [tid, f"beta_{week_idx}_{j}"],
        )

    provenance = "online" if week_idx == 7 else "paper"
    con.execute("UPDATE tournaments SET provenance = ? WHERE id = ?", [provenance, tid])


def _build_corpus() -> duckdb.DuckDBPyConnection:
    from legacy_engine.ingestion import store

    con = store.connect(":memory:")
    for i in range(8):
        _load_week(con, i, _WEEK0 + timedelta(weeks=i))
    return con


@pytest.fixture(scope="module")
def corpus() -> duckdb.DuckDBPyConnection:
    return _build_corpus()


# ---------------------------------------------------------------------------
# Spot-week exactness (Alpha: bucket_weeks == 1, so buckets align 1:1 with weeks)
# ---------------------------------------------------------------------------


class TestSpotWeeks:
    def test_alpha_qualifies_with_default_floors_and_is_weekly(self, corpus):
        series = build_entity_series(corpus)
        alpha = series["Alpha"]
        assert alpha.entity == "Alpha"
        assert alpha.parent == "Alpha"
        assert alpha.bucket_weeks == 1  # median weekly decks (15) >= 10
        assert len(alpha.buckets) == 8

    def test_week_0_bucket_exact(self, corpus):
        series = build_entity_series(corpus)
        b0 = series["Alpha"].buckets[0]
        assert b0.start == _WEEK0.isoformat()
        assert b0.decks == 15
        assert b0.field_decks == 29  # 15 Alpha + 3 Beta + 7 Gamma + 4 Delta
        assert b0.wins == 3   # 3 decisive Alpha-beats-Beta matches
        assert b0.losses == 0
        assert b0.complete is True  # corpus starts exactly on this bucket's Monday

    def test_week_3_bucket_exact(self, corpus):
        series = build_entity_series(corpus)
        b3 = series["Alpha"].buckets[3]
        assert b3.start == (_WEEK0 + timedelta(weeks=3)).isoformat()
        assert b3.decks == 15
        assert b3.field_decks == 25  # Delta has already dropped out by week 3
        assert b3.wins == 0
        assert b3.losses == 0
        assert b3.complete is True

    def test_week_7_trailing_bucket_is_partial(self, corpus):
        series = build_entity_series(corpus)
        b7 = series["Alpha"].buckets[7]
        assert b7.start == (_WEEK0 + timedelta(weeks=7)).isoformat()
        assert b7.decks == 3
        assert b7.field_decks == 13  # 3 Alpha + 3 Beta + 7 Gamma
        assert b7.complete is False  # trailing partial bucket


# ---------------------------------------------------------------------------
# Entity floors
# ---------------------------------------------------------------------------


class TestEntityFloors:
    def test_default_floor_only_alpha_survives(self, corpus):
        series = build_entity_series(corpus)  # default min_entity_decks=100
        assert "Alpha" in series          # 105 (paper) + 3 (online) = 108 total
        assert "Beta" not in series       # 24 total
        assert "Gamma" not in series       # 56 total
        assert "Delta" not in series       # 8 total

    def test_lowered_floor_admits_beta_and_gamma_but_not_delta(self, corpus):
        series = build_entity_series(corpus, min_entity_decks=20)
        assert "Alpha" in series
        assert "Beta" in series
        assert "Gamma" in series
        assert "Delta" not in series  # 8 total decks, below even the lowered floor


# ---------------------------------------------------------------------------
# Density-adaptive bucket width
# ---------------------------------------------------------------------------


class TestDensityBucketing:
    def test_low_density_entity_gets_wider_buckets(self, corpus):
        series = build_entity_series(corpus, min_entity_decks=20)
        assert series["Alpha"].bucket_weeks == 1   # median 15/week
        assert series["Gamma"].bucket_weeks == 2   # median 7/week
        assert series["Beta"].bucket_weeks == 4    # median 3/week

    def test_gamma_two_week_buckets_group_correctly(self, corpus):
        series = build_entity_series(corpus, min_entity_decks=20)
        gamma = series["Gamma"]
        assert len(gamma.buckets) == 4  # 8 canonical weeks / 2
        assert gamma.buckets[0].decks == 14   # 7 + 7
        assert gamma.buckets[0].field_decks == 58  # 29 + 29
        last = gamma.buckets[-1]
        assert last.decks == 14
        assert last.field_decks == 38  # week6 (25) + week7 (13)
        assert last.complete is False


# ---------------------------------------------------------------------------
# Camp entities
# ---------------------------------------------------------------------------


class TestCampEntities:
    def test_campx_qualifies_as_its_own_entity(self, corpus):
        series = build_entity_series(corpus, min_entity_decks=20)
        assert "Alpha [CampX]" in series
        campx = series["Alpha [CampX]"]
        assert campx.parent == "Alpha"
        # 10/week for 7 weeks + 2 in the trailing week
        assert sum(b.decks for b in campx.buckets) == 72

    def test_thin_camp_never_becomes_its_own_entity(self, corpus):
        series = build_entity_series(corpus, min_entity_decks=20, min_camp_decks=30)
        assert "Beta [ThinCamp]" not in series  # 2/week * 8 = 16 < 30

    def test_thin_camp_present_when_floor_lowered_enough(self, corpus):
        series = build_entity_series(corpus, min_entity_decks=20, min_camp_decks=10)
        assert "Beta [ThinCamp]" in series

    def test_signature_card_is_in_alphas_flex_band_not_campxs(self, corpus):
        series = build_entity_series(corpus, min_entity_decks=20)
        assert "Signature Card" in series["Alpha"].flex_cards
        assert "Signature Card" not in series["Alpha [CampX]"].flex_cards
        assert "Filler Card" not in series["Alpha"].flex_cards  # 100% inclusion -> excluded


# ---------------------------------------------------------------------------
# Provenance filter
# ---------------------------------------------------------------------------


class TestProvenanceFilter:
    def test_paper_only_excludes_the_online_trailing_week(self, corpus):
        series = build_entity_series(corpus, provenance="paper")
        alpha = series["Alpha"]
        assert len(alpha.buckets) == 7  # week 7 (online) dropped entirely
        assert alpha.buckets[-1].start == (_WEEK0 + timedelta(weeks=6)).isoformat()
        # the "paper" corpus now ends at week 6 -> that bucket is the trailing partial one
        assert alpha.buckets[-1].complete is False

    def test_online_only_returns_just_the_trailing_week(self, corpus):
        series = build_entity_series(corpus, provenance="online", min_entity_decks=1)
        alpha = series["Alpha"]
        assert len(alpha.buckets) == 1
        assert alpha.buckets[0].decks == 3


# ---------------------------------------------------------------------------
# Hermetic / empty-corpus behavior
# ---------------------------------------------------------------------------


class TestHermeticAndEmpty:
    def test_empty_db_returns_empty_dict(self):
        from legacy_engine.ingestion import store

        con = store.connect(":memory:")
        store.init_schema(con)
        assert build_entity_series(con) == {}

    def test_runs_entirely_against_a_tmp_in_memory_db(self, corpus):
        # No reference anywhere in this module to config.DUCKDB_PATH / the default DB file.
        series = build_entity_series(corpus, min_entity_decks=20)
        assert series  # non-empty; proves the query path works against an in-memory connection


# ---------------------------------------------------------------------------
# Leading partial bucket (corpus starting mid-bucket)
# ---------------------------------------------------------------------------


class TestLeadingPartialBucket:
    def test_first_bucket_incomplete_when_corpus_starts_mid_week(self):
        from legacy_engine.ingestion import store
        from legacy_engine.ingestion.cache import parse_cache_item

        con = store.connect(":memory:")
        mid_week_date = _WEEK0 + timedelta(days=2)  # Wednesday of week 0
        next_monday = _WEEK0 + timedelta(weeks=1)

        for idx, d in enumerate([mid_week_date, next_monday]):
            raw = {
                "Tournament": {
                    "Name": f"Solo {idx}",
                    "Date": d.isoformat(),
                    "Uri": f"https://example.com/solo-{idx}",
                    "Formats": "Legacy",
                },
                "Decks": [
                    {"Player": f"solo_{idx}_{j}", "Mainboard": [], "Sideboard": []}
                    for j in range(15)
                ],
                "Rounds": [],
                "Standings": [],
            }
            tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
            con.execute(
                "UPDATE decks SET archetype = 'Solo' WHERE tournament_id = ?", [tid]
            )
            con.execute("UPDATE tournaments SET provenance = 'paper' WHERE id = ?", [tid])

        series = build_entity_series(con, min_entity_decks=1)
        solo = series["Solo"]
        assert solo.buckets[0].start == _WEEK0.isoformat()
        assert solo.buckets[0].complete is False  # corpus's first tournament lands on Wednesday
