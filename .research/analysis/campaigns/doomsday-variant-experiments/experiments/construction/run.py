#!/usr/bin/env python3
"""Deterministic construction/access measurements for registered Doomsday 75s.

This experiment measures deck composition and exact unordered opening-hand
probabilities. It does not model mulligans, card sequencing, Doomsday piles,
opposing interaction, or matchup win rate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path

from legacy_engine.ingestion.banlist import banlist_as_of, current_banlist, validate_deck
from legacy_engine.models.decklist import parse_decklist


ROOT = Path(__file__).resolve().parents[6]
MANIFEST = ROOT / "decks/doomsday-variants/manifest.json"
CARDS = ROOT / "data/scryfall/oracle_cards.json"
HISTORICAL_SNAPSHOT = banlist_as_of(date(2026, 8, 10))

ACCELERATION = {"Dark Ritual", "Cabal Ritual", "Lion's Eye Diamond", "Lotus Petal"}
ACCESS = {"Doomsday", "Personal Tutor"}
SELECTION = {
    "Brainstorm", "Consider", "Flow State", "Mishra's Bauble", "Ponder",
    "Street Wraith",
}
PROTECTION = {
    "Chancellor of the Annex", "Consign to Memory", "Daze", "Duress",
    "Flusterstorm", "Force of Negation", "Force of Will", "Hexing Squelcher",
    "Inquisition of Kozilek", "Misdirection", "Pyroblast", "Teferi, Time Raveler",
    "Thoughtseize", "Veil of Summer", "Voice of Victory",
}
INTERACTION = {
    "Abrupt Decay", "Bitter Triumph", "Brazen Borrower", "Consign to Memory",
    "Engineered Explosives", "Fatal Push", "Hexing Squelcher", "Hydroblast",
    "Long Goodbye", "Molten Collapse", "Portable Hole", "Prismatic Ending",
    "Pyroblast", "Snuff Out", "Swords to Plowshares", "Teferi, Time Raveler",
    "Witherbloom Charm", "Wasteland",
}
MAIN_VALUE_TEMPO = {
    "Bilbo, Thief in the Night", "Hexing Squelcher", "Jace, Wielder of Mysteries",
    "Murktide Regent", "Quantum Riddler", "Tamiyo, Inquisitive Student",
    "Teferi, Time Raveler", "Wasteland",
}
SIDE_PIVOT = {
    "Barrowgoyf", "Brazen Borrower", "Chancellor of the Annex",
    "Containment Priest", "Cori-Steel Cutter", "Dauthi Voidwalker",
    "Moonshadow", "Murktide Regent", "Orcish Bowmasters", "Quantum Riddler",
    "Sheoldred, the Apocalypse", "Tamiyo, Inquisitive Student", "Voice of Victory",
}
SIDE_ALT_COMBO = {
    "Emrakul, the Aeons Torn", "Jace, Wielder of Mysteries", "Paradigm Shift",
    "Shelldock Isle", "Thassa's Oracle",
}
COLORS = ("W", "U", "B", "R", "G")


def load_cards() -> dict[str, dict]:
    cards: dict[str, dict] = {}
    with CARDS.open(encoding="utf-8") as handle:
        for line in handle:
            card = json.loads(line)
            cards[card["name"]] = card
            for face in card.get("card_faces") or []:
                # Decklists use the front-face name for transforming cards.
                cards.setdefault(face["name"], {**card, **face})
    return cards


def canonical_hash(main: dict[str, int], side: dict[str, int]) -> str:
    payload = {
        "main": sorted([[name, count] for name, count in main.items()]),
        "side": sorted([[name, count] for name, count in side.items()]),
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def fetch_types(card: dict) -> set[str]:
    text = card.get("oracle_text") or ""
    match = re.search(r"an? ([A-Za-z]+) or ([A-Za-z]+) card", text)
    return set(match.groups()) if match else set()


def land_sources(main: dict[str, int], cards: dict[str, dict]) -> tuple[dict[str, set[str]], set[str], set[str]]:
    lands = {name for name in main if "Land" in (cards[name].get("type_line") or "")}
    typed_lands: dict[str, set[str]] = {}
    for name in lands:
        type_line = cards[name].get("type_line") or ""
        typed_lands[name] = {t for t in ("Plains", "Island", "Swamp", "Mountain", "Forest") if t in type_line}

    by_color = {color: set() for color in COLORS}
    fetches: set[str] = set()
    restricted: set[str] = set()
    for name in lands:
        card = cards[name]
        produced = set(card.get("produced_mana") or [])
        if name == "Cavern of Souls":
            restricted.add(name)
        else:
            for color in COLORS:
                if color in produced:
                    by_color[color].add(name)
        targets = fetch_types(card)
        if targets:
            fetches.add(name)
            for color in COLORS:
                if any(targets & types and color in set(cards[target].get("produced_mana") or [])
                       for target, types in typed_lands.items()):
                    by_color[color].add(name)
    return by_color, fetches, restricted


def copies(board: dict[str, int], names: set[str]) -> int:
    return sum(board.get(name, 0) for name in names)


def probability_at_least_one(deck_size: int, successes: int, draws: int) -> float:
    return 1.0 - math.comb(deck_size - successes, draws) / math.comb(deck_size, draws)


def probability_at_least(deck_size: int, successes: int, draws: int, threshold: int) -> float:
    denominator = math.comb(deck_size, draws)
    excluded = sum(
        math.comb(successes, k) * math.comb(deck_size - successes, draws - k)
        for k in range(threshold)
        if k <= successes and draws - k <= deck_size - successes
    )
    return 1.0 - excluded / denominator


def probability_mask(main: dict[str, int], category_sets: list[set[str]], required_mask: int, draws: int = 7) -> float:
    """Exact probability that all required category bits appear in an unordered hand."""
    groups: Counter[int] = Counter()
    for name, count in main.items():
        mask = 0
        for i, category in enumerate(category_sets):
            if name in category:
                mask |= 1 << i
        groups[mask] += count

    states: dict[tuple[int, int], int] = {(0, 0): 1}
    for mask, count in groups.items():
        next_states: dict[tuple[int, int], int] = {}
        for (used, seen), ways in states.items():
            for take in range(min(count, draws - used) + 1):
                key = (used + take, seen | (mask if take else 0))
                next_states[key] = next_states.get(key, 0) + ways * math.comb(count, take)
        states = next_states
    favorable = sum(ways for (used, seen), ways in states.items() if used == draws and seen & required_mask == required_mask)
    return favorable / math.comb(sum(main.values()), draws)


def pct(value: float) -> float:
    return round(100.0 * value, 3)


def measure(candidate: dict, cards: dict[str, dict]) -> dict:
    path = ROOT / candidate["path"]
    main, side = parse_decklist(path.read_text(encoding="utf-8"))
    if sum(main.values()) != 60 or sum(side.values()) != 15:
        raise ValueError(f"{candidate['id']}: expected 60/15")
    digest = canonical_hash(main, side)
    if digest != candidate["canonical_deck_sha256"]:
        raise ValueError(f"{candidate['id']}: canonical hash mismatch")
    legality = {}
    for label, snapshot in (("2026-08-10", HISTORICAL_SNAPSHOT), ("current", current_banlist())):
        errors = validate_deck(main, side, snapshot=snapshot)
        legality[label] = {"legal": not errors, "errors": errors}
        if errors:
            raise ValueError(f"{candidate['id']}: illegal at {label}: {errors}")

    by_color, fetches, restricted = land_sources(main, cards)
    lands = {name for name in main if "Land" in (cards[name].get("type_line") or "")}
    access = set(main) & ACCESS
    selection = set(main) & SELECTION
    acceleration = set(main) & ACCELERATION
    protection = set(main) & PROTECTION
    black_or_petal = by_color["B"] | ({"Lotus Petal"} if "Lotus Petal" in main else set())
    splash_colors = [color for color in ("W", "G", "R") if by_color[color]]

    return {
        "id": candidate["id"],
        "path": candidate["path"],
        "status": candidate["status"],
        "evidence_posture": candidate["evidence_posture"],
        "sha256": digest,
        "boards": {"main": sum(main.values()), "side": sum(side.values())},
        "legality": legality,
        "composition": {
            "lands": copies(main, lands),
            "fetchlands": copies(main, fetches),
            "restricted_rainbow_lands": copies(main, restricted),
            "acceleration": copies(main, ACCELERATION),
            "access": copies(main, ACCESS),
            "direct_doomsday": main.get("Doomsday", 0),
            "personal_tutor": main.get("Personal Tutor", 0),
            "selection": copies(main, SELECTION),
            "protection": copies(main, PROTECTION),
            "interaction": copies(main, INTERACTION),
            "main_value_tempo": copies(main, MAIN_VALUE_TEMPO),
            "side_pivot": copies(side, SIDE_PIVOT),
            "side_alt_combo": copies(side, SIDE_ALT_COMBO),
            "side_interaction": copies(side, INTERACTION),
            "max_pivot_displacement_pct": round(100.0 * copies(side, SIDE_PIVOT) / 60.0, 2),
            "land_sources": {color: copies(main, names) for color, names in by_color.items()},
            "splash_colors": splash_colors,
        },
        "opening_7_pct": {
            "land_1plus": pct(probability_at_least_one(60, copies(main, lands), 7)),
            "land_2plus": pct(probability_at_least(60, copies(main, lands), 7, 2)),
            "acceleration_1plus": pct(probability_at_least_one(60, copies(main, ACCELERATION), 7)),
            "doomsday_1plus": pct(probability_at_least_one(60, main.get("Doomsday", 0), 7)),
            "access_1plus": pct(probability_at_least_one(60, copies(main, ACCESS), 7)),
            "selection_1plus": pct(probability_at_least_one(60, copies(main, SELECTION), 7)),
            "protection_1plus": pct(probability_at_least_one(60, copies(main, PROTECTION), 7)),
            "black_land_source_1plus": pct(probability_at_least_one(60, copies(main, by_color["B"]), 7)),
            "blue_land_source_1plus": pct(probability_at_least_one(60, copies(main, by_color["U"]), 7)),
            "access_and_black_or_petal": pct(probability_mask(main, [access, black_or_petal], 0b11)),
            "access_and_selection_and_black_or_petal": pct(probability_mask(main, [access, selection, black_or_petal], 0b111)),
            **{
                f"{color.lower()}_land_source_1plus": pct(probability_at_least_one(60, copies(main, by_color[color]), 7))
                for color in splash_colors
            },
        },
    }


def write_csv(rows: list[dict], path: Path) -> None:
    fields = [
        "id", "status", "lands", "fetchlands", "acceleration", "access", "selection",
        "protection", "interaction", "main_value_tempo", "side_pivot", "side_alt_combo",
        "W_sources", "U_sources", "B_sources", "R_sources", "G_sources",
        "p_land", "p_2land", "p_accel", "p_access", "p_selection", "p_protection",
        "p_access_black", "p_access_selection_black",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            c, p = row["composition"], row["opening_7_pct"]
            writer.writerow({
                "id": row["id"], "status": row["status"], "lands": c["lands"],
                "fetchlands": c["fetchlands"], "acceleration": c["acceleration"],
                "access": c["access"], "selection": c["selection"],
                "protection": c["protection"], "interaction": c["interaction"],
                "main_value_tempo": c["main_value_tempo"], "side_pivot": c["side_pivot"],
                "side_alt_combo": c["side_alt_combo"],
                **{f"{color}_sources": c["land_sources"][color] for color in COLORS},
                "p_land": p["land_1plus"], "p_2land": p["land_2plus"],
                "p_accel": p["acceleration_1plus"], "p_access": p["access_1plus"],
                "p_selection": p["selection_1plus"], "p_protection": p["protection_1plus"],
                "p_access_black": p["access_and_black_or_petal"],
                "p_access_selection_black": p["access_and_selection_and_black_or_petal"],
            })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cards = load_cards()
    rows = [measure(candidate, cards) for candidate in manifest["candidates"]]
    output = {
        "schema": "doomsday-construction-experiment-v1",
        "generated_on": "2026-08-20",
        "method": {
            "draw_model": "exact multivariate hypergeometric; unordered seven-card hand; no mulligans",
            "seed": None,
            "limits": [
                "no sequencing or mana-spending order",
                "no Doomsday-pile construction",
                "no opponent interaction",
                "no matchup or win-rate inference",
                "role-map categories are analyst-composed from the registered card names",
            ],
        },
        "candidate_count": len(rows),
        "candidates": rows,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "results.json").write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    write_csv(rows, args.output_dir / "comparison.csv")
    print(f"wrote {len(rows)} candidates; all 60/15, hash-matched, and legal at both snapshots")


if __name__ == "__main__":
    main()
