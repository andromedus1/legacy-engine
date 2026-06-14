"""UserDeck domain operations — save (new deck / append version), load, list, show.

Versioning is **append-only**: every call to ``save_deck`` on an existing deck
appends a new ``DeckVersion`` (new UUID, version+1) and updates
``current_version_id``.  Prior versions are immutable.

``format_decklist`` (from ``generation.export``) is used for the ``deck load``
export path, keeping the round-trip contract: ``parse(format(deck)) == deck``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from legacy_engine.config import LOCAL_OWNER
from legacy_engine.models.collection import DeckCardRef, DeckVersion, UserDeck
from legacy_engine.models.decklist import parse_decklist


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mint_id() -> str:
    """Mint a new stable opaque UUID."""
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Core ops
# ---------------------------------------------------------------------------


def save_deck(
    name: str,
    mainboard: dict[str, int],
    sideboard: dict[str, int] | None = None,
    *,
    owner: str = LOCAL_OWNER,
    deck_id: str | None = None,
    note: str = "",
    label: str = "",
    archetype_hint: str | None = None,
) -> UserDeck:
    """Create a new UserDeck or append a new version to an existing one.

    ``deck_id=None`` → mint a new ``UserDeck`` with version 1.
    ``deck_id=<existing-id>`` → load the existing deck and append a new version.

    The caller is responsible for persisting the returned deck via
    ``collection.persist.save_user_deck``.

    Returns the updated (or newly created) UserDeck.
    """
    from legacy_engine.collection.persist import load_user_deck

    sideboard = sideboard or {}
    now = _now_utc()

    # Build the DeckCardRef list for the new version.
    cards: list[DeckCardRef] = []
    for card_name, count in sorted(mainboard.items()):
        cards.append(DeckCardRef(name=card_name, count=count, board="main"))
    for card_name, count in sorted(sideboard.items()):
        cards.append(DeckCardRef(name=card_name, count=count, board="side"))

    new_version = DeckVersion(
        id=_mint_id(),
        version=1,
        label=label,
        cards=cards,
        created=now,
        note=note,
    )

    if deck_id is None:
        # New deck.
        deck = UserDeck(
            id=_mint_id(),
            owner=owner,
            name=name,
            archetype_hint=archetype_hint,
            versions=[new_version],
            current_version_id=new_version.id,
            created=now,
            updated=now,
        )
    else:
        # Append new version to existing deck.
        existing = load_user_deck(deck_id)
        if existing is None:
            raise ValueError(f"save_deck: no deck found with id {deck_id!r}")
        next_version_num = max((v.version for v in existing.versions), default=0) + 1
        new_version = new_version.model_copy(update={"version": next_version_num})
        deck = existing.model_copy(
            update={
                "name": name,  # allow rename on new-version
                "archetype_hint": archetype_hint if archetype_hint is not None else existing.archetype_hint,
                "versions": [*existing.versions, new_version],
                "current_version_id": new_version.id,
                "updated": now,
            }
        )

    return deck


def current_version(deck: UserDeck) -> DeckVersion | None:
    """Return the current DeckVersion for this deck, or None if no versions exist."""
    if not deck.versions:
        return None
    if deck.current_version_id:
        for v in deck.versions:
            if v.id == deck.current_version_id:
                return v
    # Fallback: the last appended version.
    return deck.versions[-1]


def current_cards(deck: UserDeck) -> tuple[dict[str, int], dict[str, int]]:
    """Return ``(mainboard, sideboard)`` dicts for the current version.

    Returns ``({}, {})`` if the deck has no versions.
    """
    ver = current_version(deck)
    if ver is None:
        return {}, {}
    main: dict[str, int] = {}
    side: dict[str, int] = {}
    for c in ver.cards:
        if c.board == "side":
            side[c.name] = side.get(c.name, 0) + c.count
        else:
            main[c.name] = main.get(c.name, 0) + c.count
    return main, side


def get_version_by_number(deck: UserDeck, version_num: int) -> DeckVersion | None:
    """Look up a specific version by its monotonic version number."""
    for v in deck.versions:
        if v.version == version_num:
            return v
    return None


def export_deck_text(deck: UserDeck, version_num: int | None = None) -> str:
    """Export the deck's current (or specified) version as plain-text decklist.

    Delegates to ``generation.export.format_decklist`` so the export format is
    byte-compatible with every other command's ``--deck FILE`` input.
    """
    from legacy_engine.generation.export import format_decklist

    if version_num is not None:
        ver = get_version_by_number(deck, version_num)
        if ver is None:
            raise ValueError(f"export_deck_text: version {version_num} not found in deck {deck.name!r}")
    else:
        ver = current_version(deck)
        if ver is None:
            raise ValueError(f"export_deck_text: deck {deck.name!r} has no versions")

    main: dict[str, int] = {}
    side: dict[str, int] = {}
    for c in ver.cards:
        if c.board == "side":
            side[c.name] = side.get(c.name, 0) + c.count
        else:
            main[c.name] = main.get(c.name, 0) + c.count

    return format_decklist(main, side)


def save_deck_from_file(
    deck_file_text: str,
    name: str,
    *,
    owner: str = LOCAL_OWNER,
    deck_id: str | None = None,
    note: str = "",
    label: str = "",
    archetype_hint: str | None = None,
) -> UserDeck:
    """Parse a plain-text decklist file and save it as a deck (or new version).

    Convenience wrapper over ``save_deck`` that calls ``parse_decklist`` first.
    """
    mainboard, sideboard = parse_decklist(deck_file_text)
    return save_deck(
        name,
        mainboard,
        sideboard,
        owner=owner,
        deck_id=deck_id,
        note=note,
        label=label,
        archetype_hint=archetype_hint,
    )
