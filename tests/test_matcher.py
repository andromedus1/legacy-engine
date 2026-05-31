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


# ── Regression tests for peer-review findings 1-4 ──────────────────────────────────────────────

# Finding #1: variant uses its OWN include_color_in_name flag, NOT OR'd with parent's flag.
# A variant with IncludeColorInName=false under a color-prefixed parent must NOT get a color prefix.
class TestFinding1VariantOwnColorFlag:
    def test_variant_false_parent_true_no_prefix(self):
        """Variant with include_color_in_name=False under a color-prefixed parent → no color prefix."""
        parent = ArchetypeRule(
            name="Delver",
            include_color_in_name=True,
            conditions=[Condition(type="InMainboard", cards=["Delver of Secrets"])],
            variants=[
                ArchetypeRule(
                    name="Temur Delver",
                    include_color_in_name=False,  # the bug: parent=True should NOT bleed in
                    conditions=[Condition(type="InMainboard", cards=["Nimble Mongoose"])],
                )
            ],
        )
        rs = RuleSet(archetypes=[parent])
        r = classify({"Delver of Secrets": 4, "Nimble Mongoose": 4, "Island": 12}, {}, rs, "URG")
        # The variant has include_color_in_name=False, so the label must be "Temur Delver",
        # not "Temur Temur Delver" or any other color-prefixed form.
        assert r.archetype == "Temur Delver"
        assert r.kind == "variant"

    def test_variant_true_parent_false_has_prefix(self):
        """Variant with include_color_in_name=True under a non-color-prefixed parent → color prefix."""
        parent = ArchetypeRule(
            name="Control",
            include_color_in_name=False,
            conditions=[Condition(type="InMainboard", cards=["Brainstorm"])],
            variants=[
                # Use a distinct variant name so _parent_of resolves correctly.
                ArchetypeRule(
                    name="Taxblade",
                    include_color_in_name=True,
                    conditions=[Condition(type="InMainboard", cards=["Force of Will"])],
                )
            ],
        )
        rs = RuleSet(archetypes=[parent])
        r = classify({"Brainstorm": 4, "Force of Will": 4, "Island": 12}, {}, rs, "UB")
        # Variant has include_color_in_name=True → label should be "Dimir Taxblade"
        assert r.archetype == "Dimir Taxblade"
        assert r.kind == "variant"


# Finding #2: Conflict label built from each match's color-prefixed _label() in ruleset order,
# no sort, no dedupe.  Color-prefixed archetypes produce color-prefixed conflict labels.
class TestFinding2ConflictLabel:
    def test_conflict_preserves_ruleset_order_no_sort(self):
        """Two matches in ruleset order: conflict label is in that order (not alphabetically sorted)."""
        # Zeta before Alpha in ruleset → Zeta must appear first in Conflict label.
        zeta = ArchetypeRule(name="Zeta", conditions=[Condition(type="InMainboard", cards=["Brainstorm"])])
        alpha = ArchetypeRule(name="Alpha", conditions=[Condition(type="InMainboard", cards=["Brainstorm"])])
        rs = RuleSet(archetypes=[zeta, alpha])
        r = classify({"Brainstorm": 4, "Island": 16}, {}, rs, "U")
        assert r.archetype == "Conflict(Zeta,Alpha)"
        assert r.kind == "conflict"

    def test_conflict_includes_color_prefixes(self):
        """Archetypes with include_color_in_name=True produce color-prefixed labels inside Conflict."""
        a = ArchetypeRule(
            name="Tempo",
            include_color_in_name=True,
            conditions=[Condition(type="InMainboard", cards=["Brainstorm"])],
        )
        b = ArchetypeRule(
            name="Control",
            include_color_in_name=True,
            conditions=[Condition(type="InMainboard", cards=["Brainstorm"])],
        )
        rs = RuleSet(archetypes=[a, b])
        r = classify({"Brainstorm": 4, "Island": 16}, {}, rs, "UB")
        # Both have include_color_in_name=True; deck_colors="UB" → "Dimir"
        assert r.archetype == "Conflict(Dimir Tempo,Dimir Control)"
        assert r.kind == "conflict"

    def test_conflict_no_dedupe_duplicate_labels(self):
        """Two matches producing the same label must both appear (no dedupe)."""
        a = ArchetypeRule(name="Same", conditions=[Condition(type="InMainboard", cards=["Brainstorm"])])
        b = ArchetypeRule(name="Same", conditions=[Condition(type="InMainboard", cards=["Brainstorm"])])
        rs = RuleSet(archetypes=[a, b])
        r = classify({"Brainstorm": 4, "Island": 16}, {}, rs, "U")
        assert r.archetype == "Conflict(Same,Same)"


# Finding #3: fallback = (main+side matching copies) / (main rows + side rows), strict >.
class TestFinding3FallbackDenominator:
    @pytest.fixture
    def make_fallback_ruleset(self):
        """Return a factory building a simple RuleSet with one Fallback pile."""
        def _make(pile_cards: list[str], include_color: bool = False) -> RuleSet:
            fb = Fallback(name="Pile", include_color_in_name=include_color, common_cards=pile_cards)
            return RuleSet(fallbacks=[fb])
        return _make

    def test_sideboard_cards_count_toward_weight(self, make_fallback_ruleset):
        """Sideboard copies of common_cards contribute to the numerator."""
        rs = make_fallback_ruleset(["Bolt"])
        # main: 1 entry, side: 1 entry → total_entries=2; weight=4+3=7; 7/2=3.5 > 0.10
        r = classify({"Bolt": 4}, {"Bolt": 3}, rs, "R")
        assert r.kind == "fallback" and r.archetype == "Pile"

    def test_denominator_is_row_count_not_copies(self, make_fallback_ruleset):
        """Denominator is len(mainboard)+len(sideboard), NOT sum of all copies."""
        # 20 entries (1 distinct each) with only 1 matching card → weight=4, total_entries=20+0=20
        # old bug: weight/total_copies = 4/80 = 0.05 ≤ 0.10 (Unknown)
        # correct:  weight/total_entries = 4/20 = 0.20 > 0.10 (fallback)
        rs = make_fallback_ruleset(["Bolt"])
        main = {f"Card{i}": 4 for i in range(19)}
        main["Bolt"] = 4  # 20 distinct entries; only Bolt matches
        r = classify(main, {}, rs, "R")
        assert r.kind == "fallback", (
            "Fallback should fire: weight=4, entries=20, ratio=0.20 > 0.10"
        )

    def test_fallback_below_threshold_is_unknown(self, make_fallback_ruleset):
        """If best_weight / total_entries ≤ MIN_FALLBACK_SIMILARITY, result is Unknown."""
        rs = make_fallback_ruleset(["Bolt"])
        # 100 distinct entries, 1 match (4 copies) → weight=4, entries=100; 4/100=0.04 ≤ 0.10
        main = {f"Filler{i}": 1 for i in range(99)}
        main["Bolt"] = 4
        r = classify(main, {}, rs, "R")
        assert r.kind == "unknown"

    def test_sideboard_entries_reduce_ratio(self, make_fallback_ruleset):
        """Adding sideboard entries not in common_cards increases denominator without raising weight."""
        rs = make_fallback_ruleset(["Bolt"])
        # main: Bolt×4 (1 entry, weight=4); side: 100 non-matching entries
        # ratio = 4 / (1+100) ≈ 0.040 ≤ 0.10 → Unknown
        side = {f"SideCard{i}": 1 for i in range(100)}
        r = classify({"Bolt": 4}, side, rs, "R")
        assert r.kind == "unknown"

    def test_strict_greater_than_at_exact_boundary(self, make_fallback_ruleset):
        """At exactly MIN_FALLBACK_SIMILARITY (= 0.10), strict > means Unknown (not fallback)."""
        rs = make_fallback_ruleset(["Bolt"])
        # weight=1 copy, total_entries=10 → 1/10 = 0.10 exactly → NOT > 0.10 → Unknown
        main = {f"Filler{i}": 1 for i in range(9)}
        main["Bolt"] = 1  # 10 entries, weight=1
        r = classify(main, {}, rs, "R")
        assert r.kind == "unknown", "Exact boundary must be Unknown (strict >)"


# Finding #4: condition semantics contract alignment.
class TestFinding4ConditionSemantics:
    main = {"Daze", "Wasteland", "Brainstorm"}
    side = {"Surgical Extraction", "Daze"}  # Daze in BOTH zones for double-count tests

    # 4a: empty Cards list is non-constraining (returns True)
    def test_empty_cards_returns_true(self):
        for t in [
            "InMainboard", "InSideboard", "InMainOrSideboard",
            "OneOrMoreInMainboard", "OneOrMoreInSideboard", "OneOrMoreInMainOrSideboard",
            "TwoOrMoreInMainboard", "TwoOrMoreInSideboard", "TwoOrMoreInMainOrSideboard",
            "DoesNotContain", "DoesNotContainMainboard", "DoesNotContainSideboard",
        ]:
            result = evaluate_condition(Condition(type=t, cards=[]), self.main, self.side)
            assert result is True, f"Empty Cards for {t!r} should be True (non-constraining)"

    # 4b: single-card types use Cards[0]; a second card in the list is ignored
    @pytest.mark.parametrize(
        "ctype,cards,expected",
        [
            # Cards[0] present → True even if second card is absent
            ("InMainboard", ["Brainstorm", "Force of Will"], True),
            # Cards[0] absent → False even if second card is present
            ("InMainboard", ["Force of Will", "Brainstorm"], False),
            ("InSideboard", ["Surgical Extraction", "Force of Will"], True),
            ("InSideboard", ["Force of Will", "Surgical Extraction"], False),
            ("InMainOrSideboard", ["Wasteland", "Force of Will"], True),  # Wasteland in main
            ("InMainOrSideboard", ["Force of Will", "Wasteland"], False),
            ("DoesNotContain", ["Force of Will", "Brainstorm"], True),   # FoW absent → True
            ("DoesNotContain", ["Brainstorm", "Force of Will"], False),  # Brainstorm present → False
            ("DoesNotContainMainboard", ["Force of Will", "Daze"], True),
            ("DoesNotContainMainboard", ["Daze", "Force of Will"], False),
            ("DoesNotContainSideboard", ["Force of Will", "Surgical Extraction"], True),
            ("DoesNotContainSideboard", ["Surgical Extraction", "Force of Will"], False),
        ],
    )
    def test_single_card_uses_cards_zero(self, ctype, cards, expected):
        assert evaluate_condition(Condition(type=ctype, cards=cards), self.main, self.side) is expected

    # 4c: TwoOrMoreInMainOrSideboard — same card in both zones counts twice
    def test_two_or_more_same_card_in_both_zones_counts_twice(self):
        """'Daze' is in both main and side → _present(["Daze"], main)=1 + _present(["Daze"], side)=1 = 2 ≥ 2."""
        main = {"Daze"}
        side = {"Daze"}
        cond = Condition(type="TwoOrMoreInMainOrSideboard", cards=["Daze"])
        assert evaluate_condition(cond, main, side) is True

    def test_two_or_more_distinct_cards_across_zones(self):
        """One card in main, a different card in side → both zones contribute one hit each → 2 ≥ 2."""
        main = {"Alpha"}
        side = {"Beta"}
        cond = Condition(type="TwoOrMoreInMainOrSideboard", cards=["Alpha", "Beta"])
        assert evaluate_condition(cond, main, side) is True

    def test_two_or_more_single_zone_sufficient(self):
        """Two distinct cards both in main → _present(cards, main)=2 + _present(cards, side)=0 = 2 ≥ 2."""
        main = {"Alpha", "Beta"}
        side: set[str] = set()
        cond = Condition(type="TwoOrMoreInMainOrSideboard", cards=["Alpha", "Beta"])
        assert evaluate_condition(cond, main, side) is True

    def test_two_or_more_only_one_hit_fails(self):
        """Only one card present across both zones → 1 < 2 → False."""
        main = {"Alpha"}
        side: set[str] = set()
        cond = Condition(type="TwoOrMoreInMainOrSideboard", cards=["Alpha", "Beta"])
        assert evaluate_condition(cond, main, side) is False

    # 4d: OneOrMore* retains whole-list semantics (not Cards[0])
    def test_one_or_more_uses_whole_list(self):
        """OneOrMoreInMainboard hits on any card in the list, not just Cards[0]."""
        main = {"Wasteland"}  # not the first card in the list
        cond = Condition(type="OneOrMoreInMainboard", cards=["Brainstorm", "Wasteland"])
        assert evaluate_condition(cond, main, set()) is True

    # Integrated: a rule whose condition has empty Cards still matches (non-constraining)
    def test_empty_cards_condition_passes_in_classify(self):
        """An archetype with an empty-Cards condition matches any deck (non-constraining skip)."""
        arch = ArchetypeRule(
            name="AnyDeck",
            conditions=[Condition(type="InMainboard", cards=[])],
        )
        rs = RuleSet(archetypes=[arch])
        r = classify({"Island": 20}, {}, rs, "U")
        assert r.archetype == "AnyDeck" and r.kind == "archetype"
