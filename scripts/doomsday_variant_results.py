"""Validate and describe the paired Doomsday splash-variant playtest log.

The CSV is deliberately a small game-level contract.  This command reports counts and paired
differences only; it does not rank lists or turn a pilot log into causal evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from legacy_engine.models.decklist import parse_decklist


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "decks/doomsday-variants/manifest.json"
CONTROL_ID = "current-dimir-creature-transform"
STOPPING_MATCHES = 20
NOT_SEEN = "not_seen"
NOT_APPLICABLE = "not_applicable"

FIELDS = (
    "matchup_block_id",
    "match_id",
    "game_id",
    "pair_id",
    "played_on",
    "pilot_id",
    "list_id",
    "list_version",
    "opponent_archetype",
    "opponent_list_version",
    "board_state",
    "play_draw",
    "list_order",
    "opening_hand_size",
    "mulligan_count",
    "opening_hand_decision",
    "combo_turn",
    "game_result",
    "match_result",
    "splash_mana_effect",
    "splash_color_failure",
    "wasteland_exposed",
    "wasteland_punished",
    "cards_boarded_in",
    "cards_boarded_out",
    "protection_present",
    "protection_live",
    "protection_relevant",
    "alternate_plan",
    "alternate_plan_result",
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_CARD_LIST_RE = re.compile(r"^(?:\d+ .+)(?:;\d+ .+)*$")
_SENTINELS = frozenset({NOT_SEEN, NOT_APPLICABLE})
_YES_NO = frozenset({"yes", "no", NOT_SEEN, NOT_APPLICABLE})
_RESULTS = frozenset({"win", "loss", "draw"})


class LogValidationError(ValueError):
    """A row or manifest violates the playtest contract."""


def _canonical_hash(main: dict[str, int], side: dict[str, int]) -> str:
    payload = {
        "main": sorted([[name, count] for name, count in main.items()]),
        "side": sorted([[name, count] for name, count in side.items()]),
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, dict[str, Any]]:
    """Load candidate ids and verify their paths/hashes from the manifest itself."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LogValidationError(f"manifest {path}: {exc}") from exc
    if value.get("schema") != "doomsday-variant-candidates":
        raise LogValidationError("manifest has unknown schema")
    candidates = value.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise LogValidationError("manifest candidates must be a non-empty list")
    entries: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise LogValidationError("manifest candidates must be objects")
        candidate_id = candidate.get("id")
        relative_path = candidate.get("path")
        expected_hash = candidate.get("canonical_deck_sha256")
        if not isinstance(candidate_id, str) or not _ID_RE.fullmatch(candidate_id):
            raise LogValidationError(f"manifest candidate has invalid id {candidate_id!r}")
        if candidate_id in entries:
            raise LogValidationError(f"manifest contains duplicate list id {candidate_id!r}")
        if not isinstance(relative_path, str) or not relative_path.startswith("decks/"):
            raise LogValidationError(f"manifest candidate {candidate_id!r} has invalid path")
        if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise LogValidationError(f"manifest candidate {candidate_id!r} has invalid deck hash")
        deck_path = ROOT / relative_path
        try:
            main, side = parse_decklist(deck_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise LogValidationError(f"manifest candidate {candidate_id!r}: cannot parse {relative_path}: {exc}") from exc
        actual_hash = _canonical_hash(main, side)
        if actual_hash != expected_hash:
            raise LogValidationError(
                f"manifest candidate {candidate_id!r}: deck hash {expected_hash} does not match {actual_hash}"
            )
        if not isinstance(candidate.get("evidence_posture"), str) or not candidate["evidence_posture"].strip():
            raise LogValidationError(f"manifest candidate {candidate_id!r} is missing evidence_posture")
        entries[candidate_id] = candidate
    if CONTROL_ID not in entries:
        raise LogValidationError(f"manifest is missing comparison control {CONTROL_ID!r}")
    return entries


def _require_token(row_number: int, field: str, value: str, allowed: Iterable[str]) -> None:
    allowed_set = frozenset(allowed)
    if value not in allowed_set:
        raise LogValidationError(
            f"row {row_number}: invalid {field} {value!r}; allowed set is {sorted(allowed_set)!r}"
        )


def _require_int(row_number: int, field: str, value: str, *, minimum: int, maximum: int) -> int | None:
    if value in _SENTINELS:
        return None
    try:
        number = int(value)
    except ValueError as exc:
        raise LogValidationError(f"row {row_number}: {field} must be an integer or an explicit sentinel") from exc
    if not minimum <= number <= maximum:
        raise LogValidationError(f"row {row_number}: impossible {field} {number}; expected {minimum}..{maximum}")
    return number


def _require_date(row_number: int, value: str) -> None:
    if not _DATE_RE.fullmatch(value):
        raise LogValidationError(f"row {row_number}: played_on must be YYYY-MM-DD, got {value!r}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise LogValidationError(f"row {row_number}: played_on is not a real date: {value!r}") from exc


def _validate_row(row_number: int, row: dict[str, str], ids: set[str]) -> dict[str, str]:
    for field in FIELDS:
        value = row.get(field)
        if value is None or not value.strip():
            raise LogValidationError(f"row {row_number}: required field {field!r} is blank")
        row[field] = value.strip()
    unknown = sorted(set(row) - set(FIELDS))
    if unknown:
        raise LogValidationError(f"row {row_number}: unknown columns {unknown!r}")
    for field in ("matchup_block_id", "match_id", "game_id", "pair_id", "pilot_id", "list_version", "opponent_list_version"):
        if not _ID_RE.fullmatch(row[field]):
            raise LogValidationError(f"row {row_number}: invalid {field} {row[field]!r}")
    if row["list_id"] not in ids:
        raise LogValidationError(f"row {row_number}: unknown list_id {row['list_id']!r}")
    _require_date(row_number, row["played_on"])
    _require_token(row_number, "board_state", row["board_state"], {"pre", "post"})
    _require_token(row_number, "play_draw", row["play_draw"], {"play", "draw"})
    _require_token(row_number, "list_order", row["list_order"], {"candidate_first", "control_first"})
    _require_token(row_number, "opening_hand_decision", row["opening_hand_decision"], {"keep", "mulligan"})
    opening_size = _require_int(row_number, "opening_hand_size", row["opening_hand_size"], minimum=0, maximum=7)
    mulligans = _require_int(row_number, "mulligan_count", row["mulligan_count"], minimum=0, maximum=7)
    if opening_size is None or mulligans is None:
        raise LogValidationError(f"row {row_number}: opening_hand_size and mulligan_count cannot be sentinels")
    if row["opening_hand_decision"] == "mulligan" and mulligans < 1:
        raise LogValidationError(f"row {row_number}: a mulligan decision requires mulligan_count >= 1")
    _require_int(row_number, "combo_turn", row["combo_turn"], minimum=1, maximum=30)
    _require_token(row_number, "game_result", row["game_result"], _RESULTS)
    _require_token(row_number, "match_result", row["match_result"], _RESULTS | _SENTINELS)
    _require_token(row_number, "splash_mana_effect", row["splash_mana_effect"], {"helped", "hurt", "neutral", * _SENTINELS})
    _require_token(row_number, "splash_color_failure", row["splash_color_failure"], _YES_NO)
    _require_token(row_number, "wasteland_exposed", row["wasteland_exposed"], _YES_NO)
    _require_token(row_number, "wasteland_punished", row["wasteland_punished"], _YES_NO)
    _require_token(row_number, "protection_present", row["protection_present"], _YES_NO)
    _require_token(row_number, "protection_live", row["protection_live"], _YES_NO)
    _require_token(row_number, "protection_relevant", row["protection_relevant"], _YES_NO)
    _require_token(row_number, "alternate_plan", row["alternate_plan"], {"yes", "no", * _SENTINELS})
    _require_token(row_number, "alternate_plan_result", row["alternate_plan_result"], _RESULTS | _SENTINELS)
    for field in ("cards_boarded_in", "cards_boarded_out"):
        value = row[field]
        if value not in _SENTINELS and not _CARD_LIST_RE.fullmatch(value):
            raise LogValidationError(
                f"row {row_number}: {field} must be 'not_seen', 'not_applicable', or ';'-separated '<count> <card>' values"
            )
    if row["board_state"] == "pre":
        for field in ("cards_boarded_in", "cards_boarded_out", "alternate_plan", "alternate_plan_result"):
            if row[field] != NOT_APPLICABLE:
                raise LogValidationError(f"row {row_number}: {field} must be not_applicable before boarding")
    if row["board_state"] == "post" and row["alternate_plan"] == NOT_APPLICABLE:
        raise LogValidationError(f"row {row_number}: post-board alternate_plan must be yes, no, or not_seen")
    if row["alternate_plan"] in {NOT_APPLICABLE, NOT_SEEN, "no"} and row["alternate_plan_result"] != NOT_APPLICABLE:
        raise LogValidationError(f"row {row_number}: alternate_plan_result must be not_applicable when no plan was deployed")
    if row["alternate_plan"] == "yes" and row["alternate_plan_result"] not in _RESULTS | {NOT_SEEN}:
        raise LogValidationError(f"row {row_number}: deployed alternate plan needs win, loss, or not_seen result")
    if row["splash_mana_effect"] == NOT_APPLICABLE and row["splash_color_failure"] != NOT_APPLICABLE:
        raise LogValidationError(f"row {row_number}: splash_color_failure must be not_applicable without a splash effect")
    if row["splash_mana_effect"] != NOT_APPLICABLE and row["splash_color_failure"] == NOT_APPLICABLE:
        raise LogValidationError(f"row {row_number}: splash_color_failure is required when splash mana was observed")
    if row["wasteland_exposed"] != "yes" and row["wasteland_punished"] != NOT_APPLICABLE:
        raise LogValidationError(f"row {row_number}: wasteland_punished requires wasteland_exposed=yes")
    if row["protection_present"] != "yes" and row["protection_live"] != NOT_APPLICABLE:
        raise LogValidationError(f"row {row_number}: protection_live requires protection_present=yes")
    if row["protection_present"] != "yes" and row["protection_relevant"] != NOT_APPLICABLE:
        raise LogValidationError(f"row {row_number}: protection_relevant requires protection_present=yes")
    if row["protection_present"] == "yes" and row["protection_relevant"] == NOT_APPLICABLE:
        raise LogValidationError(f"row {row_number}: protection_relevant is required when protection was presented")
    return row


def validate_log(log_path: Path, manifest_path: Path = DEFAULT_MANIFEST) -> list[dict[str, str]]:
    """Validate a log and return normalized rows, failing at the first bad row."""
    entries = load_manifest(manifest_path)
    try:
        handle = log_path.open(newline="", encoding="utf-8")
    except OSError as exc:
        raise LogValidationError(f"cannot open log {log_path}: {exc}") from exc
    with handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(FIELDS):
            raise LogValidationError(
                f"log header mismatch; expected {','.join(FIELDS)}"
            )
        rows: list[dict[str, str]] = []
        seen_games: set[tuple[str, str, str]] = set()
        for row_number, raw in enumerate(reader, start=2):
            if None in raw:
                raise LogValidationError(f"row {row_number}: too many columns")
            row = _validate_row(row_number, {str(k): str(v) for k, v in raw.items()}, set(entries))
            game_key = (row["list_id"], row["match_id"], row["game_id"])
            if game_key in seen_games:
                raise LogValidationError(f"row {row_number}: duplicate game identity {game_key!r}")
            seen_games.add(game_key)
            rows.append(row)
    _validate_pairs(rows)
    return rows


def _validate_pairs(rows: list[dict[str, str]]) -> None:
    by_block: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_block[row["matchup_block_id"]].append(row)
    for block_id, block in by_block.items():
        lists = {row["list_id"] for row in block}
        if CONTROL_ID not in lists:
            raise LogValidationError(f"matchup block {block_id!r}: missing control list {CONTROL_ID!r}")
        if len(lists) < 2:
            raise LogValidationError(f"matchup block {block_id!r}: needs a candidate paired with the control")
        opponent_versions = {row["opponent_list_version"] for row in block}
        if len(opponent_versions) != 1:
            raise LogValidationError(f"matchup block {block_id!r}: opponent list/version is not held constant")
        for list_id in lists:
            subset = [row for row in block if row["list_id"] == list_id]
            plays = sum(row["play_draw"] == "play" for row in subset)
            draws = len(subset) - plays
            if abs(plays - draws) > 1:
                raise LogValidationError(f"matchup block {block_id!r}: play/draw is unbalanced for {list_id!r}")
            first = sum(row["list_order"] == "candidate_first" for row in subset)
            second = len(subset) - first
            if abs(first - second) > 1:
                raise LogValidationError(f"matchup block {block_id!r}: list order is unbalanced for {list_id!r}")
        by_pair: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in block:
            by_pair[row["pair_id"]].append(row)
        for pair_id, pair in by_pair.items():
            pair_lists = {row["list_id"] for row in pair}
            if CONTROL_ID not in pair_lists or len(pair_lists) != 2:
                raise LogValidationError(f"matchup block {block_id!r}, pair {pair_id!r}: must contain exactly one control and one candidate")
            if len(pair) != 2:
                raise LogValidationError(f"matchup block {block_id!r}, pair {pair_id!r}: expected one game per paired list")


def _numeric(value: str) -> int | None:
    return None if value in _SENTINELS else int(value)


def summarize(rows: list[dict[str, str]], *, stopping_matches: int = STOPPING_MATCHES) -> dict[str, Any]:
    """Build stable, descriptive per-list and paired summaries."""
    by_list: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_list[row["list_id"]].append(row)
    lists: dict[str, dict[str, Any]] = {}
    for list_id, subset in by_list.items():
        match_results = {
            (row["matchup_block_id"], row["match_id"]): row["match_result"]
            for row in subset
            if row["match_result"] not in _SENTINELS
        }
        wins = sum(row["game_result"] == "win" for row in subset)
        losses = sum(row["game_result"] == "loss" for row in subset)
        draws = sum(row["game_result"] == "draw" for row in subset)
        match_wins = sum(result == "win" for result in match_results.values())
        lists[list_id] = {
            "games": len(subset),
            "game_wins": wins,
            "game_losses": losses,
            "game_draws": draws,
            "matches": len(match_results),
            "match_wins": match_wins,
            "match_losses": sum(result == "loss" for result in match_results.values()),
            "match_draws": sum(result == "draw" for result in match_results.values()),
            "keep_rate": sum(row["opening_hand_decision"] == "keep" for row in subset) / len(subset) if subset else None,
            "combo_turns_observed": [_numeric(row["combo_turn"]) for row in subset if _numeric(row["combo_turn"]) is not None],
            "sample_label": "thin-sample" if len(match_results) < stopping_matches else "threshold-reached",
        }
    paired: dict[str, dict[str, Any]] = {}
    by_pair: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_pair[row["pair_id"]].append(row)
    for pair_id, pair in by_pair.items():
        candidate = next(row for row in pair if row["list_id"] != CONTROL_ID)
        control = next(row for row in pair if row["list_id"] == CONTROL_ID)
        candidate_win = candidate["game_result"] == "win"
        control_win = control["game_result"] == "win"
        paired[pair_id] = {
            "candidate_id": candidate["list_id"],
            "candidate_game_result": candidate["game_result"],
            "control_game_result": control["game_result"],
            "delta": int(candidate_win) - int(control_win),
        }
    paired_deltas: dict[str, dict[str, int | float]] = defaultdict(
        lambda: {"paired_games": 0, "candidate_wins": 0, "control_wins": 0}
    )
    for result in paired.values():
        aggregate = paired_deltas[result["candidate_id"]]
        aggregate["paired_games"] += 1
        aggregate["candidate_wins"] += int(result["candidate_game_result"] == "win")
        aggregate["control_wins"] += int(result["control_game_result"] == "win")
    for aggregate in paired_deltas.values():
        games = aggregate["paired_games"]
        aggregate["delta"] = (aggregate["candidate_wins"] - aggregate["control_wins"]) / games if games else 0.0
    return {
        "stopping_matches": stopping_matches,
        "lists": lists,
        "paired": paired,
        "paired_deltas": dict(paired_deltas),
        "ranking": None,
    }


def render_summary(summary: dict[str, Any]) -> str:
    lines = [
        "Doomsday variant playtest summary (descriptive; no ranking)",
        f"Stopping threshold: {summary['stopping_matches']} matches per list",
    ]
    for list_id, result in summary["lists"].items():
        lines.append(
            f"{list_id}: games={result['games']} (W-L-D {result['game_wins']}-{result['game_losses']}-{result['game_draws']}), "
            f"matches={result['matches']} (W-L-D {result['match_wins']}-{result['match_losses']}-{result['match_draws']}), "
            f"keeps={result['keep_rate']:.3f}, sample={result['sample_label']}"
        )
    lines.append("Paired game deltas (candidate minus Dimir control):")
    for candidate_id, result in summary["paired_deltas"].items():
        lines.append(
            f"{candidate_id}: paired_games={result['paired_games']}, "
            f"candidate_wins={result['candidate_wins']}, control_wins={result['control_wins']}, "
            f"delta={result['delta']:+.3f}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="CSV game log to validate and summarize")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="candidate manifest (default: %(default)s)")
    parser.add_argument("--stopping-matches", type=int, default=STOPPING_MATCHES)
    args = parser.parse_args(argv)
    if args.stopping_matches < 1:
        parser.error("--stopping-matches must be positive")
    try:
        rows = validate_log(args.log, args.manifest)
        print(render_summary(summarize(rows, stopping_matches=args.stopping_matches)))
    except LogValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
