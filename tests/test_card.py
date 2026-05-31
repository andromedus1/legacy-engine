"""Card model — Scryfall field mapping, is_land, split faces, extra-key drop, power/toughness."""

from __future__ import annotations

import pytest

from legacy_engine.models import Card as CardExport
from legacy_engine.models.card import Card


class TestCard:
    def test_from_scryfall_maps_fields(self):
        c = Card.from_scryfall(
            {
                "name": "Brainstorm",
                "mana_cost": "{U}",
                "cmc": 1.0,
                "type_line": "Instant",
                "colors": ["U"],
                "oracle_text": "Draw three cards, then put two cards from your hand on top of your library.",
                "set": "ice",  # unmodeled
                "rarity": "common",  # unmodeled
            }
        )
        assert c.name == "Brainstorm"
        assert c.cmc == 1.0
        assert c.colors == ["U"]
        assert not hasattr(c, "set")

    def test_is_land(self):
        assert Card(name="Volcanic Island", type_line="Land — Island Mountain").is_land
        assert not Card(name="Brainstorm", type_line="Instant").is_land

    def test_land_produced_mana_vs_colors(self):
        # A dual land has empty `colors` but produces colored mana.
        land = Card(name="Volcanic Island", type_line="Land — Island Mountain", produced_mana=["U", "R"])
        assert land.colors == []
        assert set(land.produced_mana) == {"U", "R"}

    def test_split_faces_preserved(self):
        c = Card.from_scryfall(
            {"name": "Fire // Ice", "layout": "split", "card_faces": [{"name": "Fire"}, {"name": "Ice"}]}
        )
        assert len(c.card_faces) == 2
        assert c.card_faces[0]["name"] == "Fire"

    def test_exported_from_models_package(self):
        assert CardExport is Card

    # ------------------------------------------------------------------
    # power / toughness fields + power_int()
    # ------------------------------------------------------------------

    def test_power_toughness_default_none(self):
        """power and toughness default to None when not provided."""
        c = Card(name="Brainstorm", type_line="Instant")
        assert c.power is None
        assert c.toughness is None

    def test_power_toughness_from_scryfall(self):
        """power and toughness auto-populate from Scryfall raw data via model_validate."""
        c = Card.from_scryfall(
            {
                "name": "Tarmogoyf",
                "type_line": "Creature — Lhurgoyf",
                "cmc": 2.0,
                "power": "*",
                "toughness": "*+1",
            }
        )
        assert c.power == "*"
        assert c.toughness == "*+1"

    def test_power_int_numeric_string(self):
        """Plain numeric power strings parse to int."""
        assert Card(name="X", type_line="Creature", power="2").power_int() == 2
        assert Card(name="X", type_line="Creature", power="0").power_int() == 0
        assert Card(name="X", type_line="Creature", power="10").power_int() == 10

    def test_power_int_star_returns_none(self):
        """Variable power strings ("*", "1+*") return None."""
        assert Card(name="X", type_line="Creature", power="*").power_int() is None
        assert Card(name="X", type_line="Creature", power="1+*").power_int() is None

    def test_power_int_none_returns_none(self):
        """power=None (non-creatures, Scryfall omits field) returns None."""
        assert Card(name="X", type_line="Instant", power=None).power_int() is None

    def test_power_int_non_numeric_string_returns_none(self):
        """Any non-integer string returns None without raising."""
        assert Card(name="X", type_line="Creature", power="X").power_int() is None

    @pytest.mark.parametrize(
        "power,expected",
        [
            ("2", 2),
            ("0", 0),
            ("*", None),
            ("1+*", None),
            (None, None),
        ],
    )
    def test_power_int_parametrized(self, power: str | None, expected: int | None):
        c = Card(name="X", type_line="Creature", power=power)
        assert c.power_int() == expected
