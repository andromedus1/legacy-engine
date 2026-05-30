"""The archetype matcher — a Python port of Badaro's ArchetypeAnalyzer.Detect.

Given a decklist + the loaded ruleset + the deck's colors (from foundations' compute_deck_colors),
produce an archetype label. Faithful to the C# engine:
- AND-test every archetype's conditions; collect ALL matches.
- A matched archetype's variants are nested: each passing variant is its own match; if none pass, the
  bare parent is the match. So a parent with N passing variants yields N matches.
- >1 match across the ruleset → a literal ``Conflict(A,B,...)`` label (no default tie-break).
- 0 matches → most-card-overlap fallback pile (>10% similarity floor), else ``Unknown``.
Conflict/Unknown are returned RAW — analytics owns any bucketing (locked design decision).
"""

from __future__ import annotations

from legacy_engine.archetype.rules import (
    KNOWN_CONDITION_TYPES,
    Condition,
    RuleSet,
    UnknownConditionTypeError,
)
from legacy_engine.colors import guild_name
from legacy_engine.models.base import LegacyEngineModel

MIN_FALLBACK_SIMILARITY = 0.10


class ArchetypeResult(LegacyEngineModel):
    archetype: str  # final (possibly color-prefixed) label
    base_archetype: str = ""  # archetype/variant name without color prefix ("" for conflict/unknown)
    color: str = ""  # the deck's WUBRG color string
    kind: str = "archetype"  # archetype | variant | conflict | fallback | unknown


def _present(cards: list[str], names: set[str]) -> int:
    """Number of the listed cards present in the given name set."""
    return sum(1 for c in cards if c in names)


def evaluate_condition(cond: Condition, main: set[str], side: set[str]) -> bool:
    """Evaluate one condition against the deck's mainboard/sideboard name sets."""
    t, cards = cond.type, cond.cards
    both = main | side
    if t == "InMainboard" or t == "OneOrMoreInMainboard":
        return _present(cards, main) >= 1
    if t == "InSideboard" or t == "OneOrMoreInSideboard":
        return _present(cards, side) >= 1
    if t == "InMainOrSideboard" or t == "OneOrMoreInMainOrSideboard":
        return _present(cards, both) >= 1
    if t == "TwoOrMoreInMainboard":
        return _present(cards, main) >= 2
    if t == "TwoOrMoreInSideboard":
        return _present(cards, side) >= 2
    if t == "TwoOrMoreInMainOrSideboard":
        return _present(cards, both) >= 2
    if t == "DoesNotContain":
        return _present(cards, both) == 0
    if t == "DoesNotContainMainboard":
        return _present(cards, main) == 0
    if t == "DoesNotContainSideboard":
        return _present(cards, side) == 0
    raise UnknownConditionTypeError(t)  # defensive; loader already validated


def _all_pass(conditions, main: set[str], side: set[str]) -> bool:
    return all(evaluate_condition(c, main, side) for c in conditions)


def _label(base: str, include_color: bool, colors: str) -> str:
    if include_color and colors:
        return f"{guild_name(colors)} {base}"
    return base


def classify(
    mainboard: dict[str, int],
    sideboard: dict[str, int],
    ruleset: RuleSet,
    deck_colors: str,
) -> ArchetypeResult:
    """Classify a decklist into an archetype label. ``mainboard``/``sideboard`` are name->count maps."""
    main, side = set(mainboard), set(sideboard)
    matches: list[tuple[str, str, bool]] = []  # (display_base, base_name, include_color)

    for arch in ruleset.archetypes:
        if not _all_pass(arch.conditions, main, side):
            continue
        passing_variants = [v for v in arch.variants if _all_pass(v.conditions, main, side)]
        if passing_variants:
            for v in passing_variants:
                matches.append((v.name, v.name, v.include_color_in_name or arch.include_color_in_name))
        else:
            matches.append((arch.name, arch.name, arch.include_color_in_name))

    if len(matches) == 1:
        base, base_name, inc = matches[0]
        kind = "variant" if base_name != _parent_of(ruleset, base_name) else "archetype"
        return ArchetypeResult(
            archetype=_label(base, inc, deck_colors), base_archetype=base_name, color=deck_colors, kind=kind
        )
    if len(matches) > 1:
        names = ",".join(sorted({m[0] for m in matches}))
        return ArchetypeResult(archetype=f"Conflict({names})", color=deck_colors, kind="conflict")

    return _fallback(mainboard, ruleset, deck_colors)


def _parent_of(ruleset: RuleSet, name: str) -> str:
    """Return name if it's a top-level archetype, else its parent's name (used to tag variant vs archetype)."""
    for arch in ruleset.archetypes:
        if arch.name == name:
            return name
        if any(v.name == name for v in arch.variants):
            return arch.name
    return name


def _fallback(mainboard: dict[str, int], ruleset: RuleSet, deck_colors: str) -> ArchetypeResult:
    total = sum(mainboard.values())
    best = None
    best_weight = -1
    for fb in ruleset.fallbacks:
        common = set(fb.common_cards)
        weight = sum(cnt for name, cnt in mainboard.items() if name in common)
        if weight > best_weight or (
            weight == best_weight and best is not None and len(fb.common_cards) < len(best.common_cards)
        ):
            best, best_weight = fb, weight

    if best is not None and total > 0 and best_weight / total > MIN_FALLBACK_SIMILARITY:
        return ArchetypeResult(
            archetype=_label(best.name, best.include_color_in_name, deck_colors),
            base_archetype=best.name,
            color=deck_colors,
            kind="fallback",
        )
    return ArchetypeResult(archetype="Unknown", color=deck_colors, kind="unknown")


# Re-export for callers that want to introspect the supported condition set.
__all__ = ["ArchetypeResult", "classify", "evaluate_condition", "KNOWN_CONDITION_TYPES"]
