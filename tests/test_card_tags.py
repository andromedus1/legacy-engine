"""Legacy card tags — is_free_spell, mana_base_tags, staple_role."""

from __future__ import annotations

from legacy_engine.card_tags import is_free_spell, mana_base_tags, staple_role
from legacy_engine.models.card import Card


class TestIsFreeSpell:
    def test_force_of_will(self):
        fow = Card(
            name="Force of Will",
            type_line="Instant",
            oracle_text="You may pay 1 life and exile a blue card from your hand rather than pay this spell's mana cost.\nCounter target spell.",
        )
        assert is_free_spell(fow)

    def test_daze(self):
        daze = Card(
            name="Daze",
            type_line="Instant",
            oracle_text="You may return an Island you control to its owner's hand rather than pay this spell's mana cost.\nCounter target spell unless its controller pays {1}.",
        )
        assert is_free_spell(daze)

    def test_normal_spell_is_not_free(self):
        assert not is_free_spell(Card(name="Brainstorm", type_line="Instant", oracle_text="Draw three cards..."))


class TestManaBaseTags:
    def test_fetchland(self):
        delta = Card(
            name="Polluted Delta",
            type_line="Land",
            oracle_text="{T}, Pay 1 life, Sacrifice Polluted Delta: Search your library for an Island or Swamp card, put it onto the battlefield, then shuffle.",
        )
        assert "fetchland" in mana_base_tags(delta)

    def test_dual(self):
        sea = Card(name="Underground Sea", type_line="Land — Island Swamp", produced_mana=["U", "B"], oracle_text="")
        assert "dual" in mana_base_tags(sea)

    def test_fast_mana_land(self):
        tomb = Card(
            name="Ancient Tomb",
            type_line="Land",
            produced_mana=["C"],
            oracle_text="{T}: Add {C}{C}. Ancient Tomb deals 1 damage to you.",
        )
        assert "fast_mana_land" in mana_base_tags(tomb)

    def test_denial(self):
        waste = Card(
            name="Wasteland",
            type_line="Land",
            produced_mana=["C"],
            oracle_text="{T}: Add {C}.\n{T}, Sacrifice Wasteland: Destroy target nonbasic land.",
        )
        assert "denial" in mana_base_tags(waste)

    def test_nonland_has_no_tags(self):
        assert mana_base_tags(Card(name="Brainstorm", type_line="Instant")) == set()


class TestStapleRole:
    def test_known_staples(self):
        assert staple_role("Brainstorm") == "cantrip"
        assert staple_role("Force of Will") == "free_interaction"
        assert staple_role("Wasteland") == "land_denial"
        assert staple_role("Underground Sea") == "dual_land"

    def test_unknown_card(self):
        assert staple_role("Random Bulk Rare") is None
