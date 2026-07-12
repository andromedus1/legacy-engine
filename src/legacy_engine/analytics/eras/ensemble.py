"""Ensemble merge + fleet-wide BH-FDR + deck floor + camp inheritance -> `stable_since(entity)`.

Takes every detector's raw `CandidateBoundary` output (S1-S4, `detect.py`) plus the `EntitySeries`
map it was derived from, and reduces it to one `EntityEras` per entity: a chronological list of
merged boundaries (both accepted and rejected — an honest audit trail) and a single
`stable_since` date (or `None` for full history).

Three passes, in order (epic Unit 4, brief §4):

1. **Merge** — per entity, candidates within `merge_tolerance_buckets` of each other (bucket
   distance computed off THAT entity's own bucket grid, since bucket width is density-adaptive)
   collapse into one `EraBoundary`; the merged date is the min-p component's date, and every
   component survives in `signals` (multi-signal corroboration strengthens a boundary without
   losing any evidence).
2. **BH-FDR**, fleet-wide, across every merged boundary's pre-BH p-value (`alpha`, default 0.05)
   — the make-or-break false-positive control the brief insists on (§4: per-entity screening
   accumulates error across ~50-150 entities every refresh).
3. **Deck floor** — a BH-surviving boundary is still `floor_rejected` (a sanctioned extra field,
   see `EraBoundary`) unless the entity has `>= min_new_era_decks` decks in buckets at/after the
   boundary date; `stable_since` is the date of the LAST boundary that is both `bh_accepted` and
   not `floor_rejected`.

Camp entities that end up with zero of their own accepted boundaries inherit their parent's
boundaries and `stable_since` wholesale (`inherited_from_parent=True`) — a thin camp cannot
fabricate its own eras (brief §6). A camp WITH its own accepted boundaries keeps them, but a
parent-wide disturbance still disturbs every camp: its effective `stable_since` is
`max(own, parent's)` (the later — more truncating — of the two), documented at `_max_date`.

Pure; no DB, no persistence (the era-ledger feature owns storage/attribution downstream).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date

from statsmodels.stats.multitest import multipletests

from legacy_engine.analytics.eras.detect import CandidateBoundary
from legacy_engine.analytics.eras.series import EntitySeries


@dataclass(frozen=True)
class EraBoundary:
    """One merged, fleet-FDR-screened era boundary for a single entity.

    ``pvalue`` is the min component p-value, captured BEFORE BH correction (the corrected
    decision lives in ``bh_accepted``). ``floor_rejected`` is a sanctioned deviation from the
    epic's Unit 4 contract (which specified only ``date``/``signals``/``pvalue``/``bh_accepted``):
    without it there is no way to represent "survived FDR but the resulting era is too thin to
    trust" as anything other than silently indistinguishable from "never survived FDR at all" —
    and the deck floor is deliberately a SEPARATE defense from FDR (brief §4 items 1-2 vs. item
    3), so collapsing the two into one boolean would erase an audit-relevant distinction.
    """

    date: str
    signals: tuple[CandidateBoundary, ...]
    pvalue: float
    bh_accepted: bool
    floor_rejected: bool = False


@dataclass(frozen=True)
class EntityEras:
    """Per-entity derived era history."""

    entity: str
    stable_since: str | None
    boundaries: tuple[EraBoundary, ...]
    inherited_from_parent: bool


# ---------------------------------------------------------------------------
# Pass 1 — merge within tolerance, per entity
# ---------------------------------------------------------------------------


def _bucket_index_map(s: EntitySeries) -> dict[str, int]:
    return {b.start: i for i, b in enumerate(s.buckets)}


def _bucket_distance(
    s: EntitySeries, date_a: str, date_b: str, bucket_idx: dict[str, int],
) -> int:
    """Distance between two bucket-start dates, in THIS entity's own bucket units."""
    if date_a in bucket_idx and date_b in bucket_idx:
        return abs(bucket_idx[date_a] - bucket_idx[date_b])
    # Fallback for a date that isn't one of this entity's own bucket starts (shouldn't normally
    # happen — every CandidateBoundary.date comes from a bucket of the series it was detected
    # against) — estimate off the entity's own bucket width so the tolerance stays meaningful.
    days = abs((date.fromisoformat(date_a) - date.fromisoformat(date_b)).days)
    return round(days / (7 * max(s.bucket_weeks, 1)))


def _merge_entity_candidates(
    s: EntitySeries, cands: list[CandidateBoundary], *, tolerance: int,
) -> list[EraBoundary]:
    """Single-linkage merge of one entity's candidates within `tolerance` buckets of each other."""
    if not cands:
        return []
    bucket_idx = _bucket_index_map(s)
    ordered = sorted(cands, key=lambda c: bucket_idx.get(c.date, 10**9))

    groups: list[list[CandidateBoundary]] = []
    for c in ordered:
        if groups and _bucket_distance(s, groups[-1][-1].date, c.date, bucket_idx) <= tolerance:
            groups[-1].append(c)
        else:
            groups.append([c])

    merged = []
    for g in groups:
        strongest = min(g, key=lambda c: c.pvalue)
        merged.append(EraBoundary(
            date=strongest.date,
            signals=tuple(g),
            pvalue=strongest.pvalue,
            bh_accepted=False,  # set by the fleet-wide BH pass
        ))
    return sorted(merged, key=lambda b: bucket_idx.get(b.date, 10**9))


# ---------------------------------------------------------------------------
# Pass 3 — camp inheritance helper
# ---------------------------------------------------------------------------


def _max_date(a: str | None, b: str | None) -> str | None:
    """The later (more truncating) of two `stable_since` dates; `None` means "no disturbance"."""
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)  # ISO 'YYYY-MM-DD' strings sort lexicographically == chronologically


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def derive_eras(
    series: dict[str, EntitySeries],
    candidates: list[CandidateBoundary],
    *,
    alpha: float = 0.05,
    merge_tolerance_buckets: int = 2,
    min_new_era_decks: int = 30,
) -> dict[str, EntityEras]:
    """Reduce raw detector candidates to one `EntityEras` per entity in `series`."""
    by_entity: dict[str, list[CandidateBoundary]] = defaultdict(list)
    for c in candidates:
        by_entity[c.entity].append(c)

    # ---- Pass 1: per-entity merge -----------------------------------------
    merged_by_entity: dict[str, list[EraBoundary]] = {
        entity: _merge_entity_candidates(
            s, by_entity.get(entity, []), tolerance=merge_tolerance_buckets,
        )
        for entity, s in series.items()
    }

    # ---- Pass 2: fleet-wide BH-FDR -----------------------------------------
    flat_keys: list[tuple[str, int]] = []
    pvals: list[float] = []
    for entity, boundaries in merged_by_entity.items():
        for i, b in enumerate(boundaries):
            flat_keys.append((entity, i))
            pvals.append(b.pvalue)

    if pvals:
        reject, _, _, _ = multipletests(pvals, alpha=alpha, method="fdr_bh")
        for (entity, i), accepted in zip(flat_keys, reject):
            merged_by_entity[entity][i] = replace(
                merged_by_entity[entity][i], bh_accepted=bool(accepted),
            )

    # ---- Pass 3: deck floor -------------------------------------------------
    for entity, boundaries in merged_by_entity.items():
        s = series[entity]
        for i, b in enumerate(boundaries):
            if not b.bh_accepted:
                continue
            decks_after = sum(bucket.decks for bucket in s.buckets if bucket.start >= b.date)
            if decks_after < min_new_era_decks:
                boundaries[i] = replace(b, floor_rejected=True)

    # ---- Own (pre-inheritance) stable_since per entity ----------------------
    own_stable_since: dict[str, str | None] = {}
    for entity, boundaries in merged_by_entity.items():
        accepted = [b for b in boundaries if b.bh_accepted and not b.floor_rejected]
        own_stable_since[entity] = accepted[-1].date if accepted else None

    # ---- Pass 4 (camp inheritance) + assemble -------------------------------
    result: dict[str, EntityEras] = {}
    for entity, s in series.items():
        own_boundaries = tuple(merged_by_entity.get(entity, []))
        own_since = own_stable_since.get(entity)
        parent = s.parent

        if parent != entity and parent in series:
            parent_since = own_stable_since.get(parent)
            parent_boundaries = tuple(merged_by_entity.get(parent, []))
            parent_has_accepted = any(
                b.bh_accepted and not b.floor_rejected for b in parent_boundaries
            )
            has_own_accepted = any(
                b.bh_accepted and not b.floor_rejected for b in own_boundaries
            )
            if not has_own_accepted and parent_has_accepted:
                # Thin-camp inheritance: a camp with no accepted boundaries of its own rides
                # its parent's era history wholesale (brief §6 — never let a thin camp
                # fabricate, or silently miss, its own eras).
                result[entity] = EntityEras(
                    entity=entity,
                    stable_since=parent_since,
                    boundaries=parent_boundaries,
                    inherited_from_parent=True,
                )
                continue
            # A camp with its own accepted boundaries keeps them — but a parent-wide
            # disturbance disturbs every camp, so the effective stable_since is the LATER of
            # own vs parent's (`_max_date`); a camp can be MORE recently disturbed than its
            # parent, never less. When the parent's date wins, the parent's winning boundary
            # is appended to the camp's boundary list so `stable_since` always resolves to a
            # boundary PRESENT in `boundaries` — the explain surface must never have to hunt
            # a horizon's justification on a different entity.
            effective_since = _max_date(own_since, parent_since)
            camp_boundaries = own_boundaries
            if effective_since is not None and effective_since != own_since:
                parent_winning = [
                    b for b in parent_boundaries
                    if b.bh_accepted and not b.floor_rejected and b.date == effective_since
                ]
                camp_boundaries = tuple(
                    sorted((*own_boundaries, *parent_winning), key=lambda b: b.date)
                )
            result[entity] = EntityEras(
                entity=entity,
                stable_since=effective_since,
                boundaries=camp_boundaries,
                inherited_from_parent=False,
            )
            continue

        result[entity] = EntityEras(
            entity=entity,
            stable_since=own_since,
            boundaries=own_boundaries,
            inherited_from_parent=False,
        )
    return result
