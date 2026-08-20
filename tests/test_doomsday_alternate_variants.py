"""Data and legality contract for the bounded alternate Doomsday modules."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import re
import shutil

import duckdb
import pytest

from legacy_engine.ingestion.banlist import banlist_as_of, current_banlist, validate_deck
from legacy_engine.models.decklist import parse_decklist


VARIANT_DIR = Path("decks/doomsday-variants/alternate")
CARD_DB = Path("data/legacy.duckdb")
MANIFEST: tuple[tuple[str, str], ...] = (
    ("paradigm-shift-oracle", "paradigm-shift-oracle.txt"),
    ("emrakul-shelldock-isle", "emrakul-shelldock-isle.txt"),
    ("moonshadow-creature-switch", "moonshadow-creature-switch.txt"),
    ("cori-steel-cutter-barrowgoyf", "cori-steel-cutter-barrowgoyf.txt"),
    ("chancellor-annex-protection", "chancellor-annex-protection.txt"),
    ("value-threats-jace-riddler-sheoldred", "value-threats-jace-riddler-sheoldred.txt"),
)

EXPECTED_MODULES: dict[str, dict[str, int]] = {
    "paradigm-shift-oracle.txt": {"Paradigm Shift": 4, "Thassa's Oracle": 4},
    "emrakul-shelldock-isle.txt": {"Emrakul, the Aeons Torn": 1, "Shelldock Isle": 1},
    "moonshadow-creature-switch.txt": {"Moonshadow": 4},
    "cori-steel-cutter-barrowgoyf.txt": {"Cori-Steel Cutter": 4, "Barrowgoyf": 4},
    "chancellor-annex-protection.txt": {"Chancellor of the Annex": 4},
    "value-threats-jace-riddler-sheoldred.txt": {
        "Quantum Riddler": 2,
        "Jace, Wielder of Mysteries": 1,
        "Sheoldred, the Apocalypse": 2,
    },
}


def _read(name: str) -> tuple[str, dict[str, int], dict[str, int]]:
    text = (VARIANT_DIR / name).read_text(encoding="utf-8")
    main, side = parse_decklist(text)
    return text, main, side


def _combined(main: dict[str, int], side: dict[str, int]) -> dict[str, int]:
    out = dict(main)
    for card, count in side.items():
        out[card] = out.get(card, 0) + count
    return out


def test_workbook_manifest_matches_exactly_six_files() -> None:
    workbook = (VARIANT_DIR / "README.md").read_text(encoding="utf-8")
    rows = []
    for line in workbook.splitlines():
        if not line.startswith("| `"):
            continue
        fields = [field.strip().strip("`") for field in line.split("|")[1:-1]]
        if len(fields) == 6:
            rows.append((fields[0], fields[1]))
    assert len(rows) == len(MANIFEST)
    assert len({prototype_id for prototype_id, _filename in rows}) == len(MANIFEST)
    assert len({filename for _prototype_id, filename in rows}) == len(MANIFEST)
    assert set(rows) == set(MANIFEST)
    assert sorted(name for _id, name in MANIFEST) == sorted(
        path.name for path in VARIANT_DIR.glob("*.txt")
    )


@pytest.mark.parametrize("_prototype_id,filename", MANIFEST)
def test_variant_is_an_importable_60_plus_15_with_provenance(
    _prototype_id: str, filename: str
) -> None:
    text, main, side = _read(filename)
    assert sum(line.strip().lower() == "sideboard" for line in text.splitlines()) == 1
    assert sum(main.values()) == 60
    assert sum(side.values()) == 15
    assert "The Fantasticar" not in _combined(main, side)
    for label in ("Status:", "Evidence through:", "Observed source:", "Reconstruction:"):
        assert f"// {label}" in text


@pytest.mark.parametrize("_prototype_id,filename", MANIFEST)
def test_nonbasic_copy_limit_and_named_module(_prototype_id: str, filename: str) -> None:
    _text, main, side = _read(filename)
    combined = _combined(main, side)
    basics = {"Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes"}
    assert all(count <= 4 for card, count in combined.items() if card not in basics)
    for card, expected in EXPECTED_MODULES[filename].items():
        assert combined.get(card) == expected


@pytest.mark.parametrize("_prototype_id,filename", MANIFEST)
def test_variants_are_legal_at_cutoff_and_current_snapshot(
    _prototype_id: str, filename: str
) -> None:
    _text, main, side = _read(filename)
    assert validate_deck(main, side, snapshot=banlist_as_of(date(2026, 8, 20))) == []
    assert validate_deck(main, side, snapshot=current_banlist()) == []


def test_all_card_names_resolve_against_local_card_dimension(tmp_path: Path) -> None:
    if not CARD_DB.exists():
        pytest.skip("local card dimension is not present in this checkout")
    names = set()
    for _prototype_id, filename in MANIFEST:
        _text, main, side = _read(filename)
        names.update(main)
        names.update(side)
    # A full-suite run may hold the shared DuckDB open.  Copy the immutable card
    # dimension to a hermetic path before opening it, matching the project's
    # file-backed test-database convention.
    local_db = tmp_path / "legacy.duckdb"
    shutil.copy2(CARD_DB, local_db)
    con = duckdb.connect(str(local_db), read_only=True)
    try:
        rows = con.execute(
            "SELECT name FROM cards WHERE name IN (SELECT UNNEST(?))", [sorted(names)]
        ).fetchall()
    finally:
        con.close()
    assert {row[0] for row in rows} == names


def test_reconstruction_headers_disclose_every_inferred_swap() -> None:
    moon_text, _main, _side = _read("moonshadow-creature-switch.txt")
    cutter_text, _main, _side = _read("cori-steel-cutter-barrowgoyf.txt")
    assert re.search(r"-4 The Fantasticar,? \+4 Personal Tutor", moon_text)
    assert re.search(r"-3 The Fantasticar,? \+3 Personal Tutor", cutter_text)
