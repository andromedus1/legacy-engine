"""Typed loader for the vendored MTGOFormatData archetype rules.

Loads the rules-as-JSON into typed Pydantic objects. An unknown condition ``Type`` raises at load
time (fail-fast, mirroring the foundation's unknown-role convention) — a silently-skipped condition
would mislabel decks and corrupt the meta-share the platform exists to produce.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import Field

from legacy_engine.models.base import LegacyEngineModel

# Trailing comma before a closing ] or } — invalid strict JSON but present in some hand-maintained
# MTGOFormatData files (e.g. Fallbacks/Dredge.json, Stompy.json, color_overrides.json).
_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _loads_lenient(text: str) -> Any:
    """Parse JSON, tolerating trailing commas in the hand-maintained upstream rule files.

    Strict ``json.loads`` first; on a trailing-comma failure, strip them and retry rather than
    dropping a real archetype/fallback. (The rule-file values are card-name strings, so the regex
    can't corrupt legitimate content.)
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return json.loads(_TRAILING_COMMA_RE.sub(r"\1", text))

# The 12 condition types defined by MTGOFormatData (mtgoformatdata-rule-schema brief).
KNOWN_CONDITION_TYPES: frozenset[str] = frozenset({
    "InMainboard", "InSideboard", "InMainOrSideboard",
    "OneOrMoreInMainboard", "OneOrMoreInSideboard", "OneOrMoreInMainOrSideboard",
    "TwoOrMoreInMainboard", "TwoOrMoreInSideboard", "TwoOrMoreInMainOrSideboard",
    "DoesNotContain", "DoesNotContainMainboard", "DoesNotContainSideboard",
})


class UnknownConditionTypeError(ValueError):
    """Raised when a vendored rule uses a condition Type the matcher doesn't implement."""


class Condition(LegacyEngineModel):
    type: str = Field(alias="Type")
    cards: list[str] = Field(default_factory=list, alias="Cards")


class ArchetypeRule(LegacyEngineModel):
    name: str = Field(alias="Name")
    include_color_in_name: bool = Field(default=False, alias="IncludeColorInName")
    conditions: list[Condition] = Field(default_factory=list, alias="Conditions")
    variants: list["ArchetypeRule"] = Field(default_factory=list, alias="Variants")


class Fallback(LegacyEngineModel):
    name: str = Field(alias="Name")
    include_color_in_name: bool = Field(default=False, alias="IncludeColorInName")
    common_cards: list[str] = Field(default_factory=list, alias="CommonCards")


class RuleSet(LegacyEngineModel):
    archetypes: list[ArchetypeRule] = Field(default_factory=list)
    fallbacks: list[Fallback] = Field(default_factory=list)
    color_overrides: dict = Field(default_factory=dict)


def _validate_condition_types(rule: ArchetypeRule, source: Path) -> None:
    for cond in rule.conditions:
        if cond.type not in KNOWN_CONDITION_TYPES:
            raise UnknownConditionTypeError(f"unknown condition Type '{cond.type}' in {source}")
    for variant in rule.variants:
        _validate_condition_types(variant, source)


def load_ruleset(rules_dir: Path) -> RuleSet:
    """Load the Legacy ruleset from a vendored MTGOFormatData ``Formats/Legacy/`` tree."""
    legacy = Path(rules_dir) / "Formats" / "Legacy"
    archetypes: list[ArchetypeRule] = []
    fallbacks: list[Fallback] = []

    arch_dir = legacy / "Archetypes"
    if arch_dir.exists():
        for path in sorted(arch_dir.glob("*.json")):
            rule = ArchetypeRule.model_validate(_loads_lenient(path.read_text()))
            _validate_condition_types(rule, path)  # fail-fast on unknown Type
            archetypes.append(rule)

    fb_dir = legacy / "Fallbacks"
    if fb_dir.exists():
        for path in sorted(fb_dir.glob("*.json")):
            fallbacks.append(Fallback.model_validate(_loads_lenient(path.read_text())))

    overrides_path = legacy / "color_overrides.json"
    color_overrides = _loads_lenient(overrides_path.read_text()) if overrides_path.exists() else {}

    return RuleSet(archetypes=archetypes, fallbacks=fallbacks, color_overrides=color_overrides)
