"""Legacy-specific card tags derived from Scryfall fields.

Pure functions over a Card. These are the analytically valuable Legacy signals the foundations brief
identified: free-spell detection, mana-base classification, and curated staple roles.
"""

from __future__ import annotations

import re

from legacy_engine.colors import WUBRG
from legacy_engine.models.card import Card

# Alternative-cost ("free") spell patterns (case-insensitive) — Force of Will, Daze, Misdirection,
# Force of Negation/Vigor, Gush, the MH "pitch elemental" cycle, etc.
_FREE_SPELL_PATTERNS = [
    r"without paying its mana cost",
    r"without paying (its|their) mana cost",
    r"rather than pay this spell's mana cost",
    r"you may pay \[?0\]? rather than pay",
    r"you may exile .* rather than pay",
    r"you may return .* to its owner's hand rather than pay",  # Daze
]
_FREE_SPELL_RE = re.compile("|".join(_FREE_SPELL_PATTERNS), re.IGNORECASE)

# Curated staple roles seeded from legacy-foundations.md's staples table.
_STAPLE_ROLES: dict[str, str] = {
    # dual lands
    "Underground Sea": "dual_land", "Volcanic Island": "dual_land", "Tropical Island": "dual_land",
    "Tundra": "dual_land", "Bayou": "dual_land", "Scrubland": "dual_land", "Badlands": "dual_land",
    "Plateau": "dual_land", "Savannah": "dual_land", "Taiga": "dual_land",
    # fetchlands
    "Polluted Delta": "fetchland", "Flooded Strand": "fetchland", "Misty Rainforest": "fetchland",
    "Scalding Tarn": "fetchland", "Verdant Catacombs": "fetchland", "Wooded Foothills": "fetchland",
    "Bloodstained Mire": "fetchland", "Marsh Flats": "fetchland", "Arid Mesa": "fetchland",
    "Windswept Heath": "fetchland",
    # land denial
    "Wasteland": "land_denial", "Rishadan Port": "land_denial",
    # fast mana
    "Ancient Tomb": "fast_mana", "City of Traitors": "fast_mana", "Chrome Mox": "fast_mana",
    "Lotus Petal": "fast_mana", "Lion's Eye Diamond": "fast_mana",
    # free interaction
    "Force of Will": "free_interaction", "Force of Negation": "free_interaction",
    "Daze": "free_interaction", "Force of Vigor": "free_interaction",
    "Pyroblast": "free_interaction", "Red Elemental Blast": "free_interaction",
    # cantrips
    "Brainstorm": "cantrip", "Ponder": "cantrip", "Preordain": "cantrip",
    # discard
    "Thoughtseize": "discard", "Duress": "discard", "Hymn to Tourach": "discard",
    # lock pieces
    "Chalice of the Void": "lock_piece", "Trinisphere": "lock_piece", "Blood Moon": "lock_piece",
}


def is_free_spell(card: Card) -> bool:
    """True if the card can be cast without paying its mana cost (alternative cost)."""
    return bool(_FREE_SPELL_RE.search(card.oracle_text or ""))


def mana_base_tags(card: Card) -> set[str]:
    """Classify a land into Legacy mana-base roles (empty set for nonlands)."""
    if not card.is_land:
        return set()
    text = (card.oracle_text or "").lower()
    tags: set[str] = set()
    produced = {m for m in card.produced_mana if m in WUBRG}

    if "search your library for a" in text and "land" in text:
        tags.add("fetchland")
    if len(produced) >= 2 and "enters the battlefield tapped" not in text:
        tags.add("dual")
    if re.search(r"add \{c\}\{c\}", text) or "add two mana" in text or "add {c}{c}{c}" in text:
        tags.add("fast_mana_land")
    if ("destroy target" in text and "land" in text) or ("tap target land" in text):
        tags.add("denial")
    return tags


def staple_role(name: str) -> str | None:
    """Return the curated staple role for a card name, or None if not a tracked staple."""
    return _STAPLE_ROLES.get(name)
