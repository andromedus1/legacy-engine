"""Inventory domain operations.

Provides text/CSV import, merge/replace semantics, and owner-scoped count
aggregation.  All functions work against ``Inventory`` Pydantic docs in memory;
callers are responsible for loading/saving via ``collection.persist``.

Text import reuses ``models.decklist.parse_decklist`` (the same ``<count> <name>``
format every other command speaks).  The ``printing`` field is not set from the
text path — text is name-only; printing-aware import would require a CSV with
explicit columns (not yet implemented).
"""

from __future__ import annotations

from legacy_engine.config import LOCAL_OWNER
from legacy_engine.models.collection import Inventory, InventoryEntry
from legacy_engine.models.decklist import parse_decklist


def import_inventory(
    text: str,
    *,
    owner: str = LOCAL_OWNER,
    merge: bool = True,
) -> Inventory:
    """Parse a plain-text decklist into an Inventory.

    Uses the standard ``<count> <name>`` format (same as decklists).  Both
    the mainboard and sideboard sections are treated as owned cards (the
    "sideboard" section of a decklist is just a secondary block here — useful
    if someone pastes a full 75 where the 15 live after a blank line).

    ``merge=True`` (default): if the caller supplies an existing inventory via
    a subsequent call, they should merge the returned inventory into their
    existing one using ``merge_inventory``.  This function always returns a
    fresh Inventory built from the text.

    ``merge=False``: the returned Inventory fully *replaces* the existing one
    (but callers must still call ``save_inventory`` to persist it).
    """
    mainboard, sideboard = parse_decklist(text)

    entries_map: dict[tuple[str, None, None, bool], InventoryEntry] = {}

    def _add(name: str, count: int) -> None:
        key = (name, None, None, False)
        if key in entries_map:
            existing = entries_map[key]
            entries_map[key] = existing.model_copy(update={"count": existing.count + count})
        else:
            entries_map[key] = InventoryEntry(name=name, count=count)

    for name, count in mainboard.items():
        _add(name, count)
    for name, count in sideboard.items():
        _add(name, count)

    return Inventory(owner=owner, entries=list(entries_map.values()))


def merge_inventory(
    existing: Inventory,
    incoming: Inventory,
) -> Inventory:
    """Merge ``incoming`` entries into ``existing``, summing overlapping counts.

    Matches entries by ``(name, printing, condition, foil)``.  Returns a new
    Inventory (does not mutate either input).
    """
    # Build a mutable map from the existing entries.
    result: dict[tuple, InventoryEntry] = {}
    for e in existing.entries:
        key = (e.name, e.printing, e.condition, e.foil)
        result[key] = e

    for e in incoming.entries:
        key = (e.name, e.printing, e.condition, e.foil)
        if key in result:
            old = result[key]
            result[key] = old.model_copy(update={"count": old.count + e.count})
        else:
            result[key] = e

    return existing.model_copy(update={"entries": list(result.values())})


def replace_inventory(
    existing: Inventory,
    incoming: Inventory,
) -> Inventory:
    """Replace ``existing`` entries with ``incoming`` entries (same owner).

    Preserves the owner from ``existing``.  Returns a new Inventory.
    """
    return existing.model_copy(update={"entries": list(incoming.entries)})


def owned_count(
    inv: Inventory,
    name: str,
    *,
    printing: str | None = None,
) -> int:
    """Return how many copies of ``name`` the owner has (any printing when ``printing=None``).

    When ``printing`` is given, returns only copies matching that exact printing.
    """
    total = 0
    for e in inv.entries:
        if e.name != name:
            continue
        if printing is not None and e.printing != printing:
            continue
        total += e.count
    return total


def owned_counts_map(inv: Inventory) -> dict[str, int]:
    """Return a ``{card_name: total_owned}`` map, summed across all printings.

    This is the name-level view used by the buildability and contention checks.
    """
    result: dict[str, int] = {}
    for e in inv.entries:
        result[e.name] = result.get(e.name, 0) + e.count
    return result
