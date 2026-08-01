"""Boundary attribution — snap a detected era boundary to the ban/release ledger within
tolerance, or label it an honest unattributed disturbance (the drift alarm's raw material).

**Ban check**: `events_on_nearest_date` finds the single `BAN_EVENTS` date closest to the
boundary date within `tolerance_days` and collects EVERY card banned on that date (a same-date
cohort can hold more than one card — e.g. Entomb + Nadu, Winged Wisdom on 2025-11-10).
`rank_same_date_cards` ranks that cohort by this entity's own pre-boundary inclusion so the
card that actually explains the disturbance wins, not whichever one happens to sort first
alphabetically. If the best-ranked card is trackable in the entity's OWN flex band (`series.py`'s
10-95% inclusion-rate window), the entity must have run it in >= `BAN_AFFECT_THRESHOLD` (0.25 —
reusing `analytics/affectedness.py`'s own bar) of its pre-boundary decks to count as "ban". When
the card is NOT trackable (too ubiquitous — >95%, or too rare — <10% — to ever enter the flex
band), the attribution falls back to date-match alone, honestly noting the inclusion is
unverified. This fallback is not a loophole: it is the mechanism for the epic's own headline
ground-truth case — Tron runs Candelabra of Tawnos in ~100% of its decks, which sits ABOVE the
flex band's ceiling and can therefore never be verified via `card_incl`, exactly like the real
`tron_cliff_series` fixture documents. Any other same-date cards are named as secondaries in
`.detail`, never silently dropped.

**Release check**: only for a boundary carrying its own S1 `presence-adopt` signal (the only
signal type that names a `trigger_card`) whose set release date (an injected `releases` mapping)
falls within tolerance of the boundary date. When `releases` has no entry at all for the trigger
card (the common case: the `cards` table carries no release-date column, so `run.py`'s default
`releases` source is empty), a `corpus_first_seen` mapping (the card's earliest corpus
appearance — `run.py`'s batched fallback query) fills the gap: an S1 adoption boundary that lines
up with the card's first appearance in the corpus attributes as `"release"` too, honestly noting
the date is a first-appearance proxy rather than an authoritative release date. The injected/
schema `releases` source always wins outright when it names the card — the fallback only ever
fires on a missing entry, never overriding a present-but-out-of-tolerance one.

Neither check matching -> `"unattributed disturbance — possible unregistered B&R change"`, the
raw material `run.compute_drift_alarms` surfaces loudly for high-share entities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from legacy_engine.analytics.eras.ensemble import EntityEras
from legacy_engine.analytics.eras.series import EntitySeries

# Closed vocabulary (closed-vocabulary-fail-fast-token pattern).
_ATTRIBUTION_KINDS = frozenset({"ban", "release", "unattributed"})

# Reuses analytics/affectedness.py's own bar (`_DEFAULT_AFFECT_THRESHOLD`) as a literal constant
# rather than importing it: that module's constant is private, and its own home is a DB-driven
# code path (`archetype_valid_since`/`explain_valid_since`) distinct from this pure-series one —
# the THRESHOLD is the shared, sanctioned number here, not the implementation. Public (was
# `_BAN_AFFECT_THRESHOLD`) — shared with `run.py`'s alarm-wording gate, not just this module's own
# ban-attribution decision.
BAN_AFFECT_THRESHOLD: float = 0.25


@dataclass(frozen=True)
class Attribution:
    """One boundary's provenance verdict."""

    kind: str
    card: str | None
    detail: str

    def __post_init__(self) -> None:
        if self.kind not in _ATTRIBUTION_KINDS:
            raise ValueError(
                f"Attribution: kind {self.kind!r} must be one of {sorted(_ATTRIBUTION_KINDS)}"
            )


def _card_inclusion_before(s: "EntitySeries | None", card: str, before: date) -> float | None:
    """Pooled pre-boundary inclusion rate for ``card`` over ``s``'s COMPLETE buckets strictly
    before ``before``. ``None`` when ``s`` is absent, ``card`` isn't in this entity's own flex
    band, or there is no pre-boundary sample — the caller's signal to fall back to date-match-only
    attribution.
    """
    if s is None or card not in s.flex_cards:
        return None
    pre = [b for b in s.buckets if b.complete and b.start < before.isoformat()]
    total_decks = sum(b.decks for b in pre)
    if total_decks == 0:
        return None
    total_incl = sum(b.card_incl.get(card, 0) for b in pre)
    return total_incl / total_decks


def is_plausible_ban(inclusion_rate: float | None) -> bool:
    """True unless we have POSITIVE evidence this entity doesn't run the card enough for a
    nearby ban to explain its disturbance. ``None`` (not trackable in this entity's own flex
    band — e.g. a ubiquitous chassis card like Candelabra of Tawnos in Tron, or one this entity
    never runs at all) is plausible-by-default: unproven, not disproven. Only a MEASURED rate
    below ``BAN_AFFECT_THRESHOLD`` is disqualifying. Shared by `_attribute_one`'s ban/fall-through
    decision and `run.compute_drift_alarms`'s wording gate so the two call sites can never
    quietly disagree on what "plausible" means.
    """
    return inclusion_rate is None or inclusion_rate >= BAN_AFFECT_THRESHOLD


def events_on_nearest_date(
    ban_events: tuple[tuple[date, str, str], ...], boundary_date: date, tolerance_days: int,
) -> tuple[date, list[str]] | None:
    """The single ``BAN_EVENTS`` date closest to ``boundary_date`` within ``tolerance_days`` (ties
    broken by earliest date), plus EVERY card banned on that date — the same-date cohort a single
    boundary/disturbance must rank across, rather than the first card in list/alphabetical order.
    ``None`` when nothing is within tolerance.
    """
    candidates = [
        (abs((event_date - boundary_date).days), event_date)
        for event_date, _card, _reason in ban_events
        if abs((event_date - boundary_date).days) <= tolerance_days
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda t: (t[0], t[1]))
    _delta, nearest_date = candidates[0]
    cards = sorted({card for event_date, card, _r in ban_events if event_date == nearest_date})
    return nearest_date, cards


def rank_same_date_cards(
    cards: list[str], s: "EntitySeries | None", boundary_date: date,
) -> list[tuple[str, float | None]]:
    """Rank a same-date ban cohort by entity relevance, best-supported first:

    1. verified AND affecting (``inclusion_rate >= BAN_AFFECT_THRESHOLD``) — ranked by inclusion
       descending (the 2025-11-10 fix: Nadu's 91% must outrank Entomb here);
    2. unverifiable (``_card_inclusion_before`` returns ``None`` — not in this entity's own flex
       band, e.g. Candelabra in Tron) — unproven but not ruled out, so these outrank...
    3. verified BUT below threshold — this entity demonstrably does not run the card enough to be
       the cause of ITS OWN boundary (e.g. a 15%-inclusion card on an entity whose disturbance is
       something else entirely).

    A single-card cohort trivially returns that one card — this generalizes the existing
    single-candidate behavior rather than replacing it (every prior test with exactly one
    same-date event gets byte-identical output).
    """
    scored = [(card, _card_inclusion_before(s, card, boundary_date)) for card in cards]

    def _tier(rate: float | None) -> int:
        if rate is not None and rate >= BAN_AFFECT_THRESHOLD:
            return 0
        if rate is None:
            return 1
        return 2

    def _key(item: tuple[str, float | None]) -> tuple[int, float, str]:
        card, rate = item
        return (_tier(rate), -(rate if rate is not None else 0.0), card)

    return sorted(scored, key=_key)


def _attribute_one(
    boundary,
    boundary_date: date,
    s: "EntitySeries | None",
    *,
    ban_events: tuple[tuple[date, str, str], ...],
    releases: dict[str, date],
    tolerance_days: int,
    corpus_first_seen: dict[str, date] | None = None,
) -> Attribution:
    nearest = events_on_nearest_date(ban_events, boundary_date, tolerance_days)
    if nearest is not None:
        event_date, cards = nearest
        ranked = rank_same_date_cards(cards, s, boundary_date)
        card, rate = ranked[0]
        secondaries = [c for c, _r in ranked[1:]]
        secondary_note = f"; also banned this date: {', '.join(secondaries)}" if secondaries else ""
        if rate is None:
            return Attribution(
                kind="ban",
                card=card,
                detail=(
                    f"ban: {card} ({event_date.isoformat()}) — inclusion unverified "
                    f"(not in this entity's flex band){secondary_note}"
                ),
            )
        if is_plausible_ban(rate):
            return Attribution(
                kind="ban",
                card=card,
                detail=(
                    f"ban: {card} ({event_date.isoformat()}, {rate:.0%} pre-boundary inclusion)"
                    f"{secondary_note}"
                ),
            )
        # Best-ranked same-date card is verified but below threshold: none of this date's bans
        # explain this boundary — fall through to the release check, then unattributed.

    for sig in boundary.signals:
        if sig.signal != "presence-adopt" or not sig.trigger_card:
            continue
        release_date = releases.get(sig.trigger_card)
        fallback_note: str | None = None
        if release_date is None and corpus_first_seen:
            first_seen = corpus_first_seen.get(sig.trigger_card)
            if first_seen is not None:
                release_date = first_seen
                fallback_note = f"first corpus appearance {first_seen.isoformat()}"
        if release_date is None:
            continue
        if abs((release_date - boundary_date).days) <= tolerance_days:
            detail = (
                f"release: {sig.trigger_card} adoption ({fallback_note})"
                if fallback_note is not None
                else f"release: {sig.trigger_card} adoption ({release_date.isoformat()})"
            )
            return Attribution(kind="release", card=sig.trigger_card, detail=detail)

    return Attribution(
        kind="unattributed",
        card=None,
        detail="unattributed disturbance — possible unregistered B&R change",
    )


def attribute_boundaries(
    eras: dict[str, EntityEras],
    *,
    ban_events: tuple[tuple[date, str, str], ...],
    releases: dict[str, date],
    series: dict[str, EntitySeries],
    tolerance_days: int = 14,
    corpus_first_seen: dict[str, date] | None = None,
) -> dict[tuple[str, str], Attribution]:
    """Attribute every boundary in every entity's `EntityEras.boundaries` — accepted or not, the
    full audit trail (mirrors `explain_valid_since`'s per-event derivation walk, which shows every
    ban event regardless of whether it ultimately moved `valid_since`).

    ``corpus_first_seen`` (optional; ``None``/empty = no-op, byte-identical to the pre-fallback
    behavior) is the release check's corpus-first-seen fallback — see module docstring.
    """
    out: dict[tuple[str, str], Attribution] = {}
    for entity, entity_eras in eras.items():
        s = series.get(entity)
        for boundary in entity_eras.boundaries:
            boundary_date = date.fromisoformat(boundary.date)
            out[(entity, boundary.date)] = _attribute_one(
                boundary, boundary_date, s,
                ban_events=ban_events, releases=releases, tolerance_days=tolerance_days,
                corpus_first_seen=corpus_first_seen,
            )
    return out
