"""The Card model — a typed view over a Scryfall oracle-card object.

Carries only the fields legacy-engine keys on; `extra="ignore"` (from
LegacyEngineModel) drops the rest of Scryfall's large object. Legacy-specific
derivations (deck colors, staple roles, mana-base tags) are layered in the
`card_derivations` feature, not here.
"""

from __future__ import annotations

from legacy_engine.models.base import LegacyEngineModel


class Card(LegacyEngineModel):
    """A Magic card, resolved from Scryfall.

    ``colors`` is the card's cast-cost color (Scryfall ``colors``); ``produced_mana``
    is what it taps for (Scryfall ``produced_mana``) — the two inputs the archetype
    color computation intersects. ``legalities`` is kept for reference but is NOT the
    authoritative legality source (the version-stamped ban-list blacklist is).
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

    @property
    def is_land(self) -> bool:
        return "Land" in self.type_line

    @classmethod
    def from_scryfall(cls, raw: dict) -> "Card":
        """Build a Card from a raw Scryfall oracle-card dict (unmodeled keys dropped)."""
        return cls.model_validate(raw)
