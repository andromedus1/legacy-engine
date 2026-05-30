"""Deck-color computation + guild naming.

Implements MTGOArchetypeParser's GetColors: a deck's color is the INTERSECTION of the colors its
lands produce and the colors its nonland cards cast as. This is NOT Scryfall `color_identity` (that
would fold in off-color rules-text symbols and mis-name decks). Used by the archetype classifier's
color-prefix step (e.g. "Dimir Tempo").
"""

from __future__ import annotations

from collections.abc import Iterable

from legacy_engine.models.card import Card

WUBRG = ["W", "U", "B", "R", "G"]
_WUBRG_SET = set(WUBRG)

# Guild / shard / wedge / 4c / 5c names, keyed by the canonical WUBRG-ordered color string.
_COLOR_NAMES: dict[str, str] = {
    "": "Colorless",
    "W": "White", "U": "Blue", "B": "Black", "R": "Red", "G": "Green",
    "WU": "Azorius", "UB": "Dimir", "BR": "Rakdos", "RG": "Gruul", "WG": "Selesnya",
    "WB": "Orzhov", "UR": "Izzet", "BG": "Golgari", "WR": "Boros", "UG": "Simic",
    "WUB": "Esper", "UBR": "Grixis", "BRG": "Jund", "WRG": "Naya", "WUG": "Bant",
    "WBG": "Abzan", "WUR": "Jeskai", "UBG": "Sultai", "WBR": "Mardu", "URG": "Temur",
    "UBRG": "4c (no White)", "WBRG": "4c (no Blue)", "WURG": "4c (no Black)",
    "WUBG": "4c (no Red)", "WUBR": "4c (no Green)", "WUBRG": "5c",
}


def compute_deck_colors(cards: Iterable[Card]) -> str:
    """Return the deck's canonical WUBRG color string.

    A color is included iff it appears in at least one land's ``produced_mana`` AND at least one
    nonland card's ``colors``.
    """
    land_colors: set[str] = set()
    nonland_colors: set[str] = set()
    for card in cards:
        if card.is_land:
            land_colors |= {m for m in card.produced_mana if m in _WUBRG_SET}
        else:
            nonland_colors |= {m for m in card.colors if m in _WUBRG_SET}
    deck = land_colors & nonland_colors
    return "".join(w for w in WUBRG if w in deck)


def guild_name(colors: str) -> str:
    """Map a canonical WUBRG color string to its guild/shard/wedge label."""
    return _COLOR_NAMES.get(colors, colors or "Colorless")
