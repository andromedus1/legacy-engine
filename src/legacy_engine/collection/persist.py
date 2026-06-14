"""JSON SSOT read/write for Inventory and UserDeck documents.

Raw files under ``data/collection/`` are the source of truth — user-authored,
precious, git-friendly, hand-editable.  DuckDB tables are a rebuildable derived
cache (see ``collection/store.py``).

Layout:
  data/collection/inventory.json       — one Inventory document (single owner)
  data/collection/decks/<deck-id>.json — one UserDeck document per deck

``save_*`` functions always atomically update ``updated`` to the current UTC
timestamp before writing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from legacy_engine.config import COLLECTION_DIR, DECKS_DIR, INVENTORY_PATH, LOCAL_OWNER
from legacy_engine.models.collection import Inventory, UserDeck


def _now_utc() -> str:
    """Current time as a UTC ISO-8601 string (no microseconds)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


def load_inventory(owner: str = LOCAL_OWNER) -> Inventory:
    """Load the Inventory for ``owner`` from JSON, or return an empty one.

    Tolerates a missing file — returns a fresh ``Inventory(owner=owner)`` so
    callers can treat "no inventory yet" and "empty inventory" uniformly.
    """
    if not INVENTORY_PATH.exists():
        return Inventory(owner=owner)
    raw = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    inv = Inventory.model_validate(raw)
    # Owner scoping: if the stored doc has a different owner, return empty.
    # (Single-user now; future multi-user would maintain per-owner files.)
    if inv.owner != owner:
        return Inventory(owner=owner)
    return inv


def save_inventory(inv: Inventory) -> None:
    """Persist the Inventory to ``data/collection/inventory.json``.

    Updates ``inv.updated`` to now (UTC) before writing.  Creates the
    ``data/collection/`` directory if absent.
    """
    COLLECTION_DIR.mkdir(parents=True, exist_ok=True)
    inv = inv.model_copy(update={"updated": _now_utc()})
    INVENTORY_PATH.write_text(
        json.dumps(inv.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# UserDecks
# ---------------------------------------------------------------------------


def _deck_path(deck_id: str) -> Path:
    return DECKS_DIR / f"{deck_id}.json"


def load_user_deck(deck_id: str) -> UserDeck | None:
    """Load a UserDeck by id, or ``None`` if the file does not exist."""
    path = _deck_path(deck_id)
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return UserDeck.model_validate(raw)


def save_user_deck(deck: UserDeck) -> None:
    """Persist a UserDeck to ``data/collection/decks/<id>.json``.

    Updates ``deck.updated`` to now (UTC) before writing.  Creates the
    ``data/collection/decks/`` directory if absent.
    """
    DECKS_DIR.mkdir(parents=True, exist_ok=True)
    deck = deck.model_copy(update={"updated": _now_utc()})
    _deck_path(deck.id).write_text(
        json.dumps(deck.model_dump(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def list_user_decks(owner: str = LOCAL_OWNER) -> list[UserDeck]:
    """Return all UserDeck documents for ``owner``, sorted by name."""
    if not DECKS_DIR.exists():
        return []
    decks = []
    for path in sorted(DECKS_DIR.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            deck = UserDeck.model_validate(raw)
            if deck.owner == owner:
                decks.append(deck)
        except Exception:
            continue  # tolerate corrupt files; log in caller if needed
    return sorted(decks, key=lambda d: d.name.lower())


def find_deck_by_name(name: str, owner: str = LOCAL_OWNER) -> UserDeck | None:
    """Find a UserDeck by its human-readable name (case-insensitive exact match).

    Returns the first match if multiple decks share the name (shouldn't happen,
    but tolerated).  Returns ``None`` if not found.
    """
    for deck in list_user_decks(owner):
        if deck.name.lower() == name.lower():
            return deck
    return None
