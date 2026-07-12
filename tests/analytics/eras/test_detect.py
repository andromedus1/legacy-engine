"""Tests for analytics.eras.detect — S1-S4 signal detectors.

House style: hermetic, no DB, hand-built/frozen `EntitySeries` fixtures from conftest.py, TestX
classes, deterministic. Calibration tests pin `_PELT_PEN`/`_SHARE_PEN` against the frozen
real-corpus and synthetic fixtures — see detect.py's module-level constant comments for the
calibration evidence.
"""

from __future__ import annotations

import pytest

from legacy_engine.analytics.eras.detect import (
    SIGNAL_TYPES,
    CandidateBoundary,
    corroborate_winrate,
    detect_composition,
    detect_presence,
    detect_share,
)

_FLOW_STATE_DATE_WINDOW = {"2026-04-13", "2026-04-20", "2026-04-27"}  # +/-1 bucket of 04-20
_TRON_SHARE_DATE_WINDOW = {"2026-06-08", "2026-06-15", "2026-06-22", "2026-06-29"}


class TestPresenceFlowStateAdoption:
    """Ground truth #2 — the Flow State one-week adoption step (brief §1)."""

    def test_fires_presence_adopt_on_all_three_archetypes(self, flow_state_series):
        for entity, series in flow_state_series.items():
            cands = detect_presence(series)
            adopts = [c for c in cands if c.signal == "presence-adopt"]
            assert adopts, f"{entity}: expected a presence-adopt candidate"
            assert any(c.date in _FLOW_STATE_DATE_WINDOW for c in adopts), (
                f"{entity}: adopt dates {[c.date for c in adopts]} not within "
                f"+/-1 bucket of 2026-04-20"
            )

    def test_trigger_card_is_flow_state(self, flow_state_series):
        for series in flow_state_series.values():
            adopts = [c for c in detect_presence(series) if c.signal == "presence-adopt"]
            assert all(c.trigger_card == "Flow State" for c in adopts)

    def test_evidence_names_deck_counts(self, flow_state_series):
        cands = detect_presence(flow_state_series["Doomsday"])
        adopt = next(c for c in cands if c.signal == "presence-adopt")
        assert "Flow State" in adopt.evidence
        assert "decks" in adopt.evidence

    def test_magnitude_is_the_absolute_fraction_jump(self, flow_state_series):
        cands = detect_presence(flow_state_series["Dimir Tempo"])
        adopt = next(c for c in cands if c.signal == "presence-adopt")
        assert 0.0 < adopt.magnitude <= 1.0


class TestPresenceTronNoFalseFireOnCandelabra:
    """Candelabra's inclusion FRACTION never drops (every Tron deck runs it) — the decks vanish,
    not the card. `detect_presence` must not manufacture a vanish candidate from share collapse."""

    def test_no_presence_candidates_at_all(self, tron_cliff_series):
        assert detect_presence(tron_cliff_series) == []


class TestShareTronCliff:
    """Ground truth #1 — the Candelabra ban cliff, a pure share collapse (brief §1)."""

    def test_fires_a_boundary_near_the_cliff(self, tron_cliff_series):
        cands = detect_share(tron_cliff_series)
        assert cands, "expected at least one share candidate"
        assert any(c.date in _TRON_SHARE_DATE_WINDOW for c in cands), (
            f"share dates {[c.date for c in cands]} not within +/-1 bucket of 2026-06-15/22"
        )

    def test_signal_is_share_and_no_trigger_card(self, tron_cliff_series):
        cands = detect_share(tron_cliff_series)
        cliff = next(c for c in cands if c.date in _TRON_SHARE_DATE_WINDOW)
        assert cliff.signal == "share"
        assert cliff.trigger_card is None

    def test_pvalue_is_a_valid_permutation_p(self, tron_cliff_series):
        cands = detect_share(tron_cliff_series)
        for c in cands:
            assert 0.0 < c.pvalue <= 1.0


class TestStableNonEvent:
    """A well-calibrated detector must not manufacture eras out of deterministic wobble."""

    def test_all_detectors_return_zero_candidates(self, stable_nonevent_series):
        assert detect_presence(stable_nonevent_series) == []
        assert detect_composition(stable_nonevent_series) == []
        assert detect_share(stable_nonevent_series) == []

    def test_corroborate_winrate_is_a_no_op_on_empty_candidates(self, stable_nonevent_series):
        assert corroborate_winrate(stable_nonevent_series, []) == []


class TestCompositionRebalance:
    """Synthetic S2 ground truth: a 4-card rebalance at bucket 18, kept inside [0.10, 0.90] so
    S1 cannot fire."""

    def test_s1_stays_silent(self, composition_rebalance_series):
        assert detect_presence(composition_rebalance_series) == []

    def test_s2_fires_near_bucket_18_with_significant_p(self, composition_rebalance_series):
        cands = detect_composition(composition_rebalance_series)
        assert cands, "expected at least one composition candidate"
        # bucket 18 -> 2026-01-05 + 18 weeks
        from datetime import date, timedelta
        target = (date(2026, 1, 5) + timedelta(weeks=18)).isoformat()
        window = {
            (date(2026, 1, 5) + timedelta(weeks=w)).isoformat() for w in (17, 18, 19)
        }
        hits = [c for c in cands if c.date in window]
        assert hits, f"composition dates {[c.date for c in cands]} not within +/-1 of {target}"
        assert any(c.pvalue < 0.05 for c in hits)

    def test_evidence_names_flex_cards(self, composition_rebalance_series):
        cands = detect_composition(composition_rebalance_series)
        hit = cands[0]
        assert any(f"Flex{i:02d}" in hit.evidence for i in range(12))


class TestClosedVocabulary:
    def test_unknown_signal_raises_value_error_naming_token_and_allowed_set(self):
        with pytest.raises(ValueError) as exc_info:
            CandidateBoundary(
                entity="X", date="2026-01-05", signal="bogus-signal", magnitude=0.1,
                pvalue=0.5, evidence="n/a", trigger_card=None,
            )
        message = str(exc_info.value)
        assert "bogus-signal" in message
        assert str(sorted(SIGNAL_TYPES)) in message

    def test_every_known_signal_constructs_cleanly(self):
        for signal in SIGNAL_TYPES:
            CandidateBoundary(
                entity="X", date="2026-01-05", signal=signal, magnitude=0.1,
                pvalue=0.5, evidence="n/a", trigger_card=None,
            )


class TestDeterminism:
    def test_same_seed_gives_identical_composition_results(self, composition_rebalance_series):
        a = detect_composition(composition_rebalance_series, seed=7)
        b = detect_composition(composition_rebalance_series, seed=7)
        assert a == b

    def test_same_seed_gives_identical_share_results(self, tron_cliff_series):
        a = detect_share(tron_cliff_series, seed=3)
        b = detect_share(tron_cliff_series, seed=3)
        assert a == b

    def test_different_seed_same_detections_on_strong_fixtures(self, tron_cliff_series):
        a = detect_share(tron_cliff_series, seed=0)
        b = detect_share(tron_cliff_series, seed=99)
        assert [c.date for c in a] == [c.date for c in b]
        assert [c.signal for c in a] == [c.signal for c in b]


class TestShortSeriesFloor:
    def test_fewer_than_eight_complete_buckets_returns_empty_everywhere(
        self, make_entity_series, make_bucket,
    ):
        from datetime import date, timedelta
        starts = [(date(2026, 1, 5) + timedelta(weeks=i)).isoformat() for i in range(5)]
        buckets = tuple(make_bucket(start=start) for start in starts)
        s = make_entity_series(flex_cards=("Filler",), buckets=buckets)
        assert detect_presence(s) == []
        assert detect_composition(s) == []
        assert detect_share(s) == []


class TestWinrateCorroboration:
    def test_corroborates_when_delta_and_floor_both_clear(self, make_entity_series, make_bucket):
        # 4 complete buckets before the boundary date, 4 after (8 total -- clears the
        # _MIN_COMPLETE_BUCKETS floor) -- 32 wins/8 losses before (80%), 8 wins/32 losses after
        # (20%) -- delta 60pp, well above the 5pp/30-match floor.
        before = [
            make_bucket(start=f"2026-01-{5 + 7*i:02d}", wins=8, losses=2, decks=20)
            for i in range(4)
        ]
        after = [
            make_bucket(start=f"2026-03-{2 + 7*i:02d}", wins=2, losses=8, decks=20)
            for i in range(4)
        ]
        s = make_entity_series(buckets=tuple(before + after))
        cand = CandidateBoundary(
            entity="Test", date=after[0].start, signal="share", magnitude=0.1,
            pvalue=0.01, evidence="share 10%->5%/wk", trigger_card=None,
        )
        out = corroborate_winrate(s, [cand])
        assert len(out) == 1
        assert "WR corroborates" in out[0].evidence
        assert out[0] is not cand  # frozen dataclass -> a new instance

    def test_no_corroboration_below_the_match_floor(self, make_entity_series, make_bucket):
        # 4 + 4 = 8 buckets (clears _MIN_COMPLETE_BUCKETS) but only 2 wins/1 loss per bucket
        # (12 matches total per side) -- well below the 30-match floor, so no corroboration even
        # though the win-rate delta itself (80% vs 20%, ignoring the floor) would qualify.
        before = [
            make_bucket(start=f"2026-01-{5 + 7*i:02d}", wins=2, losses=1, decks=10)
            for i in range(4)
        ]
        after = [
            make_bucket(start=f"2026-03-{2 + 7*i:02d}", wins=1, losses=2, decks=10)
            for i in range(4)
        ]
        s = make_entity_series(buckets=tuple(before + after))
        cand = CandidateBoundary(
            entity="Test", date=after[0].start, signal="share", magnitude=0.1,
            pvalue=0.01, evidence="share 10%->5%/wk", trigger_card=None,
        )
        out = corroborate_winrate(s, [cand])
        assert out[0].evidence == cand.evidence  # unchanged
