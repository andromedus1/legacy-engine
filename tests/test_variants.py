"""Tests for archetype.variants — registry loader + resolver (Unit 2 of feature-subarchetype-variants).

All tests are pure (no DB). Tests cover:
- Registry load from JSON (lenient + unknown type fail-fast)
- resolve_variant: single match, default complement, no-match → None, >1 match → AmbiguousVariantError
- parent mismatch → None
- Shipped data/variants/legacy.json lint: mutual exclusivity over fixture deck sets
"""

from __future__ import annotations

import json
import pathlib

import pytest

from legacy_engine.archetype.variants import AmbiguousVariantError, load_variant_registry, resolve_variant
from legacy_engine.archetype.rules import UnknownConditionTypeError
from legacy_engine.models.variant import VariantRegistry, VariantRule
from legacy_engine.archetype.rules import Condition


# ---------------------------------------------------------------------------
# Helpers to build in-memory registries without files
# ---------------------------------------------------------------------------

def _make_registry(variants: list[dict], defaults: dict | None = None) -> VariantRegistry:
    return VariantRegistry(
        version="test",
        variants=[VariantRule.model_validate(v) for v in variants],
        defaults=defaults or {},
    )


def _rule(parent: str, name: str, conditions: list[dict]) -> dict:
    return {"parent": parent, "name": name, "conditions": conditions}


def _cond(type_: str, cards: list[str]) -> dict:
    return {"Type": type_, "Cards": cards}


# ---------------------------------------------------------------------------
# Registry loader tests
# ---------------------------------------------------------------------------

class TestLoadVariantRegistry:
    def test_load_shipped_registry(self):
        """The shipped data/variants/legacy.json loads without errors."""
        from legacy_engine.config import VARIANTS_REGISTRY_PATH
        assert VARIANTS_REGISTRY_PATH.exists(), f"Expected registry at {VARIANTS_REGISTRY_PATH}"
        registry = load_variant_registry(VARIANTS_REGISTRY_PATH)
        assert registry.version
        assert len(registry.variants) > 0

    def test_load_lenient_json_trailing_comma(self, tmp_path):
        """Loader tolerates trailing commas (same as rules._loads_lenient)."""
        content = '''{
            "version": "test",
            "variants": [
                {"parent": "A", "name": "x",
                 "conditions": [{"Type": "InMainboard", "Cards": ["Brainstorm"],}],}
            ],
            "defaults": {}
        }'''
        p = tmp_path / "reg.json"
        p.write_text(content)
        registry = load_variant_registry(p)
        assert len(registry.variants) == 1

    def test_unknown_condition_type_fails_fast(self, tmp_path):
        """Unknown Type raises UnknownConditionTypeError at load time."""
        raw = {
            "version": "test",
            "variants": [
                {"parent": "A", "name": "x", "conditions": [{"Type": "BOGUS", "Cards": ["B"]}]}
            ],
            "defaults": {},
        }
        p = tmp_path / "bad.json"
        p.write_text(json.dumps(raw))
        with pytest.raises(UnknownConditionTypeError):
            load_variant_registry(p)

    def test_empty_conditions_allowed(self, tmp_path):
        """A variant with no conditions is valid (always-matches rule)."""
        raw = {
            "version": "test",
            "variants": [{"parent": "A", "name": "default", "conditions": []}],
            "defaults": {},
        }
        p = tmp_path / "empty_cond.json"
        p.write_text(json.dumps(raw))
        registry = load_variant_registry(p)
        assert registry.variants[0].name == "default"


# ---------------------------------------------------------------------------
# resolve_variant tests (pure, no DB)
# ---------------------------------------------------------------------------

class TestResolveVariant:
    def _deck_with(self, *cards: str) -> tuple[dict[str, int], dict[str, int]]:
        """Build a (mainboard, sideboard) pair where all listed cards are mainboard."""
        return {c: 4 for c in cards}, {}

    def test_single_match_returns_name(self):
        registry = _make_registry([
            _rule("Dimir Tempo", "Bauble", [_cond("InMainboard", ["Mishra's Bauble"])]),
            _rule("Dimir Tempo", "non-Bauble", [_cond("DoesNotContain", ["Mishra's Bauble"])]),
        ])
        main, side = self._deck_with("Mishra's Bauble", "Brainstorm")
        result = resolve_variant("Dimir Tempo", main, side, registry)
        assert result == "Bauble"

    def test_complement_matches_non_variant(self):
        registry = _make_registry([
            _rule("Dimir Tempo", "Bauble", [_cond("InMainboard", ["Mishra's Bauble"])]),
            _rule("Dimir Tempo", "non-Bauble", [_cond("DoesNotContain", ["Mishra's Bauble"])]),
        ])
        main, side = self._deck_with("Brainstorm", "Force of Will")
        result = resolve_variant("Dimir Tempo", main, side, registry)
        assert result == "non-Bauble"

    def test_no_match_returns_declared_default(self):
        registry = _make_registry(
            [_rule("Smallpox", "Loam", [_cond("OneOrMoreInMainOrSideboard", ["Life from the Loam"])])],
            defaults={"Smallpox": "non-Loam"},
        )
        main, side = {}, {}  # no Life from the Loam
        result = resolve_variant("Smallpox", main, side, registry)
        assert result == "non-Loam"

    def test_no_match_no_default_returns_none(self):
        registry = _make_registry(
            [_rule("Smallpox", "Loam", [_cond("OneOrMoreInMainOrSideboard", ["Life from the Loam"])])],
            defaults={},
        )
        main, side = {}, {}
        result = resolve_variant("Smallpox", main, side, registry)
        assert result is None

    def test_parent_mismatch_returns_none(self):
        registry = _make_registry([
            _rule("Dimir Tempo", "Bauble", [_cond("InMainboard", ["Mishra's Bauble"])]),
        ])
        main, side = self._deck_with("Mishra's Bauble")
        # Different parent → no rules → None
        result = resolve_variant("Izzet Tempo", main, side, registry)
        assert result is None

    def test_ambiguous_raises(self):
        """Two matching rules for the same parent → AmbiguousVariantError."""
        registry = _make_registry([
            _rule("A", "v1", [_cond("InMainboard", ["X"])]),
            _rule("A", "v2", [_cond("InMainboard", ["X"])]),  # same positive condition
        ])
        main, side = {"X": 4}, {}
        with pytest.raises(AmbiguousVariantError):
            resolve_variant("A", main, side, registry)

    def test_sideboard_condition(self):
        """InSideboard condition properly checks the sideboard, not the main."""
        registry = _make_registry([
            _rule("A", "SideTech", [_cond("InSideboard", ["Pyroblast"])]),
        ])
        main, side = {}, {"Pyroblast": 4}
        assert resolve_variant("A", main, side, registry) == "SideTech"

    def test_sideboard_condition_does_not_match_main(self):
        """InSideboard condition does not match a card in mainboard."""
        registry = _make_registry([
            _rule("A", "SideTech", [_cond("InSideboard", ["Pyroblast"])]),
        ])
        main, side = {"Pyroblast": 4}, {}
        assert resolve_variant("A", main, side, registry) is None

    def test_empty_conditions_always_matches(self):
        """A rule with zero conditions always passes (AND of empty list is True)."""
        registry = _make_registry([
            _rule("A", "always", []),
        ])
        main, side = {}, {}
        assert resolve_variant("A", main, side, registry) == "always"


# ---------------------------------------------------------------------------
# Shipped registry lint: mutual exclusivity over fixture deck sets
# ---------------------------------------------------------------------------

class TestShippedRegistryLint:
    """Asserts the shipped legacy.json registry resolves mutually exclusively over deck fixtures."""

    _REGISTRY_PATH = (
        pathlib.Path(__file__).parent.parent
        / "src" / "legacy_engine" / "data" / "variants" / "legacy.json"
    )

    @pytest.fixture(autouse=True)
    def registry(self):
        if not self._REGISTRY_PATH.exists():
            pytest.skip("Shipped registry not found")
        self._registry = load_variant_registry(self._REGISTRY_PATH)

    def test_dimir_tempo_bauble_decks_do_not_ambiguate(self):
        """A Dimir Tempo deck with Mishra's Bauble resolves to exactly one variant."""
        main = {"Mishra's Bauble": 4, "Brainstorm": 4}
        side: dict[str, int] = {}
        # Must not raise AmbiguousVariantError
        result = resolve_variant("Dimir Tempo", main, side, self._registry)
        assert result == "Bauble"

    def test_dimir_tempo_non_bauble_decks_do_not_ambiguate(self):
        main = {"Brainstorm": 4, "Force of Will": 4}
        side: dict[str, int] = {}
        result = resolve_variant("Dimir Tempo", main, side, self._registry)
        assert result == "non-Bauble"

    def test_smallpox_loam_resolves(self):
        main = {"Life from the Loam": 3, "Smallpox": 4}
        side: dict[str, int] = {}
        result = resolve_variant("Smallpox", main, side, self._registry)
        assert result == "Loam"

    def test_smallpox_non_loam_resolves(self):
        main = {"Smallpox": 4, "Liliana of the Veil": 4}
        side: dict[str, int] = {}
        result = resolve_variant("Smallpox", main, side, self._registry)
        assert result == "non-Loam"

    def test_all_parent_variants_are_exclusive(self):
        """For every parent, test that ambiguous decks cannot exist by definition.

        Since Dimir Tempo and Smallpox use strict positive+complement pairs, confirm
        that the fixture decks each resolve to exactly one variant (no AmbiguousVariantError).
        """
        from legacy_engine.archetype.variants import AmbiguousVariantError

        fixture_decks = {
            "Dimir Tempo": [
                ({"Mishra's Bauble": 4}, {}),
                ({"Brainstorm": 4}, {}),
            ],
            "Smallpox": [
                ({"Life from the Loam": 3}, {}),
                ({"Smallpox": 4}, {}),
            ],
        }
        for parent, decks in fixture_decks.items():
            for main, side in decks:
                try:
                    resolve_variant(parent, main, side, self._registry)
                except AmbiguousVariantError as exc:
                    pytest.fail(f"Ambiguous variant for {parent} with deck {main}: {exc}")
