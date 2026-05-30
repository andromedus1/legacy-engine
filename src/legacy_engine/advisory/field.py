"""Field distribution model — the advisory SSOT for "what is the field".

Provides ``FieldDistribution`` (archetype→share map with confidence-backing counts),
and two builders:

- ``build_global_field`` — derived from the labeled corpus via ``compute_metashare``.
- ``build_custom_field`` — from a user-supplied archetype→share map.

All consumers (positioning, sideboard, what-to-play) read ``FieldDistribution``; none
re-derive the field independently.  ``field_source`` is ALWAYS set (PRINCIPLES #6 spirit).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import duckdb

from legacy_engine.analytics.metashare import _is_never_other, compute_metashare

log = logging.getLogger(__name__)

_SUM_TOLERANCE = 1e-6

# ---------------------------------------------------------------------------
# Unit 1 — _normalize_shares
# ---------------------------------------------------------------------------


def _normalize_shares(raw: dict[str, float]) -> tuple[dict[str, float], list[str]]:
    """Validate and normalize a raw archetype→share map to sum 1.0.

    Returns ``(normalized_shares, warnings)``.  Fail-fast (``ValueError``) on an empty
    map, any negative share, or an all-zero/zero-sum map.  If the input sum deviates
    from 1.0 beyond ``_SUM_TOLERANCE``, normalize and emit a warning naming the original
    sum.
    """
    if not raw:
        raise ValueError("_normalize_shares: share map must not be empty")

    for archetype, share in raw.items():
        if share < 0:
            raise ValueError(
                f"_normalize_shares: negative share {share!r} for archetype {archetype!r}"
            )

    total = sum(raw.values())
    if total <= 0:
        raise ValueError(
            f"_normalize_shares: shares sum to {total!r} (all-zero or zero-sum); cannot normalize"
        )

    warnings: list[str] = []
    if abs(total - 1.0) > _SUM_TOLERANCE:
        warnings.append(
            f"field shares summed to {total:.4f}; normalized to 1.0"
        )

    normalized = {archetype: share / total for archetype, share in raw.items()}
    return normalized, warnings


# ---------------------------------------------------------------------------
# Unit 2 — FieldSource + FieldDistribution
# ---------------------------------------------------------------------------

FieldSource = Literal["global", "custom", "local"]


@dataclass
class FieldDistribution:
    """The expected field a deck is positioned against — the advisory SSOT for 'what is the field'.

    ``shares`` sums to ~1.0 over positionable archetypes (Unknown/Conflict excluded).
    ``counts`` is the per-archetype backing sample for a Dirichlet posterior, or ``None`` for a
    share-only custom field (positioning then uses point shares).  ``field_source`` is ALWAYS set.
    ``no_data`` are field archetypes lacking backing data (wide-uncertainty imputation downstream).
    """

    shares: dict[str, float]
    field_source: FieldSource
    counts: dict[str, int] | None
    no_data: frozenset[str]
    warnings: tuple[str, ...]


# ---------------------------------------------------------------------------
# Unit 3 — build_global_field
# ---------------------------------------------------------------------------


def build_global_field(
    con: duckdb.DuckDBPyConnection,
    *,
    definition: str = "raw",
    provenance: str | None = None,
    min_share: float = 0.0,
) -> FieldDistribution:
    """Build the global field from the labeled corpus via ``compute_metashare``.

    Uses ``group_other=False`` so every archetype is an explicit element.  Excludes
    Unknown/Conflict labels (renormalizing + warning with the excluded share fraction).
    Carries the per-archetype deck counts as the Dirichlet ``counts``.
    ``field_source='global'``.
    """
    report = compute_metashare(
        con,
        definition=definition,
        provenance=provenance,
        min_share=min_share,
        group_other=False,
    )

    kept_entries = []
    excluded_share = 0.0
    for entry in report.entries:
        if _is_never_other(entry.archetype):
            excluded_share += entry.share
        else:
            kept_entries.append(entry)

    warnings: list[str] = []
    if excluded_share > 0:
        warnings.append(
            f"excluded {excluded_share:.1%} unclassified (Unknown/Conflict) from the field"
        )

    if not kept_entries:
        # No positionable archetypes — return an empty distribution with a warning
        warnings.append("no positionable archetypes found; field is empty")
        return FieldDistribution(
            shares={},
            field_source="global",
            counts={},
            no_data=frozenset(),
            warnings=tuple(warnings),
        )

    raw_shares = {entry.archetype: entry.share for entry in kept_entries}
    normalized, norm_warnings = _normalize_shares(raw_shares)
    warnings.extend(norm_warnings)

    counts = {entry.archetype: entry.n for entry in kept_entries}

    return FieldDistribution(
        shares=normalized,
        field_source="global",
        counts=counts,
        no_data=frozenset(),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Unit 4 — build_custom_field
# ---------------------------------------------------------------------------


def build_custom_field(
    shares: dict[str, float],
    *,
    known_archetypes: frozenset[str] | None = None,
) -> FieldDistribution:
    """Build a user-supplied custom field (the 'best call for MY room' headline).

    Normalizes via ``_normalize_shares`` (warn on sum!=1).  If ``known_archetypes`` is
    given, archetypes absent from it are flagged in ``no_data`` + warned (kept in the
    field for downstream wide-uncertainty imputation).  ``counts=None`` (share-only) →
    positioning uses point shares; emits a warning to that effect.
    ``field_source='custom'``.
    """
    normalized, warnings = _normalize_shares(shares)

    no_data: frozenset[str]
    if known_archetypes is not None:
        missing = frozenset(a for a in normalized if a not in known_archetypes)
        no_data = missing
        if missing:
            missing_str = ", ".join(sorted(missing))
            warnings.append(
                f"archetypes not in known corpus (no matchup data — wide-uncertainty imputation "
                f"downstream): {missing_str}"
            )
    else:
        no_data = frozenset()

    warnings.append(
        "custom field is share-only (counts=None); positioning will use point shares "
        "(no field-share uncertainty)"
    )

    return FieldDistribution(
        shares=normalized,
        field_source="custom",
        counts=None,
        no_data=no_data,
        warnings=tuple(warnings),
    )
