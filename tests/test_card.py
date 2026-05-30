"""Card model — Scryfall field mapping, is_land, split faces, extra-key drop."""

from __future__ import annotations

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
