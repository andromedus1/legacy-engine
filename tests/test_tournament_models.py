"""Tournament models — PascalCase alias mapping + defaults."""

from __future__ import annotations

from legacy_engine.models.tournament import CardCount, Deck, RoundMatch, Standing


def test_cardcount_aliases():
    cc = CardCount.model_validate({"Count": 4, "CardName": "Brainstorm"})
    assert cc.count == 4 and cc.name == "Brainstorm"


def test_cardcount_by_python_name():
    cc = CardCount(count=2, name="Daze")
    assert cc.count == 2 and cc.name == "Daze"


def test_round_match_aliases():
    m = RoundMatch.model_validate({"Player1": "alice", "Player2": "bob", "Result": "2-1"})
    assert (m.player1, m.player2, m.result) == ("alice", "bob", "2-1")


def test_standing_aliases_and_defaults():
    s = Standing.model_validate({"Rank": 1, "Player": "alice", "Points": 18, "Wins": 6, "Losses": 1})
    assert s.rank == 1 and s.points == 18 and s.draws == 0  # default


def test_deck_mainboard_sideboard():
    d = Deck.model_validate(
        {"Player": "alice", "Result": "1st Place",
         "Mainboard": [{"Count": 4, "CardName": "Brainstorm"}],
         "Sideboard": [{"Count": 2, "CardName": "Surgical Extraction"}]}
    )
    assert d.player == "alice"
    assert d.mainboard[0].name == "Brainstorm" and d.mainboard[0].count == 4
    assert d.sideboard[0].name == "Surgical Extraction"
