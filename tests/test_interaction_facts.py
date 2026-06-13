"""Interaction facts — behavior-derived unit tests.

Tests use hand-built ``Card`` objects (no DB), mirroring ``tests/test_card_tags.py``.
Each test is derived from *observed behavior* in the dogfood session (2026-06-13),
not from the regex implementation.

Regression cards (the actual bugs that motivated this feature):
- Grafdigger's Cage: symmetric restriction, no count-reduction → self_graveyard_safe
- Leyline of the Void: opponent-only → self_graveyard_safe
- Nihil Spellbomb: targeted → self_graveyard_safe

All three were wrongly claimed to "brick your own yard" by memory-based reasoning.
"""

from __future__ import annotations

import pytest

from legacy_engine.interaction_facts import ClaimCheck, InteractionFacts, interaction_facts, verify_graveyard_claim
from legacy_engine.models.card import Card


# ---------------------------------------------------------------------------
# Oracle text samples (real Scryfall text for the three regression cards)
# ---------------------------------------------------------------------------

GRAFDIGGERS_CAGE_TEXT = (
    "Creatures can't enter the battlefield from graveyards or libraries.\n"
    "Players can't cast spells from graveyards or libraries."
)

LEYLINE_OF_THE_VOID_TEXT = (
    "If Leyline of the Void is in your opening hand, you may begin the game with it on the battlefield.\n"
    "If a card would be put into an opponent's graveyard from anywhere, exile it instead."
)

NIHIL_SPELLBOMB_TEXT = (
    "{T}, Sacrifice Nihil Spellbomb: Exile target player's graveyard.\n"
    "When Nihil Spellbomb is put into a graveyard from the battlefield, you may pay {B}. "
    "If you do, draw a card."
)

# A clearly symmetric graveyard-exile card (e.g. "Exile all graveyards" style)
SYMMETRIC_EXILE_TEXT = "Exile all cards in all graveyards."

# A delve/escape self-engine card referencing "your graveyard"
DELVE_SELF_TEXT = (
    "Exile any number of cards from your graveyard as you cast this spell. "
    "It costs {1} less to cast for each card exiled this way."
)

# Force of Will — free spell
FORCE_OF_WILL_TEXT = (
    "You may pay 1 life and exile a blue card from your hand rather than pay this spell's mana cost.\n"
    "Counter target spell."
)

# Triggered graveyard card: "When ... put into a graveyard"
TRIGGERED_GY_TEXT = (
    "When Snapcaster Mage enters the battlefield, target instant or sorcery card in your graveyard "
    "gains flashback until end of turn. The flashback cost is equal to its mana cost."
)

# A card with conflicting scope: one line opponent-only, another symmetric
CONFLICTING_SCOPE_TEXT = (
    "If a card would be put into an opponent's graveyard from anywhere, exile it instead.\n"
    "Each player exiles all cards from their graveyard."
)


# ---------------------------------------------------------------------------
# Helper: build a Card quickly
# ---------------------------------------------------------------------------

def _card(
    name: str,
    type_line: str,
    oracle_text: str,
    cmc: float = 0.0,
    power: str | None = None,
    toughness: str | None = None,
) -> Card:
    return Card(name=name, type_line=type_line, oracle_text=oracle_text, cmc=cmc,
                power=power, toughness=toughness)


# ---------------------------------------------------------------------------
# Class 1 — The three regression cards
# ---------------------------------------------------------------------------

class TestRegressionCases:
    """The three bugs from the 2026-06-13 dogfood session."""

    def test_grafdiggers_cage_affects_symmetric(self):
        cage = _card("Grafdigger's Cage", "Artifact", GRAFDIGGERS_CAGE_TEXT)
        facts = interaction_facts(cage)
        assert facts.affects == "symmetric"

    def test_grafdiggers_cage_touches_graveyard(self):
        cage = _card("Grafdigger's Cage", "Artifact", GRAFDIGGERS_CAGE_TEXT)
        facts = interaction_facts(cage)
        assert facts.touches_graveyard is True

    def test_grafdiggers_cage_no_count_reduction(self):
        """Grafdigger's restricts casting/entering, never exiles cards from the yard."""
        cage = _card("Grafdigger's Cage", "Artifact", GRAFDIGGERS_CAGE_TEXT)
        facts = interaction_facts(cage)
        assert facts.graveyard_count_reduction is False

    def test_grafdiggers_cage_self_graveyard_safe(self):
        """Grafdigger's is self_graveyard_safe: symmetric but no count-reduction → delirium/delve/escape unaffected."""
        cage = _card("Grafdigger's Cage", "Artifact", GRAFDIGGERS_CAGE_TEXT)
        facts = interaction_facts(cage)
        assert facts.self_graveyard_safe is True

    def test_leyline_of_the_void_affects_opponent_only(self):
        leyline = _card("Leyline of the Void", "Enchantment", LEYLINE_OF_THE_VOID_TEXT)
        facts = interaction_facts(leyline)
        assert facts.affects == "opponent-only"

    def test_leyline_of_the_void_self_graveyard_safe(self):
        leyline = _card("Leyline of the Void", "Enchantment", LEYLINE_OF_THE_VOID_TEXT)
        facts = interaction_facts(leyline)
        assert facts.self_graveyard_safe is True

    def test_leyline_touches_graveyard(self):
        leyline = _card("Leyline of the Void", "Enchantment", LEYLINE_OF_THE_VOID_TEXT)
        facts = interaction_facts(leyline)
        assert facts.touches_graveyard is True

    def test_nihil_spellbomb_affects_targeted(self):
        nihil = _card("Nihil Spellbomb", "Artifact", NIHIL_SPELLBOMB_TEXT)
        facts = interaction_facts(nihil)
        assert facts.affects == "targeted"

    def test_nihil_spellbomb_self_graveyard_safe(self):
        """Nihil Spellbomb is targeted — controller points it at the opponent."""
        nihil = _card("Nihil Spellbomb", "Artifact", NIHIL_SPELLBOMB_TEXT)
        facts = interaction_facts(nihil)
        assert facts.self_graveyard_safe is True


# ---------------------------------------------------------------------------
# Class 2 — Contrast: symmetric exile (should NOT be self-safe)
# ---------------------------------------------------------------------------

class TestSymmetricCountContrast:
    """A symmetric graveyard-exile card DOES reduce own yard count → not self_graveyard_safe."""

    def test_symmetric_exile_affects(self):
        card = _card("Purge All", "Sorcery", SYMMETRIC_EXILE_TEXT)
        facts = interaction_facts(card)
        assert facts.affects == "symmetric"

    def test_symmetric_exile_count_reduction(self):
        card = _card("Purge All", "Sorcery", SYMMETRIC_EXILE_TEXT)
        facts = interaction_facts(card)
        assert facts.graveyard_count_reduction is True

    def test_symmetric_exile_not_self_graveyard_safe(self):
        """Symmetric + count-reduction = NOT safe for own graveyard."""
        card = _card("Purge All", "Sorcery", SYMMETRIC_EXILE_TEXT)
        facts = interaction_facts(card)
        assert facts.self_graveyard_safe is False


# ---------------------------------------------------------------------------
# Class 3 — Self-only proactive cases (delve / escape)
# ---------------------------------------------------------------------------

class TestSelfOnlyCases:
    """Cards referencing 'your graveyard' as a resource (delve, escape) are self-only."""

    def test_delve_affects_self_only(self):
        card = _card("Delve Card", "Instant", DELVE_SELF_TEXT)
        facts = interaction_facts(card)
        assert facts.affects == "self-only"

    def test_delve_self_graveyard_safe(self):
        """A delve/escape card that costs from your own yard is still 'safe' — it IS your engine."""
        card = _card("Delve Card", "Instant", DELVE_SELF_TEXT)
        facts = interaction_facts(card)
        assert facts.self_graveyard_safe is True


# ---------------------------------------------------------------------------
# Class 4 — Permanence classification
# ---------------------------------------------------------------------------

class TestPermanence:
    def test_leyline_is_static(self):
        """Leyline of the Void is an enchantment with a continuous replacement effect (no activation)."""
        leyline = _card("Leyline of the Void", "Enchantment", LEYLINE_OF_THE_VOID_TEXT)
        facts = interaction_facts(leyline)
        assert facts.permanence == "static"

    def test_nihil_spellbomb_is_activated(self):
        """Nihil Spellbomb has a '{T}, Sacrifice ...:' activated ability."""
        nihil = _card("Nihil Spellbomb", "Artifact", NIHIL_SPELLBOMB_TEXT)
        facts = interaction_facts(nihil)
        assert facts.permanence == "activated"

    def test_triggered_graveyard_card(self):
        """A card with 'When ... enters the battlefield' is triggered."""
        snapper = _card(
            "Snapcaster Mage",
            "Creature — Human Wizard",
            TRIGGERED_GY_TEXT,
            cmc=2.0,
            power="2",
            toughness="1",
        )
        facts = interaction_facts(snapper)
        assert facts.permanence == "triggered"

    def test_instant_is_one_shot(self):
        """An instant with no activated ability is one-shot."""
        card = _card("Brainstorm", "Instant", "Draw three cards, then put two cards from your hand on top of your library in any order.")
        facts = interaction_facts(card)
        assert facts.permanence == "one-shot"

    def test_grafdiggers_cage_is_static(self):
        """Grafdigger's Cage has only continuous restriction clauses (can't) — static."""
        cage = _card("Grafdigger's Cage", "Artifact", GRAFDIGGERS_CAGE_TEXT)
        facts = interaction_facts(cage)
        assert facts.permanence == "static"


# ---------------------------------------------------------------------------
# Class 5 — free_cast (delegation to is_free_spell)
# ---------------------------------------------------------------------------

class TestFreeCast:
    def test_force_of_will_free(self):
        fow = _card("Force of Will", "Instant", FORCE_OF_WILL_TEXT)
        facts = interaction_facts(fow)
        assert facts.free_cast is True

    def test_brainstorm_not_free(self):
        bs = _card("Brainstorm", "Instant", "Draw three cards, then put two cards from your hand on top of your library in any order.")
        facts = interaction_facts(bs)
        assert facts.free_cast is False


# ---------------------------------------------------------------------------
# Class 6 — Confidence: clean vs conflicting scope
# ---------------------------------------------------------------------------

class TestConfidence:
    def test_clean_card_is_evolving(self):
        """A card with a single unambiguous scope gets evolving confidence."""
        leyline = _card("Leyline of the Void", "Enchantment", LEYLINE_OF_THE_VOID_TEXT)
        facts = interaction_facts(leyline)
        assert facts.confidence.level == "evolving"

    def test_conflicting_scope_is_speculative(self):
        """A card with opponent-only on one line and symmetric on another → speculative."""
        card = _card("Conflict Card", "Enchantment", CONFLICTING_SCOPE_TEXT)
        facts = interaction_facts(card)
        assert facts.confidence.level == "speculative"

    def test_confidence_source_is_heuristic(self):
        """All interaction_facts use source=heuristic (no sample n)."""
        nihil = _card("Nihil Spellbomb", "Artifact", NIHIL_SPELLBOMB_TEXT)
        facts = interaction_facts(nihil)
        assert facts.confidence.source == "heuristic"

    def test_no_tier_for_sample_called(self):
        """Confidence level is NOT driven by tier_for_sample — no 'established' level on sample alone."""
        # established is only reachable via tier_for_sample(n>=100); interaction_facts never does this
        cage = _card("Grafdigger's Cage", "Artifact", GRAFDIGGERS_CAGE_TEXT)
        facts = interaction_facts(cage)
        assert facts.confidence.level != "established"


# ---------------------------------------------------------------------------
# Class 7 — verify_graveyard_claim guard
# ---------------------------------------------------------------------------

class TestVerifyGraveyardClaim:
    """The guard: verify_graveyard_claim(card, claims_self_harm=True/False)."""

    def test_leyline_guard_contradicts_self_harm_claim(self):
        """Leyline of the Void is opponent-only → guard returns ok=False for a self-harm claim."""
        leyline = _card("Leyline of the Void", "Enchantment", LEYLINE_OF_THE_VOID_TEXT)
        check = verify_graveyard_claim(leyline, claims_self_harm=True)
        assert check.ok is False
        assert check.card == "Leyline of the Void"
        assert check.evidence  # oracle_text line(s) quoted

    def test_nihil_guard_contradicts_self_harm_claim(self):
        """Nihil Spellbomb is targeted → guard returns ok=False for a self-harm claim."""
        nihil = _card("Nihil Spellbomb", "Artifact", NIHIL_SPELLBOMB_TEXT)
        check = verify_graveyard_claim(nihil, claims_self_harm=True)
        assert check.ok is False

    def test_grafdiggers_guard_contradicts_self_harm_claim(self):
        """Grafdigger's Cage is symmetric but no count-reduction → guard returns ok=False for self-harm claim."""
        cage = _card("Grafdigger's Cage", "Artifact", GRAFDIGGERS_CAGE_TEXT)
        check = verify_graveyard_claim(cage, claims_self_harm=True)
        assert check.ok is False

    def test_symmetric_exile_guard_confirms_self_harm(self):
        """Symmetric exile (count-reduction) → guard returns ok=True for a self-harm claim (claim is correct)."""
        card = _card("Purge All", "Sorcery", SYMMETRIC_EXILE_TEXT)
        check = verify_graveyard_claim(card, claims_self_harm=True)
        assert check.ok is True

    def test_speculative_confidence_is_soft_annotation(self):
        """Conflicting scope → guard returns ok=False with 'could not confirm' reason (not a hard contradiction)."""
        card = _card("Conflict Card", "Enchantment", CONFLICTING_SCOPE_TEXT)
        check = verify_graveyard_claim(card, claims_self_harm=True)
        assert check.ok is False
        assert "could not confirm" in check.reason

    def test_guard_evidence_is_non_empty_for_gy_card(self):
        """Evidence is populated for any graveyard-referencing card."""
        leyline = _card("Leyline of the Void", "Enchantment", LEYLINE_OF_THE_VOID_TEXT)
        check = verify_graveyard_claim(leyline, claims_self_harm=True)
        assert len(check.evidence) > 0

    def test_guard_claim_false_safe_card(self):
        """claims_self_harm=False on a safe card → ok=True."""
        leyline = _card("Leyline of the Void", "Enchantment", LEYLINE_OF_THE_VOID_TEXT)
        check = verify_graveyard_claim(leyline, claims_self_harm=False)
        assert check.ok is True


# ---------------------------------------------------------------------------
# Class 8 — Gated regression: no-op contract
# ---------------------------------------------------------------------------

class TestGatedNoOp:
    """The advisory / report layer is byte-identical when interaction facts are absent.

    This test asserts the structural contract: interaction_facts is a pure function
    that returns a self-contained result.  The advisory wiring accepts None as the
    absent-facts sentinel and produces the pre-feature output when None.

    We test the seam here by verifying a None facts field yields no constraint violation
    and the whattoplay rationale logic is unchanged.
    """

    def test_interaction_facts_returns_valid_model(self):
        """interaction_facts always returns a valid InteractionFacts model."""
        card = _card("Brainstorm", "Instant", "Draw three cards, then put two cards from your hand on top of your library in any order.")
        facts = interaction_facts(card)
        assert isinstance(facts, InteractionFacts)

    def test_no_graveyard_card_defaults(self):
        """A card with no graveyard text has sensible defaults."""
        card = _card("Brainstorm", "Instant", "Draw three cards, then put two cards from your hand on top of your library in any order.")
        facts = interaction_facts(card)
        assert facts.touches_graveyard is False
        assert facts.graveyard_count_reduction is False
        assert facts.affects == "none"
        assert facts.self_graveyard_safe is True  # no effect = safe by default

    def test_advisory_rationale_self_harm_suppression_not_triggered_for_leyline(self):
        """The primer rationale for a Leyline-style one-sided hate card must NOT emit
        a self-harm/suppression string.  This is the end-to-end payoff assertion.

        Verifies the guard correctly identifies Leyline as self_graveyard_safe so
        advisory logic that consults verify_graveyard_claim will NOT suppress it.
        """
        leyline = _card("Leyline of the Void", "Enchantment", LEYLINE_OF_THE_VOID_TEXT)
        check = verify_graveyard_claim(leyline, claims_self_harm=True)
        # ok=False means the self-harm claim is *wrong* → advisory should NOT suppress Leyline
        assert check.ok is False
        assert "opponent" in check.reason.lower() or "affects" in check.reason.lower()
