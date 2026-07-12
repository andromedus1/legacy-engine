"""Tests for analytics.eras.attribution — ban/release/unattributed boundary attribution (Unit C).

House style: hand-built EntityEras/EraBoundary/CandidateBoundary/EntitySeries fixtures (no DB, no
detectors) for full control over dates/rates — self-contained, not dependent on the shared
tests/analytics/eras/conftest.py fixtures (which are tuned for detector calibration, not
attribution's own edge cases).
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from legacy_engine.analytics.eras.attribution import Attribution, attribute_boundaries
from legacy_engine.analytics.eras.detect import CandidateBoundary
from legacy_engine.analytics.eras.ensemble import EntityEras, EraBoundary
from legacy_engine.analytics.eras.series import Bucket, EntitySeries

_BAN_EVENTS = (
    (date(2026, 3, 2), "Test Banned Card", "test ban"),
)


def _boundary(date_str, *, signals=(), pvalue=0.01, bh_accepted=True, floor_rejected=False):
    return EraBoundary(
        date=date_str, signals=signals, pvalue=pvalue, bh_accepted=bh_accepted,
        floor_rejected=floor_rejected,
    )


def _eras(entity, boundaries):
    since = boundaries[-1].date if boundaries else None
    return EntityEras(entity=entity, stable_since=since, boundaries=tuple(boundaries), inherited_from_parent=False)


def _trackable_card_series(entity, card, weekly_rate, *, n=6, start=date(2026, 1, 19), decks_per_week=20):
    """A card present at a CONSTANT `weekly_rate` fraction every (complete) week — trackable in
    the entity's own flex band (rate is passed straight through, no need to hit the real 10-95%
    computation since this is a hand-built fixture, not build_entity_series output)."""
    buckets = []
    for i in range(n):
        d = (start + timedelta(weeks=i)).isoformat()
        incl = round(weekly_rate * decks_per_week)
        buckets.append(Bucket(
            start=d, complete=True, decks=decks_per_week, field_decks=decks_per_week * 5,
            wins=0, losses=0, card_incl={card: incl} if incl else {},
        ))
    return EntitySeries(entity=entity, parent=entity, bucket_weeks=1, flex_cards=(card,), buckets=tuple(buckets))


def _ubiquitous_untracked_card_series(entity, card, *, n=6, start=date(2026, 1, 19), decks_per_week=20):
    """A card at 100% inclusion every week but explicitly NOT in flex_cards — mirrors the real
    build_entity_series behavior for a card like Candelabra of Tawnos, whose overall-pool
    inclusion rate (100%) sits ABOVE the flex band's 95% ceiling and is therefore excluded."""
    buckets = []
    for i in range(n):
        d = (start + timedelta(weeks=i)).isoformat()
        buckets.append(Bucket(
            start=d, complete=True, decks=decks_per_week, field_decks=decks_per_week * 5,
            wins=0, losses=0, card_incl={card: decks_per_week},
        ))
    return EntitySeries(entity=entity, parent=entity, bucket_weeks=1, flex_cards=(), buckets=tuple(buckets))


class TestBanAttributionVerified:
    def test_high_pre_boundary_inclusion_is_attributed_ban(self):
        s = _trackable_card_series("Foo", "Test Banned Card", 0.40)
        boundary = _boundary("2026-03-02")
        eras = {"Foo": _eras("Foo", [boundary])}
        out = attribute_boundaries(eras, ban_events=_BAN_EVENTS, releases={}, series={"Foo": s}, tolerance_days=14)
        attr = out[("Foo", "2026-03-02")]
        assert attr.kind == "ban"
        assert attr.card == "Test Banned Card"
        assert "40%" in attr.detail

    def test_low_pre_boundary_inclusion_is_not_ban(self):
        s = _trackable_card_series("Foo", "Test Banned Card", 0.15)
        boundary = _boundary("2026-03-02")
        eras = {"Foo": _eras("Foo", [boundary])}
        out = attribute_boundaries(eras, ban_events=_BAN_EVENTS, releases={}, series={"Foo": s})
        assert out[("Foo", "2026-03-02")].kind == "unattributed"

    def test_no_series_for_entity_falls_back_to_unverified_ban(self):
        # Defensive path: attribution must not crash when a series entry is absent for an entity.
        boundary = _boundary("2026-03-02")
        eras = {"Foo": _eras("Foo", [boundary])}
        out = attribute_boundaries(eras, ban_events=_BAN_EVENTS, releases={}, series={})
        attr = out[("Foo", "2026-03-02")]
        assert attr.kind == "ban"
        assert "unverified" in attr.detail


class TestBanAttributionUnverifiedFallback:
    def test_ubiquitous_card_outside_flex_band_falls_back_to_date_match(self):
        # A Candelabra-shaped card: 100% inclusion, therefore excluded from flex_cards, therefore
        # unverifiable — the headline ground-truth case's own attribution path.
        s = _ubiquitous_untracked_card_series("Tron", "Candelabra of Tawnos")
        ban_events = ((date(2026, 6, 15), "Candelabra of Tawnos", "test ban"),)
        boundary = _boundary("2026-06-15")
        eras = {"Tron": _eras("Tron", [boundary])}
        out = attribute_boundaries(eras, ban_events=ban_events, releases={}, series={"Tron": s})
        attr = out[("Tron", "2026-06-15")]
        assert attr.kind == "ban"
        assert attr.card == "Candelabra of Tawnos"
        assert "unverified" in attr.detail


class TestReleaseAttribution:
    def test_adopt_signal_with_matching_release_date(self):
        sig = CandidateBoundary(
            entity="Bar", date="2026-04-20", signal="presence-adopt", magnitude=0.9,
            pvalue=0.01, evidence="Flow State 0%->95%", trigger_card="Flow State",
        )
        boundary = _boundary("2026-04-20", signals=(sig,))
        eras = {"Bar": _eras("Bar", [boundary])}
        releases = {"Flow State": date(2026, 4, 18)}
        out = attribute_boundaries(eras, ban_events=(), releases=releases, series={})
        attr = out[("Bar", "2026-04-20")]
        assert attr.kind == "release"
        assert attr.card == "Flow State"
        assert "Flow State" in attr.detail

    def test_adopt_signal_without_a_release_date_is_unattributed(self):
        sig = CandidateBoundary(
            entity="Bar", date="2026-04-20", signal="presence-adopt", magnitude=0.9,
            pvalue=0.01, evidence="...", trigger_card="Mystery Card",
        )
        boundary = _boundary("2026-04-20", signals=(sig,))
        eras = {"Bar": _eras("Bar", [boundary])}
        out = attribute_boundaries(eras, ban_events=(), releases={}, series={})
        assert out[("Bar", "2026-04-20")].kind == "unattributed"

    def test_non_adopt_signal_never_triggers_release_check(self):
        # A "share" signal has no trigger_card at all — release attribution must never fire off it.
        sig = CandidateBoundary(
            entity="Bar", date="2026-04-20", signal="share", magnitude=0.5,
            pvalue=0.01, evidence="...", trigger_card=None,
        )
        boundary = _boundary("2026-04-20", signals=(sig,))
        eras = {"Bar": _eras("Bar", [boundary])}
        releases = {"Something": date(2026, 4, 20)}
        out = attribute_boundaries(eras, ban_events=(), releases=releases, series={})
        assert out[("Bar", "2026-04-20")].kind == "unattributed"

    def test_ban_takes_priority_over_a_matching_release_when_both_are_in_tolerance(self):
        s = _trackable_card_series("Foo", "Test Banned Card", 0.40, start=date(2026, 1, 19))
        sig = CandidateBoundary(
            entity="Foo", date="2026-03-02", signal="presence-adopt", magnitude=0.9,
            pvalue=0.01, evidence="...", trigger_card="Some Release",
        )
        boundary = _boundary("2026-03-02", signals=(sig,))
        eras = {"Foo": _eras("Foo", [boundary])}
        releases = {"Some Release": date(2026, 3, 1)}
        out = attribute_boundaries(eras, ban_events=_BAN_EVENTS, releases=releases, series={"Foo": s})
        assert out[("Foo", "2026-03-02")].kind == "ban"


class TestCorpusFirstSeenReleaseFallback:
    """Finding 1 (completion review): when the injected/schema `releases` mapping has no entry
    for an S1 presence-adopt trigger card (the common case — the `cards` table carries no
    release-date column), `corpus_first_seen` fills the gap so a real release-driven adoption
    boundary (the Flow State case) attributes as "release" instead of mislabeling as an
    "unattributed disturbance"."""

    def test_first_seen_near_boundary_attributes_release_with_first_seen_detail(self):
        sig = CandidateBoundary(
            entity="Bar", date="2026-04-20", signal="presence-adopt", magnitude=0.9,
            pvalue=0.01, evidence="Flow State 0%->95%", trigger_card="Flow State",
        )
        boundary = _boundary("2026-04-20", signals=(sig,))
        eras = {"Bar": _eras("Bar", [boundary])}
        # No injected/schema release-date source names "Flow State" at all.
        corpus_first_seen = {"Flow State": date(2026, 4, 20)}
        out = attribute_boundaries(
            eras, ban_events=(), releases={}, series={},
            corpus_first_seen=corpus_first_seen,
        )
        attr = out[("Bar", "2026-04-20")]
        assert attr.kind == "release"
        assert attr.card == "Flow State"
        assert "first corpus appearance 2026-04-20" in attr.detail

    def test_long_existing_card_does_not_spuriously_attribute_release(self):
        # The trigger card has been in the corpus for years — its first appearance is nowhere
        # near this boundary, so the fallback must NOT manufacture a release attribution.
        sig = CandidateBoundary(
            entity="Bar", date="2026-04-20", signal="presence-adopt", magnitude=0.9,
            pvalue=0.01, evidence="...", trigger_card="Ancient Staple",
        )
        boundary = _boundary("2026-04-20", signals=(sig,))
        eras = {"Bar": _eras("Bar", [boundary])}
        corpus_first_seen = {"Ancient Staple": date(2020, 1, 1)}
        out = attribute_boundaries(
            eras, ban_events=(), releases={}, series={},
            corpus_first_seen=corpus_first_seen,
        )
        assert out[("Bar", "2026-04-20")].kind == "unattributed"

    def test_injected_release_source_still_wins_over_corpus_fallback(self):
        # The injected/schema `releases` source names the card (even if its date sits right at
        # the edge of tolerance) — the corpus-first-seen fallback must never be consulted, let
        # alone override it, whenever an entry already exists.
        sig = CandidateBoundary(
            entity="Bar", date="2026-04-20", signal="presence-adopt", magnitude=0.9,
            pvalue=0.01, evidence="...", trigger_card="Flow State",
        )
        boundary = _boundary("2026-04-20", signals=(sig,))
        eras = {"Bar": _eras("Bar", [boundary])}
        releases = {"Flow State": date(2026, 4, 18)}
        # A corpus-first-seen date that would ALSO match, but must be ignored since `releases`
        # already has an entry for this card.
        corpus_first_seen = {"Flow State": date(2020, 1, 1)}
        out = attribute_boundaries(
            eras, ban_events=(), releases=releases, series={},
            corpus_first_seen=corpus_first_seen,
        )
        attr = out[("Bar", "2026-04-20")]
        assert attr.kind == "release"
        assert "first corpus appearance" not in attr.detail
        assert "2026-04-18" in attr.detail

    def test_no_corpus_first_seen_at_all_is_a_no_op(self):
        """`corpus_first_seen=None` (the default) must be byte-identical to the pre-fallback
        behavior — an adopt signal with no release data anywhere is still unattributed."""
        sig = CandidateBoundary(
            entity="Bar", date="2026-04-20", signal="presence-adopt", magnitude=0.9,
            pvalue=0.01, evidence="...", trigger_card="Mystery Card",
        )
        boundary = _boundary("2026-04-20", signals=(sig,))
        eras = {"Bar": _eras("Bar", [boundary])}
        out = attribute_boundaries(eras, ban_events=(), releases={}, series={})
        assert out[("Bar", "2026-04-20")].kind == "unattributed"


class TestToleranceBoundary:
    def test_exactly_tolerance_days_matches(self):
        s = _trackable_card_series("Foo", "Test Banned Card", 0.40, start=date(2026, 1, 19))
        boundary = _boundary("2026-03-16")  # 14 days after 2026-03-02
        eras = {"Foo": _eras("Foo", [boundary])}
        out = attribute_boundaries(eras, ban_events=_BAN_EVENTS, releases={}, series={"Foo": s}, tolerance_days=14)
        assert out[("Foo", "2026-03-16")].kind == "ban"

    def test_one_day_beyond_tolerance_is_unattributed(self):
        s = _trackable_card_series("Foo", "Test Banned Card", 0.40, start=date(2026, 1, 19))
        boundary = _boundary("2026-03-17")  # 15 days after 2026-03-02
        eras = {"Foo": _eras("Foo", [boundary])}
        out = attribute_boundaries(eras, ban_events=_BAN_EVENTS, releases={}, series={"Foo": s}, tolerance_days=14)
        assert out[("Foo", "2026-03-17")].kind == "unattributed"

    def test_exactly_tolerance_days_before_also_matches(self):
        s = _trackable_card_series("Foo", "Test Banned Card", 0.40, start=date(2026, 1, 19))
        boundary = _boundary("2026-02-16")  # 14 days before 2026-03-02
        eras = {"Foo": _eras("Foo", [boundary])}
        out = attribute_boundaries(eras, ban_events=_BAN_EVENTS, releases={}, series={"Foo": s}, tolerance_days=14)
        assert out[("Foo", "2026-02-16")].kind == "ban"


class TestFullAuditTrail:
    def test_every_boundary_gets_an_attribution_regardless_of_bh_acceptance(self):
        s = _trackable_card_series("Foo", "Test Banned Card", 0.40, start=date(2026, 1, 19))
        accepted = _boundary("2026-03-02", bh_accepted=True)
        rejected = _boundary("2026-03-16", bh_accepted=False)
        eras = {"Foo": EntityEras(entity="Foo", stable_since="2026-03-02", boundaries=(accepted, rejected), inherited_from_parent=False)}
        out = attribute_boundaries(eras, ban_events=_BAN_EVENTS, releases={}, series={"Foo": s})
        assert ("Foo", "2026-03-02") in out
        assert ("Foo", "2026-03-16") in out


class TestClosedVocabulary:
    def test_invalid_kind_raises(self):
        with pytest.raises(ValueError, match="kind"):
            Attribution(kind="maybe", card=None, detail="...")

    def test_valid_kinds_construct_fine(self):
        for kind in ("ban", "release", "unattributed"):
            Attribution(kind=kind, card=None, detail="...")
