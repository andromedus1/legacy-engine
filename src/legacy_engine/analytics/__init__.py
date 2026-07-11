"""Meta & performance analytics — meta-share, matchup matrix, trends."""

from legacy_engine.analytics.card_value import (
    CardValue,
    card_value_marginal,
    card_value_matchup,
    card_values_vs,
)
from legacy_engine.analytics.match_results import (
    ArchetypeRecord,
    CardMarginalRecord,
    CardMatchupRecord,
    CardWinRates,
    MatchCoverage,
    MatchOutcome,
    MatchResults,
    MatchupTally,
    compute_card_winrates,
    compute_match_results,
    effective_label,
    normalize_player,
    parse_match_result,
)
from legacy_engine.analytics.matchup import (
    AdaptiveMatrix,
    MatchupMatrix,
    beta_binomial_shrink,
    beta_binomial_shrink_to,
    build_adaptive_matrix,
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
from legacy_engine.analytics.affectedness import (
    AffectednessExplanation,
    explain_valid_since,
)
from legacy_engine.analytics.matchup import lookup_head_to_head
from legacy_engine.analytics.trends import (
    BiggestMover,
    RegimeWindow,
    TrendCell,
    TrendSeries,
    biggest_movers,
    compute_trends,
    regime_windows,
)

__all__ = [
    # card_value
    "CardValue",
    "card_value_marginal",
    "card_value_matchup",
    "card_values_vs",
    # match_results
    "ArchetypeRecord",
    "CardMarginalRecord",
    "CardMatchupRecord",
    "CardWinRates",
    "MatchCoverage",
    "MatchOutcome",
    "MatchResults",
    "MatchupTally",
    "compute_card_winrates",
    "compute_match_results",
    "effective_label",
    "normalize_player",
    "parse_match_result",
    # matchup matrix
    "AdaptiveMatrix",
    "MatchupMatrix",
    "beta_binomial_shrink",
    "beta_binomial_shrink_to",
    "build_adaptive_matrix",
    "build_cell",
    "build_matrix",
    "build_mirror_cell",
    "lookup_head_to_head",
    "wilson_or_jeffreys_ci",
    # metashare
    "MetaShareEntry",
    "MetaShareReport",
    "blend_shares",
    "compute_all",
    "compute_metashare",
    # trends
    "BiggestMover",
    "RegimeWindow",
    "TrendCell",
    "TrendSeries",
    "biggest_movers",
    "compute_trends",
    "regime_windows",
    # affectedness
    "AffectednessExplanation",
    "explain_valid_since",
]
