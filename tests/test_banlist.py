"""Ban-list snapshots — as-of-date legality + deck-construction validation."""

from __future__ import annotations

from datetime import date

from legacy_engine.ingestion.banlist import banlist_as_of, current_banlist, validate_deck


class TestAsOfDate:
    def test_current_includes_latest_ban(self):
        snap = current_banlist()
        assert snap.is_banned("Undercity Informer")
        assert snap.is_banned("Black Lotus")  # baseline
        assert snap.is_legal("Force of Will")  # never banned
        assert snap.is_legal("Brainstorm")

    def test_before_psychic_frog_ban(self):
        snap = banlist_as_of(date(2024, 6, 1))
        assert snap.is_legal("Psychic Frog")  # banned 2024-12-16
        assert snap.is_legal("Entomb")  # banned 2025-11-10
        assert snap.is_legal("Grief")  # banned 2024-08-26
        assert snap.is_banned("Ragavan, Nimble Pilferer")  # banned 2022
        assert snap.is_banned("Black Lotus")  # baseline

    def test_after_psychic_frog_before_entomb(self):
        snap = banlist_as_of(date(2025, 1, 1))
        assert snap.is_banned("Psychic Frog")
        assert snap.is_legal("Entomb")

    def test_entomb_banned_after_nov_2025(self):
        assert banlist_as_of(date(2026, 1, 1)).is_banned("Entomb")
        assert banlist_as_of(date(2026, 1, 1)).is_legal("Undercity Informer")  # banned 2026-05-18


class TestValidateDeck:
    def _legal_60(self):
        # 20 basics + ten legal 4-ofs = 60, all within the 4-copy rule.
        return {
            "Island": 20,
            "Brainstorm": 4, "Ponder": 4, "Preordain": 4, "Force of Will": 4, "Daze": 4,
            "Murktide Regent": 4, "Wasteland": 4, "Flooded Strand": 4, "Fatal Push": 4, "Spell Pierce": 4,
        }

    def test_legal_deck(self):
        assert validate_deck(self._legal_60()) == []

    def test_banned_card_flagged(self):
        deck = {**self._legal_60(), "Island": 19, "Black Lotus": 1}  # swap one basic for a banned card
        errors = validate_deck(deck)
        assert any("Black Lotus is banned" in e for e in errors)

    def test_too_many_copies(self):
        errors = validate_deck({"Island": 16, "Brainstorm": 5, "Ponder": 4, "Force of Will": 35})
        assert any("Brainstorm: 5 copies" in e for e in errors)

    def test_basics_unlimited(self):
        # 60 Islands is legal (basics exempt from the 4-of rule).
        assert validate_deck({"Island": 60}) == []

    def test_undersized_maindeck(self):
        errors = validate_deck({"Island": 59})
        assert any("minimum 60" in e for e in errors)

    def test_oversized_sideboard(self):
        errors = validate_deck(self._legal_60(), sideboard={"Surgical Extraction": 16})
        assert any("maximum 15" in e for e in errors)

    def test_as_of_date_legality(self):
        # A legal-60 that runs Psychic Frog (swap one basic for the 4-of being tested → still 60).
        deck = {**self._legal_60(), "Island": 16, "Psychic Frog": 4}
        # Legal in mid-2024...
        assert validate_deck(deck, snapshot=banlist_as_of(date(2024, 6, 1))) == []
        # ...banned now.
        assert any("Psychic Frog is banned" in e for e in validate_deck(deck))
