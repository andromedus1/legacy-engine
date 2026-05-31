"""BanListSnapshot — Legacy legality as a dated blacklist.

Legacy legality is a blacklist (everything legal except the banned list), and the list changes
~quarterly, so legality is always evaluated *as of* a date — a 2024 deck that legally ran Psychic
Frog must validate against the legality in effect then. This is the authoritative legality source,
NOT Scryfall's `legacy` flag (which lags B&R announcements).
"""

from __future__ import annotations

from datetime import date

from legacy_engine.models.base import LegacyEngineModel

# Ante + offensive cards not derivable from type_line and not already in BASELINE_BANS.
# These are banned in Legacy by category regardless of the dated B&R snapshot.
# Name-enumerated so validate_deck can check them without importing Scryfall or the store
# (Ports & Adapters — domain must stay infrastructure-free).
CATEGORY_BANNED_NAMES: frozenset[str] = frozenset({
    # Ante cards
    "Amulet of Quoz",
    "Bronze Tablet",
    "Contract from Below",
    "Darkpact",
    "Demonic Attorney",
    "Jeweled Bird",
    "Rebirth",
    "Tempest Efreet",
    "Timmerian Fiends",
    # Offensive cards
    "Invoke Prejudice",
    "Cleanse",
    "Stone-Throwing Devils",
    "Pradesh Gypsies",
    "Jihad",
    "Imprison",
    "Crusade",
})

# Cards whose copy limit exceeds 4 (explicit text overrides). Basics are unlimited separately.
COPY_LIMIT_OVERRIDES: dict[str, int] = {
    "Seven Dwarves": 7,
}
UNLIMITED_COPIES: frozenset[str] = frozenset(
    {"Relentless Rats", "Shadowborn Apostle", "Rat Colony", "Persistent Petitioners", "Dragon's Approach"}
)
BASIC_LAND_NAMES: frozenset[str] = frozenset(
    {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes", "Snow-Covered Plains",
     "Snow-Covered Island", "Snow-Covered Swamp", "Snow-Covered Mountain", "Snow-Covered Forest"}
)


class BanListSnapshot(LegacyEngineModel):
    """The set of cards banned in Legacy as of a given date, plus category bans."""

    as_of: date
    banned: frozenset[str]
    categories: tuple[str, ...] = ()  # whole-class bans: conspiracy, ante, stickers/attractions, offensive

    def is_banned(self, name: str) -> bool:
        return name in self.banned

    def is_legal(self, name: str) -> bool:
        """A card is legal iff it is not on the banned list (category predicates handled by the caller)."""
        return name not in self.banned
