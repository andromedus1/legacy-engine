"""Legacy ban-list data + as-of-date snapshots + deck-construction validation.

Seeded from docs/briefs/legacy-foundations.md (current to the 2026-05-18 Undercity Informer ban).
BASELINE_BANS are the long-standing bans (effective before our 2022+ tracking window); BAN_EVENTS
are the dated B&R actions, so a snapshot as of date D = BASELINE ∪ (events with date <= D).

BAN_EVENTS is loaded from the package-shipped curated JSON (``data/banlist/events.json``,
curated-json-resource-loader pattern) rather than hand-edited here — the module API is
unchanged (``BAN_EVENTS`` is still importable as a tuple bound once at import), but the data now
has a write path: ``append_ban_event`` is the confirm loop's entry point (``eras confirm`` CLI),
so a human-confirmed drift-alarm registration lands as a JSON edit, not a code change.

Deviation from the general curated-json-resource-loader convention (documented): most curated
loaders in this project degrade to an EMPTY structure when the shipped file is missing/broken
(gated-additive — the feature just no-ops). BAN_EVENTS does not: an empty ban list would
silently declare every dated-banned card legal again, which is a correctness/legality regression,
not a missing-feature no-op. ``_load_default_ban_events`` therefore lets a load failure propagate
(fail loudly at import) rather than swallow it.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

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

# ---------------------------------------------------------------------------
# BAN_EVENTS — curated JSON loader (curated-json-resource-loader pattern)
# ---------------------------------------------------------------------------


def load_ban_events(path: "Path | str") -> tuple[tuple[date, str, str], ...]:
    """Load dated B&R events from a curated JSON file.

    Format: ``{"events": [{"date": "YYYY-MM-DD", "card": str, "reason": str}, ...]}``. Order in
    the file is not load-bearing — the result is always returned sorted by ``(date, card)``, the
    same ordering ``banlist_as_of``/``current_banlist`` fold over.

    Raises ``ValueError`` citing the offending path/index/key on any schema violation (missing
    root key, bad entry shape, unparseable date, duplicate ``(date, card)`` pair), or
    ``FileNotFoundError`` when ``path`` is absent.
    """
    path = Path(path)
    raw = json.loads(path.read_text(encoding="utf-8"))

    events_raw = raw.get("events")
    if not isinstance(events_raw, list):
        raise ValueError(f"load_ban_events: 'events' must be a list in {path}")

    events: list[tuple[date, str, str]] = []
    seen: set[tuple[date, str]] = set()
    for idx, entry in enumerate(events_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"load_ban_events: entry[{idx}] must be an object in {path}")

        date_raw = entry.get("date")
        if not isinstance(date_raw, str):
            raise ValueError(f"load_ban_events: entry[{idx}] missing/invalid 'date' in {path}")
        try:
            event_date = date.fromisoformat(date_raw)
        except ValueError as exc:
            raise ValueError(
                f"load_ban_events: entry[{idx}] 'date' {date_raw!r} is not ISO YYYY-MM-DD "
                f"in {path}"
            ) from exc

        card = entry.get("card")
        if not isinstance(card, str) or not card:
            raise ValueError(f"load_ban_events: entry[{idx}] missing/empty 'card' in {path}")

        reason = entry.get("reason")
        if not isinstance(reason, str) or not reason:
            raise ValueError(f"load_ban_events: entry[{idx}] missing/empty 'reason' in {path}")

        key = (event_date, card)
        if key in seen:
            raise ValueError(
                f"load_ban_events: duplicate (date, card) {key!r} at entry[{idx}] in {path}"
            )
        seen.add(key)
        events.append((event_date, card, reason))

    return tuple(sorted(events, key=lambda e: (e[0], e[1])))


def append_ban_event(
    event_date: date, card: str, reason: str, *, path: "Path | str",
) -> tuple[tuple[date, str, str], ...]:
    """Append one dated B&R event to the curated JSON at ``path`` (creating it if absent).

    The confirm loop's write path (``eras confirm`` CLI): a human-confirmed drift-alarm
    registration lands here, and every downstream consumer of ``BAN_EVENTS``
    (``banlist_as_of``/``current_banlist``, ``analytics.trends.regime_windows``,
    ``analytics.affectedness``) heals on its next read since they all derive from this file.

    Raises ``ValueError`` on a duplicate ``(event_date, card)`` pair — registration is a
    deliberate one-time event, never an upsert. Returns the full, updated event tuple (sorted by
    ``(date, card)``) so callers can report the healed regime without a second read.
    """
    path = Path(path)
    existing = load_ban_events(path) if path.exists() else ()

    if any(d == event_date and c == card for d, c, _r in existing):
        raise ValueError(
            f"append_ban_event: {card!r} already has an event on {event_date.isoformat()} "
            f"in {path}"
        )

    updated = tuple(
        sorted([*existing, (event_date, card, reason)], key=lambda e: (e[0], e[1]))
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_comment": (
            "Dated B&R events (curated-json-resource-loader pattern). Loaded by "
            "ingestion.banlist.load_ban_events at import to bind BAN_EVENTS; appended to by "
            "`eras confirm` (analytics.eras.attribution/CLI). Order is not load-bearing — the "
            "loader sorts by (date, card) — but is kept sorted here for readable diffs."
        ),
        "events": [
            {"date": d.isoformat(), "card": c, "reason": r} for d, c, r in updated
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return updated


def _load_default_ban_events() -> tuple[tuple[date, str, str], ...]:
    """Bind BAN_EVENTS from the shipped curated JSON at import.

    Deliberately does NOT catch/degrade-to-empty (see module docstring): an empty BAN_EVENTS
    would silently un-ban every dated card, a legality regression far worse than the missing-
    feature no-ops other curated loaders degrade to. A broken/missing shipped file is a
    packaging bug that must fail loudly, not a runtime data-presence gap.
    """
    from legacy_engine.config import BAN_EVENTS_PATH

    return load_ban_events(BAN_EVENTS_PATH)


# Dated B&R actions, 2022-2026 (date the card BECAME banned). Bound once at import from the
# package-shipped curated JSON (data/banlist/events.json) — see module docstring.
BAN_EVENTS: tuple[tuple[date, str, str], ...] = _load_default_ban_events()

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
