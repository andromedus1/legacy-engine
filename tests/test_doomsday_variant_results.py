"""Contracts for the Doomsday paired-playtest registry and CSV validator."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from scripts.doomsday_variant_results import (
    FIELDS,
    LogValidationError,
    load_manifest,
    render_summary,
    summarize,
    validate_log,
)


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "decks/doomsday-variants/manifest.json"
FIXTURE = ROOT / "tests/fixtures/doomsday_variants/playtest-valid.csv"
TEMPLATE = ROOT / "decks/doomsday-variants/playtest-log.csv"


def _rows() -> list[dict[str, str]]:
    with FIXTURE.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_log(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def test_manifest_canonicalizes_fifteen_artifacts_as_fourteen_unique_lists() -> None:
    entries = load_manifest(MANIFEST)
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert len(entries) == 14
    assert raw["unique_candidate_count"] == 14
    assert raw["artifact_count"] == 15
    assert len({entry["path"] for entry in entries.values()}) == 14
    assert len({entry["canonical_deck_sha256"] for entry in entries.values()}) == 14
    assert len(raw["artifact_aliases"]) == 1
    alias = raw["artifact_aliases"][0]
    assert alias["id"] == "tamiyo-bilbo-unearth-value"
    assert alias["canonical_id"] == "current-esper-teferi-swords"
    assert alias["canonical_deck_sha256"] == entries[alias["canonical_id"]]["canonical_deck_sha256"]
    assert len(entries) + len(raw["artifact_aliases"]) == 15
    assert all(entry["evidence_posture"] for entry in entries.values())
    assert all(len(entry["canonical_deck_sha256"]) == 64 for entry in entries.values())


def test_header_only_template_and_valid_fixture_are_accepted() -> None:
    assert validate_log(TEMPLATE, MANIFEST) == []
    rows = validate_log(FIXTURE, MANIFEST)
    result = summarize(rows)
    assert result["lists"]["personal-tutor-turbo"]["matches"] == 1
    assert result["lists"]["personal-tutor-turbo"]["sample_label"] == "thin-sample"
    assert result["paired"]["pair-01"]["delta"] == 1
    assert result["lists"]["personal-tutor-turbo"]["mulligans"] == 1
    assert result["lists"]["personal-tutor-turbo"]["combo_turn_distribution"] == {"3": 1, "4": 1}
    rendered = render_summary(result)
    assert "mulligans=1 (denom games=2)" in rendered
    assert "combo_turns={'3': 1, '4': 1} (observed=2/games=2)" in rendered
    assert result["ranking"] is None


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("game_result", "maybe", "invalid game_result"),
        ("list_id", "not-a-list", "unknown list_id"),
        ("deck_sha256", "0" * 64, "deck_sha256 does not match"),
        ("combo_turn", "31", "impossible combo_turn"),
        ("splash_color_failure", "no", "splash_color_failure must be not_applicable"),
    ],
)
def test_rows_fail_fast_with_row_specific_errors(tmp_path: Path, field: str, value: str, message: str) -> None:
    rows = _rows()
    rows[0][field] = value
    path = tmp_path / "invalid.csv"
    _write_log(path, rows)
    with pytest.raises(LogValidationError, match=rf"row 2: .*{message}"):
        validate_log(path, MANIFEST)


def test_conditional_protection_and_wasteland_fields_fail_fast(tmp_path: Path) -> None:
    rows = _rows()
    rows[0]["protection_present"] = "no"
    rows[0]["protection_live"] = "yes"
    path = tmp_path / "invalid-protection.csv"
    _write_log(path, rows)
    with pytest.raises(LogValidationError, match="row 2: protection live/relevant"):
        validate_log(path, MANIFEST)

    rows = _rows()
    rows[0]["wasteland_exposed"] = "no"
    rows[0]["wasteland_punished"] = "yes"
    path = tmp_path / "invalid-wasteland.csv"
    _write_log(path, rows)
    with pytest.raises(LogValidationError, match="row 2: wasteland_punished"):
        validate_log(path, MANIFEST)


def test_pairing_rejects_unpaired_block(tmp_path: Path) -> None:
    rows = _rows()
    rows[1]["pair_id"] = "different-pair"
    path = tmp_path / "invalid-pair.csv"
    _write_log(path, rows)
    with pytest.raises(LogValidationError, match="pair"):
        validate_log(path, MANIFEST)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda rows: rows[1].__setitem__("opponent_archetype", "Show and Tell"), "opponent archetype/list version"),
        (
            lambda rows: (
                rows[1].__setitem__("board_state", "post"),
                rows[1].__setitem__("cards_boarded_in", "not_seen"),
                rows[1].__setitem__("cards_boarded_out", "not_seen"),
                rows[1].__setitem__("alternate_plan", "no"),
            ),
            "board state must match",
        ),
        (lambda rows: rows[1].__setitem__("play_draw", "draw"), "play/draw condition must match"),
        (lambda rows: rows[1].__setitem__("list_order", "control_first"), "list order must match"),
    ],
)
def test_pairing_holds_experimental_conditions_constant(
    tmp_path: Path,
    mutate,
    message: str,
) -> None:
    rows = _rows()
    mutate(rows)
    path = tmp_path / "invalid-paired-condition.csv"
    _write_log(path, rows)
    with pytest.raises(LogValidationError, match=message):
        validate_log(path, MANIFEST)


def test_block_rejects_multiple_candidates_and_reused_pair_ids(tmp_path: Path) -> None:
    rows = _rows()
    entries = load_manifest(MANIFEST)
    rows[3]["list_id"] = "wasteland-murktide-tempo"
    rows[3]["deck_sha256"] = entries["wasteland-murktide-tempo"]["canonical_deck_sha256"]
    path = tmp_path / "multiple-candidates.csv"
    _write_log(path, rows)
    with pytest.raises(LogValidationError, match="exactly one control and one candidate"):
        validate_log(path, MANIFEST)

    rows = _rows()
    copied = [dict(row) for row in rows]
    for row in copied:
        row["matchup_block_id"] = "block-02"
        row["match_id"] = "match-02"
    path = tmp_path / "reused-pairs.csv"
    _write_log(path, rows + copied)
    with pytest.raises(LogValidationError, match="reused across matchup blocks"):
        validate_log(path, MANIFEST)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("play_draw", "play", "play/draw is unbalanced"),
        ("list_order", "candidate_first", "list order is unbalanced"),
    ],
)
def test_block_rejects_unbalanced_assignments(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    rows = _rows()
    rows[2][field] = value
    rows[3][field] = value
    path = tmp_path / "unbalanced.csv"
    _write_log(path, rows)
    with pytest.raises(LogValidationError, match=message):
        validate_log(path, MANIFEST)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda rows: rows[0].__setitem__("match_result", "not_applicable"), "match_result"),
        (lambda rows: rows[0].__setitem__("combo_turn", "2"), "combo_turn is only valid"),
        (lambda rows: rows[2].__setitem__("cards_boarded_in", "not_applicable"), "cannot be not_applicable"),
        (
            lambda rows: (
                rows[0].__setitem__("wasteland_exposed", "yes"),
                rows[0].__setitem__("wasteland_punished", "not_applicable"),
            ),
            "exposed Wasteland",
        ),
        (lambda rows: rows[0].__setitem__("protection_live", "not_applicable"), "presented protection"),
        (
            lambda rows: (
                rows[2].__setitem__("alternate_plan", "yes"),
                rows[2].__setitem__("alternate_plan_result", "draw"),
            ),
            "alternate_plan_result",
        ),
    ],
)
def test_conditional_states_reject_the_adversarial_direction(
    tmp_path: Path,
    mutate,
    message: str,
) -> None:
    rows = _rows()
    mutate(rows)
    path = tmp_path / "invalid-condition.csv"
    _write_log(path, rows)
    with pytest.raises(LogValidationError, match=message):
        validate_log(path, MANIFEST)


def test_completed_matches_require_one_consistent_terminal_result(tmp_path: Path) -> None:
    rows = _rows()
    rows[0]["match_result"] = "loss"
    path = tmp_path / "two-terminals.csv"
    _write_log(path, rows)
    with pytest.raises(LogValidationError, match="exactly one terminal result"):
        validate_log(path, MANIFEST)

    rows = _rows()
    rows[3]["combo_turn"] = "not_seen"
    rows[3]["game_result"] = "loss"
    path = tmp_path / "false-match-win.csv"
    _write_log(path, rows)
    with pytest.raises(LogValidationError, match="match win requires at least two game wins"):
        validate_log(path, MANIFEST)


def test_unfinished_matches_do_not_reach_the_fixed_threshold(tmp_path: Path) -> None:
    rows = _rows()
    rows[2]["match_result"] = "not_seen"
    rows[3]["match_result"] = "not_seen"
    path = tmp_path / "unfinished.csv"
    _write_log(path, rows)
    validated = validate_log(path, MANIFEST)
    summary = summarize(validated)
    assert summary["lists"]["personal-tutor-turbo"]["completed_matches"] == 0
    assert summary["lists"]["personal-tutor-turbo"]["sample_label"] == "thin-sample"
    with pytest.raises(ValueError, match="exactly 20"):
        summarize(validated, stopping_matches=1)
def test_manifest_rejects_root_escape_bad_root_and_posture_drift(tmp_path: Path) -> None:
    raw = json.loads(MANIFEST.read_text(encoding="utf-8"))

    path = tmp_path / "bad-root.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(LogValidationError, match="root must be an object"):
        load_manifest(path)

    escaped = json.loads(json.dumps(raw))
    escaped["candidates"][0]["path"] = "decks/../README.md"
    path = tmp_path / "escaped.json"
    path.write_text(json.dumps(escaped), encoding="utf-8")
    with pytest.raises(LogValidationError, match="path escapes decks root"):
        load_manifest(path)

    relabeled = json.loads(json.dumps(raw))
    bug = next(candidate for candidate in relabeled["candidates"] if candidate["id"] == "bug-veil-carpet-reconstructed")
    bug["evidence_posture"] = "exact-registration"
    path = tmp_path / "relabeled.json"
    path.write_text(json.dumps(relabeled), encoding="utf-8")
    with pytest.raises(LogValidationError, match="disagrees with artifact"):
        load_manifest(path)
