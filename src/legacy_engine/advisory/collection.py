"""Collection read port + owned-annotation helpers.

Decouples the recommenders from the sibling ``Inventory`` store so any command
can become collection-aware without importing the persistence layer.  Also
constructible from pasted text (``CollectionView.from_text``) so the feature is
usable before a persistent inventory exists — the dogfood collection was pasted
as a plain list.

Gated-additive no-op contract
------------------------------
``annotate_owned(cards, cv=None)`` returns ``{}`` when ``cv`` is ``None``.
Callers treat the empty dict as "not collection-aware" — no annotations attached,
``collection_aware=False``.  This is the grep-able gate that preserves
byte-identical output for every caller that does not supply a collection.

See ``gated-additive-augmentation`` pattern in ``.claude/rules/patterns.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # avoid circular imports


# ---------------------------------------------------------------------------
# OwnedPrinting — per-printing ownership record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OwnedPrinting:
    """One owned printing of a card.

    ``set_code`` and ``collector_number`` mirror Scryfall's ``set`` + ``cn``
    fields (e.g. ``"mh3"`` / ``"62"``).  Both are optional so the struct can
    be populated from name-only import (text path).

    ``condition`` is free-text (NM / LP / MP / HP / DMG); tolerated as-is.
    ``qty`` is the copy count for this (name, set, cn, condition) bucket.
    """

    set_code: str | None
    collector_number: str | None
    condition: str
    qty: int


# ---------------------------------------------------------------------------
# CollectionView — injected read port
# ---------------------------------------------------------------------------

class CollectionView:
    """Injected read port over the user's owned cards.

    Decouples recommenders from the sibling ``Inventory`` store; also
    constructible from pasted ``<qty> <name>`` text so the feature is usable
    before the persistent store lands.

    Internally stores:
    - ``_qty``:      ``{card_name: total_owned}`` (across all printings).
    - ``_printings``: ``{card_name: [OwnedPrinting, ...]}``.

    All comparisons are case-sensitive on the oracle name (matching the
    engine's convention everywhere else).
    """

    def __init__(
        self,
        qty: dict[str, int],
        printings: dict[str, list[OwnedPrinting]] | None = None,
    ) -> None:
        self._qty: dict[str, int] = dict(qty)
        self._printings: dict[str, list[OwnedPrinting]] = {}
        if printings:
            for name, ps in printings.items():
                self._printings[name] = list(ps)

    # ── Query primitives ────────────────────────────────────────────────────

    def owned_qty(self, card_name: str) -> int:
        """Total copies owned across all printings for ``card_name``."""
        return self._qty.get(card_name, 0)

    def printings(self, card_name: str) -> tuple[OwnedPrinting, ...]:
        """All owned printings for ``card_name`` (empty tuple if none)."""
        return tuple(self._printings.get(card_name, []))

    def is_owned(self, card_name: str, qty: int = 1) -> bool:
        """True iff ``owned_qty(card_name) >= qty``."""
        return self.owned_qty(card_name) >= qty

    # ── Factory: from pasted text ───────────────────────────────────────────

    @classmethod
    def from_text(cls, text: str) -> "CollectionView":
        """Construct from a pasted ``<qty> <name>`` list.

        Uses the same ``parse_decklist`` parser as decklists — both the
        mainboard and sideboard sections are treated as owned cards.

        Blank lines, ``#``-prefixed comments, and the ``Sideboard`` header are
        all handled by ``parse_decklist``.  Raises ``ValueError`` for malformed
        lines (delegated to the parser).
        """
        from legacy_engine.models.decklist import parse_decklist

        mainboard, sideboard = parse_decklist(text)
        qty: dict[str, int] = {}
        for name, count in mainboard.items():
            qty[name] = qty.get(name, 0) + count
        for name, count in sideboard.items():
            qty[name] = qty.get(name, 0) + count
        return cls(qty)

    # ── Factory: from Inventory (sibling dep adapter) ───────────────────────

    @classmethod
    def from_inventory(cls, inv: object) -> "CollectionView":
        """Construct from a sibling ``Inventory`` Pydantic doc.

        Accepts any object with an ``entries`` attribute whose items have
        ``name``, ``count``, ``printing`` (optional), and ``condition``
        (optional) fields — matches ``Inventory`` from
        ``legacy_engine.models.collection``.

        ``printing`` is the ``"set:cn"`` string (e.g. ``"mh3:62"``); we split
        it into ``set_code`` / ``collector_number`` for ``OwnedPrinting``.
        """
        qty: dict[str, int] = {}
        printings: dict[str, list[OwnedPrinting]] = {}

        for entry in getattr(inv, "entries", []):
            name = entry.name
            count = getattr(entry, "count", 1)
            condition = getattr(entry, "condition", None) or "unknown"
            printing_str: str | None = getattr(entry, "printing", None)

            qty[name] = qty.get(name, 0) + count

            # Parse "set:cn" or "set/cn" printing string into fields.
            set_code: str | None = None
            collector_number: str | None = None
            if printing_str:
                for sep in (":", "/"):
                    if sep in printing_str:
                        parts = printing_str.split(sep, 1)
                        set_code = parts[0].strip() or None
                        collector_number = parts[1].strip() or None
                        break

            op = OwnedPrinting(
                set_code=set_code,
                collector_number=collector_number,
                condition=condition,
                qty=count,
            )
            if name not in printings:
                printings[name] = []
            printings[name].append(op)

        return cls(qty, printings)

    # ── repr for debugging ───────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"CollectionView({len(self._qty)} cards, {sum(self._qty.values())} copies)"


# ---------------------------------------------------------------------------
# OwnedAnnotation — per-card ownership annotation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OwnedAnnotation:
    """Per-recommended-card ownership annotation.

    ``owned``: ``owned_copies >= recommended_copies``.
    ``to_acquire``: ``max(0, recommended_copies - owned_copies)``.
    """

    card: str
    recommended_copies: int
    owned_copies: int
    to_acquire: int      # max(0, recommended - owned)
    owned: bool          # owned_copies >= recommended_copies


# ---------------------------------------------------------------------------
# annotate_owned — the gated no-op helper
# ---------------------------------------------------------------------------

def annotate_owned(
    cards: dict[str, int],
    cv: "CollectionView | None",
) -> dict[str, OwnedAnnotation]:
    """Map recommended ``card → copies`` to ownership annotations.

    **Gate contract**: ``cv is None`` → returns ``{}`` immediately.
    Callers treat the empty dict as "not collection-aware" — no annotations,
    ``collection_aware=False``.  This is the explicit no-op gate (grep-able,
    per the ``gated-additive-augmentation`` pattern).

    When ``cv`` is supplied, returns one ``OwnedAnnotation`` per card in
    ``cards``.
    """
    if cv is None:
        return {}  # GATE: no collection → no-op; byte-identical to pre-feature

    result: dict[str, OwnedAnnotation] = {}
    for card, recommended in cards.items():
        owned_qty = cv.owned_qty(card)
        to_acquire = max(0, recommended - owned_qty)
        result[card] = OwnedAnnotation(
            card=card,
            recommended_copies=recommended,
            owned_copies=owned_qty,
            to_acquire=to_acquire,
            owned=owned_qty >= recommended,
        )
    return result
