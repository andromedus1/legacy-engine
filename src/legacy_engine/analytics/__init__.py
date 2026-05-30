"""Meta & performance analytics — meta-share, matchup matrix, trends, charts."""

from legacy_engine.analytics.match_results import (
    ArchetypeRecord,
    MatchCoverage,
    MatchOutcome,
    MatchResults,
    MatchupTally,
    compute_match_results,
    normalize_player,
    parse_match_result,
)
from legacy_engine.analytics.matchup import (
    MatchupMatrix,
    beta_binomial_shrink,
    build_cell,
    build_matrix,
    build_mirror_cell,
    wilson_or_jeffreys_ci,
)
from legacy_engine.analytics.metashare import (
    MetaShareEntry,
    MetaShareReport,
    blend_shares,
    compute_all,
    compute_metashare,
)
from legacy_engine.analytics.trends import (
    RegimeWindow,
    TrendCell,
    TrendSeries,
    compute_trends,
    regime_windows,
)

__all__ = [
    "ArchetypeRecord",
    "MatchCoverage",
    "MatchOutcome",
    "MatchResults",
    "MatchupTally",
    "compute_match_results",
    "normalize_player",
    "parse_match_result",
    # matchup matrix
    "MatchupMatrix",
    "beta_binomial_shrink",
    "build_cell",
    "build_matrix",
    "build_mirror_cell",
    "wilson_or_jeffreys_ci",
    # metashare
    "MetaShareEntry",
    "MetaShareReport",
    "blend_shares",
    "compute_all",
    "compute_metashare",
    # trends
    "RegimeWindow",
    "TrendCell",
    "TrendSeries",
    "compute_trends",
    "regime_windows",
]
