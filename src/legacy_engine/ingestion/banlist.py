"""Legacy ban-list data + as-of-date snapshots + deck-construction validation.

Seeded from docs/briefs/legacy-foundations.md (current to the 2026-05-18 Undercity Informer ban).
BASELINE_BANS are the long-standing bans (effective before our 2022+ tracking window); BAN_EVENTS
are the dated B&R actions, so a snapshot as of date D = BASELINE ∪ (events with date <= D). Update
this module when WotC issues a new B&R announcement.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from legacy_engine.models.banlist import (
    BASIC_LAND_NAMES,
    CATEGORY_BANNED_NAMES,
    COPY_LIMIT_OVERRIDES,
    UNLIMITED_COPIES,
    BanListSnapshot,
)

# Long-standing bans (Power 9, fast mana, broken tutors/draw, and pre-2022 format-warpers).
BASELINE_BANS: frozenset[str] = frozenset({
    # Power 9 + classic fast mana / restricted-in-Vintage = banned in Legacy
    "Ancestral Recall", "Black Lotus", "Mox Emerald", "Mox Jet", "Mox Pearl", "Mox Ruby",
    "Mox Sapphire", "Time Walk", "Timetwister", "Mana Crypt", "Mana Vault", "Sol Ring",
    "Time Vault", "Channel", "Tinker", "Tolarian Academy", "Mishra's Workshop", "Bazaar of Baghdad",
    "Library of Alexandria", "Strip Mine",
    # broken tutors / card advantage / combo enablers banned long ago
    "Balance", "Demonic Tutor", "Demonic Consultation", "Imperial Seal", "Mystical Tutor",
    "Vampiric Tutor", "Necropotence", "Yawgmoth's Bargain", "Yawgmoth's Will", "Mind Twist",
    "Wheel of Fortune", "Windfall", "Memory Jar", "Fastbond", "Earthcraft", "Survival of the Fittest",
    "Oath of Druids", "Goblin Recruiter", "Hermit Druid", "Flash", "Skullclamp",
    "Treasure Cruise", "Dig Through Time", "Gush", "Frantic Search", "Gitaxian Probe",
    "Mental Misstep", "Arcum's Astrolabe", "Dreadhorde Arcanist", "Sensei's Divining Top",
    "Deathrite Shaman", "Wrenn and Six", "Oko, Thief of Crowns", "Lurrus of the Dream-Den",
    "Zirda, the Dawnwaker", "Mana Drain",
    # NOTE: Entomb is NOT here — it has a dated BAN_EVENTS entry (2025-11-10) for as-of correctness.
    # ante / un-set physical-dexterity cards
    "Chaos Orb", "Falling Star", "Shahrazad",
})

# Dated B&R actions, 2022-2026 (date the card BECAME banned).
BAN_EVENTS: tuple[tuple[date, str, str], ...] = (
    (date(2022, 1, 1), "Ragavan, Nimble Pilferer", "Format-warping UR Delver engine"),
    (date(2023, 3, 6), "Expressive Iteration", "Izzet Delver dominance"),
    (date(2023, 3, 6), "White Plume Adventurer", "Mono-W Initiative dominance"),
    (date(2024, 8, 26), "Grief", "Powered Dimir Reanimator hand disruption"),
    (date(2024, 12, 16), "Psychic Frog", "Dimir Reanimator/tempo at 2x next deck"),
    (date(2024, 12, 16), "Vexing Bauble", "Suppressed non-blue tempo"),
    (date(2025, 2, 1), "Underworld Breach", "Cross-format combo engine (exact Legacy date approx)"),
    (date(2025, 3, 31), "Troll of Khazad-dûm", "Low-downside reanimator target"),
    (date(2025, 3, 31), "Sowing Mycospawn", "Flexible Eldrazi/Ancient Tomb land denial"),
    (date(2025, 11, 10), "Entomb", "Decouple cheat-a-fatty from fair decks"),
    (date(2025, 11, 10), "Nadu, Winged Wisdom", "Power-level / uninteractive engine"),
    (date(2026, 5, 18), "Undercity Informer", "De-power MH3 Oops All Spells"),
)

CATEGORY_BANS: tuple[str, ...] = ("conspiracy", "ante", "stickers_or_attractions", "offensive")


def banlist_as_of(as_of: date) -> BanListSnapshot:
    """Build the ban-list snapshot in effect on ``as_of`` (cumulative bans up to that date)."""
    banned = set(BASELINE_BANS)
    for event_date, card, _reason in BAN_EVENTS:
        if event_date <= as_of:
            banned.add(card)
    return BanListSnapshot(as_of=as_of, banned=frozenset(banned), categories=CATEGORY_BANS)


def current_banlist() -> BanListSnapshot:
    """The latest known ban-list snapshot (through the most recent BAN_EVENTS entry)."""
    latest = max(d for d, _c, _r in BAN_EVENTS)
    return banlist_as_of(latest)


def _copy_limit(name: str) -> int | None:
    """Max legal copies of a card; None = unlimited (basics + explicit overrides)."""
    if name in BASIC_LAND_NAMES or name in UNLIMITED_COPIES:
        return None
    return COPY_LIMIT_OVERRIDES.get(name, 4)


def validate_deck(
    maindeck: dict[str, int],
    sideboard: dict[str, int] | None = None,
    snapshot: BanListSnapshot | None = None,
    type_line_of: Callable[[str], str | None] | None = None,
) -> list[str]:
    """Validate a decklist against Legacy construction rules + a ban-list snapshot.

    Returns a list of human-readable violations (empty = legal).  ``maindeck``/``sideboard`` map card
    name -> count.  ``snapshot`` defaults to the current ban list.

    ``type_line_of`` is an optional injected resolver (Ports & Adapters — domain must not import
    Scryfall/store).  When provided, cards whose type line contains "Conspiracy", "Attraction", or
    "Sticker" are flagged as not Legacy-legal.  When ``None``, type-line predicates are skipped
    entirely (those card types never appear in real Legacy data).
    """
    sideboard = sideboard or {}
    snapshot = snapshot or current_banlist()
    errors: list[str] = []

    main_total = sum(maindeck.values())
    if main_total < 60:
        errors.append(f"maindeck has {main_total} cards (minimum 60)")
    sb_total = sum(sideboard.values())
    if sb_total > 15:
        errors.append(f"sideboard has {sb_total} cards (maximum 15)")

    # Nonpositive count guard (finding #7): counts must be positive integers. Check each zone
    # independently — a negative count in one zone must not be masked by positive copies of the
    # same card in the other zone after merging.
    for zone, cards in (("maindeck", maindeck), ("sideboard", sideboard)):
        for name, count in cards.items():
            if count <= 0:
                errors.append(f"{name}: nonpositive count ({count}) in {zone}")

    combined: dict[str, int] = dict(maindeck)
    for name, count in sideboard.items():
        combined[name] = combined.get(name, 0) + count

    for name, count in combined.items():
        if snapshot.is_banned(name):
            errors.append(f"{name} is banned (as of {snapshot.as_of})")

        # Category bans: ante + offensive cards, name-enumerated (finding #7).
        if name in CATEGORY_BANNED_NAMES:
            errors.append(f"{name} is banned by category (ante/offensive)")

        # Type-line category predicates — only when a resolver is injected.
        if type_line_of is not None:
            tl = type_line_of(name) or ""
            if any(k in tl for k in ("Conspiracy", "Attraction", "Sticker")):
                errors.append(f"{name} is not Legacy-legal (type: {tl})")

        limit = _copy_limit(name)
        if limit is not None and count > limit:
            errors.append(f"{name}: {count} copies (max {limit})")

    return errors
