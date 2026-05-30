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
from legacy_engine.advisory.whattoplay import (
    BestDeckCall,
    ProactivityProfile,
    best_deck_vs_best_call,
    covered_share,
    field_vulnerability_tags,
    hate_equity,
    plan_clash,
    proactivity_score,
    vulnerability_tags,
    vulnerability_tags_for_deck,
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
    # whattoplay
    "BestDeckCall",
    "ProactivityProfile",
    "best_deck_vs_best_call",
    "covered_share",
    "field_vulnerability_tags",
    "hate_equity",
    "plan_clash",
    "proactivity_score",
    "vulnerability_tags",
    "vulnerability_tags_for_deck",
]
