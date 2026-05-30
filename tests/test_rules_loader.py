"""Rule loader — parse archetypes/variants/fallbacks; fail-fast on unknown condition Type."""

from __future__ import annotations

import json

import pytest

from legacy_engine.archetype.rules import (
    KNOWN_CONDITION_TYPES,
    UnknownConditionTypeError,
    load_ruleset,
)

DELVER = {
    "Name": "Delver",
    "IncludeColorInName": True,
    "Conditions": [
        {"Type": "InMainboard", "Cards": ["Delver of Secrets"]},
        {"Type": "DoesNotContain", "Cards": ["Entomb"]},
    ],
    "Variants": [{"Name": "Tempo", "Conditions": [{"Type": "OneOrMoreInMainboard", "Cards": ["Daze", "Wasteland"]}]}],
}
AGGRO_FALLBACK = {"Name": "Aggro", "IncludeColorInName": True, "CommonCards": ["Lightning Bolt", "Goblin Guide"]}
COLOR_OVERRIDES = {"Lands": [{"Name": "Underground Sea", "Color": "UB"}], "NonLands": []}


def _build_rules(tmp_path, *, extra_archetype=None):
    legacy = tmp_path / "Formats" / "Legacy"
    (legacy / "Archetypes").mkdir(parents=True)
    (legacy / "Fallbacks").mkdir(parents=True)
    (legacy / "Archetypes" / "Delver.json").write_text(json.dumps(DELVER))
    (legacy / "Fallbacks" / "Aggro.json").write_text(json.dumps(AGGRO_FALLBACK))
    (legacy / "color_overrides.json").write_text(json.dumps(COLOR_OVERRIDES))
    if extra_archetype is not None:
        (legacy / "Archetypes" / "Extra.json").write_text(json.dumps(extra_archetype))
    return tmp_path


def test_loads_archetypes_variants_fallbacks(tmp_path):
    rs = load_ruleset(_build_rules(tmp_path))
    assert len(rs.archetypes) == 1
    delver = rs.archetypes[0]
    assert delver.name == "Delver" and delver.include_color_in_name is True
    assert delver.conditions[0].type == "InMainboard"
    assert delver.conditions[0].cards == ["Delver of Secrets"]
    assert len(delver.variants) == 1 and delver.variants[0].name == "Tempo"
    assert rs.fallbacks[0].name == "Aggro" and rs.fallbacks[0].common_cards
    assert rs.color_overrides["Lands"][0]["Name"] == "Underground Sea"


def test_twelve_condition_types_recognized():
    assert len(KNOWN_CONDITION_TYPES) == 12


def test_unknown_condition_type_fails_fast(tmp_path):
    bad = {"Name": "Bad", "Conditions": [{"Type": "BogusType", "Cards": ["X"]}]}
    with pytest.raises(UnknownConditionTypeError):
        load_ruleset(_build_rules(tmp_path, extra_archetype=bad))


def test_unknown_type_in_variant_fails_fast(tmp_path):
    bad = {"Name": "BadVariantParent", "Conditions": [{"Type": "InMainboard", "Cards": ["A"]}],
           "Variants": [{"Name": "BadV", "Conditions": [{"Type": "Nonsense", "Cards": ["B"]}]}]}
    with pytest.raises(UnknownConditionTypeError):
        load_ruleset(_build_rules(tmp_path, extra_archetype=bad))


def test_empty_rules_dir(tmp_path):
    rs = load_ruleset(tmp_path)  # no Formats/Legacy tree
    assert rs.archetypes == [] and rs.fallbacks == []
