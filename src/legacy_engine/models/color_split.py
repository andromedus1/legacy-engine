"""Color-split registry models — color-defined sub-archetype labels.

A colour split carves ONE parent archetype label into mutually exclusive children keyed on the
colours the deck actually casts, not on named cards. The archetype rule DSL
(``matcher.evaluate_condition``) can only ask about card names, and MTGOFormatData's own
``IncludeColorInName`` flag names a deck after its full guild identity — too coarse in the other
direction, since a fixed core with a two-card splash fragments into a dozen guild labels. This
layer is the middle: the parent's core stays one archetype, and a curated colour predicate names
its real branches.

Loaded from ``src/legacy_engine/data/color_splits/legacy.json`` by ``archetype/color_splits.py``.
Curated (hand-authored, version-stamped), never generated — unlike ``DiscoveredSplitRecord``.
"""

from __future__ import annotations

from pydantic import Field

from legacy_engine.models.base import LegacyEngineModel

WUBRG = frozenset("WUBRG")


class ColorBucket(LegacyEngineModel):
    """One child label of a colour split.

    A bucket matches when the deck's observed colour set contains at least one colour in
    ``requires_any`` (when non-empty) AND contains none of ``forbids_all``. An empty
    ``requires_any`` means "no positive requirement" — the bucket is defined purely by what it
    excludes, which is how the complement branch of a two-way split is written.
    """

    name: str
    requires_any: list[str] = Field(default_factory=list)
    forbids_all: list[str] = Field(default_factory=list)


class ColorSplit(LegacyEngineModel):
    """A colour split of one parent archetype into mutually exclusive child labels.

    ``parent`` is the exact **display** label as written to ``decks.archetype`` (colour prefix
    included where the parent label carries one) — the labeler resolves splits against the
    classifier's final label, not the internal rule name.

    ``min_copies`` is the copy count a colour must reach in the counted zone before it registers,
    so a split can require a real commitment rather than any single card. The default of 1 is the
    plain reading of "the deck plays cards of that colour".

    Only mainboard nonland cards are counted: a sideboard splash is a configuration choice inside
    one deck, not a different deck, and lands are excluded because a fetch-and-dual manabase
    produces colours the deck never casts.
    """

    parent: str
    buckets: list[ColorBucket] = Field(default_factory=list)
    min_copies: int = 1
    note: str = ""


class ColorSplitRegistry(LegacyEngineModel):
    """Immutable registry of colour splits for a format version."""

    version: str
    splits: list[ColorSplit] = Field(default_factory=list)

    def for_parent(self, parent: str) -> ColorSplit | None:
        """Return the split whose ``parent`` exactly matches ``parent``, else ``None``."""
        return next((s for s in self.splits if s.parent == parent), None)
