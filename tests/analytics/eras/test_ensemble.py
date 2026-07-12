"""Tests for analytics.eras.ensemble — merge + fleet BH-FDR + deck floor + camp inheritance.

House style: hermetic, no DB, hand-built/frozen `EntitySeries` fixtures from conftest.py, TestX
classes, deterministic. The real-case integration tests run the FULL detector stack over the
frozen real-corpus fixtures and assert what the pinned operating point actually derives — see
the inline comments where the frozen data's true behavior is richer than the naive expectation.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from legacy_engine.analytics.eras.detect import (
    CandidateBoundary,
    corroborate_winrate,
    detect_composition,
    detect_presence,
    detect_share,
)
from legacy_engine.analytics.eras.ensemble import EntityEras, EraBoundary, derive_eras
from legacy_engine.analytics.eras.series import Bucket, EntitySeries


def _run_all_detectors(series: dict[str, EntitySeries]) -> list[CandidateBoundary]:
    """The production-shaped per-entity detector stack (S1 + S2 + S3, then S4 corroboration)."""
    out: list[CandidateBoundary] = []
    for s in series.values():
        cands = detect_presence(s) + detect_composition(s) + detect_share(s)
        out.extend(corroborate_winrate(s, cands))
    return out


def _accepted(e: EntityEras) -> list[EraBoundary]:
    return [b for b in e.boundaries if b.bh_accepted and not b.floor_rejected]


def _cand(
    entity: str = "Test", date_: str = "2026-01-05", signal: str = "share",
    pvalue: float = 0.001, magnitude: float = 0.1, trigger_card: str | None = None,
) -> CandidateBoundary:
    return CandidateBoundary(
        entity=entity, date=date_, signal=signal, magnitude=magnitude,
        pvalue=pvalue, evidence="hand-built", trigger_card=trigger_card,
    )


def _grid_series(
    entity: str = "Test", *, parent: str | None = None, n: int = 12,
    decks_per_bucket: int = 20, start: date = date(2026, 1, 5),
) -> EntitySeries:
    """A minimal weekly series whose bucket grid the merge/floor logic can resolve dates on."""
    buckets = tuple(
        Bucket(
            start=(start + timedelta(weeks=i)).isoformat(), complete=True,
            decks=decks_per_bucket, field_decks=200, wins=5, losses=5, card_incl={},
        )
        for i in range(n)
    )
    return EntitySeries(
        entity=entity, parent=parent or entity, bucket_weeks=1, flex_cards=(), buckets=buckets,
    )


def _wk(i: int, start: date = date(2026, 1, 5)) -> str:
    return (start + timedelta(weeks=i)).isoformat()


class TestNullFleet:
    def test_synthetic_null_candidates_zero_accepted(
        self, stationary_fleet_series, make_null_candidates,
    ):
        # p-values are drawn from [0.02, 1.0) — at/above a 199-permutation scheme's realistic
        # floor. For seed 0 this yields 32 candidates across 20 entities whose smallest p is
        # ~0.023; BH at alpha=0.05 with m=32 needs p_(1) <= 0.05/32 ~= 0.0016 to accept anything,
        # so acceptance count is exactly 0 for this seed (a tiny-p outlier COULD legitimately
        # survive BH under a truly uniform null — the [0.02, 1.0) floor models the permutation
        # detectors' actual resolution instead).
        series = stationary_fleet_series(100)
        names = sorted(series)[:20]
        cands = make_null_candidates(entity_names=names, seed=0)
        eras = derive_eras(series, cands)

        assert sum(len(_accepted(e)) for e in eras.values()) == 0
        assert all(e.stable_since is None for e in eras.values())
        # Rejected boundaries are still recorded (audit trail), just never accepted — every
        # input candidate survives inside some merged boundary's `signals` tuple (within-
        # tolerance same-entity pairs merge, so the boundary count may be lower).
        assert sum(len(b.signals) for e in eras.values() for b in e.boundaries) == len(cands) > 0

    def test_detector_integration_null_accepts_zero(self, stationary_fleet_series):
        # The REAL detectors over 100 stationary synthetic entities: the pinned operating point
        # produces zero candidates at all, so derive_eras trivially accepts zero fleet-wide.
        series = stationary_fleet_series(100)
        cands = _run_all_detectors(series)
        assert cands == []
        eras = derive_eras(series, cands)
        assert len(eras) == 100
        assert all(e.stable_since is None and e.boundaries == () for e in eras.values())


class TestRealCaseIntegration:
    """Frozen real-corpus fixtures through the full stack (detectors -> derive_eras)."""

    @pytest.fixture
    def real_eras(self, flow_state_series, tron_cliff_series):
        series = {**flow_state_series, "Tron": tron_cliff_series}
        return derive_eras(series, _run_all_detectors(series))

    def test_flow_state_adoption_is_an_accepted_boundary_for_all_three(self, real_eras):
        window = {"2026-04-13", "2026-04-20", "2026-04-27"}  # +/-1 bucket of 2026-04-20
        for entity in ("Doomsday", "Izzet Delver", "Dimir Tempo"):
            accepted_dates = {b.date for b in _accepted(real_eras[entity])}
            assert accepted_dates & window, (
                f"{entity}: accepted {sorted(accepted_dates)} misses the adoption window"
            )

    def test_doomsday_and_izzet_stable_since_is_the_adoption_bucket(self, real_eras):
        assert real_eras["Doomsday"].stable_since == "2026-04-20"
        assert real_eras["Izzet Delver"].stable_since == "2026-04-13"  # within +/-1 bucket

    def test_dimir_stable_since_is_the_post_adoption_share_settling(self, real_eras):
        # The frozen real corpus contains a GENUINE second disturbance for Dimir Tempo: its
        # play rate halves after the Flow State meta shift (weekly decks ~40-45 pre-adoption vs
        # ~17-24 from mid-May), and the share detector legitimately dates that settling
        # 2026-05-11 with permutation p=0.005 — 3 buckets after the adoption boundary, outside
        # the 2-bucket merge tolerance. stable_since = the LAST accepted boundary by contract,
        # so it is the share settling, not the adoption step. The adoption boundary itself is
        # separately accepted (asserted above) — both are real, and truncating to the later one
        # is the conservative windowing choice.
        assert real_eras["Dimir Tempo"].stable_since == "2026-05-11"

    def test_adoption_boundary_merges_presence_and_share_evidence(self, real_eras):
        adoption = next(
            b for b in real_eras["Doomsday"].boundaries if b.date == "2026-04-20"
        )
        signals = {c.signal for c in adoption.signals}
        assert "presence-adopt" in signals
        assert adoption.pvalue == min(c.pvalue for c in adoption.signals)

    def test_tron_cliff_is_recorded_but_not_yet_accepted_at_this_snapshot(self, real_eras):
        # The Candelabra cliff is 1 complete bucket old at the corpus edge (2026-06-22 = 20
        # decks, 2026-06-29 partial). Two independent defenses HOLD it back, by design:
        # a segment-permutation p on a boundary this close to the series end is bounded below
        # at roughly 1/n_pooled (the low bucket can land in the short segment in ~1/n of
        # permutations), so it cannot clear fleet BH; and the true cliff bucket would leave
        # only 21 decks in the new era, below the 30-deck floor. This is the brief §4
        # "confirmation asymmetry" case: the offline stable_since derivation must NOT truncate
        # on a 1-week-old era — the BOCPD drift alarm (bocpd.py, era-ledger feature) is the
        # designed mechanism for flagging it immediately. The detect-level test already pins
        # that the share detector FIRES at the transition; here we pin that the ensemble
        # honestly holds it below acceptance until the new era accumulates sample.
        tron = real_eras["Tron"]
        cliff_window = {"2026-06-08", "2026-06-15", "2026-06-22", "2026-06-29"}
        assert any(b.date in cliff_window for b in tron.boundaries), (
            "the cliff candidate must at least be recorded"
        )
        assert tron.stable_since is None

    def test_no_entity_inherits_in_a_parents_only_fleet(self, real_eras):
        assert all(not e.inherited_from_parent for e in real_eras.values())


class TestMerge:
    def test_two_candidates_one_bucket_apart_merge_into_one_boundary(self):
        series = {"Test": _grid_series()}
        cands = [
            _cand(date_=_wk(4), signal="share", pvalue=0.02),
            _cand(date_=_wk(5), signal="presence-adopt", pvalue=0.001, trigger_card="X"),
        ]
        eras = derive_eras(series, cands)
        boundaries = eras["Test"].boundaries
        assert len(boundaries) == 1
        merged = boundaries[0]
        assert len(merged.signals) == 2
        assert merged.pvalue == 0.001            # min component p
        assert merged.date == _wk(5)             # the min-p (strongest) component's date
        assert {c.signal for c in merged.signals} == {"share", "presence-adopt"}

    def test_candidates_beyond_tolerance_stay_separate(self):
        series = {"Test": _grid_series()}
        cands = [
            _cand(date_=_wk(2), pvalue=0.001),
            _cand(date_=_wk(5), pvalue=0.001),  # 3 buckets apart > default tolerance 2
        ]
        eras = derive_eras(series, cands)
        assert len(eras["Test"].boundaries) == 2

    def test_merge_distance_uses_the_entity_bucket_grid(self):
        # A 2-week-bucket entity: dates 2 weeks apart are ONE bucket apart -> merge.
        start = date(2026, 1, 5)
        buckets = tuple(
            Bucket(
                start=(start + timedelta(weeks=2 * i)).isoformat(), complete=True,
                decks=20, field_decks=200, wins=5, losses=5, card_incl={},
            )
            for i in range(10)
        )
        series = {"Test": EntitySeries(
            entity="Test", parent="Test", bucket_weeks=2, flex_cards=(), buckets=buckets,
        )}
        cands = [
            _cand(date_=buckets[3].start, pvalue=0.01),
            _cand(date_=buckets[5].start, pvalue=0.001),  # 2 buckets apart == tolerance
        ]
        eras = derive_eras(series, cands)
        assert len(eras["Test"].boundaries) == 1


class TestDeckFloor:
    def test_thin_new_era_is_floor_rejected_and_stable_since_none(self):
        # 12 buckets x 2 decks = plenty of history, but only 2 buckets (4 decks) at/after the
        # boundary — BH accepts (p tiny, sole candidate) yet the floor rejects.
        series = {"Test": _grid_series(decks_per_bucket=2)}
        cands = [_cand(date_=_wk(10), pvalue=0.001)]
        eras = derive_eras(series, cands)
        [boundary] = eras["Test"].boundaries
        assert boundary.bh_accepted is True       # survived FDR...
        assert boundary.floor_rejected is True    # ...but the new era is too thin to trust
        assert eras["Test"].stable_since is None

    def test_stable_since_falls_back_to_the_prior_accepted_boundary(self):
        # Boundary A (wk 3): 9 buckets x 20 decks after it -> passes floor. Boundary B (wk 10):
        # 2 buckets x 20 = 40... shrink the tail instead: use decks 10/bucket -> B has 20 < 30.
        series = {"Test": _grid_series(decks_per_bucket=10)}
        cands = [
            _cand(date_=_wk(3), pvalue=0.0001),
            _cand(date_=_wk(10), pvalue=0.001),
        ]
        eras = derive_eras(series, cands)
        a, b = eras["Test"].boundaries
        assert a.bh_accepted and not a.floor_rejected
        assert b.bh_accepted and b.floor_rejected
        assert eras["Test"].stable_since == _wk(3)


class TestCampInheritance:
    def test_camp_without_own_boundaries_inherits_parent(self):
        series = {
            "P": _grid_series("P"),
            "P [c]": _grid_series("P [c]", parent="P"),
        }
        cands = [_cand(entity="P", date_=_wk(4), pvalue=0.001)]
        eras = derive_eras(series, cands)

        camp = eras["P [c]"]
        assert camp.inherited_from_parent is True
        assert camp.stable_since == eras["P"].stable_since == _wk(4)
        assert camp.boundaries == eras["P"].boundaries

    def test_camp_with_own_earlier_boundary_takes_parents_later_date(self):
        # The max rule: a parent-wide disturbance disturbs every camp, so a camp's effective
        # stable_since can never be EARLIER than its parent's.
        series = {
            "P": _grid_series("P"),
            "P [c]": _grid_series("P [c]", parent="P"),
        }
        cands = [
            _cand(entity="P [c]", date_=_wk(2), pvalue=0.0001),
            _cand(entity="P", date_=_wk(7), pvalue=0.001),
        ]
        eras = derive_eras(series, cands)

        camp = eras["P [c]"]
        assert camp.inherited_from_parent is False  # keeps its own boundaries
        assert [b.date for b in camp.boundaries] == [_wk(2)]
        assert camp.stable_since == _wk(7)          # parent's later date wins

    def test_camp_with_own_later_boundary_keeps_it(self):
        series = {
            "P": _grid_series("P"),
            "P [c]": _grid_series("P [c]", parent="P"),
        }
        cands = [
            _cand(entity="P [c]", date_=_wk(8), pvalue=0.0001),
            _cand(entity="P", date_=_wk(3), pvalue=0.001),
        ]
        eras = derive_eras(series, cands)
        assert eras["P [c]"].stable_since == _wk(8)

    def test_camp_with_no_accepted_anything_stays_uninherited_and_none(self):
        # Parent has NO accepted boundaries either -> nothing to inherit; the camp keeps its
        # own (empty) history rather than carrying a misleading inherited flag.
        series = {
            "P": _grid_series("P"),
            "P [c]": _grid_series("P [c]", parent="P"),
        }
        eras = derive_eras(series, [])
        camp = eras["P [c]"]
        assert camp.inherited_from_parent is False
        assert camp.stable_since is None
        assert camp.boundaries == ()


class TestEndToEndSeam:
    def test_series_shape_through_detectors_to_entity_eras(
        self, flow_state_series, tron_cliff_series, stationary_fleet_series,
    ):
        # The consumable seam the era-ledger feature builds on: a build_entity_series-shaped
        # dict (constructed via dataclasses here — same types, no DB) -> detector stack ->
        # derive_eras -> dict[str, EntityEras] covering every input entity.
        series: dict[str, EntitySeries] = {
            **flow_state_series,
            "Tron": tron_cliff_series,
            **stationary_fleet_series(3),
        }
        eras = derive_eras(series, _run_all_detectors(series))

        assert set(eras) == set(series)
        for entity, e in eras.items():
            assert isinstance(e, EntityEras)
            assert e.entity == entity
            assert isinstance(e.boundaries, tuple)
            assert e.stable_since is None or isinstance(e.stable_since, str)
