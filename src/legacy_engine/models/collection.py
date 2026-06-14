"""Persistent user-collection models: Inventory and UserDeck.

All subclass ``LegacyEngineModel`` (pydantic-base-model pattern: extra="ignore",
populate_by_name).  Every owned entity carries an ``owner`` key (defaulted
``LOCAL_OWNER = "local"``) and every persistent entity a stable UUID id, so a
future hosted/multi-user surface migrates without a schema rewrite.

Versioning is **append-only**: editing a deck appends a new ``DeckVersion``
(new UUID, version+1) and moves ``current_version_id``; prior versions are
immutable.  Allocation (cards → deck vs free binder) is a pure derived view,
not a stored entity — see ``collection/allocation.py``.
"""

from __future__ import annotations

from legacy_engine.models.base import LegacyEngineModel

# The single-user default owner constant — becomes a real user id under a hosted surface.
LOCAL_OWNER = "local"


class InventoryEntry(LegacyEngineModel):
    """One physical-copy bucket in the binder.

    Identity = (name, printing, condition, foil).  The $33-vs-$2 Dismember
    lesson: same oracle name, different printing = materially different copy.
    """

    name: str
    count: int = 1
    printing: str | None = None   # Scryfall set+collector, e.g. "mh3:62" — optional
    condition: str | None = None  # NM/LP/MP/HP/DMG — free text, optional
    foil: bool = False


class Inventory(LegacyEngineModel):
    """The user's complete card binder for one owner.

    ``entries`` is the list of physical-copy buckets.  Aggregate "how many
    <name> do I own across any printing" is a derived query, not stored here.
    """

    owner: str = LOCAL_OWNER
    entries: list[InventoryEntry] = []
    updated: str = ""  # UTC ISO-8601; set on every write


class DeckCardRef(LegacyEngineModel):
    """A card slot in a deck version: oracle name + count + board + optional printing pin."""

    name: str
    count: int
    board: str = "main"           # "main" | "side"
    printing: str | None = None   # pin a version to a specific printing for value/allocation


class DeckVersion(LegacyEngineModel):
    """An immutable snapshot of a deck at a point in time.

    Once created, a ``DeckVersion`` is never mutated in-place — a new version
    is appended instead (append-only versioning).
    """

    id: str                      # stable UUID, immutable once minted
    version: int                 # monotonic per UserDeck, 1-based
    label: str = ""              # optional human tag, e.g. "post-Frog-ban"
    cards: list[DeckCardRef] = []  # the 75 (main + side)
    created: str = ""            # UTC ISO-8601
    note: str = ""               # free-text changelog for this version


class UserDeck(LegacyEngineModel):
    """The user's named, versioned deck — a first-class persistent entity.

    ``id`` is a stable UUID that survives renames (the id, not the name, is
    the primary key; the filename under ``data/collection/decks/`` is
    ``<id>.json``).  ``versions`` is an append-only history; the newest entry
    is the current deck by default but ``current_version_id`` lets the user
    pin to an older version.
    """

    id: str                             # stable UUID — survives renames
    owner: str = LOCAL_OWNER
    name: str                           # user-facing label, mutable, NOT the key
    archetype_hint: str | None = None   # optional user label; engine archetype still inferred
    versions: list[DeckVersion] = []    # append-only history; newest = current by default
    current_version_id: str | None = None  # which version is "the deck" right now
    created: str = ""                   # UTC ISO-8601
    updated: str = ""                   # UTC ISO-8601
