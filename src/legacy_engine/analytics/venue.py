"""Venue abstraction for the three-lens meta frame (epic-three-venue-meta-frame).

Defines the ``Venue`` dataclass — one analysis lens (today: online / paper via
``tournaments.provenance``; local/regional deferred to epic-local-meta-support /
new event-tier dimension).  Provides:

- ``resolve_venues`` — map requested venue keys to ``Venue`` objects (fail-loud on
  unknown keys; absence-is-information — a zero-deck venue is kept, not silently
  dropped).
- ``compute_venue_metashare`` — thin composition layer over ``compute_metashare``
  that yields one ``VenueMetaShare`` per requested venue.
- ``venue_divergence`` — pure analytic: union archetypes across venues, compute
  per-archetype spread, sort desc, annotate speculative-tier rows (honesty contract).

Placement rule: analytics layer, NO advisory import.  Both ``analytics`` and
``advisory`` may import from here without a cycle (mirrors ``affectedness.py``).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import duckdb

from legacy_engine.analytics.metashare import MetaShareReport, MetaShareEntry, compute_metashare
from legacy_engine.confidence import tier_for_sample

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Venue abstraction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Venue:
    """One lens in the meta frame.

    ``provenance`` is the DuckDB filter today (``"online"`` / ``"paper"``).
    ``key``/``label`` are stable identifiers for display and dict keys.
    Future local/regional venues set ``provenance=None`` and carry their own
    filter predicate (added in the geo/event-tier phase) — the comparison
    surface iterates ``list[Venue]`` and never branches on provenance identity,
    so those future venues require no call-site changes here.
    """

    key: str            # "online" | "paper"  (later: "local:local", "regional")
    label: str          # "Online (MTGO)" | "Paper"
    provenance: str | None   # the only filter axis available today


ONLINE = Venue(key="online", label="Online (MTGO)", provenance="online")
PAPER = Venue(key="paper", label="Paper", provenance="paper")

DEFAULT_VENUES: tuple[Venue, ...] = (ONLINE, PAPER)

_VENUE_REGISTRY: dict[str, Venue] = {v.key: v for v in DEFAULT_VENUES}


def resolve_venues(
    con: duckdb.DuckDBPyConnection,
    requested: list[str] | None = None,
) -> list[Venue]:
    """Map requested venue keys to ``Venue`` objects, defaulting to ``DEFAULT_VENUES``.

    Unknown keys raise ``ValueError`` listing the available keys (fail-loud per
    the CLI pattern).  A requested venue with zero decks in the corpus is KEPT —
    its panel renders an explicit 'no data for this venue' note; absence is
    information in a divergence frame.
    """
    if requested is None:
        return list(DEFAULT_VENUES)

    resolved: list[Venue] = []
    unknown: list[str] = []
    for key in requested:
        venue = _VENUE_REGISTRY.get(key)
        if venue is None:
            unknown.append(key)
        else:
            resolved.append(venue)

    if unknown:
        valid_keys = sorted(_VENUE_REGISTRY.keys())
        raise ValueError(
            f"Unknown venue key(s) {unknown!r}; valid keys: {valid_keys}"
        )

    return resolved


# ---------------------------------------------------------------------------
# Unit 1 — compute_venue_metashare
# ---------------------------------------------------------------------------


@dataclass
class VenueMetaShare:
    """One venue's meta-share result.

    ``report`` is ``None`` when the venue has zero decks (not an empty report —
    renderers distinguish 'no data' from 'data, but everything below floor').
    """

    venue: Venue
    report: MetaShareReport | None   # None = zero-deck corpus for this venue


def compute_venue_metashare(
    con: duckdb.DuckDBPyConnection,
    venues: list[Venue],
    *,
    definition: str = "raw",
    min_share: float = 0.02,
    since: str | None = None,
    until: str | None = None,
) -> list[VenueMetaShare]:
    """Compute one ``MetaShareReport`` per venue via ``compute_metashare``.

    Uses ``group_other=False`` so every archetype is explicit (divergence needs
    raw per-archetype shares, not rolled-up Other buckets).  Empty-corpus venues
    return ``report=None`` rather than an empty report so the renderer can
    distinguish 'no data' from 'data, but everything below floor'.

    ``wrw`` + window is unsupported upstream and will raise ``NotImplementedError``
    from ``compute_metashare`` — the caller (CLI) guards this before calling here.
    """
    results: list[VenueMetaShare] = []
    for venue in venues:
        report = compute_metashare(
            con,
            definition=definition,
            provenance=venue.provenance,
            min_share=min_share,
            group_other=False,
            since=since,
            until=until,
        )
        if report.total_decks == 0:
            results.append(VenueMetaShare(venue=venue, report=None))
        else:
            results.append(VenueMetaShare(venue=venue, report=report))
    return results


# ---------------------------------------------------------------------------
# Unit 2 — venue_divergence
# ---------------------------------------------------------------------------


@dataclass
class ArchetypeDivergence:
    """Per-archetype divergence across venues."""

    archetype: str
    shares: dict[str, float]   # venue.key -> share (0.0 if absent in that venue)
    tiers: dict[str, str]      # venue.key -> confidence tier
    spread: float              # max(share) - min(share) across venues
    max_venue: str             # venue.key with the highest share
    min_venue: str             # venue.key with the lowest share


@dataclass
class VenueDivergence:
    """Full divergence frame across all venues."""

    venues: list[Venue]
    rows: list[ArchetypeDivergence]   # sorted desc by spread
    definition: str
    notes: list[str] = field(default_factory=list)


def venue_divergence(
    venue_shares: list[VenueMetaShare],
    *,
    min_spread: float = 0.0,
) -> VenueDivergence:
    """Union archetypes across venue reports; compute per-archetype spread, sort desc.

    Honesty contract (PRINCIPLES + confidence-metadata pattern): a divergence row
    whose larger share rests on a ``speculative`` or ``evolving`` tier is annotated
    in ``notes``, never silently presented as established fact.  Empty-corpus venues
    (``report=None``) generate a note and contribute 0.0 to every archetype's share
    on that side — this is intentional: absence is information and should not be hidden.

    ``min_spread`` filters rows below the threshold (default 0.0 = all rows shown).
    """
    notes: list[str] = []
    venues = [vs.venue for vs in venue_shares]

    # Collect all archetypes across venues that have data.
    # Build per-venue lookup: venue.key -> {archetype -> MetaShareEntry}
    venue_entry_map: dict[str, dict[str, MetaShareEntry]] = {}
    for vs in venue_shares:
        if vs.report is None:
            notes.append(
                f"{vs.venue.label} ({vs.venue.key}) has 0 decks; "
                "divergence vs other venues uses 0.0 share for all archetypes on this side"
            )
            venue_entry_map[vs.venue.key] = {}
        else:
            venue_entry_map[vs.venue.key] = {
                entry.archetype: entry for entry in vs.report.entries
            }

    # Union all archetypes appearing in any venue.
    all_archetypes: set[str] = set()
    for entry_map in venue_entry_map.values():
        all_archetypes.update(entry_map.keys())

    if not all_archetypes:
        return VenueDivergence(
            venues=venues,
            rows=[],
            definition=venue_shares[0].report.definition if venue_shares and venue_shares[0].report else "raw",
            notes=notes + ["no archetypes found across any venue"],
        )

    definition = _infer_definition(venue_shares)

    # Build divergence rows.
    rows: list[ArchetypeDivergence] = []
    speculative_high_spread: list[str] = []

    for archetype in all_archetypes:
        shares: dict[str, float] = {}
        tiers: dict[str, str] = {}
        for venue in venues:
            entry = venue_entry_map[venue.key].get(archetype)
            if entry is not None:
                shares[venue.key] = entry.share
                tiers[venue.key] = entry.tier
            else:
                # Archetype exists in another venue but not this one: share = 0.0
                shares[venue.key] = 0.0
                # Tier for 0 sample = speculative
                tiers[venue.key] = tier_for_sample(0)

        share_values = list(shares.values())
        spread = max(share_values) - min(share_values)

        if spread < min_spread:
            continue

        max_venue = max(shares, key=lambda k: shares[k])
        min_venue = min(shares, key=lambda k: shares[k])

        rows.append(ArchetypeDivergence(
            archetype=archetype,
            shares=shares,
            tiers=tiers,
            spread=spread,
            max_venue=max_venue,
            min_venue=min_venue,
        ))

        # Honesty annotation: high-spread row backed by speculative or evolving tier.
        if spread > 0:
            max_tier = tiers[max_venue]
            if max_tier in ("speculative", "evolving"):
                speculative_high_spread.append(
                    f"{archetype} (spread={spread:.3f}, {max_venue} tier={max_tier})"
                )

    # Sort desc by spread.
    rows.sort(key=lambda r: r.spread, reverse=True)

    _DIVERGENCE_NOTE_TOP_N = 8
    if speculative_high_spread:
        shown = speculative_high_spread[:_DIVERGENCE_NOTE_TOP_N]
        extra = len(speculative_high_spread) - len(shown)
        suffix = f" (+{extra} more)" if extra > 0 else ""
        notes.append(
            "The following high-spread rows are backed by thin sample data on the "
            "higher-share venue — treat magnitudes as provisional: "
            + "; ".join(shown) + suffix
        )

    return VenueDivergence(
        venues=venues,
        rows=rows,
        definition=definition,
        notes=notes,
    )


def _infer_definition(venue_shares: list[VenueMetaShare]) -> str:
    """Extract the definition string from the first non-None report."""
    for vs in venue_shares:
        if vs.report is not None:
            return vs.report.definition
    return "raw"
