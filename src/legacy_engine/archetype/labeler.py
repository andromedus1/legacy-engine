"""Labeler — assign an archetype to every ingested deck in DuckDB.

End-to-end: read each deck's cards from the store, resolve names to Cards (for color computation),
compute deck colors, classify against the loaded ruleset, and persist the label into
``decks.archetype`` (the column ingestion left NULL). Conflict/Unknown labels are written raw.

``resolve_card`` is injected (name -> Card | None) so this is testable without the Scryfall bulk; the
CLI passes ``ScryfallClient.get_card``.
"""

from __future__ import annotations

from collections.abc import Callable

from legacy_engine.archetype.matcher import classify
from legacy_engine.archetype.rules import RuleSet
from legacy_engine.colors import compute_deck_colors
from legacy_engine.ingestion import store
from legacy_engine.models.card import Card


def label_decks(con, ruleset: RuleSet, resolve_card: Callable[[str], Card | None]) -> int:
    """Classify every deck in the store and write its archetype. Returns the count labeled."""
    store.init_schema(con)
    deck_keys = con.execute("SELECT tournament_id, deck_idx FROM decks").fetchall()

    labeled = 0
    for tid, idx in deck_keys:
        rows = con.execute(
            "SELECT board, name, count FROM deck_cards WHERE tournament_id = ? AND deck_idx = ?",
            [tid, idx],
        ).fetchall()

        mainboard: dict[str, int] = {}
        sideboard: dict[str, int] = {}
        cards: list[Card] = []
        for board, name, count in rows:
            target = mainboard if board == "main" else sideboard
            target[name] = target.get(name, 0) + count
            card = resolve_card(name)
            if card is not None:
                cards.append(card)

        colors = compute_deck_colors(cards)
        result = classify(mainboard, sideboard, ruleset, colors)
        con.execute(
            "UPDATE decks SET archetype = ? WHERE tournament_id = ? AND deck_idx = ?",
            [result.archetype, tid, idx],
        )
        labeled += 1

    return labeled
