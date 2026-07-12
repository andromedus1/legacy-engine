"""Ban-list snapshots — as-of-date legality + deck-construction validation."""

from __future__ import annotations

import json
from datetime import date

import pytest

from legacy_engine.ingestion.banlist import (
    BAN_EVENTS,
    append_ban_event,
    banlist_as_of,
    current_banlist,
    load_ban_events,
    validate_deck,
)
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


class TestLoadBanEvents:
    """Unit A — curated-JSON BAN_EVENTS loader (epic-stable-era-windows-era-ledger-store)."""

    def _write(self, tmp_path, events: list[dict]) -> "object":
        path = tmp_path / "events.json"
        path.write_text(json.dumps({"events": events}), encoding="utf-8")
        return path

    def test_shipped_events_match_the_original_hardcoded_twelve(self):
        # BAN_EVENTS (bound from the shipped JSON at import) must still carry exactly the
        # original 12 dated events, verbatim — including the non-ASCII card name.
        assert len(BAN_EVENTS) == 12
        assert (date(2022, 1, 1), "Ragavan, Nimble Pilferer",
                "Format-warping UR Delver engine") in BAN_EVENTS
        assert (date(2026, 5, 18), "Undercity Informer",
                "De-power MH3 Oops All Spells") in BAN_EVENTS
        assert any(card == "Troll of Khazad-dûm" for _d, card, _r in BAN_EVENTS)

    def test_loader_sorts_by_date_then_card_regardless_of_file_order(self, tmp_path):
        path = self._write(tmp_path, [
            {"date": "2025-01-01", "card": "Zeta", "reason": "r1"},
            {"date": "2024-01-01", "card": "Alpha", "reason": "r2"},
        ])
        events = load_ban_events(path)
        assert events == (
            (date(2024, 1, 1), "Alpha", "r2"),
            (date(2025, 1, 1), "Zeta", "r1"),
        )

    def test_missing_file_raises_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_ban_events(tmp_path / "nope.json")

    def test_non_list_events_key_fails_fast_citing_path(self, tmp_path):
        path = tmp_path / "events.json"
        path.write_text(json.dumps({"events": "not-a-list"}), encoding="utf-8")
        with pytest.raises(ValueError, match=str(path)):
            load_ban_events(path)

    def test_bad_date_fails_fast(self, tmp_path):
        path = self._write(tmp_path, [{"date": "not-a-date", "card": "X", "reason": "r"}])
        with pytest.raises(ValueError, match="not-a-date"):
            load_ban_events(path)

    def test_missing_card_fails_fast(self, tmp_path):
        path = self._write(tmp_path, [{"date": "2024-01-01", "reason": "r"}])
        with pytest.raises(ValueError, match="card"):
            load_ban_events(path)

    def test_duplicate_date_card_pair_fails_fast(self, tmp_path):
        path = self._write(tmp_path, [
            {"date": "2024-01-01", "card": "X", "reason": "r1"},
            {"date": "2024-01-01", "card": "X", "reason": "r2"},
        ])
        with pytest.raises(ValueError, match="duplicate"):
            load_ban_events(path)


class TestAppendBanEvent:
    """The `eras confirm` write path — Candelabra's real registration lands through this."""

    def test_append_to_absent_file_creates_it(self, tmp_path):
        path = tmp_path / "sub" / "events.json"
        result = append_ban_event(date(2026, 6, 29), "Candelabra of Tawnos", "Tron 4x growth engine", path=path)
        assert result == ((date(2026, 6, 29), "Candelabra of Tawnos", "Tron 4x growth engine"),)
        assert path.exists()

    def test_append_round_trips_through_load(self, tmp_path):
        path = tmp_path / "events.json"
        append_ban_event(date(2026, 1, 1), "Alpha", "r1", path=path)
        append_ban_event(date(2026, 2, 1), "Beta", "r2", path=path)
        events = load_ban_events(path)
        assert events == (
            (date(2026, 1, 1), "Alpha", "r1"),
            (date(2026, 2, 1), "Beta", "r2"),
        )

    def test_append_keeps_file_sorted_by_date(self, tmp_path):
        path = tmp_path / "events.json"
        append_ban_event(date(2026, 6, 1), "Late", "r1", path=path)
        result = append_ban_event(date(2026, 1, 1), "Early", "r2", path=path)
        assert [c for _d, c, _r in result] == ["Early", "Late"]

    def test_duplicate_date_and_card_rejected(self, tmp_path):
        path = tmp_path / "events.json"
        append_ban_event(date(2026, 1, 1), "Alpha", "r1", path=path)
        with pytest.raises(ValueError, match="already has an event"):
            append_ban_event(date(2026, 1, 1), "Alpha", "r2", path=path)

    def test_non_ascii_card_name_round_trips_verbatim(self, tmp_path):
        path = tmp_path / "events.json"
        append_ban_event(date(2026, 1, 1), "Troll of Khazad-dûm", "reason", path=path)
        events = load_ban_events(path)
        assert events[0][1] == "Troll of Khazad-dûm"
        # And the file itself carries the literal UTF-8 character (ensure_ascii=False).
        raw = path.read_text(encoding="utf-8")
        assert "Khazad-dûm" in raw
