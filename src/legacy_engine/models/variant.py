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

    ``parent`` must be the exact **display** archetype label as stored in ``decks.archetype``
    (e.g. ``"Dimir Tempo"``, color prefix included where the label carries one) — the labeler
    resolves variants against ``result.archetype``, not the internal rule ``base_archetype``.  ``conditions`` are evaluated via ``matcher.evaluate_condition``
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
    # Exact cluster membership from discovery — (tournament_id, deck_idx) per member deck.
    # apply_split labels by membership when present (signature-card rules cannot reproduce a
    # 3+-camp partition: real camps share staples, so single-card presence rules overlap and
    # trip resolve_variant's ambiguity fail-fast). None on hand-edited/legacy staging files,
    # which fall back to the transient-rules path.
    member_keys: list[tuple[str, int]] | None = None
    # Gate C temporal diagnostics (additive — epic-stable-era-windows-discovery-gate Unit 2).
    # Both None-safe: absent on staged records written before this epic, and on any camp whose
    # member decks carry no tournament date. ``extra="ignore"`` + these defaults mean an OLD
    # staged JSON record (no such keys) loads unchanged.
    median_date: str | None = None
    pct_current: float | None = None
    # Frozen flex-band centroid — the mean L2-normalized raw-count vector over this camp's member
    # decks, in the exact representation ``nearest_camp`` projects candidate decks into
    # (analytics/discovery.py::project_flex_vector / camp_centroid). None on records staged
    # before this field existed: incremental assignment declines honestly for that parent until
    # its next `discover run` repopulates it, rather than comparing against a fabricated position.
    centroid: list[float] | None = None


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
    # Gate C temporal-mixing flag, additive (see DiscoveredCamp above) — surfaced by
    # `discover run`/`discover list` as an honest-degrade warning, never gating promotion.
    temporal_mixing: bool = False
    temporal_note: str | None = None
    # The frozen flex-band vocabulary this split clustered on (FeatureMatrix.cards at discovery
    # time) — the fixed column space every ``DiscoveredCamp.centroid`` lives in and nearest-camp
    # assignment projects new decks into. Empty on records staged before this field existed
    # (honest-degrade, see DiscoveredCamp.centroid).
    flex_cards: list[str] = Field(default_factory=list)


class DiscoveredRegistry(LegacyEngineModel):
    """The staging registry persisted at ``data/variants/discovered.json`` (derived side)."""

    version: str
    splits: list[DiscoveredSplitRecord] = Field(default_factory=list)
