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

__all__ = [
    "ArchetypeRecord",
    "MatchCoverage",
    "MatchOutcome",
    "MatchResults",
    "MatchupTally",
    "compute_match_results",
    "normalize_player",
    "parse_match_result",
]
