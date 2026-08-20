"""Contracts for the Doomsday paired-playtest registry and CSV validator."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from scripts.doomsday_variant_results import (
    FIELDS,
    LogValidationError,
    load_manifest,
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


def test_manifest_is_the_complete_fifteen_list_authority() -> None:
    entries = load_manifest(MANIFEST)
    assert len(entries) == 15
    assert len({entry["path"] for entry in entries.values()}) == 15
    assert all(entry["evidence_posture"] for entry in entries.values())
    assert all(len(entry["canonical_deck_sha256"]) == 64 for entry in entries.values())


def test_header_only_template_and_valid_fixture_are_accepted() -> None:
    assert validate_log(TEMPLATE, MANIFEST) == []
    rows = validate_log(FIXTURE, MANIFEST)
    result = summarize(rows)
    assert result["lists"]["personal-tutor-turbo"]["matches"] == 1
    assert result["lists"]["personal-tutor-turbo"]["sample_label"] == "thin-sample"
    assert result["paired"]["pair-01"]["delta"] == 1
    assert result["ranking"] is None


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("game_result", "maybe", "invalid game_result"),
        ("list_id", "not-a-list", "unknown list_id"),
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
    with pytest.raises(LogValidationError, match="row 2: protection_live"):
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
