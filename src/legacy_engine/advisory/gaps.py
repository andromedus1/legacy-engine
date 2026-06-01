"""Archetype-gap finder for deck-generation mode 3 (gap discovery).

Surfaces **under-explored archetypes**: shells with high positioning ``S`` (well-positioned
versus the field) but low meta-share — the strategies the field is sleeping on. This is the
mechanical half of mode 3 (brief §4): it composes two already-shipped surfaces —
``advisory.positioning.rank_decks`` (shared-field Monte-Carlo ``S``, with the risk-adjusted
lower-quantile, ``data_coverage``, and ``low_coverage`` flagging) and
``analytics.metashare`` (via ``advisory.field.build_global_field``) — and ranks by a gap score.

Honesty: the confidence gate is delegated to ``rank_decks``'s existing ``min_coverage`` /
``low_coverage`` mechanism — archetypes whose ``S`` rests on thin matchup data are EXCLUDED from
the ranked gaps and reported in ``excluded_low_coverage`` (never silently dropped).

The scoring is split objective-search style: the DB/MC work lives in ``compute_archetype_gaps``;
the pure ranking lives in ``_assemble_gaps`` (testable with hand-built inputs, no DB, no MC).
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from legacy_engine.advisory.field import FieldDistribution, build_global_field
from legacy_engine.advisory.positioning import DeckRanking, rank_decks
from legacy_engine.analytics.matchup import build_matrix
from legacy_engine.confidence import ConfidenceLevel, tier_for_sample

_DEFAULT_SHARE_WEIGHT: float = 1.0
_DEFAULT_MIN_COVERAGE: float = 0.5
_DEFAULT_RISK_QUANTILE: float = 0.25


@dataclass(frozen=True)
class ArchetypeGap:
    """One under-exploration candidate: a well-positioned, under-played archetype."""

    archetype: str
    s_mean: float
    s_quantile: float       # risk-adjusted lower quantile of S (from rank_decks)
    share: float            # meta-share within the global field (0..1)
    gap_score: float        # s_mean − share_weight · share
    data_coverage: float    # fraction of field share-mass with a measured cell
    tier: ConfidenceLevel   # tier_for_sample(deck count) — display/transparency


@dataclass(frozen=True)
class GapReport:
    """Ranked under-explored archetypes plus the honestly-reported thin-data exclusions."""

    gaps: list[ArchetypeGap]          # sorted gap_score DESC (tie: share ASC, then name ASC)
    excluded_low_coverage: list[str]  # dropped for thin matchup data — reported, not silent
    field_source: str
    risk_quantile: float
    share_weight: float
    min_coverage: float


def _assemble_gaps(
    field: FieldDistribution,
    ranking: DeckRanking,
    *,
    share_weight: float,
    min_coverage: float,
) -> GapReport:
    """Pure gap ranking from an already-computed field + DeckRanking (no DB, no MC).

    ``gap_score = s_mean − share_weight · share``. Archetypes flagged ``low_coverage`` by
    ``rank_decks`` (``data_coverage < min_coverage``) are excluded and reported separately.
    Sort is ``gap_score`` DESC, tie-break ``share`` ASC (more under-explored first) then name ASC.
    """
    gaps: list[ArchetypeGap] = []
    excluded: list[str] = []

    for arch in ranking.decks:
        if arch in ranking.low_coverage:
            excluded.append(arch)
            continue
        share = field.shares.get(arch, 0.0)
        count = field.counts.get(arch, 0) if field.counts else 0
        gaps.append(
            ArchetypeGap(
                archetype=arch,
                s_mean=ranking.s_mean[arch],
                s_quantile=ranking.s_quantile[arch],
                share=share,
                gap_score=ranking.s_mean[arch] - share_weight * share,
                data_coverage=ranking.data_coverage[arch],
                tier=tier_for_sample(int(count)),
            )
        )

    gaps.sort(key=lambda g: (-g.gap_score, g.share, g.archetype))
    excluded.sort()
    return GapReport(
        gaps=gaps,
        excluded_low_coverage=excluded,
        field_source=field.field_source,
        risk_quantile=ranking.quantile_level,
        share_weight=share_weight,
        min_coverage=min_coverage,
    )


def compute_archetype_gaps(
    con: duckdb.DuckDBPyConnection,
    *,
    definition: str = "raw",
    provenance: str | None = None,
    share_weight: float = _DEFAULT_SHARE_WEIGHT,
    min_coverage: float = _DEFAULT_MIN_COVERAGE,
    risk_quantile: float = _DEFAULT_RISK_QUANTILE,
    min_share: float = 0.0,
    seed: int | None = None,
) -> GapReport:
    """Rank archetypes by under-exploration: high positioning ``S``, low meta-share.

    Builds the global field + matchup matrix, scores every field archetype against the shared
    field via ``rank_decks`` (which carries the ``min_coverage`` honesty gate), then assembles the
    gap ranking. Un-windowed — consistent with ``build_matrix`` / ``rank_decks`` / the field, none
    of which are windowed. Returns an empty ``GapReport`` for an empty field.
    """
    field = build_global_field(
        con, definition=definition, provenance=provenance, min_share=min_share,
    )
    candidates = list(field.shares)
    if not candidates:
        return GapReport(
            gaps=[],
            excluded_low_coverage=[],
            field_source=field.field_source,
            risk_quantile=risk_quantile,
            share_weight=share_weight,
            min_coverage=min_coverage,
        )

    matrix = build_matrix(con, provenance=provenance)
    ranking = rank_decks(
        matrix, field, candidates,
        risk_quantile=risk_quantile,
        min_coverage=min_coverage,
        seed=seed,
    )
    return _assemble_gaps(
        field, ranking, share_weight=share_weight, min_coverage=min_coverage,
    )
