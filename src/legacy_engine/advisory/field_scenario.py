"""Validated custom-field scenarios for private Deck Rankings reports.

The field-file grammar remains owned by :func:`advisory.report._load_field`.
This module adds only the scenario identity and evidence accounting needed by
the ranking report, so a custom field cannot be mistaken for global observations.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import duckdb

from legacy_engine.advisory.field import FieldDistribution
from legacy_engine.advisory.report import _load_field

_EFFECTIVE_N = re.compile(r"^effective_n\s*:\s*(\S+)$", re.IGNORECASE)


@dataclass(frozen=True)
class FieldScenario:
    """A validated custom field plus immutable source/evidence metadata."""

    field: FieldDistribution
    label: str
    source_path: str
    source_sha256: str
    supplied_counts: dict[str, int] | None
    supplied_total: int | None
    declared_effective_n: int | None
    effective_count_total: int | None
    count_basis: str
    unknown_opponents: tuple[str, ...]
    unknown_share: float
    warnings: tuple[str, ...]

    @property
    def shares(self) -> dict[str, float]:
        return dict(self.field.shares)

    @property
    def counts(self) -> dict[str, int] | None:
        return None if self.field.counts is None else dict(self.field.counts)

    @property
    def posterior_counts(self) -> dict[str, float] | None:
        """Return concentration counts with a declared effective-N total.

        The legacy parser allocates at least one count to every label, so a
        small ``# effective_n`` can intentionally overshoot when materialized
        as integers.  Keep those integers for provenance while scaling the
        counts used by the posterior back to the declared concentration.
        """
        if self.field.counts is None:
            return None
        counts = {label: float(value) for label, value in self.field.counts.items()}
        if self.declared_effective_n is None:
            return counts
        total = sum(counts.values())
        if total <= 0:
            return counts
        factor = float(self.declared_effective_n) / total
        return {label: value * factor for label, value in counts.items()}

    def projection_field(self) -> FieldDistribution:
        """Return the field object used by ranking, preserving source metadata."""
        counts = self.posterior_counts
        return FieldDistribution(
            shares=dict(self.field.shares),
            field_source=self.field.field_source,
            counts=None if counts is None else counts,
            no_data=self.field.no_data,
            warnings=self.field.warnings,
            regime_currency=self.field.regime_currency,
        )

    def identity(self) -> dict[str, Any]:
        """Stable identity used to keep refresh comparisons scenario-specific."""
        return {
            "kind": "custom",
            "label": self.label,
            "source_sha256": self.source_sha256,
            "shares": dict(sorted(self.field.shares.items())),
            "count_basis": self.count_basis,
            "supplied_total": self.supplied_total,
            "declared_effective_n": self.declared_effective_n,
            "effective_count_total": self.effective_count_total,
        }

    def model_dump(self) -> dict[str, Any]:
        """Return JSON-safe scenario provenance for ``meta.field_scenario``."""
        return {
            **self.identity(),
            "source_path": self.source_path,
            "shares": dict(sorted(self.field.shares.items())),
            "supplied_counts": (
                dict(sorted(self.supplied_counts.items()))
                if self.supplied_counts is not None else None
            ),
            "effective_counts": (
                dict(sorted(self.field.counts.items()))
                if self.field.counts is not None else None
            ),
            "posterior_counts": self.posterior_counts,
            "unknown_opponents": list(self.unknown_opponents),
            "unknown_share": self.unknown_share,
            "warnings": list(self.warnings),
        }


def _known_archetypes(con: duckdb.DuckDBPyConnection) -> frozenset[str]:
    """Read only the cheap current label dimension for unknown-field accounting."""
    rows = con.execute(
        "SELECT DISTINCT archetype FROM decks WHERE archetype IS NOT NULL AND archetype <> ''"
    ).fetchall()
    return frozenset(str(row[0]) for row in rows)


def _input_counts(text: str) -> tuple[dict[str, int], bool, bool, int | None]:
    """Collect count provenance without reimplementing field parsing.

    The actual grammar and validation are delegated to ``_load_field``.  This
    narrow scan only distinguishes supplied terminal counts from share-only
    rows, and records the declared effective-N directive for provenance.
    """
    counts: dict[str, int] = {}
    has_counts = False
    has_missing = False
    effective_n: int | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            match = _EFFECTIVE_N.match(line[1:].strip())
            if match is not None:
                try:
                    effective_n = int(match.group(1))
                except ValueError:
                    # _load_field raises the useful line-specific validation error.
                    pass
            continue
        parts = line.split(None, 1)
        if len(parts) < 2:
            has_missing = True
            continue
        remainder = parts[1]
        tail = remainder.rsplit(None, 1)
        if len(tail) == 2:
            try:
                count = int(tail[1])
            except ValueError:
                count = None
            if count is not None:
                has_counts = True
                counts[tail[0].strip()] = counts.get(tail[0].strip(), 0) + count
                continue
        has_missing = True
    return counts, has_counts, has_missing, effective_n


def load_field_scenario(
    con: duckdb.DuckDBPyConnection,
    path: Path,
    *,
    label: str | None = None,
    known_archetypes: frozenset[str] | None = None,
) -> FieldScenario:
    """Read and validate one private custom-field file without mutating the DB.

    Per-line counts are treated as supplied observations only when every field
    row has a count.  A coincident ``# effective_n`` header is ignored, matching
    the field parser's per-line-count precedence.  A header on a share-only
    field remains a concentration declaration, even when the legacy allocator's
    minimum-one rule makes its integer allocation sum to a different value.
    """
    source = Path(path)
    if not source.is_file():
        raise ValueError(f"custom field file does not exist: {source}")
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read custom field file {source}: {exc}") from exc
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    supplied, has_counts, has_missing, declared_effective_n = _input_counts(text)
    if has_counts and has_missing:
        raise ValueError(
            "custom field mixes counted and share-only rows; every row must carry a count "
            "for supplied-observation scenarios"
        )
    known = _known_archetypes(con) if known_archetypes is None else known_archetypes
    field = _load_field(
        con,
        field_text=text,
        known_archetypes=known,
        strict_counts=True,
    )
    # ``_load_field`` intentionally gives terminal per-line counts precedence
    # over the optional header.  Do not let the provenance adapter re-apply an
    # ignored header by rescaling those supplied observations.
    if has_counts:
        declared_effective_n = None
    if field.counts is not None and any(share <= 0.0 for share in field.shares.values()):
        raise ValueError(
            "custom field rows with counts require a positive share for every archetype"
        )
    if has_counts:
        count_basis = "supplied-observations"
        supplied_counts: dict[str, int] | None = dict(supplied)
        supplied_total = sum(supplied.values())
    elif declared_effective_n is not None:
        count_basis = "declared-effective-concentration"
        supplied_counts = None
        supplied_total = None
    else:
        count_basis = "share-only-fixed-weights"
        supplied_counts = None
        supplied_total = None
    unknown = tuple(sorted(field.no_data))
    unknown_share = sum(field.shares.get(name, 0.0) for name in unknown)
    warnings = tuple(field.warnings)
    if has_counts and field.counts is not None and sum(field.counts.values()) != supplied_total:
        # This should only be reachable with a future parser change; preserve a
        # truthful warning instead of silently relabeling the concentration.
        warnings += (
            "effective count allocation differs from supplied count total; supplied observations remain separate",
        )
    return FieldScenario(
        field=field,
        label=(label.strip() if label and label.strip() else source.stem),
        source_path=str(source.resolve()),
        source_sha256=digest,
        supplied_counts=supplied_counts,
        supplied_total=supplied_total,
        declared_effective_n=declared_effective_n,
        effective_count_total=(sum(field.counts.values()) if field.counts is not None else None),
        count_basis=count_basis,
        unknown_opponents=unknown,
        unknown_share=unknown_share,
        warnings=warnings,
    )


def scenario_projection_inputs(
    scenario: FieldScenario,
    *,
    global_presence: Mapping[str, float],
) -> dict[str, Any]:
    """Build explicit inputs for the shared projection without changing eligibility.

    ``shares``/``counts`` belong to the scenario.  ``candidate_presence`` is
    always the global current-corpus signal, so a deck can be recommended for a
    local room even when it is absent from that room's opponent list.
    """
    return {
        "shares": dict(scenario.field.shares),
        "counts": scenario.posterior_counts,
        "candidate_presence": dict(global_presence),
        "field_scenario": scenario.model_dump(),
    }


__all__ = ["FieldScenario", "load_field_scenario", "scenario_projection_inputs"]
