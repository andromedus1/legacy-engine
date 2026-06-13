"""Variant registry loader + resolver — sub-archetype variant tagging.

Loads a declarative signature-card variant registry from a project-owned JSON file and
resolves a variant tag for a given deck, reusing ``matcher.evaluate_condition`` and
``rules._loads_lenient`` / ``KNOWN_CONDITION_TYPES`` verbatim.

Design decision (from feature spec): declarative registry over auto-clustering — deterministic,
reproducible, domain-named, composable with existing Condition machinery.  The ``diff_compositions``
subgroup tool is the discovery front-end that tells you which card to register.
"""

from __future__ import annotations

from pathlib import Path

from legacy_engine.archetype.matcher import evaluate_condition
from legacy_engine.archetype.rules import KNOWN_CONDITION_TYPES, UnknownConditionTypeError, _loads_lenient
from legacy_engine.models.variant import VariantRegistry, VariantRule


class AmbiguousVariantError(ValueError):
    """Raised when more than one variant matches a deck for the same parent archetype."""


def load_variant_registry(path: Path | str) -> VariantRegistry:
    """Load and validate a variant registry from a JSON file.

    Uses lenient JSON parsing (tolerates trailing commas, same as ``rules._loads_lenient``).
    Fails fast on any unknown ``Condition.Type`` across all variant rules.

    Raises ``UnknownConditionTypeError`` for bad condition types.
    Raises ``ValueError`` / ``FileNotFoundError`` on malformed / missing input.
    """
    path = Path(path)
    raw = _loads_lenient(path.read_text())
    registry = VariantRegistry.model_validate(raw)
    _validate_registry_condition_types(registry, path)
    return registry


def _validate_registry_condition_types(registry: VariantRegistry, source: Path) -> None:
    """Fail fast on any unknown condition type in the registry."""
    for rule in registry.variants:
        for cond in rule.conditions:
            if cond.type not in KNOWN_CONDITION_TYPES:
                raise UnknownConditionTypeError(
                    f"unknown condition Type '{cond.type}' in variant rule "
                    f"'{rule.parent}/{rule.name}' from {source}"
                )


def resolve_variant(
    base_archetype: str,
    mainboard: dict[str, int],
    sideboard: dict[str, int],
    registry: VariantRegistry,
) -> str | None:
    """Resolve the variant tag for a deck given its parent archetype label and registry.

    Pure function — no DB, hand-testable.

    Algorithm:
    1. Filter registry to rules with ``parent == base_archetype``.
    2. Evaluate each rule's conditions via ``evaluate_condition`` (reused verbatim from matcher).
       A rule matches when ALL of its conditions pass (same AND-logic as archetype matching).
    3. Exactly one match → return that variant's name.
       Zero matches → return ``registry.defaults.get(base_archetype)`` (may be None).
       >1 matches → raise ``AmbiguousVariantError`` (author error — use DoesNotContain complements).

    Returns ``None`` when no variant matches and no default is declared.
    """
    rules = registry.for_parent(base_archetype)
    if not rules:
        return None

    main_set = set(mainboard)
    side_set = set(sideboard)

    matching: list[VariantRule] = []
    for rule in rules:
        if all(evaluate_condition(cond, main_set, side_set) for cond in rule.conditions):
            matching.append(rule)

    if len(matching) == 1:
        return matching[0].name

    if len(matching) > 1:
        names = ", ".join(f"'{r.name}'" for r in matching)
        raise AmbiguousVariantError(
            f"Multiple variant rules matched for '{base_archetype}': {names}. "
            "Variants under a parent must be mutually exclusive — use DoesNotContain complements."
        )

    # Zero matches — use the declared default for this parent, or None.
    return registry.defaults.get(base_archetype)
