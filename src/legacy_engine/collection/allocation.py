"""Pure derived allocation views — dicts in, reports out, no DB, no filesystem.

Following the objective-search-split pattern: all heavy DB value-computation
is done once upstream (in ``collection/store.py`` or the CLI); this module
receives plain dicts and returns buildability / contention reports.  Every
function here is unit-testable with hand-built inputs.

Key design decisions:
  - Allocation is **derived, not stored**: a card is "allocated" iff it appears
    in some deck's *current* version.  Free-in-binder = owned − allocated.
  - **Contention is reported, not enforced**: two decks may both "use" the same
    physical copy.  ``contention()`` surfaces overlaps loudly so the user can
    decide what to do; no write-time lock is imposed.
  - **Printing-aware is gated**: when ``printing`` keys are absent (``None``),
    the name-only path is the always-works baseline.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BuildabilityReport:
    """Can the user build ``deck_name`` from their current collection?

    ``missing`` maps card name → shortfall count (cards needed but not owned).
    ``buildable`` is ``True`` iff ``missing`` is empty.
    """

    deck_name: str = ""
    buildable: bool = False
    missing: dict[str, int] = field(default_factory=dict)
    # shortfall per card: owned < required
    # value = required − owned for each card in missing


@dataclass
class ContentionEntry:
    """One card that is over-committed across decks.

    ``decks_claiming`` lists every deck whose current version includes the card.
    ``total_claimed`` is the sum across those decks; ``owned`` is the actual
    count in the binder; ``shortfall`` = total_claimed − owned.
    """

    name: str
    owned: int
    total_claimed: int
    shortfall: int
    decks_claiming: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core pure functions
# ---------------------------------------------------------------------------


def buildability(
    deck_main: dict[str, int],
    deck_side: dict[str, int],
    owned_counts: dict[str, int],
    *,
    deck_name: str = "",
) -> BuildabilityReport:
    """Return a BuildabilityReport: can ``owned_counts`` cover the whole 75?

    ``deck_main`` / ``deck_side`` map card name → count for the current
    version's main and sideboard.  ``owned_counts`` maps card name → total
    owned (any printing, unless callers pass printing-keyed dicts).

    A card is "missing" iff ``required > owned``.  The shortfall in
    ``missing`` is ``required − owned``.  Zero shortfall → buildable.
    """
    combined: dict[str, int] = {}
    for name, cnt in deck_main.items():
        combined[name] = combined.get(name, 0) + cnt
    for name, cnt in deck_side.items():
        combined[name] = combined.get(name, 0) + cnt

    missing: dict[str, int] = {}
    for name, required in combined.items():
        owned = owned_counts.get(name, 0)
        if required > owned:
            missing[name] = required - owned

    return BuildabilityReport(
        deck_name=deck_name,
        buildable=len(missing) == 0,
        missing=missing,
    )


def free_binder(
    owned_counts: dict[str, int],
    allocated_counts: dict[str, int],
) -> dict[str, int]:
    """Return cards free in the binder (owned − allocated across current versions).

    ``allocated_counts`` maps card name → total copies claimed by all current
    deck versions combined.  The result maps card name → free count (≥ 0;
    negative would mean over-committed, which is also a contention signal).

    Note: only cards that appear in ``owned_counts`` are included in the result.
    """
    result: dict[str, int] = {}
    for name, owned in owned_counts.items():
        allocated = allocated_counts.get(name, 0)
        result[name] = max(0, owned - allocated)
    return result


def contention(
    per_deck_current_cards: dict[str, dict[str, int]],
    owned_counts: dict[str, int],
) -> list[ContentionEntry]:
    """Report cards over-committed across multiple decks.

    ``per_deck_current_cards`` maps deck_name → {card_name: count} for the
    combined (main + side) current version of each deck.  ``owned_counts``
    maps card_name → owned count.

    Returns a list of ``ContentionEntry`` for each card whose total claimed
    count exceeds the owned count, sorted by shortfall descending.

    Design: contention is a *reported overlap*, not a write-time lock.  Two
    decks can "use" the same copy.  This surface lets the user decide.
    """
    # Accumulate total claimed per card across all decks.
    total_claimed: dict[str, int] = {}
    decks_per_card: dict[str, list[str]] = {}

    for deck_name, cards in per_deck_current_cards.items():
        for card_name, cnt in cards.items():
            total_claimed[card_name] = total_claimed.get(card_name, 0) + cnt
            decks_per_card.setdefault(card_name, []).append(deck_name)

    entries: list[ContentionEntry] = []
    for card_name, claimed in total_claimed.items():
        owned = owned_counts.get(card_name, 0)
        if claimed > owned:
            entries.append(
                ContentionEntry(
                    name=card_name,
                    owned=owned,
                    total_claimed=claimed,
                    shortfall=claimed - owned,
                    decks_claiming=sorted(decks_per_card[card_name]),
                )
            )

    return sorted(entries, key=lambda e: (-e.shortfall, e.name))


def aggregate_owned(
    entries: "list",  # list[InventoryEntry] — typed as list to avoid a circular import
    *,
    name: str,
    printing: str | None = None,
) -> int:
    """Aggregate owned count for a card name (and optionally printing) across entries.

    When ``printing`` is ``None``, sums all entries matching ``name`` regardless
    of printing (name-level baseline).  When ``printing`` is set, returns only
    copies of that exact printing.

    This is a pure helper; callers supply the entry list (from
    ``load_inventory``).
    """
    total = 0
    for e in entries:
        if e.name != name:
            continue
        if printing is not None and e.printing != printing:
            continue
        total += e.count
    return total
