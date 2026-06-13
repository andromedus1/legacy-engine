"""Labeler — end-to-end: load a tournament, classify every deck, persist decks.archetype.

Extended with variant regression tests:
- registry=None → variant column stays NULL (byte-identical to pre-variant behaviour)
- with a registry → correct variant tag written per deck
"""

from __future__ import annotations

from legacy_engine.archetype.labeler import label_decks
from legacy_engine.archetype.rules import ArchetypeRule, Condition, RuleSet
from legacy_engine.ingestion import store
from legacy_engine.ingestion.cache import parse_cache_item
from legacy_engine.models.card import Card
from legacy_engine.models.variant import VariantRegistry, VariantRule

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


# ---------------------------------------------------------------------------
# Variant regression tests (gated-additive contract)
# ---------------------------------------------------------------------------

# Minimal variant registry.
# In the test RULES fixture, matching "Tempo" (the variant of "Delver") gives
# base_archetype="Tempo" (not "Dimir Tempo" — that's the color-prefixed display label).
# The variant registry keys on base_archetype, so parent="Tempo" is correct here.
_VARIANT_REGISTRY = VariantRegistry(
    version="test",
    variants=[
        VariantRule(
            parent="Tempo",
            name="Daze Variant",
            conditions=[Condition(type="InMainboard", cards=["Daze"])],
        ),
        VariantRule(
            parent="Tempo",
            name="non-Daze",
            conditions=[Condition(type="DoesNotContain", cards=["Daze"])],
        ),
    ],
    defaults={},
)

# Alice's deck matches the "Tempo" variant rule + has Daze in main → "Daze Variant"
ALICE_ARCHETYPE = "Dimir Tempo"


def test_no_registry_variant_is_null():
    """When registry=None the variant column stays NULL — byte-identical to pre-variant behaviour."""
    con = store.connect(":memory:")
    tid = store.load_tournament(con, parse_cache_item(TOURNEY, "MTGO"))
    label_decks(con, RULES, CARD_DB.get, registry=None)

    rows = {
        player: variant
        for player, variant in con.execute(
            "SELECT player, variant FROM decks WHERE tournament_id = ? ORDER BY deck_idx", [tid]
        ).fetchall()
    }
    assert rows["alice"] is None, "variant should be NULL when no registry is provided"
    assert rows["bob"] is None
    con.close()


def test_with_registry_writes_variant_tag():
    """When registry is provided, label_decks writes the resolved variant tag."""
    con = store.connect(":memory:")
    tid = store.load_tournament(con, parse_cache_item(TOURNEY, "MTGO"))
    label_decks(con, RULES, CARD_DB.get, registry=_VARIANT_REGISTRY)

    rows = {
        player: variant
        for player, variant in con.execute(
            "SELECT player, variant FROM decks WHERE tournament_id = ? ORDER BY deck_idx", [tid]
        ).fetchall()
    }
    # Alice classified as "Dimir Tempo" and has Daze in main → "Daze Variant"
    assert rows["alice"] == "Daze Variant", f"Got variant: {rows['alice']!r}"
    # Bob classified as "Unknown" → no matching parent in registry → NULL
    assert rows["bob"] is None, f"Got variant for Unknown archetype: {rows['bob']!r}"
    con.close()


def test_archetype_column_unchanged_with_registry():
    """Adding a registry must not alter the archetype column values."""
    con = store.connect(":memory:")
    tid = store.load_tournament(con, parse_cache_item(TOURNEY, "MTGO"))
    label_decks(con, RULES, CARD_DB.get, registry=_VARIANT_REGISTRY)

    rows = {
        player: archetype
        for player, archetype in con.execute(
            "SELECT player, archetype FROM decks WHERE tournament_id = ? ORDER BY deck_idx", [tid]
        ).fetchall()
    }
    assert rows["alice"] == "Dimir Tempo"  # unchanged
    assert rows["bob"] == "Unknown"        # unchanged
    con.close()
