"""Labeler — assign an archetype to every ingested deck in DuckDB.

End-to-end: read each deck's cards from the store, resolve names to Cards (for color computation),
compute deck colors, classify against the loaded ruleset, and persist the label into
``decks.archetype`` (the column ingestion left NULL). Conflict/Unknown labels are written raw.

When an optional ``VariantRegistry`` is provided, also resolves a sub-archetype variant tag
into ``decks.variant`` (new nullable column).  No registry → variant stays NULL → byte-identical
behaviour to the pre-variant codebase (gated-additive contract).

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
from legacy_engine.models.variant import VariantRegistry


def label_decks(
    con,
    ruleset: RuleSet,
    resolve_card: Callable[[str], Card | None],
    registry: VariantRegistry | None = None,
) -> int:
    """Classify every deck in the store and write its archetype (and optional variant).

    Returns the count of decks labeled.

    When ``registry`` is provided, resolves a variant tag for each deck and writes it to
    ``decks.variant``.  When ``registry`` is ``None`` the variant column is left untouched
    (stays NULL) — byte-identical to the pre-variant behaviour.
    """
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

        if registry is not None:
            from legacy_engine.archetype.variants import resolve_variant
            # Key variant resolution on the FINAL display label (result.archetype), not the
            # internal rule name (base_archetype): registry parents are written against what
            # consumers see in decks.archetype, and a color-prefixed base (e.g. 'Delver')
            # spans multiple display archetypes — keying on it would smear one archetype's
            # variant rules across its siblings.
            variant = resolve_variant(result.archetype, mainboard, sideboard, registry)
        else:
            variant = None

        con.execute(
            "UPDATE decks SET archetype = ?, variant = ? WHERE tournament_id = ? AND deck_idx = ?",
            [result.archetype, variant, tid, idx],
        )
        labeled += 1

    return labeled
