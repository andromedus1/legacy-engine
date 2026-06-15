"""CacheItem parsing — provenance, Challenge/League/Melee shapes, round flattening."""

from __future__ import annotations

import pytest

from legacy_engine.ingestion.cache import _coerce_format, derive_provenance, parse_cache_item, parse_rounds

CHALLENGE = {
    "Tournament": {
        "Name": "Legacy Challenge 32",
        "Date": "2026-05-24",
        "Uri": "https://www.mtgo.com/decklist/legacy-challenge-32-2026-05-24",
        "Formats": "Legacy",
    },
    "Decks": [
        {
            "Player": "alice",
            "Result": "1st Place",
            "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
            "Sideboard": [{"Count": 2, "CardName": "Surgical Extraction"}],
        }
    ],
    "Rounds": [{"Player1": "alice", "Player2": "bob", "Result": "2-1"}],
    "Standings": [{"Rank": 1, "Player": "alice", "Points": 18, "Wins": 6, "Losses": 1, "Draws": 0}],
}

LEAGUE = {
    "Tournament": {"Name": "Legacy League", "Date": "2026-05-24",
                   "Uri": "https://www.mtgo.com/decklist/legacy-league-2026-05-24", "Formats": "Legacy"},
    "Decks": [{"Player": "carol", "Result": "5-0", "Mainboard": [{"Count": 4, "CardName": "Ponder"}], "Sideboard": []}],
    "Rounds": [],
    "Standings": [],
}

MELEE = {
    "Tournament": {"Name": "Eternal Weekend Legacy", "Date": "2026-05-24",
                   "Uri": "https://melee.gg/Tournament/View/12345", "Formats": "Legacy"},
    "Decks": [{"Player": "dave", "Result": "Top 8", "Mainboard": [{"Count": 4, "CardName": "Force of Will"}], "Sideboard": []}],
    "Rounds": [{"RoundName": "Round 1", "Matches": [{"Player1": "dave", "Player2": "erin", "Result": "2-0"}]}],
    "Standings": [{"Rank": 5, "Player": "dave", "Points": 21}],
}


class TestDeriveProvenance:
    @pytest.mark.parametrize(
        "source,uri,expected",
        [
            ("MTGO", None, "online"),
            ("MTGmelee", None, "paper"),
            ("Topdeck", None, "paper"),
            ("", "https://www.mtgo.com/x", "online"),
            ("", "https://melee.gg/x", "paper"),
            ("", None, "unknown"),
        ],
    )
    def test_provenance(self, source, uri, expected):
        assert derive_provenance(source, uri) == expected


class TestBadDeckResilience:
    """Resilience NFR: one malformed deck is dropped (logged), not fatal to the event."""

    _MALFORMED_DECK = {"Player": "mallory", "Mainboard": [{"Count": "not-an-int", "CardName": "Foo"}]}

    def test_one_bad_deck_does_not_drop_the_event(self, caplog):
        raw = {
            "Tournament": {"Name": "Legacy Challenge", "Date": "2026-05-25", "Formats": "Legacy"},
            "Decks": [
                {"Player": "alice", "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}]},
                self._MALFORMED_DECK,
                {"Player": "bob", "Mainboard": [{"Count": 4, "CardName": "Ponder"}]},
            ],
            "Rounds": [],
            "Standings": [],
        }
        with caplog.at_level("WARNING"):
            result = parse_cache_item(raw, "MTGO")
        assert [d.player for d in result.decks] == ["alice", "bob"]  # bad deck dropped, event kept
        assert "malformed deck" in caplog.text.lower()  # logged, not silent

    def test_all_good_decks_kept(self):
        raw = {
            "Tournament": {"Name": "x", "Date": "2026-05-25", "Formats": "Legacy"},
            "Decks": [{"Player": "a", "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}]}],
            "Rounds": [],
            "Standings": [],
        }
        assert len(parse_cache_item(raw, "MTGO").decks) == 1


class TestParseRounds:
    def test_flat_matches(self):
        rounds = parse_rounds([{"Player1": "a", "Player2": "b", "Result": "2-1"}])
        assert len(rounds) == 1 and rounds[0].player1 == "a"

    def test_nested_matches(self):
        rounds = parse_rounds([{"RoundName": "R1", "Matches": [{"Player1": "a", "Player2": "b", "Result": "2-0"}]}])
        assert len(rounds) == 1 and rounds[0].result == "2-0"

    def test_bye_null_player2_coerced_to_empty(self):
        """A bye carries an explicit null Player2 in the fbettega cache — must not crash ingest.

        Regression: the field default only applies when the key is absent; an explicit null
        previously failed str validation. A bye is parsed as an empty opponent (dropped downstream).
        """
        rounds = parse_rounds([{"Player1": "alice", "Player2": None, "Result": None}])
        assert len(rounds) == 1
        assert rounds[0].player1 == "alice"
        assert rounds[0].player2 == ""
        assert rounds[0].result == ""

    def test_nested_bye_null_player2(self):
        rounds = parse_rounds([{"Matches": [{"Player1": "a", "Player2": None, "Result": "2-0"}]}])
        assert len(rounds) == 1 and rounds[0].player2 == ""


class TestParseCacheItem:
    def test_challenge(self):
        t = parse_cache_item(CHALLENGE, "MTGO")
        assert t.provenance == "online" and t.format == "Legacy"
        assert len(t.decks) == 1 and len(t.rounds) == 1 and len(t.standings) == 1
        assert t.decks[0].mainboard[0].name == "Brainstorm"
        assert t.standings[0].rank == 1

    def test_league_empty_rounds_is_normal(self):
        t = parse_cache_item(LEAGUE, "MTGO")
        assert t.provenance == "online"
        assert len(t.decks) == 1 and t.decks[0].result == "5-0"
        assert t.rounds == [] and t.standings == []  # not an error

    def test_melee_paper_with_nested_rounds(self):
        t = parse_cache_item(MELEE, "MTGmelee")
        assert t.provenance == "paper"
        assert len(t.rounds) == 1 and t.rounds[0].player1 == "dave"  # flattened from Matches


class TestCoerceFormat:
    """Finding #6 — _coerce_format multi-format list handling (hardening)."""

    def test_multi_format_list_with_legacy_returns_legacy(self):
        """["Modern", "Legacy"] must return "Legacy" so the event is not skipped."""
        assert _coerce_format(["Modern", "Legacy"]) == "Legacy"

    def test_multi_format_list_legacy_first_returns_legacy(self):
        assert _coerce_format(["Legacy", "Modern"]) == "Legacy"

    def test_single_element_list_non_legacy_returns_first(self):
        assert _coerce_format(["Modern"]) == "Modern"

    def test_single_element_list_legacy_returns_legacy(self):
        assert _coerce_format(["Legacy"]) == "Legacy"

    def test_empty_list_returns_empty_string(self):
        assert _coerce_format([]) == ""

    def test_bare_string_returned_as_is(self):
        assert _coerce_format("Legacy") == "Legacy"
        assert _coerce_format("Modern") == "Modern"

    def test_falsy_string_returns_empty(self):
        assert _coerce_format("") == ""
        assert _coerce_format(None) == ""
