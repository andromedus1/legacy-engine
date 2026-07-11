"""Variant registry models — sub-archetype variant tagging.

``VariantRule`` defines one sub-archetype variant under a parent archetype via a list of
``Condition`` objects (the same vocabulary as the matcher's archetype rules).  ``VariantRegistry``
holds all rules for a format version with an optional default-name complement per parent.

These are loaded from ``data/variants/legacy.json`` by ``archetype/variants.py``.

The ``Discovered*`` models are the *staging* side of the discovery engine
(``analytics/discovery.py``): validated candidate splits land in
``data/variants/discovered.json`` (a derived file, never hand-curated) with
``status: "candidate"`` until ``discover promote`` converts a camp into curated
``VariantRule`` entries.  Loader/staging/promotion live in ``archetype/discovered.py``.
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


class DiscoveredCamp(LegacyEngineModel):
    """One camp of a staged candidate split.

    ``signature_cards`` are the camp's top over-represented flex-band cards (positive delta vs
    the rest of the parent pool, descending) — the first entry is the card promotion uses to
    build the ``InMainboard`` condition.  ``tier`` is the sample-tier honesty label
    (``ConfidenceLevel`` value) the camp carries everywhere it is surfaced.
    """

    name: str
    signature_cards: list[str] = Field(default_factory=list)
    n: int
    tier: str


class DiscoveredSplitRecord(LegacyEngineModel):
    """One staged candidate split for a parent archetype (upserted by ``parent``).

    ``generated_from`` + ``params`` are provenance: which run produced this record and with
    what knobs, so a candidate is auditable and reproducible.  ``status`` is ``"candidate"``
    until promotion flips it to ``"promoted"`` — the staging registry never silently mutates
    the curated taxonomy.
    """

    parent: str
    generated_from: str
    params: dict = Field(default_factory=dict)
    camps: list[DiscoveredCamp] = Field(default_factory=list)
    stability: float
    status: str = "candidate"


class DiscoveredRegistry(LegacyEngineModel):
    """The staging registry persisted at ``data/variants/discovered.json`` (derived side)."""

    version: str
    splits: list[DiscoveredSplitRecord] = Field(default_factory=list)
