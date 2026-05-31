"""Meta & performance analytics — meta-share, matchup matrix, trends, charts."""

from legacy_engine.analytics.card_value import (
    CardValue,
    card_value_marginal,
    card_value_matchup,
    card_values_vs,
)
from legacy_engine.analytics.charts import (
    BarModel,
    HeatmapModel,
    TierModel,
    TrendModel,
    render_matchup_heatmap,
    render_metashare,
    render_tier_list,
    render_trends,
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
    normalize_player,
    parse_match_result,
)
from legacy_engine.analytics.matchup import (
    MatchupMatrix,
    beta_binomial_shrink,
    beta_binomial_shrink_to,
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
    # card_value
    "CardValue",
    "card_value_marginal",
    "card_value_matchup",
    "card_values_vs",
    # charts
    "BarModel",
    "HeatmapModel",
    "TierModel",
    "TrendModel",
    "render_matchup_heatmap",
    "render_metashare",
    "render_tier_list",
    "render_trends",
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
    "normalize_player",
    "parse_match_result",
    # matchup matrix
    "MatchupMatrix",
    "beta_binomial_shrink",
    "beta_binomial_shrink_to",
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
