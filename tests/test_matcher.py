"""Matcher port — golden fixtures (deck → expected label) + condition-type evaluation."""

from __future__ import annotations

import pytest

from legacy_engine.archetype.matcher import ArchetypeResult, classify, evaluate_condition
from legacy_engine.archetype.rules import ArchetypeRule, Condition, Fallback, RuleSet

# ── A small hand-curated ruleset (the golden fixture) ──
_DELVER = ArchetypeRule(
    name="Delver",
    include_color_in_name=True,
    conditions=[
        Condition(type="InMainboard", cards=["Delver of Secrets"]),
        Condition(type="DoesNotContain", cards=["Show and Tell"]),
    ],
    variants=[
        ArchetypeRule(
            name="Tempo",
            include_color_in_name=True,
            conditions=[Condition(type="OneOrMoreInMainboard", cards=["Daze", "Wasteland"])],
        )
    ],
)
_SHOWTELL = ArchetypeRule(
    name="Show and Tell",
    include_color_in_name=True,
    conditions=[Condition(type="InMainboard", cards=["Show and Tell"])],
)
_AGGRO = Fallback(
    name="Aggro", include_color_in_name=True,
    common_cards=["Lightning Bolt", "Goblin Guide", "Monastery Swiftspear"],
)
RULES = RuleSet(archetypes=[_DELVER, _SHOWTELL], fallbacks=[_AGGRO])


class TestClassifyGolden:
    def test_variant_match_color_prefixed(self):
        deck = {"Delver of Secrets": 4, "Daze": 4, "Brainstorm": 4, "Island": 8}
        r = classify(deck, {}, RULES, "UB")
        assert r.archetype == "Dimir Tempo" and r.kind == "variant"

    def test_bare_archetype_when_no_variant(self):
        deck = {"Delver of Secrets": 4, "Brainstorm": 4, "Island": 12}  # no Daze/Wasteland
        r = classify(deck, {}, RULES, "UR")
        assert r.archetype == "Izzet Delver" and r.kind == "archetype"

    def test_doesnotcontain_excludes(self):
        # Delver + Show and Tell: Delver's DoesNotContain excludes it; only Show and Tell matches.
        deck = {"Delver of Secrets": 4, "Show and Tell": 4, "Island": 12}
        r = classify(deck, {}, RULES, "UR")
        assert r.archetype == "Izzet Show and Tell" and r.kind == "archetype"

    def test_fallback_when_no_archetype(self):
        deck = {"Lightning Bolt": 4, "Goblin Guide": 4, "Monastery Swiftspear": 4, "Mountain": 8}
        r = classify(deck, {}, RULES, "R")
        assert r.kind == "fallback" and r.archetype == "Red Aggro"

    def test_unknown_when_no_match_low_overlap(self):
        deck = {"Random Bulk Rare": 4, "Mountain": 16}
        r = classify(deck, {}, RULES, "R")
        assert r.kind == "unknown" and r.archetype == "Unknown"


class TestConflict:
    def test_two_matching_archetypes_conflict(self):
        a = ArchetypeRule(name="Alpha", conditions=[Condition(type="InMainboard", cards=["Brainstorm"])])
        b = ArchetypeRule(name="Beta", conditions=[Condition(type="InMainboard", cards=["Brainstorm"])])
        rs = RuleSet(archetypes=[a, b])
        r = classify({"Brainstorm": 4, "Island": 16}, {}, rs, "U")
        assert r.kind == "conflict" and r.archetype == "Conflict(Alpha,Beta)"


class TestEvaluateCondition:
    main = {"Daze", "Wasteland", "Brainstorm"}
    side = {"Surgical Extraction"}

    @pytest.mark.parametrize(
        "ctype,cards,expected",
        [
            ("InMainboard", ["Daze"], True),
            ("InMainboard", ["Force of Will"], False),
            ("InSideboard", ["Surgical Extraction"], True),
            ("InMainOrSideboard", ["Surgical Extraction"], True),
            ("TwoOrMoreInMainboard", ["Daze", "Wasteland"], True),
            ("TwoOrMoreInMainboard", ["Daze", "Force of Will"], False),
            ("DoesNotContain", ["Entomb"], True),
            ("DoesNotContain", ["Brainstorm"], False),
            ("DoesNotContainSideboard", ["Surgical Extraction"], False),
        ],
    )
    def test_conditions(self, ctype, cards, expected):
        assert evaluate_condition(Condition(type=ctype, cards=cards), self.main, self.side) is expected


def test_result_is_typed():
    r = classify({"Brainstorm": 4}, {}, RULES, "")
    assert isinstance(r, ArchetypeResult)
