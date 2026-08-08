"""Tests for archetype.color_splits — curated colour-split loader + resolver.

Pure (no DB) except the shipped-registry lint, which only reads the tracked JSON. Covers:
- Registry load: lenient JSON, and every fail-fast in ``_validate_registry``
- ``count_deck_colors``: nonland-only, copies-weighted, unresolvable names skipped
- ``resolve_color_split``: match, complement, ``min_copies`` threshold, unsplit parent → None,
  overlapping buckets → ``AmbiguousColorSplitError``
- The shipped ``data/color_splits/legacy.json`` loads and partitions Energy exactly two ways
"""

from __future__ import annotations

import json

import pytest

from legacy_engine.archetype.color_splits import (
    AmbiguousColorSplitError,
    count_deck_colors,
    load_color_split_registry,
    resolve_color_split,
)
from legacy_engine.config import COLOR_SPLITS_REGISTRY_PATH
from legacy_engine.models.card import Card
from legacy_engine.models.color_split import ColorSplitRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def make_registry():
    """Build an in-memory ``ColorSplitRegistry`` without touching disk."""

    def _make(splits: list[dict], version: str = "test") -> ColorSplitRegistry:
        return ColorSplitRegistry.model_validate({"version": version, "splits": splits})

    return _make


@pytest.fixture
def energy_split():
    """The shipped Energy split's shape, as a plain dict."""
    return {
        "parent": "Energy",
        "min_copies": 1,
        "buckets": [
            {"name": "Mardu Energy", "requires_any": ["B"]},
            {"name": "Boros Energy", "forbids_all": ["B"]},
        ],
    }


@pytest.fixture
def make_card():
    """Deterministic ``Card`` builder — colours and land-ness are all these tests key on."""

    def _make(name: str, colors: str = "", type_line: str = "Creature") -> Card:
        return Card(name=name, colors=list(colors), type_line=type_line)

    return _make


@pytest.fixture
def resolver(make_card):
    """A ``resolve_card`` callable over a fixed little card index."""
    index = {
        "Ocelot Pride": make_card("Ocelot Pride", "W"),
        "Amped Raptor": make_card("Amped Raptor", "R"),
        "Thoughtseize": make_card("Thoughtseize", "B", "Sorcery"),
        "Psychic Frog": make_card("Psychic Frog", "UB"),
        "Scrubland": make_card("Scrubland", "", "Land"),
        "Wasteland": make_card("Wasteland", "", "Land"),
    }
    return index.get


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class TestLoadColorSplitRegistry:
    def test_loads_lenient_json_with_trailing_comma(self, tmp_path, energy_split):
        path = tmp_path / "splits.json"
        path.write_text(
            '{"version": "t", "splits": [' + json.dumps(energy_split) + ",]}"
        )
        registry = load_color_split_registry(path)
        assert registry.for_parent("Energy").buckets[0].name == "Mardu Energy"

    def test_duplicate_parent_fails_fast(self, tmp_path, energy_split):
        path = tmp_path / "splits.json"
        path.write_text(json.dumps({"version": "t", "splits": [energy_split, energy_split]}))
        with pytest.raises(ValueError, match="duplicate colour split for parent 'Energy'"):
            load_color_split_registry(path)

    def test_unknown_colour_letter_fails_fast(self, tmp_path, energy_split):
        energy_split["buckets"][0]["requires_any"] = ["Z"]
        path = tmp_path / "splits.json"
        path.write_text(json.dumps({"version": "t", "splits": [energy_split]}))
        with pytest.raises(ValueError, match=r"unknown colour\(s\) \['Z'\]"):
            load_color_split_registry(path)

    def test_bucket_with_no_predicate_fails_fast(self, tmp_path, energy_split):
        energy_split["buckets"][1] = {"name": "Anything"}
        path = tmp_path / "splits.json"
        path.write_text(json.dumps({"version": "t", "splits": [energy_split]}))
        with pytest.raises(ValueError, match="declares no colour predicate"):
            load_color_split_registry(path)

    def test_unreachable_bucket_fails_fast(self, tmp_path, energy_split):
        energy_split["buckets"][0]["forbids_all"] = ["B"]
        path = tmp_path / "splits.json"
        path.write_text(json.dumps({"version": "t", "splits": [energy_split]}))
        with pytest.raises(ValueError, match="both requires and forbids"):
            load_color_split_registry(path)

    def test_single_bucket_is_not_a_split(self, tmp_path, energy_split):
        energy_split["buckets"] = energy_split["buckets"][:1]
        path = tmp_path / "splits.json"
        path.write_text(json.dumps({"version": "t", "splits": [energy_split]}))
        with pytest.raises(ValueError, match="a split needs at least 2"):
            load_color_split_registry(path)

    def test_min_copies_below_one_fails_fast(self, tmp_path, energy_split):
        energy_split["min_copies"] = 0
        path = tmp_path / "splits.json"
        path.write_text(json.dumps({"version": "t", "splits": [energy_split]}))
        with pytest.raises(ValueError, match="must be >= 1"):
            load_color_split_registry(path)


# ---------------------------------------------------------------------------
# count_deck_colors
# ---------------------------------------------------------------------------


class TestCountDeckColors:
    def test_counts_copies_not_rows(self, resolver):
        counts = count_deck_colors({"Ocelot Pride": 4, "Amped Raptor": 3}, resolver)
        assert counts == {"W": 4, "R": 3}

    def test_gold_card_counts_toward_every_colour(self, resolver):
        assert count_deck_colors({"Psychic Frog": 2}, resolver) == {"U": 2, "B": 2}

    def test_lands_are_excluded(self, resolver):
        # Scrubland taps for black but casts nothing — a manabase must not create a colour.
        assert count_deck_colors({"Scrubland": 4, "Wasteland": 4}, resolver) == {}

    def test_unresolvable_card_is_skipped_not_guessed(self, resolver):
        assert count_deck_colors({"Ocelot Pride": 4, "Nonexistent Card": 4}, resolver) == {"W": 4}


# ---------------------------------------------------------------------------
# resolve_color_split
# ---------------------------------------------------------------------------


class TestResolveColorSplit:
    def test_black_present_takes_the_requires_bucket(self, make_registry, energy_split):
        registry = make_registry([energy_split])
        assert resolve_color_split("Energy", {"W": 4, "R": 4, "B": 8}, registry) == "Mardu Energy"

    def test_no_black_takes_the_complement_bucket(self, make_registry, energy_split):
        registry = make_registry([energy_split])
        assert resolve_color_split("Energy", {"W": 4, "R": 4}, registry) == "Boros Energy"

    def test_unsplit_parent_returns_none(self, make_registry, energy_split):
        registry = make_registry([energy_split])
        assert resolve_color_split("Lands", {"B": 8}, registry) is None

    def test_min_copies_gates_a_thin_splash(self, make_registry, energy_split):
        energy_split["min_copies"] = 4
        registry = make_registry([energy_split])
        assert resolve_color_split("Energy", {"W": 4, "B": 2}, registry) == "Boros Energy"
        assert resolve_color_split("Energy", {"W": 4, "B": 4}, registry) == "Mardu Energy"

    def test_overlapping_buckets_raise(self, make_registry):
        registry = make_registry(
            [
                {
                    "parent": "Energy",
                    "buckets": [
                        {"name": "A", "requires_any": ["B"]},
                        {"name": "B", "requires_any": ["B", "W"]},
                    ],
                }
            ]
        )
        with pytest.raises(AmbiguousColorSplitError, match="must be mutually exclusive"):
            resolve_color_split("Energy", {"B": 4}, registry)

    def test_no_bucket_matched_keeps_the_parent(self, make_registry):
        registry = make_registry(
            [
                {
                    "parent": "Energy",
                    "buckets": [
                        {"name": "A", "requires_any": ["U"]},
                        {"name": "B", "requires_any": ["G"]},
                    ],
                }
            ]
        )
        assert resolve_color_split("Energy", {"W": 4, "R": 4}, registry) is None


# ---------------------------------------------------------------------------
# Shipped registry lint
# ---------------------------------------------------------------------------


class TestShippedRegistry:
    def test_shipped_registry_loads(self):
        registry = load_color_split_registry(COLOR_SPLITS_REGISTRY_PATH)
        assert registry.version
        assert registry.splits

    def test_energy_partitions_exactly_two_ways(self):
        registry = load_color_split_registry(COLOR_SPLITS_REGISTRY_PATH)
        split = registry.for_parent("Energy")
        assert split is not None
        assert {b.name for b in split.buckets} == {"Boros Energy", "Mardu Energy"}

    @pytest.mark.parametrize(
        "counts,expected",
        [
            ({"W": 16, "R": 8}, "Boros Energy"),
            ({"W": 16, "R": 8, "B": 11}, "Mardu Energy"),
            ({"W": 16, "R": 8, "B": 1}, "Mardu Energy"),
            ({"W": 16, "R": 8, "U": 4}, "Boros Energy"),
        ],
    )
    def test_every_energy_deck_lands_in_exactly_one_bucket(self, counts, expected):
        registry = load_color_split_registry(COLOR_SPLITS_REGISTRY_PATH)
        assert resolve_color_split("Energy", counts, registry) == expected
