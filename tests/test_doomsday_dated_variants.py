"""Executable registrations and provenance contract for dated Doomsday candidates."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from legacy_engine.ingestion.banlist import banlist_as_of, current_banlist, validate_deck
from legacy_engine.models.decklist import parse_decklist


CANDIDATE_DIR = Path("decks/doomsday-variants/dated")
CANDIDATE_FILES: tuple[str, ...] = (
    "bug-veil-carpet-reconstructed.txt",
    "grixis-squelcher-refresh.txt",
)

BUG_MAIN: dict[str, int] = {
    "Bayou": 1,
    "Brainstorm": 4,
    "Cavern of Souls": 1,
    "Consider": 1,
    "Dark Ritual": 4,
    "Daze": 3,
    "Doomsday": 4,
    "Edge of Autumn": 1,
    "Flow State": 3,
    "Force of Will": 4,
    "Island": 1,
    "Lion's Eye Diamond": 1,
    "Lotus Petal": 4,
    "Misty Rainforest": 4,
    "Personal Tutor": 3,
    "Polluted Delta": 4,
    "Ponder": 4,
    "Quantum Riddler": 1,
    "Street Wraith": 1,
    "Thassa's Oracle": 2,
    "Thoughtseize": 3,
    "Tropical Island": 1,
    "Undercity Sewers": 1,
    "Underground Sea": 3,
    "Witherbloom Charm": 1,
}
BUG_SIDE: dict[str, int] = {
    "Abrupt Decay": 2,
    "Carpet of Flowers": 3,
    "Consign to Memory": 1,
    "Force of Negation": 2,
    "Jace, Wielder of Mysteries": 1,
    "Surgical Extraction": 2,
    "Veil of Summer": 2,
    "Witherbloom Charm": 2,
}
GRIXIS_MAIN: dict[str, int] = {
    "Badlands": 1,
    "Bloodstained Mire": 1,
    "Brainstorm": 4,
    "Cavern of Souls": 1,
    "Consider": 1,
    "Dark Ritual": 4,
    "Daze": 3,
    "Doomsday": 4,
    "Edge of Autumn": 2,
    "Flow State": 4,
    "Flusterstorm": 1,
    "Force of Will": 4,
    "Hexing Squelcher": 1,
    "Island": 1,
    "Jace, Wielder of Mysteries": 1,
    "Lion's Eye Diamond": 1,
    "Lotus Petal": 3,
    "Polluted Delta": 4,
    "Ponder": 4,
    "Scalding Tarn": 3,
    "Street Wraith": 2,
    "Swamp": 1,
    "Thassa's Oracle": 1,
    "Thoughtseize": 3,
    "Undercity Sewers": 1,
    "Underground Sea": 3,
    "Volcanic Island": 1,
}
GRIXIS_SIDE: dict[str, int] = {
    "Barrowgoyf": 4,
    "Brazen Borrower": 1,
    "Force of Negation": 2,
    "Hexing Squelcher": 2,
    "Long Goodbye": 2,
    "Molten Collapse": 1,
    "Pyroblast": 2,
    "Sheoldred, the Apocalypse": 1,
}


def _read_candidate(name: str) -> tuple[str, dict[str, int], dict[str, int]]:
    text = (CANDIDATE_DIR / name).read_text(encoding="utf-8")
    mainboard, sideboard = parse_decklist(text)
    return text, mainboard, sideboard


def _assert_exact_registration(
    mainboard: dict[str, int],
    sideboard: dict[str, int],
    *,
    expected_main: dict[str, int],
    expected_side: dict[str, int],
) -> None:
    assert sum(mainboard.values()) == 60
    assert sum(sideboard.values()) == 15
    assert mainboard == expected_main
    assert sideboard == expected_side


def _combined(mainboard: dict[str, int], sideboard: dict[str, int]) -> dict[str, int]:
    combined = dict(mainboard)
    for card, count in sideboard.items():
        combined[card] = combined.get(card, 0) + count
    return combined


@pytest.mark.parametrize("name", CANDIDATE_FILES)
def test_candidate_files_have_exact_registration_and_provenance(name: str) -> None:
    text, mainboard, sideboard = _read_candidate(name)
    if name.startswith("bug-"):
        _assert_exact_registration(mainboard, sideboard, expected_main=BUG_MAIN, expected_side=BUG_SIDE)
        assert "Status: inferred-reconstruction" in text
        assert "The Fantasticar" not in _combined(mainboard, sideboard)
    else:
        _assert_exact_registration(mainboard, sideboard, expected_main=GRIXIS_MAIN, expected_side=GRIXIS_SIDE)
        assert "Status: observed-historical" in text
        assert "not a post-ban finish" in text
    for label in ("Status:", "Evidence through:", "Observed source:", "Reconstruction:"):
        assert label in text


@pytest.mark.parametrize("name", CANDIDATE_FILES)
def test_candidate_files_are_legal_at_pinned_and_current_snapshots(name: str) -> None:
    _text, mainboard, sideboard = _read_candidate(name)
    assert validate_deck(mainboard, sideboard, snapshot=banlist_as_of(date(2026, 8, 20))) == []
    assert validate_deck(mainboard, sideboard, snapshot=current_banlist()) == []


def test_bug_package_and_reconstruction_contract() -> None:
    _text, mainboard, sideboard = _read_candidate(CANDIDATE_FILES[0])
    combined = _combined(mainboard, sideboard)
    for card, count in {
        "Personal Tutor": 3,
        "Thassa's Oracle": 2,
        "Carpet of Flowers": 3,
        "Veil of Summer": 2,
        "Witherbloom Charm": 3,
        "Abrupt Decay": 2,
    }.items():
        assert combined[card] == count
    assert "The Fantasticar" not in combined


def test_grixis_expected_package_contract() -> None:
    _text, mainboard, sideboard = _read_candidate(CANDIDATE_FILES[1])
    combined = _combined(mainboard, sideboard)
    assert {card: combined[card] for card in ("Hexing Squelcher", "Pyroblast", "Molten Collapse", "Barrowgoyf", "Badlands", "Volcanic Island")} == {
        "Hexing Squelcher": 3,
        "Pyroblast": 2,
        "Molten Collapse": 1,
        "Barrowgoyf": 4,
        "Badlands": 1,
        "Volcanic Island": 1,
    }


def test_manifest_names_both_candidates_and_separates_statuses() -> None:
    manifest = (CANDIDATE_DIR / "README.md").read_text(encoding="utf-8")
    rows = {
        candidate_id: next(
            line for line in manifest.splitlines() if line.startswith(f"| `{candidate_id}` |")
        )
        for candidate_id in ("bug-veil-carpet-reconstructed", "grixis-squelcher-refresh")
    }
    bug_row = rows["bug-veil-carpet-reconstructed"]
    assert "`bug-veil-carpet-reconstructed.txt`" in bug_row
    assert "`inferred-reconstruction`" in bug_row
    assert "observed 2026-07-13" in bug_row
    assert "ddv-packages-list-bug-wakame-preban.md" in bug_row

    grixis_row = rows["grixis-squelcher-refresh"]
    assert "`grixis-squelcher-refresh.txt`" in grixis_row
    assert "`observed-historical` / `legal-at-cutoff` (not observed-current)" in grixis_row
    assert "observed 2026-05-31" in grixis_row
    assert "ddv-packages-list-grixis-nevilshute.md" in grixis_row
