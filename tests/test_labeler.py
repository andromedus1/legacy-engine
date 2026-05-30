"""Labeler — end-to-end: load a tournament, classify every deck, persist decks.archetype."""

from __future__ import annotations

from legacy_engine.archetype.labeler import label_decks
from legacy_engine.archetype.rules import ArchetypeRule, Condition, RuleSet
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item
from legacy_engine.models.card import Card

# A fake card resolver (name -> Card) so the test needs no Scryfall bulk.
CARD_DB = {
    "Delver of Secrets": Card(name="Delver of Secrets", type_line="Creature — Human Wizard", colors=["U"]),
    "Daze": Card(name="Daze", type_line="Instant", colors=["U"]),
    "Underground Sea": Card(name="Underground Sea", type_line="Land — Island Swamp", produced_mana=["U", "B"]),
    "Thoughtseize": Card(name="Thoughtseize", type_line="Sorcery", colors=["B"]),
    "Llanowar Elves": Card(name="Llanowar Elves", type_line="Creature — Elf Druid", colors=["G"]),
    "Forest": Card(name="Forest", type_line="Basic Land — Forest", produced_mana=["G"]),
}

RULES = RuleSet(
    archetypes=[
        ArchetypeRule(
            name="Delver",
            include_color_in_name=True,
            conditions=[
                Condition(type="InMainboard", cards=["Delver of Secrets"]),
                Condition(type="DoesNotContain", cards=["Show and Tell"]),
            ],
            variants=[
                ArchetypeRule(
                    name="Tempo", include_color_in_name=True,
                    conditions=[Condition(type="OneOrMoreInMainboard", cards=["Daze", "Wasteland"])],
                )
            ],
        )
    ],
    fallbacks=[],  # no fallback → unmatched decks are Unknown
)

TOURNEY = {
    "Tournament": {"Name": "Legacy Challenge", "Date": "2026-05-24",
                   "Uri": "https://www.mtgo.com/decklist/legacy-challenge-2026-05-24", "Formats": "Legacy"},
    "Decks": [
        {"Player": "alice", "Result": "1st",
         "Mainboard": [{"Count": 4, "CardName": "Delver of Secrets"}, {"Count": 4, "CardName": "Daze"},
                       {"Count": 4, "CardName": "Underground Sea"}, {"Count": 4, "CardName": "Thoughtseize"}],
         "Sideboard": []},
        {"Player": "bob", "Result": "2nd",
         "Mainboard": [{"Count": 4, "CardName": "Llanowar Elves"}, {"Count": 16, "CardName": "Forest"}],
         "Sideboard": []},
    ],
    "Rounds": [], "Standings": [],
}


def test_labels_decks_end_to_end():
    con = store.connect(":memory:")
    tid = store.load_tournament(con, parse_cache_item(TOURNEY, "MTGO"))

    n = label_decks(con, RULES, CARD_DB.get)
    assert n == 2

    labels = {
        player: arch
        for player, arch in con.execute(
            "SELECT player, archetype FROM decks WHERE tournament_id = ? ORDER BY deck_idx", [tid]
        ).fetchall()
    }
    assert labels["alice"] == "Dimir Tempo"  # Delver + Daze variant, colors U∩(U)+B∩(B) = UB
    assert labels["bob"] == "Unknown"  # no archetype, no fallback
    con.close()


def test_idempotent_relabel():
    con = store.connect(":memory:")
    store.load_tournament(con, parse_cache_item(TOURNEY, "MTGO"))
    label_decks(con, RULES, CARD_DB.get)
    label_decks(con, RULES, CARD_DB.get)  # re-run overwrites, no dup
    assert con.execute("SELECT count(*) FROM decks").fetchone()[0] == 2
    con.close()
