"""Variant registry models — sub-archetype variant tagging.

``VariantRule`` defines one sub-archetype variant under a parent archetype via a list of
``Condition`` objects (the same vocabulary as the matcher's archetype rules).  ``VariantRegistry``
holds all rules for a format version with an optional default-name complement per parent.

These are loaded from ``data/variants/legacy.json`` by ``archetype/variants.py``.
"""

from __future__ import annotations

from pydantic import Field

from legacy_engine.archetype.rules import Condition
from legacy_engine.models.base import LegacyEngineModel


class VariantRule(LegacyEngineModel):
    """One sub-archetype variant definition.

    ``parent`` must be an exact ``base_archetype`` string (no color prefix — the resolver matches
    against ``base_archetype``).  ``conditions`` are evaluated via ``matcher.evaluate_condition``
    against the deck's mainboard/sideboard name sets — same vocabulary as archetype conditions.
    """

    parent: str
    name: str
    conditions: list[Condition] = Field(default_factory=list)
    include_in_label: bool = True  # future: variants that annotate but don't display


class VariantRegistry(LegacyEngineModel):
    """Immutable registry of variant rules for a format version."""

    version: str
    variants: list[VariantRule] = Field(default_factory=list)
    # parent → default variant name for decks that match the parent but no positive condition.
    # e.g. {"Smallpox": "non-Loam"} — decks with no Loam signature → "non-Loam" tag.
    defaults: dict[str, str] = Field(default_factory=dict)

    def for_parent(self, parent: str) -> list[VariantRule]:
        """Return all variant rules whose ``parent`` exactly matches ``parent``."""
        return [v for v in self.variants if v.parent == parent]
