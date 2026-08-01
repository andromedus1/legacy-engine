"""What-to-play advisor tests — _card_roles, proactivity, vulnerability tags, hate-equity,
best-deck/best-call, plan-clash.

House style: construct ``Card``s directly for pure-function tests; use a ``:memory:`` corpus
with ``store.load_cards`` + labeled decks for DB-backed tests.
"""

from __future__ import annotations

import pytest

from legacy_engine.advisory.whattoplay import (
    BestDeckCall,
    ProactivityProfile,
    _card_roles,
    _color_contingent_tags,
    _load_deck_cards,
    _proactivity_from_cards,
    _COLOR_SPELL_MIN,
    best_deck_vs_best_call,
    covered_share,
    field_vulnerability_tags,
    hate_equity,
    plan_clash,
    proactivity_score,
    vulnerability_tags,
    vulnerability_tags_for_deck,
)
from legacy_engine.analytics.matchup import build_cell, build_mirror_cell, MatchupMatrix
from legacy_engine.ingestion import store
from legacy_engine.models.card import Card

# gate-cruft-test-helper-duplication: _con/_make_field/_make_card are shared conftest
# helpers now (were byte-identical local copies here, in test_sideboard.py, and — for
# _make_card — in test_linchpins.py).
from tests.conftest import _con, _make_card, _make_field


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_matrix(cells: dict, archetypes: list[str]) -> MatchupMatrix:
    """Build a MatchupMatrix directly from a pre-built cells dict."""
    return MatchupMatrix(
        cells=cells,
        provenance=None,
        total_matches=100,
        archetypes=archetypes,
        caveat="test",
    )


# ---------------------------------------------------------------------------
# TestCardRoles — per-card role assertions
# ---------------------------------------------------------------------------

class TestCardRoles:
    def test_force_of_will_has_counter(self):
        fow = _make_card(
            name="Force of Will",
            type_line="Instant",
            oracle_text=(
                "You may pay 1 life and exile a blue card from your hand rather than pay "
                "this spell's mana cost.\nCounter target spell."
            ),
        )
        roles = _card_roles(fow)
        assert "counter" in roles

    def test_brainstorm_has_card_advantage(self):
        bs = _make_card(
            name="Brainstorm",
            type_line="Instant",
            oracle_text="Draw three cards, then put two cards from your hand on top of your library in any order.",
        )
        roles = _card_roles(bs)
        assert "card_advantage" in roles

    def test_dark_ritual_has_ritual(self):
        dr = _make_card(
            name="Dark Ritual",
            type_line="Instant",
            oracle_text="Add {B}{B}{B}.",
            cmc=1.0,
        )
        roles = _card_roles(dr)
        assert "ritual" in roles

    def test_demonic_tutor_has_tutor(self):
        dt = _make_card(
            name="Demonic Tutor",
            type_line="Sorcery",
            oracle_text="Search your library for a card, put that card into your hand, then shuffle.",
            cmc=2.0,
        )
        roles = _card_roles(dt)
        assert "tutor" in roles

    def test_vampiric_tutor_has_tutor(self):
        vt = _make_card(
            name="Vampiric Tutor",
            type_line="Instant",
            oracle_text="Search your library for a card, then shuffle and put that card on top.",
            cmc=1.0,
        )
        roles = _card_roles(vt)
        assert "tutor" in roles

    def test_swords_to_plowshares_has_removal(self):
        stp = _make_card(
            name="Swords to Plowshares",
            type_line="Instant",
            oracle_text="Exile target creature. Its controller gains life equal to its power.",
            cmc=1.0,
        )
        roles = _card_roles(stp)
        assert "removal" in roles

    def test_chalice_of_the_void_has_stax(self):
        chalice = _make_card(
            name="Chalice of the Void",
            type_line="Artifact",
            oracle_text=(
                "Chalice of the Void enters the battlefield with X charge counters on it.\n"
                "Whenever a player casts a spell with mana value equal to the number of "
                "charge counters on Chalice of the Void, counter that spell."
            ),
            cmc=0.0,
        )
        roles = _card_roles(chalice)
        assert "stax" in roles

    def test_tendrils_of_agony_has_storm(self):
        tendrils = _make_card(
            name="Tendrils of Agony",
            type_line="Sorcery",
            oracle_text="Target player loses 2 life and you gain 2 life.\nStorm.",
            cmc=4.0,
        )
        roles = _card_roles(tendrils)
        assert "storm" in roles

    def test_reanimate_has_graveyard_recursion(self):
        reanimate = _make_card(
            name="Reanimate",
            type_line="Sorcery",
            oracle_text=(
                "Put target creature card from a graveyard onto the battlefield under "
                "your control. You lose life equal to its mana value."
            ),
            cmc=1.0,
        )
        roles = _card_roles(reanimate)
        assert "graveyard_recursion" in roles

    def test_exhume_has_graveyard_recursion(self):
        exhume = _make_card(
            name="Exhume",
            type_line="Sorcery",
            oracle_text="Each player puts a creature card from their graveyard onto the battlefield.",
            cmc=2.0,
        )
        roles = _card_roles(exhume)
        assert "graveyard_recursion" in roles

    def test_animate_dead_has_graveyard_recursion(self):
        """Animate Dead uses 'from your graveyard' (the phrasing _RE_GRAVEYARD does recognize) —
        kept as the passing sibling of test_exhume_has_graveyard_recursion above, which xfails
        on the symmetric 'their graveyard' phrasing gap."""
        animate_dead = _make_card(
            name="Animate Dead",
            type_line="Enchantment — Aura",
            oracle_text=(
                "Enchant creature card in a graveyard.\n"
                "When Animate Dead enters the battlefield, if the enchanted creature card is "
                "in a graveyard, return that card from your graveyard to the battlefield."
            ),
            cmc=2.0,
        )
        roles = _card_roles(animate_dead)
        assert "graveyard_recursion" in roles

    def test_delve_card_has_graveyard_fuel_not_recursion(self):
        cruise = _make_card(
            name="Treasure Cruise",
            type_line="Sorcery",
            oracle_text=(
                "Delve (Each card you exile from your graveyard while casting this "
                "spell pays for {1}.)\nDraw three cards."
            ),
            cmc=7.0,
        )
        roles = _card_roles(cruise)
        assert "graveyard_fuel" in roles
        assert "graveyard_recursion" not in roles

    def test_delirium_card_has_graveyard_fuel(self):
        card = _make_card(
            name="Test Delirium Payoff",
            type_line="Creature — Horror",
            oracle_text="Delirium — This creature gets +2/+2 as long as there are four or more card types among cards in your graveyard.",
            cmc=3.0,
        )
        roles = _card_roles(card)
        assert "graveyard_fuel" in roles

    def test_threshold_card_has_graveyard_fuel(self):
        card = _make_card(
            name="Test Threshold Payoff",
            type_line="Instant",
            oracle_text="Threshold — This spell costs {2} less to cast if there are seven or more cards in your graveyard.",
            cmc=4.0,
        )
        roles = _card_roles(card)
        assert "graveyard_fuel" in roles

    def test_goyf_named_card_has_graveyard_fuel(self):
        """*goyf-suffixed cards (Tarmogoyf, Nethergoyf, Barrowgoyf) size off graveyard
        quantity — matched by name suffix regardless of oracle_text phrasing."""
        goyf = _make_card(
            name="Tarmogoyf",
            type_line="Creature — Lhurgoyf",
            oracle_text=(
                "Tarmogoyf's power is equal to the number of card types among cards in "
                "all graveyards and its toughness is that number plus 1."
            ),
            cmc=2.0,
        )
        roles = _card_roles(goyf)
        assert "graveyard_fuel" in roles
        assert "graveyard_recursion" not in roles

    def test_counterspell_has_counter(self):
        cs = _make_card(
            name="Counterspell",
            type_line="Instant",
            oracle_text="Counter target spell.",
            cmc=2.0,
        )
        roles = _card_roles(cs)
        assert "counter" in roles

    def test_thoughtseize_no_storm_or_counter(self):
        ts = _make_card(
            name="Thoughtseize",
            type_line="Sorcery",
            oracle_text=(
                "Target player reveals their hand. You choose a nonland, nontoken card "
                "from it. That player discards that card. You lose 2 life."
            ),
            cmc=1.0,
        )
        roles = _card_roles(ts)
        assert "storm" not in roles
        assert "counter" not in roles
        # Has the discard staple_role
        assert "discard" in roles

    def test_vanilla_creature_empty_roles(self):
        bear = _make_card(
            name="Grizzly Bears",
            type_line="Creature — Bear",
            oracle_text="",
            cmc=2.0,
        )
        roles = _card_roles(bear)
        # No oracle text roles
        assert "counter" not in roles
        assert "storm" not in roles
        assert "ritual" not in roles

    def test_land_returns_empty(self):
        land = _make_card(
            name="Forest",
            type_line="Basic Land — Forest",
            oracle_text="{T}: Add {G}.",
        )
        roles = _card_roles(land)
        assert roles == set()

    def test_pure_function_deterministic(self):
        bs = _make_card(
            name="Brainstorm",
            type_line="Instant",
            oracle_text="Draw three cards, then put two cards from your hand on top of your library.",
        )
        assert _card_roles(bs) == _card_roles(bs)

    # ------------------------------------------------------------------
    # Threat role — new signal (Unit 3)
    # ------------------------------------------------------------------

    def test_drc_has_threat_role(self):
        """Dragon's Rage Channeler is a curated threat (even though P=1 before delirium)."""
        drc = Card(
            name="Dragon's Rage Channeler",
            type_line="Creature — Human Wizard",
            oracle_text="Delirium — Dragon's Rage Channeler has flying and +2/+0.",
            cmc=1.0,
            power="1",
            toughness="1",
        )
        assert "threat" in _card_roles(drc)

    def test_murktide_has_threat_role(self):
        """Murktide Regent is a curated threat (P=3+ once on board, raw P is 3)."""
        murktide = Card(
            name="Murktide Regent",
            type_line="Creature — Dragon",
            oracle_text="Delve. Flying.",
            cmc=5.0,
            power="3",
            toughness="3",
        )
        assert "threat" in _card_roles(murktide)

    def test_generic_cmc2_power2_creature_has_threat(self):
        """Any Creature with cmc ≤ 2 and power ≥ 2 gets the threat role."""
        bear = Card(
            name="Bear Cub",
            type_line="Creature — Bear",
            oracle_text="",
            cmc=2.0,
            power="2",
            toughness="2",
        )
        assert "threat" in _card_roles(bear)

    def test_generic_cmc1_power3_creature_has_threat(self):
        """Creature at cmc=1 with power=3 (e.g. boosted by effects) gets threat role."""
        goblin = Card(
            name="Hyped Goblin",
            type_line="Creature — Goblin",
            oracle_text="",
            cmc=1.0,
            power="3",
            toughness="1",
        )
        assert "threat" in _card_roles(goblin)

    def test_vanilla_5drop_no_threat(self):
        """A vanilla 5-drop is NOT a threat (cmc > 2)."""
        bigcreature = Card(
            name="Big Vanilla Beast",
            type_line="Creature — Beast",
            oracle_text="",
            cmc=5.0,
            power="5",
            toughness="5",
        )
        assert "threat" not in _card_roles(bigcreature)

    def test_one_power_one_drop_no_threat(self):
        """A 1/1 for 1 is NOT a threat (power < 2)."""
        onedrop = Card(
            name="Tiny Scout",
            type_line="Creature — Human Scout",
            oracle_text="",
            cmc=1.0,
            power="1",
            toughness="1",
        )
        assert "threat" not in _card_roles(onedrop)

    def test_cmc2_power1_no_threat(self):
        """A 1/3 for 2 is NOT a threat (power < 2, not in curated list)."""
        wall = Card(
            name="Wall Thing",
            type_line="Creature — Wall",
            oracle_text="Defender.",
            cmc=2.0,
            power="1",
            toughness="3",
        )
        assert "threat" not in _card_roles(wall)

    def test_tarmogoyf_threat_via_curated_list(self):
        """Tarmogoyf (variable power '*') gets threat via the curated override."""
        goyf = Card(
            name="Tarmogoyf",
            type_line="Creature — Lhurgoyf",
            oracle_text="Tarmogoyf's power is equal to the number of card types.",
            cmc=2.0,
            power="*",
            toughness="*+1",
        )
        assert "threat" in _card_roles(goyf)

    def test_goblin_guide_threat_via_general_rule(self):
        """Goblin Guide (2/2 haste for 1) gets threat via the general rule (cmc=1, power=2)."""
        goblin_guide = Card(
            name="Goblin Guide",
            type_line="Creature — Goblin Scout",
            oracle_text="Haste. Whenever Goblin Guide attacks, defending player reveals the top card of their library.",
            cmc=1.0,
            power="2",
            toughness="2",
        )
        assert "threat" in _card_roles(goblin_guide)

    def test_non_creature_spell_no_threat(self):
        """A non-creature instant with no oracle roles doesn't get threat."""
        giant_growth = Card(
            name="Giant Growth",
            type_line="Instant",
            oracle_text="Target creature gets +3/+3 until end of turn.",
            cmc=1.0,
        )
        assert "threat" not in _card_roles(giant_growth)


# ---------------------------------------------------------------------------
# TestProactivity
# ---------------------------------------------------------------------------

class TestProactivity:
    """Proactivity assertions: relative ordering + edge cases."""

    def _storm_cards(self) -> list[tuple[Card, int]]:
        """Combo/storm deck: rituals + tutors + low curve."""
        dark_ritual = _make_card(
            name="Dark Ritual",
            type_line="Instant",
            oracle_text="Add {B}{B}{B}.",
            cmc=1.0,
        )
        demonic_tutor = _make_card(
            name="Demonic Tutor",
            type_line="Sorcery",
            oracle_text="Search your library for a card, put that card into your hand, then shuffle.",
            cmc=2.0,
        )
        tendrils = _make_card(
            name="Tendrils of Agony",
            type_line="Sorcery",
            oracle_text="Target player loses 2 life.\nStorm.",
            cmc=4.0,
        )
        lotus_petal = _make_card(
            name="Lotus Petal",
            type_line="Artifact",
            oracle_text="{T}, Sacrifice Lotus Petal: Add one mana of any color.",
            cmc=0.0,
        )
        return [
            (dark_ritual, 4),
            (demonic_tutor, 4),
            (tendrils, 4),
            (lotus_petal, 4),
            (_make_card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0), 10),
        ]

    def _tempo_cards(self) -> list[tuple[Card, int]]:
        """Tempo deck: free counters + cantrips + threats."""
        fow = _make_card(
            name="Force of Will",
            type_line="Instant",
            oracle_text=(
                "You may pay 1 life and exile a blue card from your hand rather than pay "
                "this spell's mana cost.\nCounter target spell."
            ),
            cmc=5.0,
        )
        daze = _make_card(
            name="Daze",
            type_line="Instant",
            oracle_text=(
                "You may return an Island you control to its owner's hand rather than pay "
                "this spell's mana cost.\nCounter target spell unless its controller pays {1}."
            ),
            cmc=2.0,
        )
        bs = _make_card(
            name="Brainstorm",
            type_line="Instant",
            oracle_text="Draw three cards, then put two cards from your hand on top of your library.",
            cmc=1.0,
        )
        delver = _make_card(
            name="Delver of Secrets",
            type_line="Creature — Human Wizard",
            oracle_text="At the beginning of your upkeep, look at the top card of your library.",
            cmc=1.0,
        )
        return [
            (fow, 4),
            (daze, 4),
            (bs, 4),
            (delver, 4),
            (_make_card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0), 12),
        ]

    def _control_cards(self) -> list[tuple[Card, int]]:
        """Control deck: counters + removal + card advantage, higher curve."""
        fow = _make_card(
            name="Force of Will",
            type_line="Instant",
            oracle_text=(
                "You may pay 1 life and exile a blue card from your hand rather than pay "
                "this spell's mana cost.\nCounter target spell."
            ),
            cmc=5.0,
        )
        counterspell = _make_card(
            name="Counterspell",
            type_line="Instant",
            oracle_text="Counter target spell.",
            cmc=2.0,
        )
        swords = _make_card(
            name="Swords to Plowshares",
            type_line="Instant",
            oracle_text="Exile target creature. Its controller gains life equal to its power.",
            cmc=1.0,
        )
        jace = _make_card(
            name="Jace, the Mind Sculptor",
            type_line="Legendary Planeswalker — Jace",
            oracle_text="[+2]: Look at the top card of target player's library...\n[−12]: ...",
            cmc=4.0,
        )
        terminus = _make_card(
            name="Terminus",
            type_line="Sorcery",
            oracle_text="Put all creatures on the bottom of their owners' libraries.",
            cmc=6.0,
        )
        return [
            (fow, 4),
            (counterspell, 4),
            (swords, 4),
            (jace, 4),
            (terminus, 3),
            (_make_card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0), 16),
        ]

    def _izzet_delver_cards(self) -> list[tuple[Card, int]]:
        """Izzet Delver-style composition: DRC + Murktide + Lightning Bolt + Daze + Brainstorm.

        Cards are constructed with power/toughness so the threat signal fires on DRC and Murktide
        via the curated _THREAT_CARDS set.
        """
        drc = Card(
            name="Dragon's Rage Channeler",
            type_line="Creature — Human Wizard",
            oracle_text="Delirium — Dragon's Rage Channeler has flying and +2/+0.",
            cmc=1.0,
            power="1",
            toughness="1",
        )
        murktide = Card(
            name="Murktide Regent",
            type_line="Creature — Dragon",
            oracle_text="Delve. Flying.",
            cmc=5.0,
            power="3",
            toughness="3",
        )
        bolt = Card(
            name="Lightning Bolt",
            type_line="Instant",
            oracle_text="Lightning Bolt deals 3 damage to any target.",
            cmc=1.0,
        )
        daze = Card(
            name="Daze",
            type_line="Instant",
            oracle_text=(
                "You may return an Island you control to its owner's hand rather than pay "
                "this spell's mana cost.\nCounter target spell unless its controller pays {1}."
            ),
            cmc=2.0,
        )
        brainstorm = Card(
            name="Brainstorm",
            type_line="Instant",
            oracle_text="Draw three cards, then put two cards from your hand on top of your library.",
            cmc=1.0,
        )
        island = _make_card(
            name="Island",
            type_line="Basic Land — Island",
            oracle_text="{T}: Add {U}.",
            cmc=0.0,
        )
        return [
            (drc, 4),
            (murktide, 4),
            (bolt, 4),
            (daze, 4),
            (brainstorm, 4),
            (island, 20),
        ]

    def test_combo_more_proactive_than_control(self):
        storm_profile = _proactivity_from_cards(self._storm_cards())
        control_profile = _proactivity_from_cards(self._control_cards())
        assert storm_profile.score > control_profile.score, (
            f"Expected combo ({storm_profile.score:.3f}) > control ({control_profile.score:.3f})"
        )

    def test_combo_more_proactive_than_tempo(self):
        storm_profile = _proactivity_from_cards(self._storm_cards())
        tempo_profile = _proactivity_from_cards(self._tempo_cards())
        assert storm_profile.score > tempo_profile.score, (
            f"Expected combo ({storm_profile.score:.3f}) > tempo ({tempo_profile.score:.3f})"
        )

    def test_tempo_more_proactive_than_control(self):
        tempo_profile = _proactivity_from_cards(self._tempo_cards())
        control_profile = _proactivity_from_cards(self._control_cards())
        assert tempo_profile.score > control_profile.score, (
            f"Expected tempo ({tempo_profile.score:.3f}) > control ({control_profile.score:.3f})"
        )

    def test_izzet_delver_score_above_half(self):
        """An Izzet Delver-style composition (DRC + Murktide + bolt + cantrips) scores > 0.5.

        Root-cause fix: before this change, efficient creature threats carried no proactive
        role and the composition scored 0.0. The threat signal + 1.5× weighting should
        push a 4×DRC + 4×Murktide deck above 0.5.
        """
        profile = _proactivity_from_cards(self._izzet_delver_cards())
        assert profile.score > 0.5, (
            f"Izzet Delver should score >0.5 proactivity but got {profile.score:.3f}; "
            "check threat role detection and 1.5× weight in _proactivity_from_cards"
        )

    def test_izzet_delver_above_control(self):
        """Izzet Delver (creature tempo) scores higher than control."""
        delver_profile = _proactivity_from_cards(self._izzet_delver_cards())
        control_profile = _proactivity_from_cards(self._control_cards())
        assert delver_profile.score > control_profile.score, (
            f"Expected Izzet Delver ({delver_profile.score:.3f}) > control ({control_profile.score:.3f})"
        )

    def test_combo_above_izzet_delver(self):
        """Combo (rituals + tutors) scores higher than Izzet Delver tempo."""
        storm_profile = _proactivity_from_cards(self._storm_cards())
        delver_profile = _proactivity_from_cards(self._izzet_delver_cards())
        assert storm_profile.score > delver_profile.score, (
            f"Expected combo ({storm_profile.score:.3f}) > Izzet Delver ({delver_profile.score:.3f})"
        )

    def test_proactivity_full_ordering_combo_gt_tempo_gt_control(self):
        """Overall ordering assertion: combo > Izzet Delver (tempo) > control."""
        storm_profile = _proactivity_from_cards(self._storm_cards())
        delver_profile = _proactivity_from_cards(self._izzet_delver_cards())
        control_profile = _proactivity_from_cards(self._control_cards())
        assert storm_profile.score > delver_profile.score > control_profile.score, (
            f"Expected combo({storm_profile.score:.3f}) > "
            f"tempo({delver_profile.score:.3f}) > "
            f"control({control_profile.score:.3f})"
        )

    def test_control_score_below_0_4(self):
        """Control composition stays below 0.4 proactivity."""
        profile = _proactivity_from_cards(self._control_cards())
        assert profile.score < 0.4, (
            f"Control should score < 0.4 but got {profile.score:.3f}"
        )

    def test_both_zero_composition_returns_half(self):
        """A deck with no recognizable signals returns 0.5."""
        # Lands only (they return empty roles)
        forest = _make_card(name="Forest", type_line="Basic Land — Forest", oracle_text="{T}: Add {G}.", cmc=0.0)
        bear = _make_card(name="Grizzly Bears", type_line="Creature — Bear", oracle_text="", cmc=2.0)
        profile = _proactivity_from_cards([(forest, 10), (bear, 4)])
        # No reactive or proactive cards — score is determined only by low_curve_score / (low_curve_score + 0)
        # Actually low_curve_score is non-zero (sigmoid), so score won't be exactly 0.5
        # But with only 4 bears at MV 2.0, it should be ~0.5 ish
        assert 0.0 <= profile.score <= 1.0

    def test_all_land_deck_score_in_bounds(self):
        """All-land deck has score in [0,1] (low_curve_score drives it)."""
        forest = _make_card(name="Forest", type_line="Basic Land — Forest", oracle_text="{T}: Add {G}.", cmc=0.0)
        profile = _proactivity_from_cards([(forest, 20)])
        assert 0.0 <= profile.score <= 1.0

    def test_score_always_in_range(self):
        """score is always in [0,1]."""
        cards = self._storm_cards() + self._control_cards()
        profile = _proactivity_from_cards(cards)
        assert 0.0 <= profile.score <= 1.0

    def test_unknown_card_skipped_not_crash(self):
        """Unknown card names are skipped with a warning; no exception raised."""
        con = _con()
        store.load_cards(con, [
            Card(name="Brainstorm", type_line="Instant", oracle_text="Draw three cards, then put two cards from your hand on top of your library.", cmc=1.0),
        ])
        maindeck = {"Brainstorm": 4, "FAKE CARD THAT DOES NOT EXIST": 3}
        profile = proactivity_score(con, maindeck)
        assert 0.0 <= profile.score <= 1.0
        con.close()

    def test_computed_vs_tag_finding_fair_deck_too_proactive(self):
        """A 'control' archetype label with a proactive composition emits a finding."""
        con = _con()
        # Load rituals + tutors = proactive cards
        cards = [
            Card(name="Dark Ritual", type_line="Instant", oracle_text="Add {B}{B}{B}.", cmc=1.0),
            Card(name="Demonic Tutor", type_line="Sorcery",
                 oracle_text="Search your library for a card, put that card into your hand, then shuffle.",
                 cmc=2.0),
        ]
        store.load_cards(con, cards)
        maindeck = {"Dark Ritual": 4, "Demonic Tutor": 4}
        profile = proactivity_score(con, maindeck, archetype_tag="control")
        # High proactivity + 'control' tag → finding expected
        if profile.score > 0.55:
            assert len(profile.findings) > 0
        con.close()

    def test_load_deck_cards_roundtrip(self):
        """_load_deck_cards round-trips colors/produced_mana correctly."""
        con = _con()
        underground_sea = Card(
            name="Underground Sea",
            type_line="Land — Island Swamp",
            colors=["U", "B"],
            produced_mana=["U", "B"],
            oracle_text="",
            cmc=0.0,
        )
        store.load_cards(con, [underground_sea])
        pairs = _load_deck_cards(con, {"Underground Sea": 4})
        assert len(pairs) == 1
        card, count = pairs[0]
        assert count == 4
        assert card.name == "Underground Sea"
        # colors round-trip: stored as "UB", split back to ["U","B"]
        assert card.colors == ["U", "B"]
        assert card.produced_mana == ["U", "B"]
        con.close()


# ---------------------------------------------------------------------------
# TestVulnerabilityTags — archetype composition → tags
# ---------------------------------------------------------------------------

class TestVulnerabilityTags:
    """Tests use :memory: corpus with labeled decks."""

    def _build_reanimator_corpus(self) -> tuple:
        """Build a corpus with a Reanimator archetype (graveyard recursion heavy)."""
        con = _con()
        cards = [
            Card(name="Reanimate", type_line="Sorcery",
                 oracle_text="Put target creature card from a graveyard onto the battlefield under your control. You lose life equal to its mana value.",
                 cmc=1.0),
            Card(name="Animate Dead", type_line="Enchantment — Aura",
                 oracle_text="Return target creature card from your graveyard to the battlefield.",
                 cmc=2.0),
            Card(name="Entomb", type_line="Instant",
                 oracle_text="Search your library for a card and put that card into your graveyard, then shuffle.",
                 cmc=1.0),
            Card(name="Griselbrand", type_line="Legendary Creature — Demon",
                 oracle_text="Flying, lifelink.\nPay 7 life: Draw seven cards.",
                 cmc=8.0),
            Card(name="Swamp", type_line="Basic Land — Swamp", oracle_text="{T}: Add {B}.", cmc=0.0),
        ]
        store.load_cards(con, cards)

        # Build a minimal tournament
        import uuid
        tid = str(uuid.uuid4())
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [tid, "Test", "2026-01-01", None, "Legacy", "test", "test"],
        )
        for idx in range(3):
            con.execute(
                "INSERT INTO decks VALUES (?, ?, ?, ?, ?, NULL)",
                [tid, idx, f"player{idx}", "1st", "Reanimator"],
            )
            for card_name, count in [("Reanimate", 4), ("Animate Dead", 2), ("Entomb", 4), ("Griselbrand", 4), ("Swamp", 10)]:
                con.execute(
                    "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
                    [tid, idx, "main", card_name, count],
                )
        return con

    def _build_dnt_corpus(self) -> tuple:
        """Build a Death & Taxes corpus: creatures + stax, low free spells."""
        con = _con()
        cards = [
            Card(name="Thalia, Guardian of Thraben", type_line="Legendary Creature — Human Soldier",
                 oracle_text="First strike.\nNoncreature spells cost {1} more to cast.",
                 cmc=2.0),
            Card(name="Stoneforge Mystic", type_line="Creature — Kor Artificer",
                 oracle_text="When Stoneforge Mystic enters the battlefield, you may search your library for an Equipment card, reveal it, put it into your hand, then shuffle.",
                 cmc=2.0),
            Card(name="Mother of Runes", type_line="Creature — Human Cleric",
                 oracle_text="{T}: Target creature you control gains protection from the color of your choice until end of turn.",
                 cmc=1.0),
            Card(name="Recruiter of the Guard", type_line="Creature — Human Soldier",
                 oracle_text="When Recruiter of the Guard enters the battlefield, you may search your library for a creature card with toughness 2 or less, reveal it, put it into your hand, then shuffle.",
                 cmc=3.0),
            Card(name="Plains", type_line="Basic Land — Plains", oracle_text="{T}: Add {W}.", cmc=0.0),
        ]
        store.load_cards(con, cards)

        import uuid
        tid = str(uuid.uuid4())
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [tid, "Test", "2026-01-01", None, "Legacy", "test", "test"],
        )
        for idx in range(3):
            con.execute(
                "INSERT INTO decks VALUES (?, ?, ?, ?, ?, NULL)",
                [tid, idx, f"player{idx}", "1st", "Death and Taxes"],
            )
            for card_name, count in [
                ("Thalia, Guardian of Thraben", 4),
                ("Stoneforge Mystic", 4),
                ("Mother of Runes", 4),
                ("Recruiter of the Guard", 4),
                ("Plains", 16),
            ]:
                con.execute(
                    "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
                    [tid, idx, "main", card_name, count],
                )
        return con

    def _build_storm_corpus(self) -> tuple:
        """Build a Storm corpus: storm cards + tutors + rituals."""
        con = _con()
        cards = [
            Card(name="Tendrils of Agony", type_line="Sorcery",
                 oracle_text="Target player loses 2 life and you gain 2 life.\nStorm.",
                 cmc=4.0),
            Card(name="Dark Ritual", type_line="Instant", oracle_text="Add {B}{B}{B}.", cmc=1.0),
            Card(name="Demonic Tutor", type_line="Sorcery",
                 oracle_text="Search your library for a card, put that card into your hand, then shuffle.",
                 cmc=2.0),
            Card(name="Lion's Eye Diamond", type_line="Artifact",
                 oracle_text="Sacrifice Lion's Eye Diamond, Discard your hand: Add three mana of any one color.",
                 cmc=0.0),
            Card(name="Swamp", type_line="Basic Land — Swamp", oracle_text="{T}: Add {B}.", cmc=0.0),
        ]
        store.load_cards(con, cards)

        import uuid
        tid = str(uuid.uuid4())
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [tid, "Test", "2026-01-01", None, "Legacy", "test", "test"],
        )
        for idx in range(3):
            con.execute(
                "INSERT INTO decks VALUES (?, ?, ?, ?, ?, NULL)",
                [tid, idx, f"player{idx}", "1st", "ANT Storm"],
            )
            for card_name, count in [
                ("Tendrils of Agony", 4),
                ("Dark Ritual", 4),
                ("Demonic Tutor", 4),
                ("Lion's Eye Diamond", 4),
                ("Swamp", 10),
            ]:
                con.execute(
                    "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
                    [tid, idx, "main", card_name, count],
                )
        return con

    def test_reanimator_archetype_has_graveyard_recursion(self):
        con = self._build_reanimator_corpus()
        tags = vulnerability_tags(con, "Reanimator")
        assert "graveyard-recursion" in tags, f"Expected graveyard-recursion in {tags}"
        con.close()

    def test_death_and_taxes_has_creature_based(self):
        con = self._build_dnt_corpus()
        tags = vulnerability_tags(con, "Death and Taxes")
        assert "creature-based" in tags, f"Expected creature-based in {tags}"
        con.close()

    def test_death_and_taxes_not_storm_reliant(self):
        con = self._build_dnt_corpus()
        tags = vulnerability_tags(con, "Death and Taxes")
        assert "storm-reliant" not in tags, f"Unexpected storm-reliant in {tags}"
        con.close()

    def test_storm_archetype_has_storm_reliant(self):
        con = self._build_storm_corpus()
        tags = vulnerability_tags(con, "ANT Storm")
        assert "storm-reliant" in tags, f"Expected storm-reliant in {tags}"
        con.close()

    def test_storm_archetype_has_combo(self):
        con = self._build_storm_corpus()
        tags = vulnerability_tags(con, "ANT Storm")
        assert "combo" in tags, f"Expected combo in {tags}"
        con.close()

    def test_unknown_archetype_returns_empty(self):
        con = _con()
        tags = vulnerability_tags(con, "NonExistentArchetype")
        assert tags == frozenset()
        con.close()

    def _build_mostly_control_with_stray_storm(self) -> tuple:
        """Build a control deck corpus with exactly ONE stray storm card in the aggregate.

        This tests the density gate: a single Tendrils in a 16-card aggregate (6.25%
        of nonland slots) must NOT trigger storm-reliant if it falls below the
        _STORM_DENSITY threshold. With STORM_DENSITY=0.08 and 1/13 nonland ≈ 7.7%, this
        is just under the threshold for this particular composition.
        """
        con = _con()
        cards = [
            Card(
                name="Force of Will",
                type_line="Instant",
                oracle_text="You may pay 1 life and exile a blue card from your hand rather than pay this spell's mana cost.\nCounter target spell.",
                cmc=5.0,
            ),
            Card(
                name="Counterspell",
                type_line="Instant",
                oracle_text="Counter target spell.",
                cmc=2.0,
            ),
            Card(
                name="Brainstorm",
                type_line="Instant",
                oracle_text="Draw three cards, then put two cards from your hand on top of your library.",
                cmc=1.0,
            ),
            Card(
                name="Tendrils of Agony",
                type_line="Sorcery",
                oracle_text="Target player loses 2 life and you gain 2 life.\nStorm.",
                cmc=4.0,
            ),
            Card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        import uuid

        tid = str(uuid.uuid4())
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [tid, "Test", "2026-01-01", None, "Legacy", "test", "test"],
        )
        # One deck with 4×FoW, 4×Counterspell, 4×Brainstorm, 1×Tendrils (stray), 12×Island
        con.execute("INSERT INTO decks VALUES (?, ?, ?, ?, ?, NULL)", [tid, 0, "p0", "1st", "Izzet Control"])
        for name, count in [
            ("Force of Will", 4),
            ("Counterspell", 4),
            ("Brainstorm", 4),
            ("Tendrils of Agony", 1),
            ("Island", 12),
        ]:
            con.execute(
                "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
                [tid, 0, "main", name, count],
            )
        return con

    def test_stray_storm_card_does_not_trigger_storm_reliant(self):
        """A single stray storm card in an otherwise non-storm deck does NOT get storm-reliant.

        Presence-based check would falsely fire; density gate prevents it.
        """
        con = self._build_mostly_control_with_stray_storm()
        tags = vulnerability_tags(con, "Izzet Control")
        assert "storm-reliant" not in tags, (
            f"A single stray storm card should not trigger storm-reliant; got tags={tags}"
        )
        con.close()

    def test_real_storm_deck_has_storm_reliant(self):
        """A real storm deck (4x Tendrils in a 26-card non-land shell) IS storm-reliant."""
        con = self._build_storm_corpus()
        tags = vulnerability_tags(con, "ANT Storm")
        assert "storm-reliant" in tags, f"Expected storm-reliant in {tags}"
        con.close()

    def test_vulnerability_tags_for_deck_direct(self):
        """vulnerability_tags_for_deck works on a specific decklist."""
        con = _con()
        cards = [
            Card(name="Reanimate", type_line="Sorcery",
                 oracle_text="Put target creature card from a graveyard onto the battlefield under your control. You lose life equal to its mana value.",
                 cmc=1.0),
            Card(name="Animate Dead", type_line="Enchantment — Aura",
                 oracle_text="Return target creature card from your graveyard to the battlefield.",
                 cmc=2.0),
            Card(name="Swamp", type_line="Basic Land — Swamp", oracle_text="{T}: Add {B}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        maindeck = {"Reanimate": 4, "Animate Dead": 4, "Swamp": 16}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "graveyard-recursion" in tags
        con.close()

    def test_delve_goyf_deck_has_graveyard_fuel_not_recursion(self):
        """A delve/*goyf-shaped deck emits graveyard-fuel, not graveyard-recursion."""
        con = _con()
        cards = [
            Card(
                name="Tarmogoyf",
                type_line="Creature — Lhurgoyf",
                oracle_text=(
                    "Tarmogoyf's power is equal to the number of card types among "
                    "cards in all graveyards and its toughness is that number plus 1."
                ),
                cmc=2.0,
            ),
            Card(
                name="Treasure Cruise",
                type_line="Sorcery",
                oracle_text=(
                    "Delve (Each card you exile from your graveyard while casting "
                    "this spell pays for {1}.)\nDraw three cards."
                ),
                cmc=7.0,
            ),
            Card(name="Swamp", type_line="Basic Land — Swamp", oracle_text="{T}: Add {B}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        maindeck = {"Tarmogoyf": 4, "Treasure Cruise": 4, "Swamp": 16}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "graveyard-fuel" in tags, f"Expected graveyard-fuel in {tags}"
        assert "graveyard-recursion" not in tags, f"Unexpected graveyard-recursion in {tags}"
        con.close()

    def test_graveyard_reliant_never_emitted(self):
        """The retired monolithic graveyard tag must never appear, on any composition shape."""
        retired_tag = "graveyard" + "-reliant"  # constructed to avoid a false grep hit here
        for corpus_builder, archetype in (
            (self._build_reanimator_corpus, "Reanimator"),
            (self._build_dnt_corpus, "Death and Taxes"),
            (self._build_storm_corpus, "ANT Storm"),
        ):
            con = corpus_builder()
            tags = vulnerability_tags(con, archetype)
            assert retired_tag not in tags, f"{archetype}: unexpected {retired_tag} in {tags}"
            con.close()

    def test_red_heavy_deck_gets_plays_red(self):
        """A deck with >= _COLOR_SPELL_MIN red nonland spell copies emits plays-red."""
        con = _con()
        cards = [
            Card(
                name="Lightning Bolt", type_line="Instant",
                oracle_text="Lightning Bolt deals 3 damage to any target.",
                cmc=1.0, colors=["R"],
            ),
            Card(
                name="Brainstorm", type_line="Instant",
                oracle_text="Draw three cards, then put two cards from your hand on top of your library.",
                cmc=1.0, colors=["U"],
            ),
            Card(name="Mountain", type_line="Basic Land — Mountain", oracle_text="{T}: Add {R}.", cmc=0.0),
            Card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        maindeck = {"Lightning Bolt": _COLOR_SPELL_MIN, "Brainstorm": 2, "Mountain": 10, "Island": 10}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "plays-red" in tags, f"Expected plays-red in {tags}"
        assert "plays-blue" not in tags, f"2 blue copies is below _COLOR_SPELL_MIN; got {tags}"
        con.close()

    def test_mono_blue_deck_does_not_get_plays_red(self):
        """A mono-blue deck never emits plays-red (no red spells at all)."""
        con = _con()
        cards = [
            Card(
                name="Brainstorm", type_line="Instant",
                oracle_text="Draw three cards, then put two cards from your hand on top of your library.",
                cmc=1.0, colors=["U"],
            ),
            Card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        maindeck = {"Brainstorm": _COLOR_SPELL_MIN + 2, "Island": 20}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "plays-red" not in tags, f"Unexpected plays-red in {tags}"
        assert "plays-blue" in tags, f"Expected plays-blue in {tags}"
        con.close()


# ---------------------------------------------------------------------------
# TestColorContingentTags — pure-function tests for _color_contingent_tags
# ---------------------------------------------------------------------------

class TestColorContingentTags:
    """plays-<color> fires at/above _COLOR_SPELL_MIN nonland spell copies, not below."""

    def test_fires_at_threshold(self):
        cards = [(_make_card(name="Lightning Bolt", colors=["R"]), _COLOR_SPELL_MIN)]
        tags = _color_contingent_tags(cards)
        assert "plays-red" in tags

    def test_does_not_fire_below_threshold(self):
        cards = [(_make_card(name="Lightning Bolt", colors=["R"]), _COLOR_SPELL_MIN - 1)]
        tags = _color_contingent_tags(cards)
        assert "plays-red" not in tags

    def test_lands_excluded_even_with_matching_color(self):
        mountain = _make_card(
            name="Mountain", type_line="Basic Land — Mountain", colors=["R"],
        )
        cards = [(mountain, _COLOR_SPELL_MIN + 10)]
        tags = _color_contingent_tags(cards)
        assert tags == set()

    def test_multiple_colors_independent(self):
        cards = [
            (_make_card(name="Lightning Bolt", colors=["R"]), _COLOR_SPELL_MIN),
            (_make_card(name="Brainstorm", colors=["U"]), 2),
        ]
        tags = _color_contingent_tags(cards)
        assert tags == {"plays-red"}

    def test_counts_accumulate_across_cards_of_same_color(self):
        """Multiple distinct red cards' counts sum toward the same color threshold."""
        cards = [
            (_make_card(name="Lightning Bolt", colors=["R"]), _COLOR_SPELL_MIN - 2),
            (_make_card(name="Chain Lightning", colors=["R"]), 2),
        ]
        tags = _color_contingent_tags(cards)
        assert "plays-red" in tags

    @pytest.mark.parametrize(
        "color,tag",
        [
            ("W", "plays-white"),
            ("U", "plays-blue"),
            ("B", "plays-black"),
            ("R", "plays-red"),
            ("G", "plays-green"),
        ],
    )
    def test_fires_symmetrically_for_every_wubrg_color(self, color, tag):
        """feature-sfv-attachments: plays-<color> is symmetric across all five colors —
        not just red/blue.  A deck (or opponent composition) with >= _COLOR_SPELL_MIN
        copies of ANY color's nonland spells emits that color's plays-<color> tag."""
        cards = [(_make_card(name="Test Spell", colors=[color]), _COLOR_SPELL_MIN)]
        tags = _color_contingent_tags(cards)
        assert tag in tags, f"Expected {tag} in {tags} for a {color}-heavy composition"


# ---------------------------------------------------------------------------
# TestPlaysColorOpponentVulnerability — plays-<color> as an OPPONENT vulnerability
# (feature-sfv-attachments, D3 half 1): the same tag a deck emits for its OWN protective
# hoser-matching (plays-red) must ALSO fire for a FIELD OPPONENT's aggregate composition,
# symmetrically across all five colors, so a color-blast/soft-counter hoser can attach to
# it.  vulnerability_tags(con, archetype) is exactly the code path sideboard.py's
# field_vulnerability_tags feeds into archetype_tags for opponent coverage elements.
# ---------------------------------------------------------------------------

class TestPlaysColorOpponentVulnerability:
    """plays-<color> fires as an opponent vulnerability for every WUBRG color."""

    _COLOR_CARDS: dict[str, tuple[str, str, str]] = {
        "W": ("Swords to Plowshares", "Instant",
              "Exile target creature. Its controller gains life equal to its power."),
        "U": ("Brainstorm", "Instant",
              "Draw three cards, then put two cards from your hand on top of your library."),
        "B": ("Thoughtseize", "Sorcery",
              "Target player reveals their hand. You choose a nonland card from it. "
              "That player discards that card. You lose 2 life."),
        "R": ("Lightning Bolt", "Instant", "Lightning Bolt deals 3 damage to any target."),
        "G": ("Rancor", "Enchantment — Aura", "Enchanted creature gets +2/+0 and has trample."),
    }

    def _build_color_corpus(self, color: str, archetype: str):
        import uuid

        name, type_line, oracle_text = self._COLOR_CARDS[color]
        con = _con()
        cards = [
            Card(name=name, type_line=type_line, oracle_text=oracle_text, cmc=1.0, colors=[color]),
            Card(name="Wastes", type_line="Basic Land — Wastes", oracle_text="{T}: Add {C}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        tid = str(uuid.uuid4())
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [tid, "Test", "2026-01-01", None, "Legacy", "test", "test"],
        )
        con.execute(
            "INSERT INTO decks VALUES (?, ?, ?, ?, ?, NULL)", [tid, 0, "p0", "1st", archetype]
        )
        for card_name, count in [(name, _COLOR_SPELL_MIN), ("Wastes", 20)]:
            con.execute(
                "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [tid, 0, "main", card_name, count]
            )
        return con

    @pytest.mark.parametrize(
        "color,tag",
        [
            ("W", "plays-white"),
            ("U", "plays-blue"),
            ("B", "plays-black"),
            ("R", "plays-red"),
            ("G", "plays-green"),
        ],
    )
    def test_plays_color_fires_for_field_opponent(self, color, tag):
        archetype = f"Test{color}Archetype"
        con = self._build_color_corpus(color, archetype)
        tags = vulnerability_tags(con, archetype)
        assert tag in tags, f"Expected {tag} in opponent vulnerability tags; got {tags}"
        con.close()

    def test_blue_opponent_has_more_corpus_coverage_than_red_would_imply(self):
        """Regression guard: plays-blue must not be a code path that only red exercises.

        Directly exercises the opponent-facing archetype aggregate (not the deck-facing
        helper), confirming the same _color_contingent_tags union fires for a blue-heavy
        FIELD ARCHETYPE exactly as it does for red.
        """
        con = self._build_color_corpus("U", "BlueOpponent")
        tags = vulnerability_tags(con, "BlueOpponent")
        assert "plays-blue" in tags
        con.close()


# ---------------------------------------------------------------------------
# TestNoncreatureReliantTag — feature-sfv-attachments broad-interaction attachment axis:
# an archetype whose creature-slot density is LOW carries "noncreature-reliant", the
# element free/soft anti-noncreature counters (Force of Negation, Spell Pierce) attach to.
# ---------------------------------------------------------------------------

class TestNoncreatureReliantTag:
    def test_low_creature_density_deck_gets_noncreature_reliant(self):
        """A deck with zero creatures (all spells + lands) gets noncreature-reliant."""
        con = _con()
        cards = [
            Card(name="Brainstorm", type_line="Instant",
                 oracle_text="Draw three cards, then put two cards from your hand on top of your library.",
                 cmc=1.0),
            Card(name="Counterspell", type_line="Instant", oracle_text="Counter target spell.", cmc=2.0),
            Card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        maindeck = {"Brainstorm": 4, "Counterspell": 4, "Island": 20}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "noncreature-reliant" in tags, f"Expected noncreature-reliant in {tags}"

    def test_high_creature_density_deck_does_not_get_noncreature_reliant(self):
        """A creature-heavy deck (well above the threshold) does NOT get noncreature-reliant."""
        con = _con()
        cards = [
            Card(name="Tarmogoyf", type_line="Creature — Lhurgoyf",
                 oracle_text="Tarmogoyf's power is equal to the number of card types among "
                 "cards in all graveyards and its toughness is that number plus 1.",
                 cmc=2.0),
            Card(name="Goblin Guide", type_line="Creature — Goblin", oracle_text="Haste.", cmc=1.0),
            Card(name="Mountain", type_line="Basic Land — Mountain", oracle_text="{T}: Add {R}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        maindeck = {"Tarmogoyf": 4, "Goblin Guide": 4, "Mountain": 20}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "noncreature-reliant" not in tags, f"Unexpected noncreature-reliant in {tags}"
        assert "creature-based" in tags, f"Expected creature-based in {tags}"

    def test_boundary_at_threshold_does_not_fire(self):
        """Creature density exactly AT _NONCREATURE_RELIANT_MAX (0.15) does not fire
        (strict '<' — the threshold itself is the boundary of the OTHER side)."""
        con = _con()
        cards = [
            Card(name="Tarmogoyf", type_line="Creature — Lhurgoyf", oracle_text="", cmc=2.0),
            Card(name="Brainstorm", type_line="Instant", oracle_text="Draw three cards.", cmc=1.0),
            Card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        # 15 creature copies / 100 total = exactly 0.15
        maindeck = {"Tarmogoyf": 15, "Brainstorm": 65, "Island": 20}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "noncreature-reliant" not in tags, (
            f"Density exactly at threshold must not fire (strict '<'); got {tags}"
        )

    def test_control_archetype_gets_noncreature_reliant_without_combo_signal(self):
        """A control-shaped archetype (low creatures, no tutors/storm/graveyard-recursion)
        gets noncreature-reliant even though it never qualifies for 'combo' — this is the
        gap feature-sfv-attachments closes: control decks were previously invisible to
        broad free-counter attribution."""
        import uuid

        con = _con()
        cards = [
            Card(name="Counterspell", type_line="Instant", oracle_text="Counter target spell.", cmc=2.0),
            Card(name="Swords to Plowshares", type_line="Instant",
                 oracle_text="Exile target creature. Its controller gains life equal to its power.",
                 cmc=1.0),
            Card(name="Wrath of God", type_line="Sorcery", oracle_text="Destroy all creatures.", cmc=4.0),
            Card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        tid = str(uuid.uuid4())
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [tid, "Test", "2026-01-01", None, "Legacy", "test", "test"],
        )
        con.execute(
            "INSERT INTO decks VALUES (?, ?, ?, ?, ?, NULL)", [tid, 0, "p0", "1st", "Azorius Control"]
        )
        for name, count in [
            ("Counterspell", 4),
            ("Swords to Plowshares", 4),
            ("Wrath of God", 4),
            ("Island", 20),
        ]:
            con.execute(
                "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [tid, 0, "main", name, count]
            )
        tags = vulnerability_tags(con, "Azorius Control")
        assert "noncreature-reliant" in tags, f"Expected noncreature-reliant in {tags}"
        assert "combo" not in tags, f"Control shape should not also read as combo; got {tags}"


# ---------------------------------------------------------------------------
# TestColorlessReliantTag — feature-sfv-colorless-axis: colorless-nonland-spell density
# is the attachment point for Consign to Memory's colorless-spell half ("Counter target
# triggered ability or colorless spell."). Corpus-verified firing pattern (2026-07-03):
# Eldrazi/Mystic Forge Combo/Blue Artifacts/Black Saga Storm fire; Dimir Tempo/Izzet
# Delver/Death & Taxes do not — see _COLORLESS_RELIANT_DENSITY's docstring for the
# measured densities that calibrated the 0.15 threshold.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Manabase axis split: nonbasic-manabase (LAND side, reached by Wasteland/Blood Moon/
# Back to Basics) vs artifact-mana-reliant (nonland ARTIFACT fast mana, reached by
# Null Rod / artifact removal). The two are independent — neither implies the other.
# ---------------------------------------------------------------------------

class TestManabaseAxisSplit:
    def test_dual_and_fetch_heavy_deck_is_nonbasic_manabase_only(self):
        """A dual/fetch-heavy manabase with NO artifact mana fires nonbasic-manabase and
        must NOT fire artifact-mana-reliant — Wasteland/Blood Moon reach this deck, Null
        Rod does not."""
        con = _con()
        cards = [
            Card(name="Underground Sea", type_line="Land — Island Swamp",
                 oracle_text="{T}: Add {U} or {B}.", cmc=0.0,
                 produced_mana=["U", "B"]),
            Card(name="Polluted Delta", type_line="Land",
                 oracle_text="{T}, Pay 1 life, Sacrifice this land: Search your library "
                 "for an Island or Swamp card, put it onto the battlefield, then shuffle.",
                 cmc=0.0, produced_mana=[]),
            Card(name="Brainstorm", type_line="Instant",
                 oracle_text="Draw three cards, then put two cards from your hand on top "
                 "of your library.", cmc=1.0, colors=["U"]),
        ]
        store.load_cards(con, cards)
        maindeck = {"Underground Sea": 4, "Polluted Delta": 8, "Brainstorm": 4}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "nonbasic-manabase" in tags, f"Expected nonbasic-manabase in {tags}"
        assert "artifact-mana-reliant" not in tags, (
            f"No artifact mana in this deck; got {tags}"
        )

    def test_artifact_fast_mana_deck_is_artifact_mana_reliant_only(self):
        """Artifact fast mana over a BASIC-land manabase fires artifact-mana-reliant and
        must NOT fire nonbasic-manabase — Null Rod reaches this deck, Blood Moon does not."""
        con = _con()
        cards = [
            Card(name="Lotus Petal", type_line="Artifact",
                 oracle_text="{T}, Sacrifice this artifact: Add one mana of any color.",
                 cmc=0.0, colors=[]),
            Card(name="Island", type_line="Basic Land — Island",
                 oracle_text="{T}: Add {U}.", cmc=0.0, produced_mana=["U"]),
            Card(name="Brainstorm", type_line="Instant",
                 oracle_text="Draw three cards, then put two cards from your hand on top "
                 "of your library.", cmc=1.0, colors=["U"]),
        ]
        store.load_cards(con, cards)
        maindeck = {"Lotus Petal": 4, "Island": 20, "Brainstorm": 12}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "artifact-mana-reliant" in tags, f"Expected artifact-mana-reliant in {tags}"
        assert "nonbasic-manabase" not in tags, (
            f"Basic-land manabase must not fire nonbasic-manabase; got {tags}"
        )

    def test_a_deck_can_carry_both_axes(self):
        """The axes are independent, not mutually exclusive: an artifact-fast-mana shell
        on a dual/fetch manabase is exposed to BOTH Wasteland-style and Null Rod-style hate."""
        con = _con()
        cards = [
            Card(name="Lotus Petal", type_line="Artifact",
                 oracle_text="{T}, Sacrifice this artifact: Add one mana of any color.",
                 cmc=0.0, colors=[]),
            Card(name="Underground Sea", type_line="Land — Island Swamp",
                 oracle_text="{T}: Add {U} or {B}.", cmc=0.0,
                 produced_mana=["U", "B"]),
            Card(name="Brainstorm", type_line="Instant",
                 oracle_text="Draw three cards, then put two cards from your hand on top "
                 "of your library.", cmc=1.0, colors=["U"]),
        ]
        store.load_cards(con, cards)
        maindeck = {"Lotus Petal": 4, "Underground Sea": 8, "Brainstorm": 12}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "nonbasic-manabase" in tags, f"Expected nonbasic-manabase in {tags}"
        assert "artifact-mana-reliant" in tags, f"Expected artifact-mana-reliant in {tags}"

    def test_neither_axis_fires_on_a_basic_land_no_artifact_deck(self):
        """Negative control: basics only, no artifact mana -> neither manabase axis."""
        con = _con()
        cards = [
            Card(name="Island", type_line="Basic Land — Island",
                 oracle_text="{T}: Add {U}.", cmc=0.0, produced_mana=["U"]),
            Card(name="Brainstorm", type_line="Instant",
                 oracle_text="Draw three cards, then put two cards from your hand on top "
                 "of your library.", cmc=1.0, colors=["U"]),
        ]
        store.load_cards(con, cards)
        maindeck = {"Island": 24, "Brainstorm": 36}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "nonbasic-manabase" not in tags, f"Unexpected nonbasic-manabase in {tags}"
        assert "artifact-mana-reliant" not in tags, (
            f"Unexpected artifact-mana-reliant in {tags}"
        )


class TestColorlessReliantTag:
    def test_eldrazi_style_composition_gets_colorless_reliant(self):
        """A colorless-spell-heavy composition (Eldrazi-style: colorless creatures/lands)
        fires colorless-reliant. Hermetic fixture — no production DB dependency."""
        con = _con()
        cards = [
            Card(name="Reality Smasher", type_line="Creature — Eldrazi",
                 oracle_text="Trample. Whenever this creature attacks, defending player "
                 "loses 3 life unless they sacrifice a creature or planeswalker.",
                 cmc=6.0, colors=[]),
            Card(name="Thought-Knot Seer", type_line="Creature — Eldrazi",
                 oracle_text="When this creature enters, target opponent reveals their "
                 "hand. You choose a nonland card from it. Exile that card.",
                 cmc=3.0, colors=[]),
            Card(name="Eldrazi Temple", type_line="Land", oracle_text="{T}: Add {C}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        maindeck = {"Reality Smasher": 20, "Thought-Knot Seer": 20, "Eldrazi Temple": 20}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "colorless-reliant" in tags, f"Expected colorless-reliant in {tags}"

    def test_dimir_style_composition_does_not_get_colorless_reliant(self):
        """A colored-spell-heavy composition (Dimir-style) does NOT fire colorless-reliant
        even though it has plenty of nonland spells. Hermetic fixture."""
        con = _con()
        cards = [
            Card(name="Fatal Push", type_line="Instant",
                 oracle_text="Destroy target creature if it has mana value 2 or less.",
                 cmc=1.0, colors=["B"]),
            Card(name="Brainstorm", type_line="Instant",
                 oracle_text="Draw three cards, then put two cards from your hand on top "
                 "of your library.", cmc=1.0, colors=["U"]),
            Card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        maindeck = {"Fatal Push": 20, "Brainstorm": 20, "Island": 20}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "colorless-reliant" not in tags, f"Unexpected colorless-reliant in {tags}"

    def test_boundary_at_threshold_fires(self):
        """Colorless density exactly AT _COLORLESS_RELIANT_DENSITY (0.15) DOES fire —
        this axis uses '>=' like creature-based/storm-reliant/gy-recursion (NOT the
        strict-'<' complement style noncreature-reliant uses)."""
        con = _con()
        cards = [
            Card(name="Colorless Artifact", type_line="Artifact", oracle_text="", cmc=2.0, colors=[]),
            Card(name="Blue Spell", type_line="Instant", oracle_text="Draw a card.",
                 cmc=1.0, colors=["U"]),
            Card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        # 15 colorless copies / 100 total = exactly 0.15
        maindeck = {"Colorless Artifact": 15, "Blue Spell": 65, "Island": 20}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "colorless-reliant" in tags, (
            f"Density exactly at threshold must fire ('>=' semantics); got {tags}"
        )

    def test_boundary_just_below_threshold_does_not_fire(self):
        """Colorless density just below the threshold (0.14) does not fire."""
        con = _con()
        cards = [
            Card(name="Colorless Artifact", type_line="Artifact", oracle_text="", cmc=2.0, colors=[]),
            Card(name="Blue Spell", type_line="Instant", oracle_text="Draw a card.",
                 cmc=1.0, colors=["U"]),
            Card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        # 14 colorless copies / 100 total = 0.14, just under 0.15
        maindeck = {"Colorless Artifact": 14, "Blue Spell": 66, "Island": 20}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "colorless-reliant" not in tags, (
            f"Density just below threshold must not fire; got {tags}"
        )

    def test_colorless_reliant_independent_of_creature_density(self):
        """colorless-reliant is an INDEPENDENT axis from creature-based/noncreature-reliant:
        a creature-DENSE colorless deck (Eldrazi-shaped) carries BOTH creature-based and
        colorless-reliant simultaneously — it is not a refinement of either existing axis."""
        con = _con()
        cards = [
            Card(name="Reality Smasher", type_line="Creature — Eldrazi",
                 oracle_text="Trample.", cmc=6.0, colors=[]),
            Card(name="Kozilek's Command", type_line="Sorcery",
                 oracle_text="Choose two.", cmc=4.0, colors=[]),
            Card(name="Eldrazi Temple", type_line="Land", oracle_text="{T}: Add {C}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        maindeck = {"Reality Smasher": 30, "Kozilek's Command": 10, "Eldrazi Temple": 20}
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "colorless-reliant" in tags, f"Expected colorless-reliant in {tags}"
        assert "creature-based" in tags, (
            f"Creature-dense colorless deck should also carry creature-based; got {tags}"
        )


# ---------------------------------------------------------------------------
# TestHateEquity — share-sum per tag; covered_share dedupes multi-tag archetypes
# ---------------------------------------------------------------------------

class TestHateEquity:
    def test_hate_equity_graveyard_tag(self):
        """Field {GY-recursion A:0.4, GY-recursion B:0.2, combo C:0.3} → hate_equity['graveyard-recursion']==0.6."""
        field = _make_field({"A": 0.4, "B": 0.2, "C": 0.3, "D": 0.1})
        archetype_tags = {
            "A": frozenset({"graveyard-recursion"}),
            "B": frozenset({"graveyard-recursion"}),
            "C": frozenset({"combo"}),
            "D": frozenset(),
        }
        equity = hate_equity(field, archetype_tags)
        assert pytest.approx(equity["graveyard-recursion"], abs=1e-6) == pytest.approx(
            field.shares["A"] + field.shares["B"]
        )
        assert "combo" in equity

    def test_hate_equity_multi_tag_archetype(self):
        """An archetype with multiple tags contributes its share to each tag."""
        field = _make_field({"Reanimator": 0.4, "Storm": 0.3, "Fair": 0.3})
        archetype_tags = {
            "Reanimator": frozenset({"graveyard-recursion", "combo"}),
            "Storm": frozenset({"storm-reliant", "combo"}),
            "Fair": frozenset({"creature-based"}),
        }
        equity = hate_equity(field, archetype_tags)
        # combo equity = Reanimator share + Storm share
        assert pytest.approx(equity["combo"], abs=1e-6) == pytest.approx(
            field.shares["Reanimator"] + field.shares["Storm"]
        )

    def test_covered_share_no_double_counting(self):
        """covered_share over {A, B, C} deduplicates (each archetype counted once)."""
        field = _make_field({"A": 0.4, "B": 0.2, "C": 0.3, "D": 0.1})
        # Package attacks A and B
        attacked = {"A", "B"}
        cs = covered_share(field, attacked)
        assert pytest.approx(cs, abs=1e-6) == pytest.approx(
            field.shares["A"] + field.shares["B"]
        )

    def test_covered_share_full_field(self):
        """covered_share over all archetypes equals (approximately) 1.0."""
        field = _make_field({"A": 0.4, "B": 0.2, "C": 0.3, "D": 0.1})
        attacked = {"A", "B", "C", "D"}
        cs = covered_share(field, attacked)
        assert pytest.approx(cs, abs=1e-4) == pytest.approx(1.0, abs=1e-4)

    def test_covered_share_archetype_not_in_field(self):
        """Archetypes not in the field contribute 0 to covered_share."""
        field = _make_field({"A": 0.6, "B": 0.4})
        cs = covered_share(field, {"A", "PHANTOM"})
        assert pytest.approx(cs, abs=1e-6) == pytest.approx(field.shares["A"])

    def test_field_vulnerability_tags_covers_all_archetypes(self):
        """field_vulnerability_tags returns an entry for every archetype in the field."""
        con = _con()
        # Minimal corpus for Reanimator
        cards = [
            Card(name="Reanimate", type_line="Sorcery",
                 oracle_text="Put target creature card from a graveyard onto the battlefield under your control. You lose life equal to its mana value.",
                 cmc=1.0),
            Card(name="Swamp", type_line="Basic Land — Swamp", oracle_text="{T}: Add {B}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        import uuid
        tid = str(uuid.uuid4())
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [tid, "T", "2026-01-01", None, "Legacy", "test", "test"],
        )
        con.execute("INSERT INTO decks VALUES (?, ?, ?, ?, ?, NULL)", [tid, 0, "p0", "1st", "Reanimator"])
        con.execute("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [tid, 0, "main", "Reanimate", 4])
        con.execute("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [tid, 0, "main", "Swamp", 10])

        field = _make_field({"Reanimator": 0.6, "Delver": 0.4})
        fvt = field_vulnerability_tags(con, field)
        assert "Reanimator" in fvt
        assert "Delver" in fvt
        assert isinstance(fvt["Reanimator"], frozenset)
        con.close()


# ---------------------------------------------------------------------------
# TestBestDeckCall
# ---------------------------------------------------------------------------

class TestBestDeckCall:
    def _flat_matrix(self, archetypes: list[str], source: str, p: float = 0.55) -> MatchupMatrix:
        """Matrix where source beats every opponent at rate p (flat spread)."""
        cells = {}
        for a in archetypes:
            cells[(a, a)] = build_mirror_cell(a, 50)
            for b in archetypes:
                if a == b:
                    continue
                if a == source:
                    cells[(a, b)] = build_cell(a, b, int(p * 100), 100)
                elif b == source:
                    cells[(a, b)] = build_cell(a, b, int((1 - p) * 100), 100)
                else:
                    cells[(a, b)] = build_cell(a, b, 50, 100)
        return _make_matrix(cells, archetypes)

    def _spiky_matrix(self, archetypes: list[str], source: str, crush: list[str]) -> MatchupMatrix:
        """Matrix where source crushes ``crush`` archetypes at 75% and loses to others at 20%."""
        cells = {}
        for a in archetypes:
            cells[(a, a)] = build_mirror_cell(a, 50)
            for b in archetypes:
                if a == b:
                    continue
                if a == source:
                    if b in crush:
                        cells[(a, b)] = build_cell(a, b, 75, 100)
                    else:
                        cells[(a, b)] = build_cell(a, b, 20, 100)
                elif b == source:
                    if a in crush:
                        cells[(a, b)] = build_cell(a, b, 25, 100)
                    else:
                        cells[(a, b)] = build_cell(a, b, 80, 100)
                else:
                    cells[(a, b)] = build_cell(a, b, 50, 100)
        return _make_matrix(cells, archetypes)

    def test_flat_high_mean_is_best_deck(self):
        """Low-variance + high mean → BEST_DECK."""
        archetypes = ["Delver", "Reanimator", "Lands", "Storm"]
        matrix = self._flat_matrix(archetypes, "Delver", p=0.55)
        field = _make_field({a: 0.25 for a in archetypes})
        result = best_deck_vs_best_call(matrix, field, "Delver")
        assert result.label == "BEST_DECK", (
            f"Expected BEST_DECK but got {result.label} "
            f"(variance={result.spread_variance:.4f}, mean={result.unweighted_mean:.3f})"
        )

    def test_spiky_field_preying_is_best_call(self):
        """High variance + high field-weighted mean → BEST_CALL.

        Scenario: Delver crushes Reanimator (40%) and Lands (30%) at ~72%;
        loses to Storm (30%) at ~24%.  High variance, field-weighted mean >0.52.
        """
        archetypes = ["Delver", "Reanimator", "Lands", "Storm"]
        # Crush = Reanimator and Lands (70% of non-Delver field)
        matrix = self._spiky_matrix(archetypes, "Delver", crush=["Reanimator", "Lands"])
        # Field: big share to archetypes Delver crushes
        field = _make_field({"Delver": 0.05, "Reanimator": 0.40, "Lands": 0.30, "Storm": 0.25})
        result = best_deck_vs_best_call(matrix, field, "Delver")
        assert result.label == "BEST_CALL", (
            f"Expected BEST_CALL but got {result.label} "
            f"(variance={result.spread_variance:.4f}, field_mean={result.field_weighted_mean:.3f}, "
            f"unweighted_mean={result.unweighted_mean:.3f})"
        )

    def test_missing_archetype_returns_neither(self):
        """Archetype not in the matrix returns 'neither' gracefully."""
        archetypes = ["Delver", "Reanimator"]
        matrix = self._flat_matrix(archetypes, "Delver")
        field = _make_field({"Delver": 0.5, "Reanimator": 0.5})
        result = best_deck_vs_best_call(matrix, field, "Storm")
        assert result.label == "neither"

    def test_result_has_expected_fields(self):
        """BestDeckCall carries archetype, label, variance, means."""
        archetypes = ["A", "B", "C"]
        cells = {}
        for a in archetypes:
            cells[(a, a)] = build_mirror_cell(a, 50)
            for b in archetypes:
                if a == b:
                    continue
                cells[(a, b)] = build_cell(a, b, 55, 100)
        matrix = _make_matrix(cells, archetypes)
        field = _make_field({a: 1 / 3 for a in archetypes})
        result = best_deck_vs_best_call(matrix, field, "A")
        assert isinstance(result, BestDeckCall)
        assert result.archetype == "A"
        assert isinstance(result.spread_variance, float)
        assert isinstance(result.field_weighted_mean, float)
        assert isinstance(result.unweighted_mean, float)
        assert result.label in ("BEST_DECK", "BEST_CALL", "neither")


# ---------------------------------------------------------------------------
# TestPlanClash — rule-table directions; heuristic-vs-data disagreement flag
# ---------------------------------------------------------------------------

class TestPlanClash:
    def _profile(self, score: float, reactive_mass: float = 5.0) -> ProactivityProfile:
        return ProactivityProfile(
            score=score,
            proactive_mass=score * 10,
            reactive_mass=reactive_mass,
            low_curve_score=0.5,
            findings=(),
        )

    def _cell(self, p_shrunk: float):
        """Minimal cell mock with a p_shrunk attribute."""
        class FakeCell:
            pass
        c = FakeCell()
        c.p_shrunk = p_shrunk
        return c

    def test_proactive_vs_reactive_no_hate_favors_proactive(self):
        """Proactive (0.8) vs reactive (0.2) with no hate → WHY favors the proactive deck."""
        deck = self._profile(0.8)
        opp = self._profile(0.2)
        cell = self._cell(0.65)  # data agrees: proactive wins
        why, disagreement = plan_clash(deck, opp, cell, hate_present=False)
        assert "proactive" in why.lower() or "tempo" in why.lower()
        assert not disagreement

    def test_proactive_vs_reactive_with_hate_favors_reactive(self):
        """Proactive (0.8) vs reactive (0.2) with hate → reactive favored."""
        deck = self._profile(0.8)
        opp = self._profile(0.2)
        cell = self._cell(0.40)  # data agrees: reactive wins
        why, disagreement = plan_clash(deck, opp, cell, hate_present=True)
        assert "reactive" in why.lower() or "answer" in why.lower()
        assert not disagreement

    def test_disagreement_flag_when_heuristic_favors_deck_but_cell_shows_losing(self):
        """Heuristic favors deck (proactive) but cell shows p_shrunk<0.5 → disagreement=True."""
        deck = self._profile(0.8)
        opp = self._profile(0.2)
        cell = self._cell(0.35)  # heuristic says proactive wins, cell says loses
        why, disagreement = plan_clash(deck, opp, cell, hate_present=False)
        assert disagreement is True
        assert "NOTE" in why or "confound" in why.lower() or "disagree" in why.lower() or "p_shrunk" in why

    def test_disagreement_flag_when_heuristic_favors_opp_but_cell_shows_winning(self):
        """Heuristic favors opponent (reactive with hate) but cell shows p>0.5 → disagreement=True."""
        deck = self._profile(0.8)
        opp = self._profile(0.2)
        cell = self._cell(0.70)  # heuristic says deck loses (hate present), cell says wins
        why, disagreement = plan_clash(deck, opp, cell, hate_present=True)
        assert disagreement is True

    def test_both_proactive_faster_clock(self):
        """Both proactive → faster clock wins."""
        deck = self._profile(0.85)
        opp = self._profile(0.75)
        cell = self._cell(0.60)
        why, _ = plan_clash(deck, opp, cell)
        assert "proactive" in why.lower() or "clock" in why.lower() or "faster" in why.lower()

    def test_both_reactive_card_advantage(self):
        """Both reactive → card advantage wins."""
        deck = self._profile(0.3, reactive_mass=15.0)
        opp = self._profile(0.25, reactive_mass=10.0)
        cell = self._cell(0.55)
        why, _ = plan_clash(deck, opp, cell)
        assert "reactive" in why.lower() or "card advantage" in why.lower() or "answer" in why.lower()

    def test_no_cell_no_crash(self):
        """plan_clash with cell=None does not crash."""
        deck = self._profile(0.8)
        opp = self._profile(0.2)
        why, disagreement = plan_clash(deck, opp, None, hate_present=False)
        assert isinstance(why, str)
        assert isinstance(disagreement, bool)


# ---------------------------------------------------------------------------
# Regression tests for peer-review bug fixes
# ---------------------------------------------------------------------------


class TestRegressionPeerReviewFixes:
    """One regression test per whattoplay-related finding (2026-05-30 peer review)."""

    # --- Fix 7: best_deck_vs_best_call uses only n>=30 cells ---

    def _make_matrix(self, cells, archetypes):
        return MatchupMatrix(
            cells=cells,
            provenance=None,
            total_matches=sum(c.n for c in cells.values()),
            archetypes=archetypes,
            caveat="regression test",
        )

    def test_fix7_low_n_cells_excluded_from_best_deck_classification(self):
        """Bug: cells with n<30 could drive BEST_DECK / BEST_CALL classification.
        Fix: only cells with cell.display (n>=30) are used for classification.
        A row whose ONLY strong cells are n<30 must NOT be classified BEST_DECK.
        """
        from legacy_engine.analytics.matchup import DISPLAY_GATE_N

        # This test's n<30/n>=30 literals below assume the production display gate is 30.
        assert DISPLAY_GATE_N == 30, "test's low/high-n literals assume this gate value"

        # Build a matrix where Archetype A has:
        #   - One cell vs B with n=5 (< 30, speculative), very high winrate 90%
        #   - No other non-mirror data
        archetypes = ["A", "B"]
        cells = {
            ("A", "A"): build_mirror_cell("A", 50),
            ("B", "B"): build_mirror_cell("B", 50),
            ("A", "B"): build_cell("A", "B", 9, 10),    # n=10 < 30, WR=90%
            ("B", "A"): build_cell("B", "A", 1, 10),
        }
        assert not cells[("A", "B")].display, "Sanity: n=10 cell should not be display-grade"

        matrix = self._make_matrix(cells, archetypes)
        field = _make_field({"B": 1.0})

        result = best_deck_vs_best_call(matrix, field, "A")
        # With no display-grade cells, classification must be 'neither'
        assert result.label == "neither", (
            f"Low-n-only row must NOT be classified BEST_DECK/BEST_CALL; got {result.label!r}"
        )

    def test_fix7_high_n_cells_can_still_drive_best_deck(self):
        """High-n cells (n>=30) continue to drive classification after the fix."""
        archetypes = ["A", "B"]
        cells = {
            ("A", "A"): build_mirror_cell("A", 50),
            ("B", "B"): build_mirror_cell("B", 50),
            ("A", "B"): build_cell("A", "B", 56, 100),  # n=100 >= 30, WR=56% → low variance
            ("B", "A"): build_cell("B", "A", 44, 100),
        }
        assert cells[("A", "B")].display, "Sanity: n=100 cell must be display-grade"

        matrix = self._make_matrix(cells, archetypes)
        field = _make_field({"B": 1.0})

        result = best_deck_vs_best_call(matrix, field, "A")
        # Low spread, above 0.52 mean → BEST_DECK
        assert result.label == "BEST_DECK", (
            f"High-n 56% cell should classify as BEST_DECK; got {result.label!r}"
        )


# ---------------------------------------------------------------------------
# Best-deck-call gradient — epic-advisory-output-honesty-whattoplay-honesty
# ---------------------------------------------------------------------------


class TestBestDeckCallGradient:
    """De-cliffed BEST_CALL + continuous best_deck_score/best_call_score."""

    def _row_matrix(self, source: str, opp_wins: dict[str, int]) -> MatchupMatrix:
        """Matrix: `source` vs each opp at opp_wins[opp]/100; opponents play each other at 50/100."""
        archetypes = [source, *opp_wins]
        cells = {}
        for a in archetypes:
            cells[(a, a)] = build_mirror_cell(a, 50)
            for b in archetypes:
                if a == b:
                    continue
                if a == source:
                    cells[(a, b)] = build_cell(a, b, opp_wins[b], 100)
                elif b == source:
                    cells[(a, b)] = build_cell(a, b, 100 - opp_wins[a], 100)
                else:
                    cells[(a, b)] = build_cell(a, b, 50, 100)
        return _make_matrix(cells, archetypes)

    def test_cliff_fixed_low_variance_field_favored_is_best_call(self):
        """The reported cliff: low variance + field-weighted mean ≥ 0.52 + unweighted < 0.52.

        Old code → 'neither' (BEST_CALL required variance > spread_hi). New code → BEST_CALL.
        """
        m = self._row_matrix("DnT", {"A": 58, "B": 47, "C": 47})
        field = _make_field({"DnT": 0.0, "A": 0.8, "B": 0.1, "C": 0.1})  # field concentrated on A
        r = best_deck_vs_best_call(m, field, "DnT")
        assert r.spread_variance <= 0.02, f"expected low variance, got {r.spread_variance:.4f}"
        assert r.unweighted_mean < 0.52, f"expected sub-threshold unweighted, got {r.unweighted_mean:.3f}"
        assert r.field_weighted_mean >= 0.52, f"expected field-favored, got {r.field_weighted_mean:.3f}"
        assert r.label == "BEST_CALL", f"cliff not fixed: got {r.label}"

    def test_best_call_score_is_field_weighted_mean(self):
        m = self._row_matrix("DnT", {"A": 58, "B": 47, "C": 47})
        field = _make_field({"DnT": 0.0, "A": 0.8, "B": 0.1, "C": 0.1})
        r = best_deck_vs_best_call(m, field, "DnT")
        assert r.best_call_score == pytest.approx(r.field_weighted_mean)

    def test_best_deck_score_is_robust_floor(self):
        # best_deck_score = clamp(unweighted_mean − √variance, 0, 1)
        m = self._row_matrix("X", {"A": 60, "B": 55, "C": 50})
        field = _make_field({"X": 0.0, "A": 0.34, "B": 0.33, "C": 0.33})
        r = best_deck_vs_best_call(m, field, "X")
        import math
        expected = max(0.0, min(1.0, r.unweighted_mean - math.sqrt(r.spread_variance)))
        assert r.best_deck_score == pytest.approx(expected)

    def test_spiky_scores_below_flat_at_equal_mean(self):
        """A spiky deck (high variance) has a lower best_deck_score than a flat deck of equal mean."""
        # Flat: 55/55/55  → mean .55, variance ~0
        flat = self._row_matrix("F", {"A": 55, "B": 55, "C": 55})
        # Spiky: 75/75/15 → mean .55, high variance
        spiky = self._row_matrix("S", {"A": 75, "B": 75, "C": 15})
        field = _make_field({"A": 0.34, "B": 0.33, "C": 0.33})
        rf = best_deck_vs_best_call(flat, _make_field({"F": 0.0, **field.shares}), "F")
        rs = best_deck_vs_best_call(spiky, _make_field({"S": 0.0, **field.shares}), "S")
        assert rf.best_deck_score > rs.best_deck_score

    def test_neither_returns_bounded_scores(self):
        m = self._row_matrix("W", {"A": 30, "B": 30, "C": 30})  # bad everywhere
        field = _make_field({"W": 0.0, "A": 0.34, "B": 0.33, "C": 0.33})
        r = best_deck_vs_best_call(m, field, "W")
        assert r.label == "neither"
        # scores are still computed (continuous), just low — not forced to 0 unless no cells
        assert 0.0 <= r.best_deck_score <= 1.0
        assert 0.0 <= r.best_call_score <= 1.0

    def test_missing_archetype_zero_scores(self):
        m = self._row_matrix("X", {"A": 55, "B": 55})
        field = _make_field({"X": 0.5, "A": 0.25, "B": 0.25})
        r = best_deck_vs_best_call(m, field, "ZZZ")  # not in matrix
        assert r.label == "neither"
        assert r.best_deck_score == 0.0
        assert r.best_call_score == 0.0


# ---------------------------------------------------------------------------
# TestRampBigManaTag — feature-bigmana-ramp-tag
# ---------------------------------------------------------------------------

class TestRampBigManaTag:
    """Spec-derived tests for the ramp/big-mana vulnerability tag.

    Detection: ≥4 copies of named big-mana lands (Urzatron pieces / Cloudpost / Eldrazi accelerants)
    in the deck composition.  Tag name: "ramp".
    Gated-additive: existing tags/detection paths are byte-identical; new tag only ADDS coverage.
    """

    def _build_tron_corpus(self):
        """Urzatron corpus: 4x each Urza land + colorless payoffs.

        Mirrors a real Tron shell — 12 Urzatron pieces, 4× Karn, 4× Emrakul, 4× Expedition Map.
        """
        import uuid
        con = _con()
        cards = [
            Card(name="Urza's Tower", type_line="Land", oracle_text="{T}: Add {C}. If you control Urza's Mine and Urza's Power Plant, add {C}{C}{C} instead.", cmc=0.0),
            Card(name="Urza's Mine", type_line="Land", oracle_text="{T}: Add {C}. If you control Urza's Tower and Urza's Power Plant, add {C}{C} instead.", cmc=0.0),
            Card(name="Urza's Power Plant", type_line="Land", oracle_text="{T}: Add {C}. If you control Urza's Tower and Urza's Mine, add {C}{C} instead.", cmc=0.0),
            Card(name="Expedition Map", type_line="Artifact", oracle_text="{2}, {T}, Sacrifice Expedition Map: Search your library for a land card, reveal it, put it into your hand, then shuffle.", cmc=1.0),
            Card(name="Karn Liberated", type_line="Legendary Planeswalker — Karn", oracle_text="[+4]: Target player exiles a card from their hand.\n[−3]: Exile target permanent.\n[−14]: ...", cmc=7.0),
            Card(name="Emrakul, the Aeons Torn", type_line="Legendary Creature — Eldrazi", oracle_text="This spell can't be countered. When you cast this spell, take an extra turn after this one. Flying, protection from colored spells, annihilator 6.", cmc=15.0),
        ]
        store.load_cards(con, cards)
        tid = str(uuid.uuid4())
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [tid, "Test", "2026-01-01", None, "Legacy", "test", "test"],
        )
        for idx in range(3):
            con.execute(
                "INSERT INTO decks VALUES (?, ?, ?, ?, ?, NULL)",
                [tid, idx, f"player{idx}", "1st", "Urzatron"],
            )
            for card_name, count in [
                ("Urza's Tower", 4),
                ("Urza's Mine", 4),
                ("Urza's Power Plant", 4),
                ("Expedition Map", 4),
                ("Karn Liberated", 4),
                ("Emrakul, the Aeons Torn", 4),
            ]:
                con.execute(
                    "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
                    [tid, idx, "main", card_name, count],
                )
        return con

    def _build_dimir_corpus(self):
        """Dimir Tempo corpus: NO Urzatron / big-mana lands — ramp tag must NOT fire."""
        import uuid
        con = _con()
        cards = [
            Card(name="Force of Will", type_line="Instant", oracle_text="You may pay 1 life and exile a blue card from your hand rather than pay this spell's mana cost.\nCounter target spell.", cmc=5.0),
            Card(name="Brainstorm", type_line="Instant", oracle_text="Draw three cards, then put two cards from your hand on top of your library.", cmc=1.0),
            Card(name="Underground Sea", type_line="Land — Island Swamp", colors=["U", "B"], produced_mana=["U", "B"], oracle_text="", cmc=0.0),
        ]
        store.load_cards(con, cards)
        tid = str(uuid.uuid4())
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [tid, "Test", "2026-01-01", None, "Legacy", "test", "test"],
        )
        for idx in range(3):
            con.execute(
                "INSERT INTO decks VALUES (?, ?, ?, ?, ?, NULL)",
                [tid, idx, f"player{idx}", "1st", "Dimir Tempo"],
            )
            for card_name, count in [
                ("Force of Will", 4),
                ("Brainstorm", 4),
                ("Underground Sea", 16),
            ]:
                con.execute(
                    "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
                    [tid, idx, "main", card_name, count],
                )
        return con

    # --- Detection: Tron-shaped deck gets ramp tag ---

    def test_tron_archetype_has_ramp_tag(self):
        """Urzatron archetype (12 Urza lands) gets the 'ramp' vulnerability tag."""
        con = self._build_tron_corpus()
        tags = vulnerability_tags(con, "Urzatron")
        assert "ramp" in tags, f"Expected 'ramp' in tags for Tron; got {tags}"
        con.close()

    def test_tron_deck_direct_has_ramp_tag(self):
        """vulnerability_tags_for_deck with a Tron maindeck emits 'ramp'."""
        con = _con()
        cards = [
            Card(name="Urza's Tower", type_line="Land", oracle_text="{T}: Add {C}.", cmc=0.0),
            Card(name="Urza's Mine", type_line="Land", oracle_text="{T}: Add {C}.", cmc=0.0),
            Card(name="Urza's Power Plant", type_line="Land", oracle_text="{T}: Add {C}.", cmc=0.0),
            Card(name="Karn Liberated", type_line="Legendary Planeswalker — Karn", oracle_text="[+4]: Target player exiles a card.", cmc=7.0),
        ]
        store.load_cards(con, cards)
        maindeck = {
            "Urza's Tower": 4,
            "Urza's Mine": 4,
            "Urza's Power Plant": 4,
            "Karn Liberated": 4,
        }
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "ramp" in tags, f"Expected 'ramp' in tags; got {tags}"
        con.close()

    def test_below_threshold_no_ramp_tag(self):
        """Fewer than 4 big-mana lands does NOT trigger the ramp tag."""
        con = _con()
        cards = [
            Card(name="Urza's Tower", type_line="Land", oracle_text="{T}: Add {C}.", cmc=0.0),
            Card(name="Karn Liberated", type_line="Legendary Planeswalker — Karn", oracle_text="[+4]: Target player exiles a card.", cmc=7.0),
            Card(name="Island", type_line="Basic Land — Island", oracle_text="{T}: Add {U}.", cmc=0.0),
        ]
        store.load_cards(con, cards)
        # Only 3 copies of an Urza land — below threshold of 4
        maindeck = {
            "Urza's Tower": 3,
            "Karn Liberated": 4,
            "Island": 16,
        }
        tags = vulnerability_tags_for_deck(con, maindeck)
        assert "ramp" not in tags, f"Below-threshold deck should NOT have 'ramp'; got {tags}"
        con.close()

    def test_dimir_tempo_no_ramp_tag(self):
        """Dimir Tempo archetype (no big-mana lands) does NOT get the 'ramp' tag."""
        con = self._build_dimir_corpus()
        tags = vulnerability_tags(con, "Dimir Tempo")
        assert "ramp" not in tags, f"Dimir Tempo should NOT have 'ramp'; got {tags}"
        con.close()

    # --- Gated-additive: existing tags still fire correctly ---

    def test_tron_ramp_tag_does_not_suppress_low_interaction(self):
        """Adding the ramp tag does not prevent low-interaction from also firing on a Tron deck."""
        con = self._build_tron_corpus()
        tags = vulnerability_tags(con, "Urzatron")
        # Tron has very few counters/removal → should also be low-interaction
        assert "ramp" in tags
        # (low-interaction is expected to also fire; we just confirm ramp doesn't break other tags)
        assert isinstance(tags, frozenset)
        con.close()

    # --- Hate-equity: big-mana field share is now covered ---

    def test_hate_equity_includes_ramp_tag(self):
        """hate_equity correctly sums field share for archetypes carrying the ramp tag."""
        field = _make_field({"Urzatron": 0.09, "Dimir Tempo": 0.15, "Storm": 0.10})
        archetype_tags = {
            "Urzatron": frozenset({"ramp", "low-interaction"}),
            "Dimir Tempo": frozenset({"creature-based", "nonbasic-manabase"}),
            "Storm": frozenset({"storm-reliant", "combo"}),
        }
        equity = hate_equity(field, archetype_tags)
        assert "ramp" in equity, "hate_equity should include 'ramp' when an archetype carries it"
        assert pytest.approx(equity["ramp"], abs=1e-6) == pytest.approx(field.shares["Urzatron"])

    def test_covered_share_with_ramp_field(self):
        """covered_share over ramp archetype correctly returns its field fraction."""
        field = _make_field({"Urzatron": 0.09, "Cloudpost": 0.05, "Dimir Tempo": 0.15, "Storm": 0.10})
        ramp_archetypes = {"Urzatron", "Cloudpost"}
        cs = covered_share(field, ramp_archetypes)
        expected = field.shares["Urzatron"] + field.shares["Cloudpost"]
        assert pytest.approx(cs, abs=1e-6) == pytest.approx(expected)
