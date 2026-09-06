"""The Card model — a typed view over a Scryfall oracle-card object.

Carries only the fields legacy-engine keys on; `extra="ignore"` (from
LegacyEngineModel) drops the rest of Scryfall's large object. Legacy-specific
derivations (deck colors, staple roles, mana-base tags) are layered in the
`card_derivations` feature, not here.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from legacy_engine.models.base import LegacyEngineModel


class Card(LegacyEngineModel):
    """A Magic card, resolved from Scryfall.

    ``colors`` is the card's cast-cost color (Scryfall ``colors``); ``produced_mana``
    is what it taps for (Scryfall ``produced_mana``) — the two inputs the archetype
    color computation intersects. ``legalities`` is kept for reference but is NOT the
    authoritative legality source (the version-stamped ban-list blacklist is).

    ``power`` and ``toughness`` are the Scryfall string fields (e.g. "2", "*", "1+*");
    they auto-populate via ``model_validate`` when the Scryfall bulk data includes them.
    Use ``power_int()`` to get a numeric value where meaningful.
    """

    name: str
    mana_cost: str | None = None
    cmc: float = 0.0
    type_line: str = ""
    colors: list[str] = []
    produced_mana: list[str] = []
    oracle_text: str = ""
    layout: str = "normal"
    card_faces: list[dict] = []
    legalities: dict[str, str] = {}
    power: str | None = None
    toughness: str | None = None

    @property
    def is_land(self) -> bool:
        return "Land" in self.type_line

    def power_int(self) -> int | None:
        """Return power as an integer, or None for non-numeric values ("*", "1+*", None).

        Scryfall power is a string that may contain "*", "1+*", or similar. Only
        plain numeric strings (e.g. "2", "10") return an integer; everything else
        returns None so callers don't need to special-case variable-power cards.
        """
        if self.power is None:
            return None
        try:
            return int(self.power)
        except ValueError:
            return None

    @classmethod
    def from_scryfall(cls, raw: dict) -> "Card":
        """Build a Card from a raw Scryfall oracle-card dict (unmodeled keys dropped)."""
        return cls.model_validate(raw)


class CardNameStatus(StrEnum):
    CANONICAL = "canonical"
    LOCALIZED = "localized"
    NEW_CARD = "new_card"
    AMBIGUOUS = "ambiguous"
    SUSPECTED_TRUNCATED = "suspected_truncated"
    UNRESOLVED = "unresolved"


class CardNameResolution(LegacyEngineModel):
    observed_name: str
    normalized_name: str
    status: CardNameStatus
    canonical_name: str | None = None
    language: str | None = None
    scryfall_id: str | None = None
    source: str
    evidence: str | None = None
    source_updated_at: str | None = None
    resolved_at: datetime
    reason: str


class PrintedCardAlias(LegacyEngineModel):
    printed_name: str
    normalized_alias: str
    canonical_name: str
    language: str
    scryfall_id: str


class CardAliasManifest(LegacyEngineModel):
    source_updated_at: str
    built_at: datetime
    release_codes: tuple[str, ...]
    alias_count: int
    ambiguous_key_count: int


class CardCoverageGap(LegacyEngineModel):
    observed_name: str
    row_count: int
    deck_count: int
    first_event_date: str
    providers: tuple[str, ...]
    event_uris: tuple[str, ...]


class CardCoverageCutoff(LegacyEngineModel):
    cutoff: str | None
    gaps: tuple[CardCoverageGap, ...]
