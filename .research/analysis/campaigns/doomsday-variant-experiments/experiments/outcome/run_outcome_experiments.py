"""Reproduce the Doomsday variant outcome experiments from the local DuckDB snapshot.

The outputs deliberately keep League 5-0 publications separate from standings-backed
records.  They describe observed entrants and publications; they do not estimate a deck's
causal win rate or the population of failed League attempts.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[6]))
from legacy_engine.models.decklist import parse_decklist


ROOT = Path(__file__).resolve().parents[6]
DB = ROOT / "data/legacy.duckdb"
MANIFEST = ROOT / "decks/doomsday-variants/manifest.json"
OUT = Path(__file__).resolve().parent

CURRENT_START = "2026-08-10"
CURRENT_END = "2026-08-19"
WINDOWS = (
    ("earlier_2026", "2026-01-01", "2026-06-30"),
    ("immediate_pre_boundary", "2026-07-01", "2026-08-09"),
    ("current", CURRENT_START, CURRENT_END),
)

ACCELERATION = {"Dark Ritual", "Lion's Eye Diamond", "Lotus Petal"}
SELECTION = {"Personal Tutor", "Flow State"}
MAIN_VALUE = {
    "Tamiyo, Inquisitive Student",
    "Bilbo, Thief in the Night",
    "Teferi, Time Raveler",
    "Murktide Regent",
    "Hexing Squelcher",
}
SIDE_FAIR = {
    "Barrowgoyf",
    "Dauthi Voidwalker",
    "Murktide Regent",
    "Orcish Bowmasters",
    "Tamiyo, Inquisitive Student",
    "Moonshadow",
    "Cori-Steel Cutter",
    "Chancellor of the Annex",
    "Sheoldred, the Apocalypse",
    "Quantum Riddler",
    "Brazen Borrower",
    "Voice of Victory",
    "Containment Priest",
}
SIDE_ALT = {"Paradigm Shift", "Thassa's Oracle", "Emrakul, the Aeons Torn", "Shelldock Isle"}

CATEGORY_CARDS = {
    "personal_tutor_main": {"Personal Tutor"},
    "wasteland_main": {"Wasteland"},
    "tamiyo_main": {"Tamiyo, Inquisitive Student"},
    "bilbo_main": {"Bilbo, Thief in the Night"},
    "teferi_main": {"Teferi, Time Raveler"},
    "murktide_main": {"Murktide Regent"},
    "squelcher_main": {"Hexing Squelcher"},
}


def canonical_hash(main: dict[str, int], side: dict[str, int]) -> str:
    payload = {
        "main": sorted([[name, count] for name, count in main.items()]),
        "side": sorted([[name, count] for name, count in side.items()]),
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def wilson(wins: int, losses: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    n = wins + losses
    if not n:
        return None, None
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return center - margin, center + margin


def pct(value: float | None) -> str:
    return "" if value is None else f"{100 * value:.1f}"


def write_csv(name: str, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path = OUT / name
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def parse_published_result(result: str | None) -> tuple[int, int, int] | None:
    if not result or "-" not in result:
        return None
    parts = result.split("-")
    if len(parts) == 2 and all(part.isdigit() for part in parts):
        return int(parts[0]), int(parts[1]), 0
    return None


def classify(metrics: dict[str, int], *, deep_value: int = 4, value: int = 6, side: int = 4) -> str:
    if metrics["wasteland"] >= 3 and metrics["main_value"] >= deep_value:
        return "D_deep_denial"
    if metrics["main_value"] >= value:
        return "C_value_combo"
    if metrics["side_fair"] >= side or metrics["side_alt"] >= 2:
        return "B_sideboard_led"
    return "A_focused_combo"


def aggregate(rows: list[dict[str, object]]) -> dict[str, object]:
    wins = sum(int(row["wins"]) for row in rows)
    losses = sum(int(row["losses"]) for row in rows)
    draws = sum(int(row["draws"]) for row in rows)
    low, high = wilson(wins, losses)
    return {
        "entries": len(rows),
        "pilots": len({row["pilot"] for row in rows}),
        "events": len({row["tournament_id"] for row in rows}),
        "exact_lists": len({row["exact_hash"] for row in rows}),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "decision_win_pct": pct(wins / (wins + losses) if wins + losses else None),
        "wilson95_low_pct": pct(low),
        "wilson95_high_pct": pct(high),
    }


def collapse_obvious_duplicates(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Collapse same-date, same-pilot, same-list, same-result duplicate source rows."""
    kept: dict[tuple[object, ...], dict[str, object]] = {}
    for row in rows:
        key = (row["date"], row["pilot"], row["exact_hash"], row["published_result"])
        kept.setdefault(key, row)
    return list(kept.values())


def main() -> None:
    connection = duckdb.connect(str(DB), read_only=True)
    deck_rows = connection.execute(
        """
        SELECT substr(t.date, 1, 10) AS event_date, t.id, t.name, t.source,
               d.deck_idx, d.player, d.result, d.archetype,
               s.rank, s.wins, s.losses, s.draws
        FROM decks d
        JOIN tournaments t ON t.id = d.tournament_id
        LEFT JOIN standings s ON s.tournament_id = d.tournament_id AND s.player = d.player
        WHERE substr(t.date, 1, 10) <= ?
          AND d.archetype = 'Doomsday'
        ORDER BY event_date, t.id, d.deck_idx
        """,
        [CURRENT_END],
    ).fetchall()

    card_rows = connection.execute(
        """
        SELECT dc.tournament_id, dc.deck_idx, dc.board, dc.name, dc.count,
               coalesce(c.is_land, false)
        FROM deck_cards dc
        JOIN decks d ON d.tournament_id = dc.tournament_id AND d.deck_idx = dc.deck_idx
        JOIN tournaments t ON t.id = d.tournament_id
        LEFT JOIN cards c ON c.name = dc.name
        WHERE substr(t.date, 1, 10) <= ?
          AND d.archetype = 'Doomsday'
        ORDER BY dc.tournament_id, dc.deck_idx, dc.board, dc.name
        """,
        [CURRENT_END],
    ).fetchall()
    cards: dict[tuple[str, int], dict[str, dict[str, int]]] = defaultdict(lambda: {"main": {}, "side": {}})
    lands: dict[tuple[str, int], int] = defaultdict(int)
    for tournament_id, deck_idx, board, name, count, is_land in card_rows:
        cards[(tournament_id, deck_idx)][board][name] = count
        if board == "main" and is_land:
            lands[(tournament_id, deck_idx)] += count

    rows: list[dict[str, object]] = []
    for event_date, tournament_id, event, source, deck_idx, pilot, result, archetype, rank, sw, sl, sd in deck_rows:
        boards = cards[(tournament_id, deck_idx)]
        main_cards, side_cards = boards["main"], boards["side"]
        metrics = {
            "lands": lands[(tournament_id, deck_idx)],
            "acceleration": sum(main_cards.get(card, 0) for card in ACCELERATION),
            "selection": sum(main_cards.get(card, 0) for card in SELECTION),
            "main_value": sum(main_cards.get(card, 0) for card in MAIN_VALUE),
            "wasteland": main_cards.get("Wasteland", 0),
            "side_fair": sum(side_cards.get(card, 0) for card in SIDE_FAIR),
            "side_alt": sum(side_cards.get(card, 0) for card in SIDE_ALT),
        }
        is_league = event == "Legacy League"
        publication = parse_published_result(result) if is_league else None
        evidence = "league_publication" if is_league else ("standings_backed" if sw is not None else "placement_only")
        wins, losses, draws = publication or (
            (int(sw), int(sl), int(sd)) if sw is not None else (0, 0, 0)
        )
        row: dict[str, object] = {
            "date": event_date,
            "tournament_id": tournament_id,
            "event": event,
            "source": source,
            "deck_idx": deck_idx,
            "pilot": pilot,
            "published_result": result,
            "rank": "" if rank is None else rank,
            "evidence_channel": evidence,
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "exact_hash": canonical_hash(main_cards, side_cards),
            **metrics,
            "baseline_class": classify(metrics),
        }
        for category, names in CATEGORY_CARDS.items():
            row[category] = int(any(main_cards.get(name, 0) > 0 for name in names))
        rows.append(row)

    current = [row for row in rows if CURRENT_START <= str(row["date"]) <= CURRENT_END]
    write_csv("current_census.csv", current)

    broader_only = connection.execute(
        """
        SELECT substr(t.date, 1, 10) AS event_date, t.id AS tournament_id, t.name AS event,
               d.deck_idx, d.player AS pilot, d.result AS published_result, d.archetype,
               sum(dc.count) AS main_doomsday_count,
               s.rank, s.wins, s.losses, s.draws
        FROM decks d
        JOIN tournaments t ON t.id = d.tournament_id
        JOIN deck_cards dc ON dc.tournament_id = d.tournament_id AND dc.deck_idx = d.deck_idx
        LEFT JOIN standings s ON s.tournament_id = d.tournament_id AND s.player = d.player
        WHERE substr(t.date, 1, 10) BETWEEN ? AND ?
          AND dc.board = 'main' AND dc.name = 'Doomsday'
          AND d.archetype <> 'Doomsday'
        GROUP BY ALL
        ORDER BY event_date, tournament_id, d.deck_idx
        """,
        [CURRENT_START, CURRENT_END],
    ).fetchall()
    write_csv(
        "current_broader_construction_only.csv",
        [
            dict(zip(
                ["date", "tournament_id", "event", "deck_idx", "pilot", "published_result", "stored_archetype", "main_doomsday_count", "rank", "wins", "losses", "draws"],
                row,
            ))
            for row in broader_only
        ],
        ["date", "tournament_id", "event", "deck_idx", "pilot", "published_result", "stored_archetype", "main_doomsday_count", "rank", "wins", "losses", "draws"],
    )

    category_rows: list[dict[str, object]] = []
    category_masks: list[tuple[str, list[dict[str, object]]]] = [("all_exact_archetype", current)]
    for category in CATEGORY_CARDS:
        category_masks.append((category, [row for row in current if row[category]]))
    for class_name in ("A_focused_combo", "B_sideboard_led", "C_value_combo", "D_deep_denial"):
        category_masks.append((class_name, [row for row in current if row["baseline_class"] == class_name]))
    cuts = {
        "all_publications": lambda row: row["evidence_channel"] != "placement_only",
        "standings_backed_only": lambda row: row["evidence_channel"] == "standings_backed",
        "mtgo_challenge_only": lambda row: row["evidence_channel"] == "standings_backed" and str(row["event"]).startswith("Legacy Challenge"),
    }
    for category, members in category_masks:
        for cut, predicate in cuts.items():
            selected = [row for row in members if predicate(row)]
            category_rows.append({"category": category, "cut": cut, **aggregate(selected)})
    write_csv("current_category_outcomes.csv", category_rows)

    dependence: list[dict[str, object]] = []
    for category, members in category_masks[1:]:
        selected = [row for row in members if row["evidence_channel"] == "standings_backed"]
        base = aggregate(selected)
        pilot_rates = []
        for pilot in sorted({str(row["pilot"]) for row in selected}):
            remaining = [row for row in selected if row["pilot"] != pilot]
            wins = sum(int(row["wins"]) for row in remaining)
            losses = sum(int(row["losses"]) for row in remaining)
            if wins + losses:
                pilot_rates.append(100 * wins / (wins + losses))
        event_rates = []
        for event_id in sorted({str(row["tournament_id"]) for row in selected}):
            remaining = [row for row in selected if row["tournament_id"] != event_id]
            wins = sum(int(row["wins"]) for row in remaining)
            losses = sum(int(row["losses"]) for row in remaining)
            if wins + losses:
                event_rates.append(100 * wins / (wins + losses))
        dependence.append({
            "category": category,
            **base,
            "leave_one_pilot_out_min_pct": f"{min(pilot_rates):.1f}" if pilot_rates else "",
            "leave_one_pilot_out_max_pct": f"{max(pilot_rates):.1f}" if pilot_rates else "",
            "leave_one_event_out_min_pct": f"{min(event_rates):.1f}" if event_rates else "",
            "leave_one_event_out_max_pct": f"{max(event_rates):.1f}" if event_rates else "",
        })
    write_csv("current_dependence_sensitivity.csv", dependence)

    thresholds = (
        ("baseline", 4, 6, 4),
        ("deep_requires_6", 6, 6, 4),
        ("side_requires_6", 4, 6, 6),
        ("value_requires_8", 4, 8, 4),
    )
    taxonomy_rows: list[dict[str, object]] = []
    for threshold_name, deep_value, value, side in thresholds:
        classified: dict[str, list[dict[str, object]]] = defaultdict(list)
        for row in current:
            class_name = classify(row, deep_value=deep_value, value=value, side=side)
            classified[class_name].append(row)
        for class_name in ("A_focused_combo", "B_sideboard_led", "C_value_combo", "D_deep_denial"):
            members = classified[class_name]
            for channel in ("all", "standings_backed"):
                selected = members if channel == "all" else [r for r in members if r["evidence_channel"] == "standings_backed"]
                taxonomy_rows.append({
                    "threshold": threshold_name,
                    "class": class_name,
                    "evidence_cut": channel,
                    **aggregate(selected),
                })
    write_csv("taxonomy_threshold_sensitivity.csv", taxonomy_rows)

    window_rows: list[dict[str, object]] = []
    for window_name, start, end in WINDOWS:
        members = [row for row in rows if start <= str(row["date"]) <= end]
        for class_name in ("all", "A_focused_combo", "B_sideboard_led", "C_value_combo", "D_deep_denial"):
            class_members = members if class_name == "all" else [r for r in members if r["baseline_class"] == class_name]
            for channel in (
                "all_entries",
                "all_entries_duplicate_collapsed",
                "league_publications",
                "standings_backed",
                "standings_backed_duplicate_collapsed",
            ):
                if channel == "league_publications":
                    selected = [r for r in class_members if r["evidence_channel"] == "league_publication"]
                elif channel == "standings_backed":
                    selected = [r for r in class_members if r["evidence_channel"] == "standings_backed"]
                elif channel == "standings_backed_duplicate_collapsed":
                    selected = collapse_obvious_duplicates(
                        [r for r in class_members if r["evidence_channel"] == "standings_backed"]
                    )
                elif channel == "all_entries_duplicate_collapsed":
                    selected = collapse_obvious_duplicates(class_members)
                else:
                    selected = class_members
                window_rows.append({
                    "window": window_name,
                    "start": start,
                    "end": end,
                    "class": class_name,
                    "channel": channel,
                    **aggregate(selected),
                })
    write_csv("historical_window_summary.csv", window_rows)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    candidate_by_hash = {candidate["canonical_deck_sha256"]: candidate for candidate in manifest["candidates"]}
    recurrences: list[dict[str, object]] = []
    def card_distance(left: dict[str, dict[str, int]], right: dict[str, dict[str, int]]) -> int:
        return sum(
            abs(left[board].get(name, 0) - right[board].get(name, 0))
            for board in ("main", "side")
            for name in set(left[board]) | set(right[board])
        )

    for exact_hash, candidate in sorted(candidate_by_hash.items(), key=lambda pair: pair[1]["id"]):
        matches = [row for row in rows if row["exact_hash"] == exact_hash]
        dedup_matches = collapse_obvious_duplicates(matches)
        main_cards, side_cards = parse_decklist((ROOT / candidate["path"]).read_text(encoding="utf-8"))
        candidate_cards = {"main": main_cards, "side": side_cards}
        distances = [
            (card_distance(candidate_cards, cards[(str(row["tournament_id"]), int(row["deck_idx"]))]), row)
            for row in rows
        ]
        nearest_distance = min((distance for distance, _row in distances), default=None)
        nearest = [row for distance, row in distances if distance == nearest_distance]
        by_channel = Counter(str(row["evidence_channel"]) for row in matches)
        standings_matches = [row for row in matches if row["evidence_channel"] == "standings_backed"]
        dedup_standings = [row for row in dedup_matches if row["evidence_channel"] == "standings_backed"]
        recurrences.append({
            "candidate_id": candidate["id"],
            "evidence_posture": candidate["evidence_posture"],
            "exact_hash": exact_hash,
            "matching_entries_all_time": len(matches),
            "duplicate_collapsed_entries": len(dedup_matches),
            "matching_entries_2026": sum(str(row["date"]) >= "2026-01-01" for row in matches),
            "matching_pilots": len({row["pilot"] for row in matches}),
            "matching_events": len({row["tournament_id"] for row in matches}),
            "first_seen": min((str(row["date"]) for row in matches), default=""),
            "last_seen": max((str(row["date"]) for row in matches), default=""),
            "league_publications": by_channel["league_publication"],
            "standings_backed_entries": by_channel["standings_backed"],
            "standings_wins": sum(int(row["wins"]) for row in standings_matches),
            "standings_losses": sum(int(row["losses"]) for row in standings_matches),
            "dedup_standings_wins": sum(int(row["wins"]) for row in dedup_standings),
            "dedup_standings_losses": sum(int(row["losses"]) for row in dedup_standings),
            "nearest_card_count_distance": "" if nearest_distance is None else nearest_distance,
            "nearest_rows": " | ".join(
                f"{row['date']}::{row['pilot']}::{row['tournament_id']}::{row['deck_idx']}"
                for row in nearest[:5]
            ),
        })
    write_csv("registered_candidate_recurrence.csv", recurrences)

    overlap = Counter()
    for row in current:
        labels = sorted(category for category in CATEGORY_CARDS if row[category])
        overlap[" + ".join(labels) if labels else "none_of_named_main_cards"] += 1
    write_csv("current_category_overlap.csv", [
        {"overlapping_signature": signature, "entries": count}
        for signature, count in sorted(overlap.items())
    ])

    metadata = {
        "schema": "doomsday-outcome-experiments",
        "generated_from": str(DB.relative_to(ROOT)),
        "database_sha256": hashlib.sha256(DB.read_bytes()).hexdigest(),
        "database_max_tournament_date": connection.execute("SELECT max(substr(date,1,10)) FROM tournaments").fetchone()[0],
        "database_max_exact_doomsday_date": max(str(row["date"]) for row in rows),
        "current_window": {"start": CURRENT_START, "end": CURRENT_END},
        "population": "decks.archetype = 'Doomsday'",
        "notes": [
            "League rows are selected 5-0 publications and have no failed-run denominator.",
            "Wilson intervals describe recorded match decisions for published entrants only.",
            "Historical windows cross construction and legality regimes and are not pooled causal estimates.",
            "Category memberships overlap; taxonomy classes are mutually exclusive by precedence.",
        ],
        "row_counts": {
            "current_exact_archetype": len(current),
            "current_broader_construction_only": len(broader_only),
            "current_league_publications": sum(r["evidence_channel"] == "league_publication" for r in current),
            "current_standings_backed": sum(r["evidence_channel"] == "standings_backed" for r in current),
        },
    }
    (OUT / "experiment_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
