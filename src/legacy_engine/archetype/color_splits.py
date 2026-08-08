"""Colour-split registry loader + resolver — colour-defined sub-archetype labels.

Loads a curated colour-split registry from a project-owned JSON file and resolves the child label
for a deck whose parent archetype the registry splits. Pure and hand-testable: the resolver takes
an already-counted colour multiset, never a DB handle.

Fails fast on an unknown colour letter, a duplicated parent, a bucket that can never be reached,
and (at resolve time) a deck that matches more than one bucket — a split whose branches overlap
would silently double-count field share, which is exactly the kind of quiet corruption the
matcher's ``Conflict(...)`` label exists to refuse.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path

from legacy_engine.archetype.rules import _loads_lenient
from legacy_engine.models.card import Card
from legacy_engine.models.color_split import WUBRG, ColorSplit, ColorSplitRegistry


class AmbiguousColorSplitError(ValueError):
    """Raised when a deck matches more than one bucket of the same colour split."""


def load_color_split_registry(path: Path | str) -> ColorSplitRegistry:
    """Load and validate a colour-split registry from a JSON file.

    Uses the same lenient JSON parsing as the archetype rules (tolerates trailing commas).

    Raises ``ValueError`` on an unknown colour letter, a duplicate parent, a bucket with no
    predicate at all, or a bucket whose ``requires_any`` and ``forbids_all`` overlap (it could
    never match). Raises ``FileNotFoundError`` / ``ValueError`` on missing or malformed input.
    """
    path = Path(path)
    registry = ColorSplitRegistry.model_validate(_loads_lenient(path.read_text()))
    _validate_registry(registry, path)
    return registry


def _validate_registry(registry: ColorSplitRegistry, source: Path) -> None:
    seen: set[str] = set()
    for split in registry.splits:
        if split.parent in seen:
            raise ValueError(f"duplicate colour split for parent {split.parent!r} in {source}")
        seen.add(split.parent)
        if split.min_copies < 1:
            raise ValueError(
                f"colour split {split.parent!r} has min_copies={split.min_copies} in {source} "
                "— must be >= 1"
            )
        if len(split.buckets) < 2:
            raise ValueError(
                f"colour split {split.parent!r} has {len(split.buckets)} bucket(s) in {source} "
                "— a split needs at least 2"
            )
        names: set[str] = set()
        for bucket in split.buckets:
            if bucket.name in names:
                raise ValueError(
                    f"duplicate bucket name {bucket.name!r} under {split.parent!r} in {source}"
                )
            names.add(bucket.name)
            colors = [*bucket.requires_any, *bucket.forbids_all]
            bad = sorted({c for c in colors if c not in WUBRG})
            if bad:
                raise ValueError(
                    f"unknown colour(s) {bad} in bucket {split.parent!r}/{bucket.name!r} "
                    f"from {source} — allowed: {sorted(WUBRG)}"
                )
            if not colors:
                raise ValueError(
                    f"bucket {split.parent!r}/{bucket.name!r} in {source} declares no colour "
                    "predicate — it would match every deck"
                )
            overlap = sorted(set(bucket.requires_any) & set(bucket.forbids_all))
            if overlap:
                raise ValueError(
                    f"bucket {split.parent!r}/{bucket.name!r} in {source} both requires and "
                    f"forbids {overlap} — it can never match"
                )


def count_deck_colors(
    mainboard: Mapping[str, int],
    resolve_card,
) -> dict[str, int]:
    """Count mainboard **nonland** copies per colour — the input the resolver keys on.

    A card contributes its full copy count to every colour in its casting cost, so a 4-of gold
    card counts 4 toward each of its colours. Cards that don't resolve (missing from the card
    index) are skipped rather than guessed at.
    """
    counts: dict[str, int] = {}
    for name, copies in mainboard.items():
        card: Card | None = resolve_card(name)
        if card is None or card.is_land:
            continue
        for color in card.colors:
            if color in WUBRG:
                counts[color] = counts.get(color, 0) + copies
    return counts


def _matches(bucket, present: Iterable[str]) -> bool:
    present = set(present)
    if bucket.requires_any and not (set(bucket.requires_any) & present):
        return False
    return not (set(bucket.forbids_all) & present)


def resolve_color_split(
    archetype: str,
    color_counts: Mapping[str, int],
    registry: ColorSplitRegistry,
) -> str | None:
    """Return the child label for ``archetype``, or ``None`` when nothing applies.

    ``None`` covers both "this archetype is not split" and "no bucket matched" — the caller keeps
    the parent label in either case, which is the honest degrade: an unmatched deck stays visibly
    in the parent rather than being forced into a branch it doesn't belong to.

    Raises ``AmbiguousColorSplitError`` when two buckets match; that is an authoring error in the
    registry, not a property of the deck.
    """
    split: ColorSplit | None = registry.for_parent(archetype)
    if split is None:
        return None

    present = {c for c, n in color_counts.items() if n >= split.min_copies}
    matching = [b for b in split.buckets if _matches(b, present)]

    if len(matching) == 1:
        return matching[0].name
    if len(matching) > 1:
        names = ", ".join(f"'{b.name}'" for b in matching)
        raise AmbiguousColorSplitError(
            f"Multiple colour buckets matched for {archetype!r} (colours present: "
            f"{sorted(present)}): {names}. Buckets under a parent must be mutually exclusive."
        )
    return None
