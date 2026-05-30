"""compute_deck_colors intersection logic + guild naming."""

from __future__ import annotations

import pytest

from legacy_engine.colors import compute_deck_colors, guild_name
from legacy_engine.models.card import Card


def _land(name, produced):
    return Card(name=name, type_line="Land", produced_mana=produced)


def _spell(name, colors):
    return Card(name=name, type_line="Instant", colors=colors)


class TestComputeDeckColors:
    def test_ub_tempo(self):
        cards = [
            _land("Underground Sea", ["U", "B"]),
            _spell("Murktide Regent", ["U"]),
            _spell("Thoughtseize", ["B"]),
        ]
        assert compute_deck_colors(cards) == "UB"

    def test_intersection_excludes_land_only_color(self):
        # Red is produced by a land but no nonland is red → excluded.
        cards = [_land("Volcanic Island", ["U", "R"]), _spell("Murktide Regent", ["U"])]
        assert compute_deck_colors(cards) == "U"

    def test_intersection_excludes_nonland_only_color(self):
        # Green nonland but no green source → excluded.
        cards = [_land("Island", ["U"]), _spell("Tarmogoyf", ["G"]), _spell("Brainstorm", ["U"])]
        assert compute_deck_colors(cards) == "U"

    def test_canonical_wubrg_order(self):
        cards = [_land("Dual", ["B", "U"]), _spell("a", ["B"]), _spell("b", ["U"])]
        assert compute_deck_colors(cards) == "UB"  # U before B

    def test_colorless(self):
        cards = [_land("Wasteland", ["C"]), Card(name="Thought-Knot Seer", type_line="Creature", colors=[])]
        assert compute_deck_colors(cards) == ""


class TestGuildName:
    @pytest.mark.parametrize(
        "colors,name",
        [("", "Colorless"), ("U", "Blue"), ("UB", "Dimir"), ("UBR", "Grixis"), ("WUBRG", "5c")],
    )
    def test_names(self, colors, name):
        assert guild_name(colors) == name
