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
import math
from collections.abc import Collection
from dataclasses import dataclass
from typing import Literal

import duckdb

from legacy_engine.analytics.metashare import _is_never_other, compute_metashare
from legacy_engine.analytics.trends import regime_windows

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
        if not math.isfinite(share):
            raise ValueError(
                f"_normalize_shares: non-finite share {share!r} for archetype {archetype!r}"
            )
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


@dataclass(frozen=True)
class RegimeCurrency:
    """Count-backed evidence for how much of a field belongs to the current ban regime."""

    current_regime_since: str
    current_regime_label: str
    current_n: int | None
    total_n: int | None
    share: float | None
    reason: str | None


def _current_regime_identity() -> tuple[str, str]:
    current = regime_windows()[-1]
    if current.since is None:  # pragma: no cover - BAN_EVENTS always defines a current regime
        raise RuntimeError("current ban regime has no opening date")
    return current.since.isoformat(), current.label


def custom_regime_currency(
    *,
    current_n: int | None,
    total_n: int | None,
) -> RegimeCurrency:
    """Build exact custom-field currency, or an honest unavailable result."""
    regime_since, regime_label = _current_regime_identity()
    if current_n is not None and (not isinstance(current_n, int) or current_n < 0):
        raise ValueError("current_regime_n must be a non-negative integer")
    if total_n is not None and (not isinstance(total_n, int) or total_n < 0):
        raise ValueError("total_n must be a non-negative integer")
    if current_n is None:
        return RegimeCurrency(
            regime_since, regime_label, None, total_n, None,
            "unavailable for undated aggregate",
        )
    if total_n is None or total_n == 0:
        raise ValueError("current_regime_n requires a positive count basis")
    if current_n > total_n:
        raise ValueError(
            f"current_regime_n ({current_n}) cannot exceed total field count ({total_n})"
        )
    return RegimeCurrency(
        regime_since, regime_label, current_n, total_n, current_n / total_n, None
    )


def compute_regime_currency(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> RegimeCurrency:
    """Measure current-regime share over the same dated, positionable global-field population."""
    return _compute_regime_currency(
        con,
        provenance=provenance,
        since=since,
        until=until,
        definition="raw",
    )


def _compute_regime_currency(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None,
    since: str | None,
    until: str | None,
    definition: str,
) -> RegimeCurrency:
    regime_since, regime_label = _current_regime_identity()

    def positionable_n(window_since: str | None, window_until: str | None) -> int:
        report = compute_metashare(
            con,
            definition=definition,
            provenance=provenance,
            group_other=False,
            since=window_since,
            until=window_until,
        )
        return sum(entry.n for entry in report.entries if not _is_never_other(entry.archetype))

    total_n = positionable_n(since, until)
    if total_n == 0:
        return RegimeCurrency(
            regime_since, regime_label, 0, 0, None,
            "no positionable decks in selected field window",
        )

    current_since = max(filter(None, (since, regime_since)), default=regime_since)
    current_n = 0 if until is not None and until <= current_since else positionable_n(
        current_since, until
    )
    return RegimeCurrency(
        regime_since, regime_label, current_n, total_n, current_n / total_n, None
    )


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
    regime_currency: RegimeCurrency | None = None

    def restrict_to(self, keep: Collection[str]) -> tuple["FieldDistribution", float]:
        """Return a copy restricted to ``keep`` (renormalized to sum 1.0) + the excluded share mass.

        ``shares`` is filtered to ``keep ∩ shares`` and renormalized directly — NOT via
        ``_normalize_shares``, since an intentional restriction is not a data-quality issue and
        should not emit a "summed to X" warning.  ``counts`` (if not ``None``) is filtered to the
        kept keys but NOT renormalized — counts are integer backing samples, not shares.
        ``no_data`` is intersected with the kept set; ``field_source`` and ``warnings`` are
        preserved.

        Returns ``(restricted_field, excluded_share)`` where ``excluded_share`` is the summed
        share-mass of the dropped archetypes.  Raises ``ValueError`` if the kept set has zero
        overlapping share mass (callers guard via a coverage check before calling).
        """
        keep_set = set(keep)
        kept = {a: s for a, s in self.shares.items() if a in keep_set}
        kept_total = sum(kept.values())
        if kept_total <= 0:
            raise ValueError(
                "FieldDistribution.restrict_to: kept set has zero share mass; "
                "nothing to renormalize"
            )

        excluded_share = 1.0 - kept_total
        restricted_shares = {a: s / kept_total for a, s in kept.items()}

        restricted_counts: dict[str, int] | None
        if self.counts is None:
            restricted_counts = None
        else:
            restricted_counts = {a: c for a, c in self.counts.items() if a in keep_set}

        return (
            FieldDistribution(
                shares=restricted_shares,
                field_source=self.field_source,
                counts=restricted_counts,
                no_data=self.no_data & frozenset(keep_set),
                warnings=self.warnings,
                regime_currency=self.regime_currency,
            ),
            excluded_share,
        )


# ---------------------------------------------------------------------------
# Unit 3 — build_global_field
# ---------------------------------------------------------------------------


def build_global_field(
    con: duckdb.DuckDBPyConnection,
    *,
    definition: str = "raw",
    provenance: str | None = None,
    min_share: float = 0.0,
    since: str | None = None,
    until: str | None = None,
) -> FieldDistribution:
    """Build the global field from the labeled corpus via ``compute_metashare``.

    Uses ``group_other=False`` so every archetype is an explicit element.  Excludes
    Unknown/Conflict labels (renormalizing + warning with the excluded share fraction).
    Carries the per-archetype deck counts as the Dirichlet ``counts``.
    ``field_source='global'``.

    ``since``/``until`` window the field by ``tournaments.date`` (half-open
    ``[since, until)``); both ``None`` (default) = full corpus. Windowed ``wrw`` is
    unsupported upstream, but the default ``raw`` definition windows fine.
    """
    report = compute_metashare(
        con,
        definition=definition,
        provenance=provenance,
        min_share=min_share,
        group_other=False,
        since=since,
        until=until,
    )
    regime_currency = _compute_regime_currency(
        con,
        provenance=provenance,
        since=since,
        until=until,
        definition=definition,
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
            regime_currency=regime_currency,
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
        regime_currency=regime_currency,
    )


# ---------------------------------------------------------------------------
# Unit 4 — build_custom_field
# ---------------------------------------------------------------------------


def build_custom_field(
    shares: dict[str, float],
    *,
    known_archetypes: frozenset[str] | None = None,
    counts: dict[str, int] | None = None,
    regime_currency: RegimeCurrency | None = None,
) -> FieldDistribution:
    """Build a user-supplied custom field (the 'best call for MY room' headline).

    Normalizes via ``_normalize_shares`` (warn on sum!=1).  If ``known_archetypes`` is
    given, archetypes absent from it are flagged in ``no_data`` + warned (kept in the
    field for downstream wide-uncertainty imputation).

    ``counts`` (optional): per-archetype backing sample counts that feed the Dirichlet
    posterior in positioning.  When provided, positioning models field-share uncertainty
    instead of using fixed point shares.  When ``None`` (share-only, the default),
    positioning uses fixed point shares and a warning is emitted to that effect.

    ``counts`` must cover exactly the same keys as ``shares`` after normalization;
    every count must be a positive integer.  A ``ValueError`` is raised if the counts
    are malformed or mismatched.

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

    resolved_counts: dict[str, int] | None
    if counts is not None:
        # Validate counts: must be a dict of positive integers keyed to the same archetypes.
        missing_keys = set(normalized) - set(counts)
        extra_keys = set(counts) - set(normalized)
        if missing_keys:
            raise ValueError(
                "build_custom_field: counts missing keys present in shares: "
                + ", ".join(sorted(missing_keys))
            )
        if extra_keys:
            raise ValueError(
                "build_custom_field: counts has extra keys not in shares: "
                + ", ".join(sorted(extra_keys))
            )
        for archetype, count in counts.items():
            if not isinstance(count, int) or count < 1:
                raise ValueError(
                    f"build_custom_field: count for {archetype!r} must be a positive integer, "
                    f"got {count!r}"
                )
        resolved_counts = counts
        warnings.append(
            "custom field carries counts; positioning will use Dirichlet-backed field-share uncertainty"
        )
    else:
        resolved_counts = None
        warnings.append(
            "custom field is share-only (counts=None); positioning will use point shares "
            "(no field-share uncertainty)"
        )

    return FieldDistribution(
        shares=normalized,
        field_source="custom",
        counts=resolved_counts,
        no_data=no_data,
        warnings=tuple(warnings),
        regime_currency=regime_currency,
    )
