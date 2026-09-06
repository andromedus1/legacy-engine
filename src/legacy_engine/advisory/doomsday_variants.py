"""Read-only Doomsday variant extraction and current-field projection.

This module deliberately keeps registration evidence, tournament standings, and
resolved rounds as separate ledgers.  A published list is useful evidence that
someone registered a configuration; it is not a played match result.  The
projection is a small, descriptive comparison using the shared deck-ranking
kernel and a fixed Beta(1, 1) cell prior.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from hashlib import sha256
import json
import math
import re
from typing import Any

import duckdb

from legacy_engine.advisory.deck_ranking import rank_matchup_rows
from legacy_engine.advisory.ranking_measurement import (
    RankingCellMeasurement,
    RankingCellSource,
)
from legacy_engine.analytics.match_results import normalize_player, resolve_match_records
from legacy_engine.analytics.matchup import build_cell
from legacy_engine.ingestion.banlist import banlist_as_of
from legacy_engine.models.banlist import CATEGORY_BANNED_NAMES
from legacy_engine.generation.export import format_decklist

__all__ = [
    "VariantSpec",
    "VariantClassification",
    "VARIANT_REGISTRY",
    "classify_variant",
    "build_variant_report",
]

_WUBRG = frozenset("WUBRG")
_SPLASH = frozenset("WRG")
_FETCH_TEXT = re.compile(r"search\s+your\s+library", re.IGNORECASE)
_DEFAULT_SINCE = "2026-01-01"
_DEFAULT_DRAWS = 10_000
_DEFAULT_SEED = 2_026_090_5


@dataclass(frozen=True)
class VariantSpec:
    """One named cohort in the report's closed registry."""

    id: str
    label: str
    signature: str
    explanation: str
    target: bool = False


_SPECS = (
    VariantSpec("dimir", "Dimir", "no W/G/R mana package", "Pure blue-black Doomsday mana; fetches, Cavern, and Petal do not create a splash.", True),
    VariantSpec("esper_teferi", "Esper + Teferi", "Teferi, Time Raveler", "White mana plus Teferi, Time Raveler in the registered 75.", True),
    VariantSpec("sultai_veil", "Sultai + Veil", "Veil of Summer", "Green mana plus Veil of Summer in the registered 75.", True),
    VariantSpec("grixis_squelcher", "Grixis + Squelcher", "Hexing Squelcher", "Red mana plus Hexing Squelcher in the registered 75.", True),
    VariantSpec("four_color_white_green", "Four-color W/G", "white and green mana", "Both white and green mana sources are present in the registered 75.", True),
    VariantSpec("white_no_teferi", "White without Teferi", "white mana, no Teferi", "A white splash without Teferi, Time Raveler.", False),
    VariantSpec("green_no_veil", "Green without Veil", "green mana, no Veil", "A green splash without Veil of Summer.", False),
    VariantSpec("red_no_squelcher", "Red without Squelcher", "red mana, no Squelcher", "A red splash without Hexing Squelcher.", False),
    VariantSpec("mixed_other", "Other splash", "other W/G/R combination", "A residual splash combination outside the named target cohorts.", False),
)
VARIANT_REGISTRY: dict[str, VariantSpec] = {spec.id: spec for spec in _SPECS}
_TARGET_IDS = tuple(spec.id for spec in _SPECS if spec.target)
_PACKAGE_CARDS = frozenset({
    # Signature / protection cards that explain the named package in a 75.
    "Teferi, Time Raveler", "Veil of Summer", "Hexing Squelcher", "Carpet of Flowers",
    "Witherbloom Charm", "Abrupt Decay", "Force of Vigor", "Swords to Plowshares",
    "Prismatic Ending", "Portable Hole", "Solitude", "Voice of Victory",
    "Containment Priest", "Pyroblast", "Red Elemental Blast", "Molten Collapse",
    "Cori-Steel Cutter", "Meltdown", "Blood Moon", "Force of Will", "Force of Negation",
    "Daze", "Thoughtseize", "Duress", "Flusterstorm",
})


@dataclass(frozen=True)
class VariantClassification:
    """Result of classifying one exact registered 75."""

    variant_id: str
    label: str
    colors: tuple[str, ...]
    splash_lands: tuple[str, ...]
    signature_counts: Mapping[str, Mapping[str, int]]
    signature_cards: tuple[str, ...]
    missing_metadata: tuple[str, ...] = ()
    malformed_cards: tuple[str, ...] = ()
    status: str = "ok"

    @property
    def id(self) -> str:
        return self.variant_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "id": self.variant_id,
            "label": self.label,
            "colors": list(self.colors),
            "splash_lands": list(self.splash_lands),
            "signature_counts": {
                board: dict(values) for board, values in self.signature_counts.items()
            },
            "signature_cards": list(self.signature_cards),
            "missing_metadata": list(self.missing_metadata),
            "malformed_cards": list(self.malformed_cards),
            "status": self.status,
        }


def _board_map(value: Mapping[str, Any] | None) -> tuple[dict[str, int], list[str]]:
    result: dict[str, int] = {}
    malformed: list[str] = []
    for raw_name, raw_count in (value or {}).items():
        if not isinstance(raw_name, str) or not raw_name.strip():
            malformed.append(str(raw_name))
            continue
        try:
            count = int(raw_count)
        except (TypeError, ValueError):
            malformed.append(raw_name)
            continue
        if count <= 0:
            malformed.append(raw_name)
            continue
        result[raw_name.strip()] = result.get(raw_name.strip(), 0) + count
    return result, malformed


def _fact(value: Any) -> tuple[bool, set[str], str]:
    """Read the card fields used here from a stored row, dict, or simple fixture."""
    if isinstance(value, Mapping):
        is_land = bool(value.get("is_land", False))
        produced = value.get("produced_mana", "")
        oracle = str(value.get("oracle_text", "") or "")
    else:
        is_land = bool(getattr(value, "is_land", False))
        produced = getattr(value, "produced_mana", "")
        oracle = str(getattr(value, "oracle_text", "") or "")
    if isinstance(produced, (list, tuple, set, frozenset)):
        raw = "".join(str(part) for part in produced)
    else:
        raw = str(produced or "")
    return is_land, {letter for letter in raw.upper() if letter in _WUBRG}, oracle


def classify_variant(
    mainboard: Mapping[str, Any],
    sideboard: Mapping[str, Any] | None = None,
    card_metadata: Mapping[str, Any] | None = None,
    *,
    card_meta: Mapping[str, Any] | None = None,
) -> VariantClassification:
    """Classify a Doomsday 75 using actual colored mana and signature cards.

    Fetchlands, Lotus Petal, Cavern of Souls, and Edge of Autumn are deliberately
    excluded from splash-mana inference.  A card's printed colour alone is not
    a splash; a coloured land source and the relevant signature card are both
    required for the named one-colour cohorts.
    """
    main, malformed_main = _board_map(mainboard)
    side, malformed_side = _board_map(sideboard)
    if card_metadata is not None and card_meta is not None:
        raise ValueError("pass card_metadata or card_meta, not both")
    metadata = card_metadata if card_metadata is not None else (card_meta or {})
    all_names = set(main) | set(side)
    missing = sorted(name for name in all_names if name not in metadata and name not in {
        "Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes",
    })
    # Basic lands remain useful in deliberately small fixture metadata.
    basic_colors = {
        "Plains": {"W"}, "Island": {"U"}, "Swamp": {"B"},
        "Mountain": {"R"}, "Forest": {"G"}, "Wastes": set(),
    }
    mana_colors: set[str] = set()
    splash_lands: list[str] = []
    for name in sorted(main):
        if name == "Cavern of Souls" or name == "Edge of Autumn":
            continue
        if name in basic_colors:
            colors = basic_colors[name]
            is_land = True
            oracle = ""
        elif name not in metadata:
            continue
        else:
            is_land, colors, oracle = _fact(metadata[name])
        # The classifier is about actual basic/dual/shock/surveil sources.
        # Rainbow lands (City of Brass, Gemstone Mine, etc.) are intentionally
        # not allowed to manufacture a one-colour splash cohort.
        if not is_land or _FETCH_TEXT.search(oracle) or len(colors) > 2:
            continue
        mana_colors.update(colors)
        relevant = colors & _SPLASH
        if relevant:
            splash_lands.append(name)

    combined = {**main}
    for name, count in side.items():
        combined[name] = combined.get(name, 0) + count
    signature_cards = tuple(sorted(name for name in combined if name in _PACKAGE_CARDS))
    sig_counts: dict[str, dict[str, int]] = {"main": {}, "side": {}}
    for board_name, board in (("main", main), ("side", side)):
        for name in sorted(board):
            if name in _PACKAGE_CARDS:
                sig_counts[board_name][name] = board[name]

    white, green, red = "W" in mana_colors, "G" in mana_colors, "R" in mana_colors
    # An absent card row cannot tell us whether the card is a land that adds a
    # splash.  Exclude the whole list from projection until every card fact is
    # present; otherwise a missing possible-land could silently become Dimir.
    # The audit retains the exact names so a data refresh can repair the row.
    unknown_land_risk = not all_names or bool(missing)
    if not unknown_land_risk:
        if white and green and not red:
            variant_id = "four_color_white_green"
        elif white and not green and not red:
            variant_id = "esper_teferi" if "Teferi, Time Raveler" in combined else "white_no_teferi"
        elif green and not white and not red:
            variant_id = "sultai_veil" if "Veil of Summer" in combined else "green_no_veil"
        elif red and not white and not green:
            variant_id = "grixis_squelcher" if "Hexing Squelcher" in combined else "red_no_squelcher"
        elif not (white or green or red):
            variant_id = "dimir"
        else:
            variant_id = "mixed_other"
    else:
        # With no card facts at all, a Dimir answer would be an unsupported
        # guess.  Preserve the record for the audit and let the report omit it
        # from the forced target/residual projection rows.
        variant_id = "unclassifiable"
    spec = VARIANT_REGISTRY.get(variant_id)
    label = spec.label if spec else "Unclassifiable"
    status = "malformed" if malformed_main or malformed_side else ("partial" if missing else "ok")
    if variant_id == "unclassifiable":
        status = "unclassifiable"
    return VariantClassification(
        variant_id=variant_id,
        label=label,
        colors=tuple(sorted(mana_colors)),
        splash_lands=tuple(sorted(set(splash_lands))),
        signature_counts=sig_counts,
        signature_cards=signature_cards,
        missing_metadata=tuple(missing),
        malformed_cards=tuple(sorted(set(malformed_main + malformed_side))),
        status=status,
    )


@dataclass
class _Registration:
    event_id: str
    event_date: date
    event_name: str
    event_uri: str
    source: str
    provenance: str
    deck_idx: int
    player: str
    result: str
    archetype: str | None
    mainboard: dict[str, int]
    sideboard: dict[str, int]
    cards_present: bool = True
    classification: VariantClassification | None = None
    banned_cards: tuple[str, ...] = ()
    list_errors: tuple[str, ...] = ()

    @property
    def player_norm(self) -> str:
        return normalize_player(self.player)

    @property
    def legal(self) -> bool:
        return not self.banned_cards and not self.list_errors

    @property
    def list_hash(self) -> str:
        raw = json.dumps(
            {"main": sorted(self.mainboard.items()), "side": sorted(self.sideboard.items())},
            ensure_ascii=False, separators=(",", ":"),
        )
        return sha256(raw.encode()).hexdigest()


def _iso_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _public_date(value: Any, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{name} must be a YYYY-MM-DD date")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid YYYY-MM-DD date") from exc


def _global_field(global_payload: Mapping[str, Any]) -> tuple[dict[str, float], dict[str, float] | None, dict[str, Any]]:
    meta = global_payload.get("meta", {}) if isinstance(global_payload, Mapping) else {}
    rankings = meta.get("deck_rankings", {}) if isinstance(meta, Mapping) else {}
    field = rankings.get("field", {}) if isinstance(rankings, Mapping) else {}
    if not isinstance(field, Mapping) or not isinstance(field.get("shares"), Mapping):
        raise ValueError("global payload is missing meta.deck_rankings.field.shares")
    raw_shares = {str(k): float(v) for k, v in field["shares"].items()}
    if any(not math.isfinite(v) or v < 0 for v in raw_shares.values()):
        raise ValueError("global field shares must be finite and non-negative")
    raw_shares = {k: v for k, v in raw_shares.items() if v > 0}
    total = sum(raw_shares.values())
    if not raw_shares or total <= 0 or not math.isfinite(total):
        raise ValueError("global field shares must have positive finite mass")
    doom = {label for label in raw_shares if _is_doomsday_label(label)}
    removed_mass = sum(raw_shares[label] for label in doom)
    retained_mass = total - removed_mass
    if retained_mass <= 0:
        raise ValueError("global field has no non-Doomsday opponent mass")
    shares = {label: value / retained_mass for label, value in raw_shares.items() if label not in doom}
    raw_counts = field.get("effective_counts")
    counts: dict[str, float] | None = None
    count_source = "none"
    if isinstance(raw_counts, Mapping):
        # Counts are concentration only.  Retain the external fraction of the
        # full field count, then distribute it according to the already
        # renormalized external shares.  This keeps the posterior centre fixed
        # while removing Doomsday mass exactly once from both inputs.
        values = [float(raw_counts.get(label, 0.0)) for label in raw_shares]
        if any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError("effective field counts must be finite and non-negative")
        source_total = sum(values)
        if source_total > 0 and math.isfinite(source_total):
            retained_external_total = source_total * (retained_mass / total)
            counts = {
                label: float(shares[label]) * retained_external_total
                for label in shares
            }
            count_source = "effective_counts"
        else:
            counts = None
    meta_since = meta.get("field_since") if isinstance(meta, Mapping) else None
    field_info = {
        "shares": shares,
        "counts": counts,
        "raw_shares": raw_shares,
        "removed_labels": sorted(doom),
        "removed_mass": removed_mass / total,
        "retained_mass": retained_mass / total,
        "counts_source": count_source,
        "since": _public_date(field.get("since") or meta_since, "field.since"),
        "until": _public_date(field.get("until"), "field.until (exclusive until)"),
        "description": "Current external field with Doomsday family mass removed once and renormalized; Unknown retained.",
    }
    return shares, counts, field_info


def _is_doomsday_label(label: str) -> bool:
    normalized = label.strip().casefold()
    return normalized == "doomsday" or normalized.startswith("doomsday [")


def _load_registrations(con: duckdb.DuckDBPyConnection, since: str, until: str) -> tuple[list[_Registration], dict[tuple[str, int], dict[str, int]], dict[str, dict[str, Any]]]:
    rows = con.execute(
        """SELECT t.id, t.date, coalesce(t.name, ''), coalesce(t.uri, ''),
                         coalesce(t.source, ''), coalesce(t.provenance, ''),
                         d.deck_idx, coalesce(d.player, ''), coalesce(d.result, ''), d.archetype
           FROM tournaments t JOIN decks d ON d.tournament_id = t.id
          WHERE t.date >= ? AND t.date < ?
          ORDER BY t.date, t.id, d.deck_idx""",
        [since, until],
    ).fetchall()
    boards: dict[tuple[str, int], dict[str, int]] = defaultdict(dict)
    board_errors: dict[tuple[str, int], list[str]] = defaultdict(list)
    board_rows = con.execute(
        """SELECT tournament_id, deck_idx, lower(board), name, count
             FROM deck_cards
            WHERE tournament_id IN (SELECT id FROM tournaments WHERE date >= ? AND date < ?)
            ORDER BY tournament_id, deck_idx, lower(board), name""",
        [since, until],
    ).fetchall()
    for tid, idx, board, name, count in board_rows:
        key = (str(tid), int(idx))
        if not isinstance(name, str) or not name.strip():
            board_errors[key].append("missing card name")
            continue
        if board not in {"main", "maindeck", "side", "sideboard"}:
            board_errors[key].append(f"unknown board: {board}")
            continue
        board_key = "side" if str(board) in {"side", "sideboard"} else "main"
        boards.setdefault(key, {})[("side:" if board_key == "side" else "main:") + name.strip()] = int(count or 0)
    # Keep board maps separate without a second SQL query; the prefixed key is
    # an internal transport detail only.
    split_boards: dict[tuple[str, int], dict[str, int]] = defaultdict(dict)
    for key, cards in boards.items():
        split_boards[key] = cards
    metadata: dict[str, dict[str, Any]] = {}
    try:
        card_rows = con.execute("SELECT name, is_land, produced_mana, oracle_text FROM cards").fetchall()
    except duckdb.CatalogException:
        card_rows = []
    for name, is_land, produced, oracle in card_rows:
        metadata[str(name)] = {
            "is_land": bool(is_land), "produced_mana": produced or "", "oracle_text": oracle or "",
        }
    registrations: list[_Registration] = []
    for tid, event_date, event_name, uri, source, provenance, idx, player, result, archetype in rows:
        key = (str(tid), int(idx))
        main: dict[str, int] = {}
        side: dict[str, int] = {}
        for raw, count in split_boards.get(key, {}).items():
            if raw.startswith("side:"):
                side[raw[5:]] = count
            elif raw.startswith("main:"):
                main[raw[5:]] = count
        registrations.append(_Registration(
            event_id=str(tid), event_date=_iso_date(event_date), event_name=str(event_name),
            event_uri=str(uri), source=str(source), provenance=str(provenance), deck_idx=int(idx),
            player=str(player), result=str(result), archetype=str(archetype) if archetype is not None else None,
            mainboard=main, sideboard=side, cards_present=key in split_boards,
            list_errors=tuple(board_errors[key]
                + (["maindeck below 60 cards"] if sum(main.values()) < 60 else [])
                + (["sideboard above 15 cards"] if sum(side.values()) > 15 else [])
                + (["nonpositive card count"] if any(n <= 0 for n in (*main.values(), *side.values())) else [])),
        ))
    return registrations, split_boards, metadata


def _verified_event_aliases(con: duckdb.DuckDBPyConnection, since: str, until: str) -> dict[str, str]:
    """Collapse copied non-League MTGO events only after all four fact tables agree.

    A changed date slug can publish the same numeric event twice. Numeric ids
    alone are insufficient (especially for daily Leagues); identical pilot/list
    pairs across genuinely different events are also legitimate observations.
    """
    pattern = re.compile(r"https?://(?:www\.)?mtgo\.com/decklist/.+-(\d{4}-\d{2}-\d{2})(\d+)$")
    groups: dict[tuple, list[tuple[str, str]]] = defaultdict(list)
    for tid, name, dt, source, provenance in con.execute(
        "SELECT id, name, date, source, provenance FROM tournaments WHERE date >= ? AND date < ?",
        [since, until],
    ).fetchall():
        match = pattern.fullmatch(tid)
        if match and "league" not in f"{name} {tid}".lower():
            groups[(name, str(dt)[:10], source, provenance, match[2])].append((tid, match[1]))
    aliases: dict[str, str] = {}
    for (_name, dt, _source, _provenance, _event), candidates in groups.items():
        if len(candidates) < 2:
            continue
        seen: dict[str, str] = {}
        for tid, _url_date in sorted(candidates, key=lambda item: (item[1] != dt, item[0])):
            contents = [con.execute(
                f"SELECT * EXCLUDE (tournament_id) FROM {table} WHERE tournament_id = ? ORDER BY ALL",
                [tid],
            ).fetchall() for table in ("decks", "deck_cards", "standings", "rounds")]
            if not contents[0] or not contents[1]:
                continue
            fingerprint = sha256(json.dumps(contents, default=str, separators=(",", ":")).encode()).hexdigest()
            if fingerprint in seen:
                aliases[tid] = seen[fingerprint]
            else:
                seen[fingerprint] = tid
    return aliases


def _banned_cards(registration: _Registration, snapshot: Any) -> tuple[str, ...]:
    names = set(registration.mainboard) | set(registration.sideboard)
    return tuple(sorted(name for name in names if snapshot.is_banned(name) or name in CATEGORY_BANNED_NAMES))


def _registration_payload(reg: _Registration) -> dict[str, Any]:
    classification = reg.classification.as_dict() if reg.classification else {}
    return {
        "date": reg.event_date.isoformat(), "pilot": reg.player, "event": reg.event_name,
        "event_id": reg.event_id, "deck_idx": reg.deck_idx, "source": reg.source,
        "source_url": reg.event_uri, "source_anchor": f"{reg.event_uri}#deck_{reg.player}",
        "result": reg.result, "legal_at_cutoff": reg.legal, "banned_cards": list(reg.banned_cards),
        "canonical_deck_sha256": reg.list_hash,
        "canonical_main": dict(sorted(reg.mainboard.items())),
        "canonical_side": dict(sorted(reg.sideboard.items())),
        "moxfield_text": format_decklist(reg.mainboard, reg.sideboard, fmt="moxfield"),
        "package": {
            "signature_counts": classification.get("signature_counts", {"main": {}, "side": {}}),
            "signature_cards": classification.get("signature_cards", []),
            "splash_lands": classification.get("splash_lands", []),
        },
    }


def _recent_lists(registrations: list[_Registration], field_since: str | None) -> list[dict[str, Any]]:
    legal = [reg for reg in registrations if reg.legal
             and sum(reg.mainboard.values()) == 60 and sum(reg.sideboard.values()) == 15]
    threshold = _iso_date(field_since) if field_since else date.min
    # Prefer current legal lists, then most recent date/event/list.  Exact hash
    # deduplication is per cohort and does not cross event IDs in the evidence ledger.
    legal.sort(key=lambda reg: (reg.event_date >= threshold, reg.event_date, reg.event_id, reg.deck_idx), reverse=True)
    chosen: list[_Registration] = []
    seen_hashes: set[str] = set()
    for reg in legal:
        if reg.list_hash in seen_hashes:
            continue
        seen_hashes.add(reg.list_hash)
        chosen.append(reg)
        if len(chosen) == 3:
            break
    return [_registration_payload(reg) for reg in chosen]


def _is_league(reg: _Registration) -> bool:
    return "league" in f"{reg.event_name} {reg.event_uri}".casefold()


def _standings(con: duckdb.DuckDBPyConnection, registrations: list[_Registration], cohort_ids: set[str]) -> dict[str, dict[str, Any]]:
    if not registrations:
        return {cohort: _empty_standings() for cohort in cohort_ids}
    event_ids = sorted({reg.event_id for reg in registrations})
    placeholders = ",".join("?" for _ in event_ids)
    try:
        rows = con.execute(
            f"SELECT tournament_id, player, wins, losses, draws FROM standings WHERE tournament_id IN ({placeholders})",
            event_ids,
        ).fetchall()
    except duckdb.CatalogException:
        rows = []
    standings_by_key: dict[tuple[str, str], list[tuple[Any, ...]]] = defaultdict(list)
    for row in rows:
        standings_by_key[(str(row[0]), normalize_player(row[1]))].append(row)
    regs_by_key: dict[tuple[str, str], list[_Registration]] = defaultdict(list)
    for reg in registrations:
        regs_by_key[(reg.event_id, reg.player_norm)].append(reg)
    out = {cohort: _empty_standings() for cohort in cohort_ids}
    for key, regs in regs_by_key.items():
        if len(regs) != 1 or not standings_by_key.get(key):
            continue
        reg = regs[0]
        if not reg.legal or not reg.classification or reg.classification.variant_id not in cohort_ids:
            continue
        if _is_league(reg) or len(standings_by_key[key]) != 1:
            continue
        row = standings_by_key[key][0]
        wins, losses, draws = (int(row[i] or 0) for i in (2, 3, 4))
        ledger = out[reg.classification.variant_id]
        if isinstance(ledger["pilots"], list):
            ledger["pilots"] = set(ledger["pilots"])
        if isinstance(ledger["events"], list):
            ledger["events"] = set(ledger["events"])
        ledger["wins"] += wins
        ledger["losses"] += losses
        ledger["draws"] += draws
        ledger["record_count"] += 1
        ledger["pilots"].add(reg.player_norm)
        ledger["events"].add(reg.event_id)
        ledger["records"].append({
            "event": reg.event_name, "event_id": reg.event_id, "date": reg.event_date.isoformat(),
            "pilot": reg.player, "wins": wins, "losses": losses, "draws": draws,
        })
    for ledger in out.values():
        ledger["pilots"] = sorted(ledger["pilots"])
        ledger["events"] = sorted(ledger["events"])
        ledger["decisive_win_rate"] = (
            ledger["wins"] / (ledger["wins"] + ledger["losses"])
            if ledger["wins"] + ledger["losses"] else None
        )
        ledger["record"] = f"{ledger['wins']}-{ledger['losses']}-{ledger['draws']}"
    return out


def _empty_standings() -> dict[str, Any]:
    return {"wins": 0, "losses": 0, "draws": 0, "record_count": 0, "pilots": [], "events": [], "records": [], "decisive_win_rate": None, "record": "0-0-0"}


def _attach_rounds(
    con: duckdb.DuckDBPyConnection,
    registrations: list[_Registration],
    shares: Mapping[str, float],
    *,
    since: str,
    until: str,
    cutoff: date,
) -> tuple[dict[str, dict[str, dict[str, Any]]], dict[str, dict[str, Any]], dict[str, int]]:
    by_event_player: dict[tuple[str, str], list[_Registration]] = defaultdict(list)
    for reg in registrations:
        by_event_player[(reg.event_id, reg.player_norm)].append(reg)
    tallies: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    audit: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "match_ids": [], "dates": [], "pilots": [], "events": [], "wins": 0, "losses": 0,
    })
    counts = Counter()
    # ``resolve_match_records`` intentionally drops ambiguous normalized names
    # before emitting a ResolvedMatch.  Count those source rows separately so
    # the report can explain why an otherwise parseable pairing is absent.
    try:
        ambiguous_rows = con.execute(
            """WITH dup AS (
                       SELECT tournament_id, lower(trim(player)) AS norm
                         FROM decks
                        GROUP BY tournament_id, lower(trim(player))
                       HAVING count(*) > 1
                   )
                   SELECT count(*)
                     FROM rounds r
                     JOIN tournaments t ON t.id = r.tournament_id
                     LEFT JOIN dup d1 ON d1.tournament_id = r.tournament_id
                                      AND d1.norm = lower(trim(r.player1))
                     LEFT JOIN dup d2 ON d2.tournament_id = r.tournament_id
                                      AND d2.norm = lower(trim(r.player2))
                    WHERE t.date >= ? AND t.date < ?
                      AND (d1.norm IS NOT NULL OR d2.norm IS NOT NULL)""",
            [since, until],
        ).fetchone()[0]
        if ambiguous_rows:
            counts["ambiguous_registration"] = int(ambiguous_rows)
    except duckdb.CatalogException:
        pass
    resolved = resolve_match_records(con, since=since, until=until)
    retained_events = {reg.event_id for reg in registrations}
    seen_match_ids: set[str] = set()
    for match in resolved:
        if match.match_id in seen_match_ids:
            counts["duplicate_match_ids"] += 1
            continue
        seen_match_ids.add(match.match_id)
        counts["resolved_match_records"] += 1
        if match.event_id not in retained_events:
            counts["excluded_event_alias"] += 1
            continue
        if match.event_date >= cutoff + timedelta(days=1):
            counts["after_cutoff"] += 1
            continue
        if _is_doomsday_label(match.subject) and _is_doomsday_label(match.opponent):
            counts["doomsday_mirror"] += 1
            continue
        if _is_doomsday_label(match.subject):
            candidate_id, candidate_won = match.subject_player_id, match.subject_won
            opponent_id, opponent_label = match.opponent_player_id, match.opponent
        elif _is_doomsday_label(match.opponent):
            candidate_id, candidate_won = match.opponent_player_id, not match.subject_won
            opponent_id, opponent_label = match.subject_player_id, match.subject
        else:
            counts["not_doomsday"] += 1
            continue
        candidate_rows = by_event_player.get((match.event_id, normalize_player(candidate_id)), [])
        opponent_rows = by_event_player.get((match.event_id, normalize_player(opponent_id)), [])
        if len(candidate_rows) != 1 or len(opponent_rows) != 1:
            counts["ambiguous_registration"] += 1
            continue
        candidate, opponent = candidate_rows[0], opponent_rows[0]
        if not candidate.cards_present:
            counts["missing_subject_list"] += 1
            continue
        if not opponent.cards_present:
            counts["missing_opponent_list"] += 1
            continue
        if candidate.list_errors:
            counts["malformed_subject_list"] += 1
            continue
        if opponent.list_errors:
            counts["malformed_opponent_list"] += 1
            continue
        if not candidate.legal:
            counts["banned_subject"] += 1
            continue
        if not opponent.legal:
            counts["banned_opponent"] += 1
            continue
        if opponent_label not in shares or shares[opponent_label] <= 0:
            counts["non_external_opponent"] += 1
            continue
        cohort = candidate.classification.variant_id if candidate.classification else "unclassifiable"
        if cohort not in VARIANT_REGISTRY:
            counts["unclassifiable_subject"] += 1
            continue
        cell = tallies[cohort].setdefault(opponent_label, {"wins": 0, "losses": 0, "match_ids": [], "dates": [], "pilots": [], "events": []})
        cell["wins" if candidate_won else "losses"] += 1
        cell["match_ids"].append(match.match_id)
        cell["dates"].append(match.event_date.isoformat())
        cell["pilots"].append(candidate.player_norm)
        cell["events"].append(match.event_id)
        summary = audit[cohort]
        summary["match_ids"].append(match.match_id)
        summary["dates"].append(match.event_date.isoformat())
        summary["pilots"].append(candidate.player_norm)
        summary["events"].append(match.event_id)
        summary["wins" if candidate_won else "losses"] += 1
        counts["compatible_external_rounds"] += 1
    for cohort, summary in audit.items():
        summary["match_ids"] = sorted(set(summary["match_ids"]))
        summary["dates"] = sorted(set(summary["dates"]))
        summary["pilots"] = sorted(set(summary["pilots"]))
        summary["events"] = sorted(set(summary["events"]))
        n = summary["wins"] + summary["losses"]
        # Sets above are used for the public audit; concentration is computed
        # from the cell ledgers below, preserving repeated observations.
        pcounts = Counter()
        ecounts = Counter()
        for cells in tallies.get(cohort, {}).values():
            pcounts.update(cells["pilots"])
            ecounts.update(cells["events"])
        summary["dominant_pilot_share"] = max(pcounts.values(), default=0) / n if n else None
        summary["dominant_event_share"] = max(ecounts.values(), default=0) / n if n else None
        summary["date_min"] = summary["dates"][0] if summary["dates"] else None
        summary["date_max"] = summary["dates"][-1] if summary["dates"] else None
    return tallies, dict(audit), {key: int(value) for key, value in counts.items()}


def _projection(
    cohort_ids: list[str],
    tallies: Mapping[str, Mapping[str, Mapping[str, Any]]],
    shares: Mapping[str, float],
    counts: Mapping[str, float] | None,
    *,
    draws: int,
    seed: int,
    since: str,
) -> dict[str, Any]:
    rows: dict[str, list[RankingCellMeasurement]] = {}
    for cohort in cohort_ids:
        cells: list[RankingCellMeasurement] = []
        for opponent in sorted(shares):
            tally = tallies.get(cohort, {}).get(opponent, {"wins": 0, "losses": 0})
            wins = int(tally.get("wins", 0))
            n = wins + int(tally.get("losses", 0))
            cell = build_cell(
                cohort, opponent, wins, n, prior_mean=0.5, prior_strength=2.0,
                prior_source="Doomsday variant fixed Beta(1,1) prior",
            )
            source = RankingCellSource(kind="full-corpus", since=since, cell=cell)
            cells.append(RankingCellMeasurement(
                subject=cohort, opponent=opponent, field_share=float(shares[opponent]),
                era=source, fallback=None, selected_kind="full-corpus", selected=source,
                selection_reason="variant-compatible decisive physical rounds",
                measured=n > 0, concentration_warning=None,
            ))
        rows[cohort] = cells
    presence = {cohort: float(sum(int(tally.get("wins", 0)) + int(tally.get("losses", 0)) for tally in tallies.get(cohort, {}).values())) for cohort in cohort_ids}
    # Presence is replaced by the caller's registration shares after ranking;
    # a positive value keeps the kernel's ineligible prior-only semantics.
    eligibility = {cohort: any(value > 0 for value in presence.values()) and presence[cohort] > 0 for cohort in cohort_ids}
    return rank_matchup_rows(
        rows, shares, counts=counts, draws=draws, seed=seed,
        candidate_presence={cohort: presence[cohort] for cohort in cohort_ids},
        candidate_eligibility=eligibility,
    )


def _view_payload(
    con: duckdb.DuckDBPyConnection,
    all_registrations: list[_Registration],
    shares: Mapping[str, float],
    counts: Mapping[str, float] | None,
    *,
    since: str,
    until: str,
    cutoff: date,
    field_since: str | None,
    draws: int,
    seed: int,
) -> dict[str, Any]:
    selected_all = [reg for reg in all_registrations if reg.event_date >= _iso_date(since) and reg.event_date < _iso_date(until)]
    selected = [reg for reg in selected_all if reg.archetype == "Doomsday"]
    cohort_ids = list(_TARGET_IDS)
    for reg in selected:
        if reg.classification and reg.classification.variant_id in VARIANT_REGISTRY and reg.classification.variant_id not in cohort_ids:
            cohort_ids.append(reg.classification.variant_id)
    tallies, round_audit, round_counts = _attach_rounds(
        con, selected_all, shares, since=since, until=until, cutoff=cutoff,
    )
    standings = _standings(con, selected_all, set(cohort_ids))
    projection = _projection(cohort_ids, tallies, shares, counts, draws=draws, seed=seed, since=since)
    legal_counts = Counter(reg.classification.variant_id for reg in selected if reg.classification and reg.legal and reg.classification.variant_id in VARIANT_REGISTRY)
    total_legal = sum(legal_counts.values())
    rows: list[dict[str, Any]] = []
    for cohort in cohort_ids:
        spec = VARIANT_REGISTRY[cohort]
        cohort_regs = [reg for reg in selected if reg.classification and reg.classification.variant_id == cohort]
        legal_regs = [reg for reg in cohort_regs if reg.legal]
        decision = dict(projection["rows"][cohort])
        for cell in decision["cells"]:
            dates = tallies.get(cohort, {}).get(cell["opponent"], {}).get("dates", [])
            cell["date_min"] = min(dates, default=None)
            cell["date_max"] = max(dates, default=None)
        decision["registration_count"] = len(cohort_regs)
        decision["legal_registration_count"] = len(legal_regs)
        decision["round_n"] = sum(int(cell.get("n", 0)) for cell in decision.get("cells", []))
        decision["raw_wins"] = sum(int(value.get("wins", 0)) for value in tallies.get(cohort, {}).values())
        decision["raw_losses"] = sum(int(value.get("losses", 0)) for value in tallies.get(cohort, {}).values())
        decision["prior_only"] = not bool(decision.get("direct_support"))
        floor_cell = next((cell for cell in decision.get("cells", []) if cell.get("opponent") == decision.get("worst_opponent")), None)
        decision["worst_pair_n"] = int(floor_cell.get("n", 0)) if floor_cell else 0
        decision["worst_pair_interval"] = (
            [floor_cell.get("ci_low"), floor_cell.get("ci_high")]
            if floor_cell and floor_cell.get("ci_low") is not None else None
        )
        decision["direct_field_coverage"] = decision.get("nonmirror_coverage")
        decision["prior_backed_mass"] = sum(float(cell.get("field_share", 0.0)) for cell in decision.get("cells", []) if int(cell.get("n", 0)) == 0)
        rows.append({
            "subject": cohort, "label": spec.label, "signature": spec.signature,
            "explanation": spec.explanation, "target": spec.target,
            "decision": decision,
            "standings": standings.get(cohort, _empty_standings()),
            "registrations": {
                "count": len(cohort_regs), "legal_count": len(legal_regs),
                "pilots": sorted({reg.player_norm for reg in cohort_regs}),
                "events": sorted({reg.event_id for reg in cohort_regs}),
                "date_min": min((reg.event_date for reg in cohort_regs), default=None).isoformat() if cohort_regs else None,
                "latest_date": max((reg.event_date for reg in cohort_regs), default=None).isoformat() if cohort_regs else None,
                "date_max": max((reg.event_date for reg in cohort_regs), default=None).isoformat() if cohort_regs else None,
                "lists": _recent_lists(cohort_regs, field_since),
            },
            "round_audit": round_audit.get(cohort, {
                "match_ids": [], "dates": [], "pilots": [], "events": [], "wins": 0, "losses": 0,
                "dominant_pilot_share": None, "dominant_event_share": None, "date_min": None, "date_max": None,
            }),
        })
    # Rank rows are target-first, then observed residuals.  A prior-only target
    # remains visible; unobserved residual labels are not invented.
    return {
        "since": since, "until": until, "field_since": field_since,
        "registration_count": len(selected), "legal_registration_count": total_legal,
        "round_audit": {"counts": round_counts, "resolved_match_records": round_counts.get("resolved_match_records", 0)},
        "ranking": projection, "rows": rows,
    }


def build_variant_report(
    con: duckdb.DuckDBPyConnection,
    global_payload: Mapping[str, Any],
    *,
    since: str = _DEFAULT_SINCE,
    draws: int = _DEFAULT_DRAWS,
) -> dict[str, Any]:
    """Build the complete Doomsday variant report from a read-only connection."""
    since = _public_date(since, "since")
    start = _iso_date(since)
    if draws < 1:
        raise ValueError("draws must be positive")
    shares, counts, field_info = _global_field(global_payload)
    field_until = field_info.get("until")
    if not field_until or not field_info.get("since"):
        raise ValueError("global field requires explicit since and exclusive until dates")
    until = str(field_until)[:10]
    cutoff = _iso_date(until) - timedelta(days=1)
    if field_info["since"] >= until:
        raise ValueError("field.since must precede field.until")
    if start >= _iso_date(until):
        raise ValueError("since must precede the global field cutoff")
    registrations, _boards, metadata = _load_registrations(con, since, until)
    aliases = _verified_event_aliases(con, since, until)
    registrations = [reg for reg in registrations if reg.event_id not in aliases]
    snapshot = banlist_as_of(cutoff)
    audit = {
        "unclassifiable": [], "partial_metadata": [], "malformed": [],
        "banned_registrations": 0, "banned_doomsday_registrations": 0,
        "event_aliases": aliases,
        "invalid_list_count": sum(bool(reg.list_errors) for reg in registrations),
        "invalid_doomsday_lists": [
            {"event_id": reg.event_id, "deck_idx": reg.deck_idx, "errors": list(reg.list_errors)}
            for reg in registrations if reg.archetype == "Doomsday" and reg.list_errors
        ],
    }
    for reg in registrations:
        reg.banned_cards = _banned_cards(reg, snapshot)
        if reg.banned_cards:
            audit["banned_registrations"] += 1
            if reg.archetype == "Doomsday":
                audit["banned_doomsday_registrations"] += 1
        if reg.archetype != "Doomsday":
            continue
        reg.classification = classify_variant(reg.mainboard, reg.sideboard, metadata)
        if reg.classification.variant_id == "unclassifiable":
            audit["unclassifiable"].append({"event_id": reg.event_id, "deck_idx": reg.deck_idx, "player": reg.player, "missing_metadata": list(reg.classification.missing_metadata)})
        elif reg.classification.missing_metadata:
            audit["partial_metadata"].append({"event_id": reg.event_id, "deck_idx": reg.deck_idx, "player": reg.player, "missing_metadata": list(reg.classification.missing_metadata)})
        if reg.classification.malformed_cards:
            audit["malformed"].append({"event_id": reg.event_id, "deck_idx": reg.deck_idx, "player": reg.player, "cards": list(reg.classification.malformed_cards)})
    field_since = str(field_info.get("since") or "")[:10] or None
    current_since = max(start, _iso_date(field_since)) if field_since else start
    all_view = _view_payload(con, registrations, shares, counts, since=since, until=until, cutoff=cutoff, field_since=field_since, draws=draws, seed=_DEFAULT_SEED)
    current_view = _view_payload(con, registrations, shares, counts, since=current_since.isoformat(), until=until, cutoff=cutoff, field_since=field_since, draws=draws, seed=_DEFAULT_SEED)
    audit["unclassifiable"] = sorted(audit["unclassifiable"], key=lambda row: (row["event_id"], row["deck_idx"]))
    audit["partial_metadata"] = sorted(audit["partial_metadata"], key=lambda row: (row["event_id"], row["deck_idx"]))
    audit["malformed"] = sorted(audit["malformed"], key=lambda row: (row["event_id"], row["deck_idx"]))
    return {
        "schema": "doomsday-variant-rankings-v1",
        "meta": {
            "protocol": "variant-compatible-physical-rounds-v1",
            "generated_for": "Doomsday variant comparison",
            "since": since,
            "field_since": field_since,
            "until": until,
            "cutoff_inclusive": cutoff.isoformat(),
            "ban_snapshot_as_of": snapshot.as_of.isoformat(),
            "draws": draws,
            "seed": _DEFAULT_SEED,
            "standings_denominator": "published non-League standings; legal subject registrations only",
            "round_denominator": "decisive resolved physical rounds with both lists legal at cutoff and non-Doomsday opponent",
            "caveat": "Observed W-L describes available published lists and repeated pilots; it is not an all-entrant or causal splash estimate. Independent-cell intervals omit pilot/event dependence and historical drift.",
        },
        "registry": [spec.__dict__ for spec in _SPECS],
        "field": field_info,
        "audit": audit,
        "views": {"all": all_view, "current": current_view},
    }
