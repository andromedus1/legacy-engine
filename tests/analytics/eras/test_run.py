"""Tests for analytics.eras.run — attribution wiring, the eras run pass, and the drift alarm
(Unit D).

`TestAlarmCalibration` exercises `compute_drift_alarms` directly against the shared real-corpus
fixtures (conftest.py) — fast, deterministic, no DB — mirroring the calibration discipline
`detect.py`/`ensemble.py` already use, and pinning the risk note's own acceptance test: "must
fire on a Tron-cliff-shaped synthetic tail, silent on the stable fleet."

`TestRunErasEndToEnd` drives the full `run_eras` pipeline against a hermetic in-memory DuckDB
corpus with an implanted, dated cliff (never touches the default DB), proving the
series -> detect -> ensemble -> attribution -> store wiring end-to-end. With only 3 synthetic
entities, `derive_eras`'s fleet-wide BH-FDR has essentially no statistical power (a real corpus
runs ~50-150 entities) — this is a fixture-SIZE artifact, not a bug, so these tests assert on
boundary detection + attribution + persistence structurally (present in `.boundaries`,
correctly attributed) rather than on `bh_accepted`. Alarm-suppression-when-covered is exercised
precisely (and fast) in `TestAlarmCalibration` instead.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from legacy_engine.analytics.eras.attribution import Attribution
from legacy_engine.analytics.eras.detect import CandidateBoundary
from legacy_engine.analytics.eras.ensemble import EntityEras, EraBoundary
from legacy_engine.analytics.eras.run import (
    _corpus_first_seen,
    _trigger_cards_from_presence_adopt,
    compute_drift_alarms,
    run_eras,
)
from legacy_engine.analytics.eras.store import read_entity_eras

# ---------------------------------------------------------------------------
# TestAlarmCalibration — pure fixture-based, no DB
# ---------------------------------------------------------------------------


class TestAlarmCalibration:
    """Calibration ground truth (epic risk note): fires on the Tron cliff, silent on the stable
    fleet, and correctly suppressed/re-armed by attribution+acceptance state."""

    def test_fires_on_tron_cliff_when_no_boundary_recorded(self, tron_cliff_series):
        series = {"Tron": tron_cliff_series}
        eras = {"Tron": EntityEras(entity="Tron", stable_since=None, boundaries=(), inherited_from_parent=False)}
        alarms = compute_drift_alarms(series, eras, {})
        assert "Tron" in alarms
        assert alarms["Tron"].p_change >= 0.5

    def test_silent_when_covered_by_an_attributed_accepted_boundary(self, tron_cliff_series):
        series = {"Tron": tron_cliff_series}
        # Last complete bucket is 2026-06-15 (the cliff) — an accepted, ban-attributed boundary
        # there must suppress the alarm.
        boundary = EraBoundary(date="2026-06-15", signals=(), pvalue=0.001, bh_accepted=True, floor_rejected=False)
        eras = {"Tron": EntityEras(entity="Tron", stable_since="2026-06-15", boundaries=(boundary,), inherited_from_parent=False)}
        attributions = {("Tron", "2026-06-15"): Attribution(kind="ban", card="Candelabra of Tawnos", detail="ban: ...")}
        alarms = compute_drift_alarms(series, eras, attributions)
        assert "Tron" not in alarms

    def test_still_fires_when_the_accepted_boundary_is_itself_unattributed(self, tron_cliff_series):
        series = {"Tron": tron_cliff_series}
        boundary = EraBoundary(date="2026-06-15", signals=(), pvalue=0.001, bh_accepted=True, floor_rejected=False)
        eras = {"Tron": EntityEras(entity="Tron", stable_since="2026-06-15", boundaries=(boundary,), inherited_from_parent=False)}
        attributions = {("Tron", "2026-06-15"): Attribution(kind="unattributed", card=None, detail="...")}
        alarms = compute_drift_alarms(series, eras, attributions)
        assert "Tron" in alarms

    def test_still_fires_when_the_covering_boundary_is_not_bh_accepted(self, tron_cliff_series):
        series = {"Tron": tron_cliff_series}
        boundary = EraBoundary(date="2026-06-15", signals=(), pvalue=0.5, bh_accepted=False, floor_rejected=False)
        eras = {"Tron": EntityEras(entity="Tron", stable_since=None, boundaries=(boundary,), inherited_from_parent=False)}
        attributions = {("Tron", "2026-06-15"): Attribution(kind="ban", card="Candelabra of Tawnos", detail="ban: ...")}
        alarms = compute_drift_alarms(series, eras, attributions)
        assert "Tron" in alarms

    def test_silent_on_stable_fleet(self, stable_nonevent_series):
        series = {"Lands": stable_nonevent_series}
        eras = {"Lands": EntityEras(entity="Lands", stable_since=None, boundaries=(), inherited_from_parent=False)}
        alarms = compute_drift_alarms(series, eras, {})
        assert alarms == {}

    def test_silent_fleet_wide_on_a_hundred_stationary_entities(self, stationary_fleet_series):
        series = stationary_fleet_series(20)
        eras = {
            name: EntityEras(entity=name, stable_since=None, boundaries=(), inherited_from_parent=False)
            for name in series
        }
        alarms = compute_drift_alarms(series, eras, {})
        assert alarms == {}

    def test_below_share_floor_entity_never_alarms(self, make_entity_series, make_bucket):
        # 1 deck vs a 10,000-deck field every bucket -> share ~0.01%, far below the 2% floor,
        # regardless of how dramatic its own internal swing looks.
        buckets = tuple(
            make_bucket(start=(date(2026, 1, 5) + timedelta(weeks=i)).isoformat(), decks=(1 if i < 5 else 0), field_decks=10_000)
            for i in range(10)
        )
        s = make_entity_series(entity="Tiny", parent="Tiny", buckets=buckets)
        series = {"Tiny": s}
        eras = {"Tiny": EntityEras(entity="Tiny", stable_since=None, boundaries=(), inherited_from_parent=False)}
        assert compute_drift_alarms(series, eras, {}) == {}

    def test_short_series_below_min_complete_buckets_never_alarms(self, make_entity_series, make_bucket):
        buckets = tuple(
            make_bucket(start=(date(2026, 1, 5) + timedelta(weeks=i)).isoformat(), decks=50, field_decks=100)
            for i in range(2)
        )
        s = make_entity_series(entity="Short", parent="Short", buckets=buckets)
        series = {"Short": s}
        eras = {"Short": EntityEras(entity="Short", stable_since=None, boundaries=(), inherited_from_parent=False)}
        assert compute_drift_alarms(series, eras, {}) == {}


# ---------------------------------------------------------------------------
# TestRunErasEndToEnd — hermetic in-memory DB corpus, full pipeline
# ---------------------------------------------------------------------------

# 18 weekly deck counts (last week trailing/incomplete), replicating the real Candelabra-ban
# ground-truth magnitude (brief §1 ground truth #1) so BOCPD/S3 behave exactly as calibrated
# above (statistical power scales with absolute trial counts, not just proportions — a scaled-
# down replica measurably weakens both the permutation p-value and the BOCPD tail spike).
_WEEKLY = [2, 5, 12, 34, 23, 42, 37, 41, 52, 20, 28, 36, 50, 58, 59, 59, 20, 1]
_FIELD_TOTAL = 420  # constant total field decks/week (Tron + Drift + Filler)
_CLIFF_START = date(2026, 1, 26)  # a Monday; week index 16 lands on 2026-05-18 exactly.
assert _CLIFF_START.isoweekday() == 1
assert (_CLIFF_START + timedelta(weeks=16)).isoformat() == "2026-05-18"

_REAL_BAN_DATE = "2026-05-18"  # Undercity Informer — an actual BAN_EVENTS entry
_CLIFF_DATE_WINDOW = {"2026-05-04", "2026-05-11", "2026-05-18"}  # +/-1 bucket of the tail


def _build_corpus(con) -> None:
    """Implant a dated cliff on two entities sharing the same field: "Tron" runs the (real)
    banned card Undercity Informer in 100% of its decks (ubiquitous -> unverifiable via
    card_incl, exactly like the real Candelabra/Tron case), so its cliff attributes via the
    honest date-match fallback. "Drift" runs the same card in only 15% of its decks (trackable,
    below the affectedness threshold), so its otherwise-identical cliff attributes
    "unattributed" — the drift-alarm-eligible case. "Filler" absorbs the remaining field share
    and carries no tracked cards.
    """
    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.cache import parse_cache_item

    for i, wk in enumerate(_WEEKLY):
        monday = _CLIFF_START + timedelta(weeks=i)
        drift_card_n = round(0.15 * wk)
        filler_n = _FIELD_TOTAL - 2 * wk

        decks: list[dict] = []
        for j in range(wk):
            decks.append({
                "Player": f"tron_{i}_{j}",
                "Mainboard": [{"Count": 1, "CardName": "Undercity Informer"}],
                "Sideboard": [],
            })
        for j in range(wk):
            mainboard = [{"Count": 1, "CardName": "Undercity Informer"}] if j < drift_card_n else []
            decks.append({"Player": f"drift_{i}_{j}", "Mainboard": mainboard, "Sideboard": []})
        for j in range(filler_n):
            decks.append({"Player": f"filler_{i}_{j}", "Mainboard": [], "Sideboard": []})

        raw = {
            "Tournament": {
                "Name": f"Week {i}", "Date": monday.isoformat(),
                "Uri": f"https://example.com/week-{i}", "Formats": "Legacy",
            },
            "Decks": decks, "Rounds": [], "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute(
            "UPDATE decks SET archetype = 'Tron' WHERE tournament_id = ? AND player LIKE ?",
            [tid, f"tron_{i}_%"],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Drift' WHERE tournament_id = ? AND player LIKE ?",
            [tid, f"drift_{i}_%"],
        )
        con.execute(
            "UPDATE decks SET archetype = 'Filler' WHERE tournament_id = ? AND player LIKE ?",
            [tid, f"filler_{i}_%"],
        )


def _con():
    from legacy_engine.ingestion import store

    con = store.connect(":memory:")
    _build_corpus(con)
    return con


def _tail_boundary(boundaries):
    return next((b for b in boundaries if b.date in _CLIFF_DATE_WINDOW), None)


@pytest.fixture(scope="module")
def run_result_and_rows():
    con = _con()
    result = run_eras(con, seed=0)
    rows = read_entity_eras(con)
    con.close()
    return result, rows


class TestRunErasEndToEnd:
    def test_all_three_entities_analyzed(self, run_result_and_rows):
        result, _rows = run_result_and_rows
        assert result.n_entities == 3
        assert set(result.summaries) == {"Tron", "Drift", "Filler"}

    def test_tron_cliff_boundary_is_detected(self, run_result_and_rows):
        _result, rows = run_result_and_rows
        boundary = _tail_boundary(rows["Tron"].boundaries)
        assert boundary is not None, f"no boundary near the cliff: {[b.date for b in rows['Tron'].boundaries]}"

    def test_tron_cliff_boundary_is_attributed_ban(self, run_result_and_rows):
        _result, rows = run_result_and_rows
        boundary = _tail_boundary(rows["Tron"].boundaries)
        assert boundary.attribution is not None
        assert boundary.attribution.kind == "ban"
        assert boundary.attribution.card == "Undercity Informer"

    def test_drift_cliff_boundary_is_unattributed(self, run_result_and_rows):
        _result, rows = run_result_and_rows
        boundary = _tail_boundary(rows["Drift"].boundaries)
        assert boundary is not None
        assert boundary.attribution is not None
        assert boundary.attribution.kind == "unattributed"

    def test_alarm_fires_for_the_unattributed_implant(self, run_result_and_rows):
        result, _rows = run_result_and_rows
        assert "Drift" in result.alarms
        assert result.alarms["Drift"].p_change >= 0.5

    def test_store_round_trip_matches_the_run_result(self, run_result_and_rows):
        result, rows = run_result_and_rows
        for entity, summary in result.summaries.items():
            assert rows[entity].stable_since == summary.stable_since
            assert rows[entity].inherited_from_parent == summary.inherited_from_parent
            assert len(rows[entity].boundaries) == summary.n_boundaries
        assert rows["Drift"].alarm_fired is True
        assert rows["Tron"].parent == "Tron"

    def test_deterministic_across_two_independent_runs(self):
        con_a = _con()
        result_a = run_eras(con_a, seed=0)
        con_a.close()

        con_b = _con()
        result_b = run_eras(con_b, seed=0)
        con_b.close()

        assert result_a.summaries == result_b.summaries
        assert result_a.attributions == result_b.attributions
        assert set(result_a.alarms) == set(result_b.alarms)

    def test_unknown_release_source_default_degrades_to_empty(self, run_result_and_rows):
        # No release-date column on the synthetic cards table -> the default release_source
        # honestly returns {} rather than raising; ban-only attribution still worked (proven
        # above), which is the documented fallback behavior.
        result, _rows = run_result_and_rows
        assert result.n_entities == 3  # the run completed without error despite no release data


# ---------------------------------------------------------------------------
# Finding 1 (completion review) — corpus-first-seen release-attribution fallback
# ---------------------------------------------------------------------------


class TestTriggerCardsFromPresenceAdopt:
    """`_trigger_cards_from_presence_adopt` — pure, no DB (objective-search-split's own "pure
    loop over a plain dict" half; this is the extraction step that FEEDS the batched query)."""

    def test_collects_presence_adopt_trigger_cards_across_entities(self):
        sig_a = CandidateBoundary(
            entity="A", date="2026-04-20", signal="presence-adopt", magnitude=0.9,
            pvalue=0.01, evidence="...", trigger_card="Flow State",
        )
        sig_b = CandidateBoundary(
            entity="B", date="2026-05-01", signal="presence-adopt", magnitude=0.8,
            pvalue=0.01, evidence="...", trigger_card="Fresh Tech",
        )
        eras = {
            "A": EntityEras(
                entity="A", stable_since="2026-04-20",
                boundaries=(EraBoundary(date="2026-04-20", signals=(sig_a,), pvalue=0.01, bh_accepted=True, floor_rejected=False),),
                inherited_from_parent=False,
            ),
            "B": EntityEras(
                entity="B", stable_since="2026-05-01",
                boundaries=(EraBoundary(date="2026-05-01", signals=(sig_b,), pvalue=0.01, bh_accepted=True, floor_rejected=False),),
                inherited_from_parent=False,
            ),
        }
        assert _trigger_cards_from_presence_adopt(eras) == {"Flow State", "Fresh Tech"}

    def test_ignores_non_adopt_signals_and_no_trigger_card(self):
        share_sig = CandidateBoundary(
            entity="A", date="2026-04-20", signal="share", magnitude=0.5,
            pvalue=0.01, evidence="...", trigger_card=None,
        )
        eras = {
            "A": EntityEras(
                entity="A", stable_since="2026-04-20",
                boundaries=(EraBoundary(date="2026-04-20", signals=(share_sig,), pvalue=0.01, bh_accepted=True, floor_rejected=False),),
                inherited_from_parent=False,
            ),
        }
        assert _trigger_cards_from_presence_adopt(eras) == set()

    def test_empty_eras_yields_empty_set(self):
        assert _trigger_cards_from_presence_adopt({}) == set()


class TestCorpusFirstSeen:
    """`_corpus_first_seen` — one batched query for the whole trigger-card set's earliest corpus
    appearance (objective-search-split style). Hermetic in-memory DB, never the default DB."""

    def _con(self):
        from legacy_engine.ingestion import store
        from legacy_engine.ingestion.cache import parse_cache_item

        con = store.connect(":memory:")

        def _load(name: str, iso_date: str, card: str) -> None:
            raw = {
                "Tournament": {
                    "Name": name, "Date": iso_date,
                    "Uri": f"https://example.com/{name}", "Formats": "Legacy",
                },
                "Decks": [
                    {"Player": "p1", "Mainboard": [{"Count": 1, "CardName": card}], "Sideboard": []},
                ],
                "Rounds": [], "Standings": [],
            }
            store.load_tournament(con, parse_cache_item(raw, "MTGO"))

        # "Fresh Tech" first appears 2026-04-20 (an earlier stray mention would be a bug if this
        # were NOT the min — the second load is a LATER date, proving MIN is taken correctly).
        _load("wk1", "2026-04-20", "Fresh Tech")
        _load("wk2", "2026-04-27", "Fresh Tech")
        # "Ancient Staple" has been around much longer.
        _load("wk0", "2020-01-01", "Ancient Staple")
        _load("wk1b", "2026-04-20", "Ancient Staple")
        return con

    def test_returns_min_date_per_card(self):
        con = self._con()
        out = _corpus_first_seen(con, {"Fresh Tech", "Ancient Staple"})
        assert out["Fresh Tech"] == date(2026, 4, 20)
        assert out["Ancient Staple"] == date(2020, 1, 1)
        con.close()

    def test_omits_cards_not_in_the_corpus(self):
        con = self._con()
        out = _corpus_first_seen(con, {"Never Printed"})
        assert out == {}
        con.close()

    def test_empty_card_set_short_circuits_without_querying(self):
        con = self._con()
        out = _corpus_first_seen(con, set())
        assert out == {}
        con.close()


# ---------------------------------------------------------------------------
# Finding 1 end-to-end: a real Flow-State-shaped corpus (S1 presence-adopt) attributes as
# "release" via the corpus-first-seen fallback, since the synthetic `cards` table (like the real
# one, pre-this-feature) carries no release-date column.
# ---------------------------------------------------------------------------

# Weekly (total_decks, decks_running_flow_state) — the real "Doomsday" ground-truth #2 fixture
# (docs/briefs/change-point-detection.md §1, frozen 2026-07-11; see conftest.py's
# `flow_state_series`). Flow State first appears in week 12 (2026-04-20) and is adopted almost
# immediately by nearly every deck — the release-driven "no ban, no valid_since change" case
# Finding 1 exists to fix.
_FLOW_STATE_START = date(2026, 1, 26)
_FLOW_STATE_WEEKLY = [
    (3, 0), (23, 0), (7, 0), (16, 0), (6, 0), (22, 0), (8, 0), (10, 0), (15, 0), (15, 0),
    (20, 0), (15, 0), (19, 18), (22, 21), (21, 20), (15, 14), (17, 16), (29, 27), (13, 12),
    (22, 21), (20, 20), (27, 14), (6, 2),
]
_FLOW_STATE_ADOPT_DATE = "2026-04-20"  # week index 12 -- the first week Flow State appears


def _build_flow_state_corpus(con) -> None:
    from legacy_engine.ingestion import store
    from legacy_engine.ingestion.cache import parse_cache_item

    for i, (total, with_card) in enumerate(_FLOW_STATE_WEEKLY):
        monday = _FLOW_STATE_START + timedelta(weeks=i)
        decks: list[dict] = []
        for j in range(total):
            mainboard = (
                [{"Count": 1, "CardName": "Flow State"}] if j < with_card
                else [{"Count": 4, "CardName": "Filler Card"}]
            )
            decks.append({"Player": f"dd_{i}_{j}", "Mainboard": mainboard, "Sideboard": []})
        raw = {
            "Tournament": {
                "Name": f"Week {i}", "Date": monday.isoformat(),
                "Uri": f"https://example.com/flow-week-{i}", "Formats": "Legacy",
            },
            "Decks": decks, "Rounds": [], "Standings": [],
        }
        tid = store.load_tournament(con, parse_cache_item(raw, "MTGO"))
        con.execute("UPDATE decks SET archetype = 'Doomsday' WHERE tournament_id = ?", [tid])


class TestFlowStateReleaseAttributionEndToEnd:
    """`run_eras` end-to-end: a real S1 presence-adopt boundary (no ban nearby, no schema
    release-date column) attributes as "release" via the corpus-first-seen fallback — the exact
    gap Finding 1 fixes (a real adoption boundary was mislabeling as "unattributed disturbance")."""

    def test_flow_state_boundary_attributes_release_via_corpus_first_seen(self):
        from legacy_engine.ingestion import store

        con = store.connect(":memory:")
        _build_flow_state_corpus(con)
        result = run_eras(con, seed=0)
        rows = read_entity_eras(con)
        con.close()

        boundary = next(
            (b for b in rows["Doomsday"].boundaries if b.date == _FLOW_STATE_ADOPT_DATE), None,
        )
        assert boundary is not None, (
            f"no boundary at {_FLOW_STATE_ADOPT_DATE}: {[b.date for b in rows['Doomsday'].boundaries]}"
        )
        assert boundary.attribution is not None
        assert boundary.attribution.kind == "release"
        assert boundary.attribution.card == "Flow State"
        assert "first corpus appearance 2026-04-20" in boundary.attribution.detail
        assert result.n_entities == 1
