"""Ban-list snapshots — as-of-date legality + deck-construction validation."""

from __future__ import annotations

from datetime import date

from legacy_engine.ingestion.banlist import banlist_as_of, current_banlist, validate_deck
from legacy_engine.models.banlist import CATEGORY_BANNED_NAMES


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

    def test_legality_at_exact_ban_date_boundary(self):
        # Pin the half-open semantics (SPEC: a ban takes effect ON banned_date).
        # Psychic Frog banned 2024-12-16: legal the day before, illegal on the day itself.
        assert banlist_as_of(date(2024, 12, 15)).is_legal("Psychic Frog")
        assert banlist_as_of(date(2024, 12, 16)).is_banned("Psychic Frog")


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


class TestNonpositiveCounts:
    """Finding #7 — nonpositive counts must be flagged (finding #7)."""

    def test_negative_count_flagged(self):
        errors = validate_deck({"Brainstorm": -1})
        assert any("nonpositive count" in e for e in errors), errors

    def test_zero_count_flagged(self):
        errors = validate_deck({"Brainstorm": 0})
        assert any("nonpositive count" in e for e in errors), errors

    def test_positive_count_not_flagged(self):
        # No nonpositive-count error for a normal deck.
        errors = validate_deck({"Island": 60})
        assert not any("nonpositive count" in e for e in errors)

    def test_negative_sideboard_count_not_masked_by_maindeck(self):
        # A negative count in one zone must not be hidden by positive copies of the same
        # card in the other zone — the guard is per-zone, not on the merged total.
        errors = validate_deck({"Island": 60, "Brainstorm": 4}, {"Brainstorm": -1})
        assert any("nonpositive count" in e and "sideboard" in e for e in errors), errors


class TestCategoryBans:
    """Finding #7 — CATEGORY_BANNED_NAMES are flagged regardless of snapshot contents."""

    def _bare_snapshot(self):
        """A snapshot with an empty banned set (category names not present in it)."""
        from legacy_engine.models.banlist import BanListSnapshot
        return BanListSnapshot(as_of=date(2024, 1, 1), banned=frozenset())

    def test_ante_card_flagged_even_when_not_in_snapshot(self):
        # "Contract from Below" is in CATEGORY_BANNED_NAMES but NOT in the bare snapshot.
        deck = {"Island": 59, "Contract from Below": 1}
        errors = validate_deck(deck, snapshot=self._bare_snapshot())
        assert any("Contract from Below" in e and "ante/offensive" in e for e in errors), errors

    def test_offensive_card_flagged(self):
        deck = {"Island": 59, "Invoke Prejudice": 1}
        errors = validate_deck(deck, snapshot=self._bare_snapshot())
        assert any("Invoke Prejudice" in e and "ante/offensive" in e for e in errors), errors

    def test_category_banned_names_non_empty(self):
        # Sanity check: the set has exactly the expected 16 cards.
        assert len(CATEGORY_BANNED_NAMES) == 16

    def test_all_expected_names_present(self):
        expected = {
            "Amulet of Quoz", "Bronze Tablet", "Contract from Below", "Darkpact",
            "Demonic Attorney", "Jeweled Bird", "Rebirth", "Tempest Efreet", "Timmerian Fiends",
            "Invoke Prejudice", "Cleanse", "Stone-Throwing Devils", "Pradesh Gypsies",
            "Jihad", "Imprison", "Crusade",
        }
        assert expected == CATEGORY_BANNED_NAMES


class TestTypeLineInjection:
    """Finding #7 — optional type_line_of resolver for Conspiracy/Attraction/Sticker."""

    def _bare_snapshot(self):
        from legacy_engine.models.banlist import BanListSnapshot
        return BanListSnapshot(as_of=date(2024, 1, 1), banned=frozenset())

    def test_conspiracy_card_flagged_with_injected_resolver(self):
        def type_line_of(name: str) -> str | None:
            return "Conspiracy" if name == "Lurker" else None

        deck = {"Island": 59, "Lurker": 1}
        errors = validate_deck(deck, snapshot=self._bare_snapshot(), type_line_of=type_line_of)
        assert any("Lurker" in e and "not Legacy-legal" in e for e in errors), errors

    def test_attraction_card_flagged_with_injected_resolver(self):
        def type_line_of(name: str) -> str | None:
            return "Artifact — Attraction" if name == "Dart Throw" else None

        deck = {"Island": 59, "Dart Throw": 1}
        errors = validate_deck(deck, snapshot=self._bare_snapshot(), type_line_of=type_line_of)
        assert any("Dart Throw" in e and "not Legacy-legal" in e for e in errors), errors

    def test_sticker_card_flagged_with_injected_resolver(self):
        def type_line_of(name: str) -> str | None:
            return "Enchantment — Sticker" if name == "_____ Bird Gets the Worm" else None

        deck = {"Island": 59, "_____ Bird Gets the Worm": 1}
        errors = validate_deck(deck, snapshot=self._bare_snapshot(), type_line_of=type_line_of)
        assert any("not Legacy-legal" in e for e in errors), errors

    def test_none_resolver_does_not_crash_or_add_type_line_error(self):
        """When type_line_of is None, no type-line errors and no exception."""
        deck = {"Island": 60}
        errors = validate_deck(deck, snapshot=self._bare_snapshot(), type_line_of=None)
        assert not any("not Legacy-legal" in e for e in errors)

    def test_none_resolver_is_the_default(self):
        """Default call (no type_line_of arg) must not crash."""
        errors = validate_deck({"Island": 60})
        assert not any("not Legacy-legal" in e for e in errors)
