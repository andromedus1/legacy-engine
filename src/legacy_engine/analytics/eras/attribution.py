"""Boundary attribution — snap a detected era boundary to the ban/release ledger within
tolerance, or label it an honest unattributed disturbance (the drift alarm's raw material).

**Ban check**: the nearest `BAN_EVENTS` entry within `tolerance_days` of the boundary date names
a candidate card. If that card is trackable in the entity's OWN flex band (`series.py`'s 10-95%
inclusion-rate window), the entity must have run it in >= `_BAN_AFFECT_THRESHOLD` (0.25 — reusing
`analytics/affectedness.py`'s own bar) of its pre-boundary decks to count as "ban". When the card
is NOT trackable (too ubiquitous — >95%, or too rare — <10% — to ever enter the flex band), the
attribution falls back to date-match alone, honestly noting the inclusion is unverified. This
fallback is not a loophole: it is the mechanism for the epic's own headline ground-truth case —
Tron runs Candelabra of Tawnos in ~100% of its decks, which sits ABOVE the flex band's ceiling
and can therefore never be verified via `card_incl`, exactly like the real `tron_cliff_series`
fixture documents.

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
# the THRESHOLD is the shared, sanctioned number here, not the implementation.
_BAN_AFFECT_THRESHOLD: float = 0.25


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


def _nearest_ban_event(
    ban_events: tuple[tuple[date, str, str], ...], boundary_date: date, tolerance_days: int,
) -> tuple[date, str] | None:
    """The closest ``BAN_EVENTS`` entry to ``boundary_date`` within ``tolerance_days`` (ties
    broken by earliest date), or ``None`` when nothing is within tolerance."""
    candidates = [
        (abs((event_date - boundary_date).days), event_date, card)
        for event_date, card, _reason in ban_events
        if abs((event_date - boundary_date).days) <= tolerance_days
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda t: (t[0], t[1]))
    _delta, event_date, card = candidates[0]
    return event_date, card


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
    nearest = _nearest_ban_event(ban_events, boundary_date, tolerance_days)
    if nearest is not None:
        event_date, card = nearest
        rate = _card_inclusion_before(s, card, boundary_date)
        if rate is None:
            return Attribution(
                kind="ban",
                card=card,
                detail=(
                    f"ban: {card} ({event_date.isoformat()}) — inclusion unverified "
                    "(not in this entity's flex band)"
                ),
            )
        if rate >= _BAN_AFFECT_THRESHOLD:
            return Attribution(
                kind="ban",
                card=card,
                detail=f"ban: {card} ({event_date.isoformat()}, {rate:.0%} pre-boundary inclusion)",
            )
        # Verified but below the affectedness threshold: this nearby ban doesn't explain THIS
        # entity's boundary — fall through to the release check, then unattributed.

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
