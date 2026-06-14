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
    the name-only path is the always-works baseline.  The printing-aware
    functions (``*_physical``) operate on ``PhysicalKey``-keyed dicts; they are
    purely additive and never called when printing data is absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NamedTuple


class PhysicalKey(NamedTuple):
    """Identity tuple for one physical card copy in the binder.

    Mirrors ``InventoryEntry``'s identity: (name, printing, condition, foil).
    ``printing`` and ``condition`` default to ``None`` (absent / any); ``foil``
    defaults to ``False``.  Two copies are the same physical bucket iff all
    four fields match.
    """

    name: str
    printing: str | None = None
    condition: str | None = None
    foil: bool = False


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

    ``physical_key`` is set only by ``contention_physical``; it is ``None`` for
    entries produced by the name-level ``contention()`` function (gated-additive).
    """

    name: str
    owned: int
    total_claimed: int
    shortfall: int
    decks_claiming: list[str] = field(default_factory=list)
    physical_key: "PhysicalKey | None" = None


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


# ---------------------------------------------------------------------------
# Printing-aware allocation (gated-additive — name-only path unchanged above)
# ---------------------------------------------------------------------------


def inventory_to_physical(
    entries: "list",  # list[InventoryEntry]
) -> dict[PhysicalKey, int]:
    """Build a ``PhysicalKey → count`` dict from an inventory entry list.

    Groups by the full ``(name, printing, condition, foil)`` identity.  This is
    the typed representation that the ``*_physical`` functions consume.

    Callers: load once upstream (objective-search-split); pass the result dict
    into ``free_binder_physical`` / ``contention_physical`` without re-scanning.
    """
    result: dict[PhysicalKey, int] = {}
    for e in entries:
        key = PhysicalKey(
            name=e.name,
            printing=e.printing,
            condition=e.condition,
            foil=getattr(e, "foil", False),
        )
        result[key] = result.get(key, 0) + e.count
    return result


def deck_to_physical(
    deck_cards: "list",  # list[DeckCardRef]
) -> dict[PhysicalKey, int]:
    """Build a ``PhysicalKey → count`` dict from a list of DeckCardRef objects.

    A ``DeckCardRef`` with ``printing=None`` maps to a key with ``printing=None``
    (unspecified printing — callers compare against owned keys with the same
    printing ``None`` for a name-level match, or a specific printing for a
    printing-pinned match).

    Combine main + side via: ``deck_to_physical(ver.cards)``.
    """
    result: dict[PhysicalKey, int] = {}
    for c in deck_cards:
        key = PhysicalKey(
            name=c.name,
            printing=c.printing,
            condition=None,   # deck refs don't carry condition
            foil=False,       # deck refs don't carry foil
        )
        result[key] = result.get(key, 0) + c.count
    return result


def free_binder_physical(
    owned: dict[PhysicalKey, int],
    allocated: dict[PhysicalKey, int],
) -> dict[PhysicalKey, int]:
    """Return physical copies free in the binder (owned − allocated).

    Operates at ``(name, printing, condition, foil)`` granularity.  Only keys
    present in ``owned`` appear in the result (same contract as ``free_binder``).

    This is the printing-aware complement to ``free_binder``; the name-only
    ``free_binder`` function is unchanged (gated-additive).
    """
    result: dict[PhysicalKey, int] = {}
    for key, count in owned.items():
        alloc = allocated.get(key, 0)
        result[key] = max(0, count - alloc)
    return result


def contention_physical(
    per_deck_physical: dict[str, dict[PhysicalKey, int]],
    owned: dict[PhysicalKey, int],
) -> list[ContentionEntry]:
    """Report physical copies over-committed across multiple decks.

    ``per_deck_physical`` maps deck_name → {PhysicalKey: count} for each deck's
    combined current version.  ``owned`` is the PhysicalKey-keyed binder.

    Returns ``ContentionEntry`` objects where ``physical_key`` is set (never
    ``None`` here — unlike the name-level ``contention``), sorted by shortfall
    descending then by name.  Each entry's ``name`` is the card oracle name;
    ``physical_key`` is the full identity.

    Contention message example:
      "both decks claim the foil mh3:62 copy of Dismember"
    which a caller can render as:
      ``entry.physical_key`` → ``PhysicalKey(name='Dismember', printing='mh3:62',
                                             condition=None, foil=True)``
    """
    total_claimed: dict[PhysicalKey, int] = {}
    decks_per_key: dict[PhysicalKey, list[str]] = {}

    for deck_name, cards in per_deck_physical.items():
        for key, cnt in cards.items():
            total_claimed[key] = total_claimed.get(key, 0) + cnt
            decks_per_key.setdefault(key, []).append(deck_name)

    entries: list[ContentionEntry] = []
    for key, claimed in total_claimed.items():
        owned_cnt = owned.get(key, 0)
        if claimed > owned_cnt:
            entries.append(
                ContentionEntry(
                    name=key.name,
                    owned=owned_cnt,
                    total_claimed=claimed,
                    shortfall=claimed - owned_cnt,
                    decks_claiming=sorted(decks_per_key[key]),
                    physical_key=key,
                )
            )

    return sorted(entries, key=lambda e: (-e.shortfall, e.name))
