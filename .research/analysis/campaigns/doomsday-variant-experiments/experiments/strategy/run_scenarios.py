#!/usr/bin/env python3
"""Emit deterministic, hypothetical Doomsday strategy scenarios.

This script does not simulate played games. It inventories registered lists, extracts the
refreshed decision-field shares embedded in the ranking page, computes algebraic break-even
requirements, and emits a prospective paired-test matrix.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
HERE = Path(__file__).resolve().parent
CONFIG = HERE / "scenario_config.json"
DATA_RE = re.compile(r"const D = (\{.*?\});\n", re.DOTALL)


def parse_deck(path: Path) -> tuple[dict[str, int], dict[str, int]]:
    boards: dict[str, dict[str, int]] = {"main": {}, "side": {}}
    board = "main"
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//")):
            continue
        if line.lower() == "sideboard":
            board = "side"
            continue
        match = re.fullmatch(r"(\d+)\s+(.+)", line)
        if not match:
            raise ValueError(f"unparseable deck line in {path}: {line!r}")
        boards[board][match.group(2)] = int(match.group(1))
    return boards["main"], boards["side"]


def canonical_hash(mainboard: dict[str, int], sideboard: dict[str, int]) -> str:
    payload = {
        "main": sorted([[name, count] for name, count in mainboard.items()]),
        "side": sorted([[name, count] for name, count in sideboard.items()]),
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    page_path = ROOT / config["field_source"]
    match = DATA_RE.search(page_path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError("ranking page does not contain the expected embedded data object")
    page = json.loads(match.group(1))
    field_by_name = {row["subject"]: row for row in page["arch"]}

    field_rows = []
    for opponent in config["representative_opponents"]:
        row = field_by_name[opponent["archetype"]]
        field_rows.append({
            "archetype": opponent["archetype"],
            "strategic_role": opponent["role"],
            "decision_field_share": row["field_share"],
            "observed_count": row["observed_count"],
            "prior_count": row["prior_count"],
            "field_evidence_kind": row["field_evidence_kind"],
            "field_since": page["meta"]["field_since"],
            "corpus_max": page["meta"]["corpus_max"],
        })
    write_csv(HERE / "representative_field.csv", field_rows, list(field_rows[0]))

    break_even_rows = []
    for share_pct in config["break_even"]["hostile_share_percent"]:
        share = share_pct / 100
        for cost in config["break_even"]["broad_field_cost_points"]:
            required_gain = cost * (1 - share) / share
            break_even_rows.append({
                "hostile_share_percent": share_pct,
                "broad_field_cost_points": cost,
                "required_hostile_gain_points": round(required_gain, 4),
            })
    write_csv(HERE / "break_even.csv", break_even_rows, list(break_even_rows[0]))

    manifest_path = ROOT / config["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    inventory_rows = []
    for candidate in manifest["candidates"]:
        deck_path = ROOT / candidate["path"]
        mainboard, sideboard = parse_deck(deck_path)
        actual_hash = canonical_hash(mainboard, sideboard)
        if actual_hash != candidate["canonical_deck_sha256"]:
            raise ValueError(f"hash drift for {candidate['id']}")
        inventory_rows.append({
            "candidate_id": candidate["id"],
            "strategic_class": config["strategic_classes"][candidate["id"]],
            "evidence_posture": candidate["evidence_posture"],
            "main_cards": sum(mainboard.values()),
            "side_cards": sum(sideboard.values()),
            "main_personal_tutor": mainboard.get("Personal Tutor", 0),
            "main_tamiyo": mainboard.get("Tamiyo, Inquisitive Student", 0),
            "main_bilbo": mainboard.get("Bilbo, Thief in the Night", 0),
            "main_teferi": mainboard.get("Teferi, Time Raveler", 0),
            "main_wasteland": mainboard.get("Wasteland", 0),
            "main_murktide": mainboard.get("Murktide Regent", 0),
            "main_hexing_squelcher": mainboard.get("Hexing Squelcher", 0),
            "side_nonoracle_creatures": sum(sideboard.get(card, 0) for card in (
                "Barrowgoyf", "Brazen Borrower", "Chancellor of the Annex", "Containment Priest",
                "Dauthi Voidwalker", "Emrakul, the Aeons Torn", "Hexing Squelcher", "Moonshadow",
                "Murktide Regent", "Orcish Bowmasters", "Quantum Riddler",
                "Sheoldred, the Apocalypse", "Tamiyo, Inquisitive Student", "Voice of Victory",
            )),
            "side_veil": sideboard.get("Veil of Summer", 0),
            "side_carpet": sideboard.get("Carpet of Flowers", 0),
            "side_swords": sideboard.get("Swords to Plowshares", 0),
        })
    write_csv(HERE / "candidate_inventory.csv", inventory_rows, list(inventory_rows[0]))

    control = config["control_id"]
    matrix_rows = []
    for candidate in manifest["candidates"]:
        if candidate["id"] == control:
            continue
        for opponent in config["representative_opponents"]:
            matrix_rows.append({
                "candidate_id": candidate["id"],
                "control_id": control,
                "opponent_archetype": opponent["archetype"],
                "opponent_list_version": "register-before-block",
                "candidate_matches": opponent["matches_per_arm"],
                "control_matches": opponent["matches_per_arm"],
                "paired_assignment": "balance-play-draw-and-list-order",
                "status": "prospective-no-results",
            })
    write_csv(HERE / "physical_test_matrix.csv", matrix_rows, list(matrix_rows[0]))

    summary = {
        "schema": config["schema"],
        "source_clock": {
            "field_since": page["meta"]["field_since"],
            "corpus_max": page["meta"]["corpus_max"],
            "field_decks": page["meta"]["field_decks"],
            "field_evidence_kind": page["meta"]["field_evidence_kind"],
        },
        "candidate_count": len(inventory_rows),
        "non_control_candidate_count": len(inventory_rows) - 1,
        "representative_opponent_share": round(sum(row["decision_field_share"] for row in field_rows), 6),
        "prospective_candidate_matches": sum(row["candidate_matches"] for row in matrix_rows),
        "prospective_control_matches": sum(row["control_matches"] for row in matrix_rows),
        "played_game_results": 0,
        "interpretation": "algebraic scenarios and prospective design only; no observed candidate matchup effects",
    }
    (HERE / "scenario_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
