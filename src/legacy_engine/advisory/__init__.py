"""Meta attack / advisory — positioning score, sideboard recommender, what-to-play, report."""

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
from legacy_engine.advisory.sideboard import (
    HOSER_CATALOG,
    HoserCard,
    ConsideringCard,
    PickTrace,
    SideboardPackage,
    recommend_sideboard,
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
from legacy_engine.advisory.report import (
    FieldReadReport,
    build_field_read_report,
    render_field_read,
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
    # sideboard
    "HOSER_CATALOG",
    "HoserCard",
    "ConsideringCard",
    "PickTrace",
    "SideboardPackage",
    "recommend_sideboard",
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
    # report
    "FieldReadReport",
    "build_field_read_report",
    "render_field_read",
]
