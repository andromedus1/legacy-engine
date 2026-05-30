"""Meta attack / advisory — positioning score, sideboard recommender, what-to-play."""

from legacy_engine.advisory.field import (
    FieldDistribution,
    FieldSource,
    build_custom_field,
    build_global_field,
)
from legacy_engine.advisory.positioning import (
    DeckRanking,
    PositioningResult,
    delta_var_S,
    positioning_score,
    rank_decks,
)

__all__ = [
    "FieldDistribution",
    "FieldSource",
    "build_custom_field",
    "build_global_field",
    "DeckRanking",
    "PositioningResult",
    "delta_var_S",
    "positioning_score",
    "rank_decks",
]
