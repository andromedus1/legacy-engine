"""Source-fidelity contracts for the post-ban Doomsday chassis registrations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pytest

from legacy_engine.ingestion.banlist import current_banlist, validate_deck
from legacy_engine.models.decklist import parse_decklist


StructuralLabel = Literal[
    "personal-tutor-turbo",
    "tamiyo-bilbo-unearth-value",
    "wasteland-murktide-tempo",
]

_ROOT = Path(__file__).resolve().parents[1]
_RESEARCH_ORIGIN = ".research/analysis/campaigns/doomsday-splash-variants/parent.md"
_CLAIM_BOUNDARY = "construction label only; no measured kill-speed or matchup-superiority claim"


@dataclass(frozen=True)
class ChassisCase:
    label: StructuralLabel
    color_configuration: Literal["dimir", "esper"]
    deck_path: Path
    fixture_path: Path
    source_path: Path
    source_player: str
    required_main: dict[str, int]
    forbidden_main: frozenset[str]


CASES = (
    ChassisCase(
        label="personal-tutor-turbo",
        color_configuration="dimir",
        deck_path=_ROOT / "decks/doomsday-personal-tutor-turbo-75.txt",
        fixture_path=_ROOT / "tests/fixtures/doomsday_variants/personal-tutor-turbo.json",
        source_path=_ROOT
        / "data/cache/Tournaments/MTGO/2026/08/18/legacy-league-2026-08-1810967.json",
        source_player="clan",
        required_main={
            "Personal Tutor": 3,
            "Lotus Petal": 3,
            "Thassa's Oracle": 2,
            "Street Wraith": 2,
        },
        forbidden_main=frozenset(
            {"Bilbo, Thief in the Night", "Tamiyo, Inquisitive Student", "Murktide Regent", "Wasteland"}
        ),
    ),
    ChassisCase(
        label="tamiyo-bilbo-unearth-value",
        color_configuration="esper",
        deck_path=_ROOT / "decks/doomsday-tamiyo-bilbo-unearth-value-75.txt",
        fixture_path=_ROOT / "tests/fixtures/doomsday_variants/tamiyo-bilbo-unearth-value.json",
        source_path=_ROOT
        / "data/cache/Tournaments/MTGO/2026/08/12/legacy-league-2026-08-1210967.json",
        source_player="Battlegrounds",
        required_main={
            "Tamiyo, Inquisitive Student": 4,
            "Bilbo, Thief in the Night": 4,
            "Unearth": 1,
        },
        forbidden_main=frozenset({"Personal Tutor", "Murktide Regent", "Wasteland"}),
    ),
    ChassisCase(
        label="wasteland-murktide-tempo",
        color_configuration="dimir",
        deck_path=_ROOT / "decks/doomsday-wasteland-murktide-tempo-75.txt",
        fixture_path=_ROOT / "tests/fixtures/doomsday_variants/wasteland-murktide-tempo.json",
        source_path=_ROOT
        / "data/cache/Tournaments/MTGO/2026/08/12/legacy-challenge-32-2026-08-1212851626.json",
        source_player="HJ_Kaiser",
        required_main={
            "Wasteland": 3,
            "Murktide Regent": 2,
            "Tamiyo, Inquisitive Student": 4,
        },
        forbidden_main=frozenset({"Personal Tutor", "Bilbo, Thief in the Night", "Unearth"}),
    ),
)

_HEADER_KEYS = {
    "structural_label",
    "color_configuration",
    "evidence_scope",
    "source_player",
    "source_result",
    "source_date",
    "source_path",
    "source_url",
    "research_origin",
    "legality_snapshot",
    "claim_boundary",
}
_FIXTURE_KEYS = {"source_path", "Date", "Player", "Result", "AnchorUri", "Mainboard", "Sideboard"}


def _parse_provenance_header(text: str) -> dict[str, str]:
    """Extract the fixed ``# key: value`` provenance block from an artifact."""
    header: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        body = line[1:].strip()
        if ":" not in body:
            continue
        key, value = body.split(":", 1)
        header[key.strip()] = value.strip()
    return header


def _load_source_registration(
    path: Path,
    player: str,
) -> tuple[dict[str, int], dict[str, int], dict[str, object]]:
    """Load the one immutable, source-exact registration fixture."""
    deck = json.loads(path.read_text())
    assert set(deck) == _FIXTURE_KEYS
    assert deck["Player"] == player, f"fixture {path} has player {deck['Player']!r}, expected {player!r}"
    main = {entry["CardName"]: entry["Count"] for entry in deck["Mainboard"]}
    side = {entry["CardName"]: entry["Count"] for entry in deck["Sideboard"]}
    return main, side, deck


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.label)
def test_chassis_artifact_matches_source_and_legality(case: ChassisCase) -> None:
    text = case.deck_path.read_text()
    header = _parse_provenance_header(text)
    main, side = parse_decklist(text)
    source_main, source_side, source = _load_source_registration(
        case.fixture_path, case.source_player
    )
    upstream_path = case.source_path.relative_to(_ROOT).as_posix()
    assert source["source_path"] == upstream_path

    assert set(header) == _HEADER_KEYS
    assert header["structural_label"] == case.label
    assert header["color_configuration"] == case.color_configuration
    assert header["evidence_scope"] == "exact-published-registration"
    assert header["source_player"] == case.source_player
    assert header["source_result"] == source["Result"]
    assert header["source_date"] == source["Date"][:10]
    assert header["source_path"] == source["source_path"]
    assert header["source_url"] == source["AnchorUri"]
    assert header["source_url"].startswith("https://www.mtgo.com/decklist/")
    assert header["research_origin"] == _RESEARCH_ORIGIN
    snapshot = current_banlist()
    assert header["legality_snapshot"] == snapshot.as_of.isoformat()
    assert header["claim_boundary"] == _CLAIM_BOUNDARY

    assert main == source_main
    assert side == source_side
    assert sum(main.values()) == 60
    assert sum(side.values()) == 15
    assert validate_deck(main, side, snapshot) == []

    for name, count in case.required_main.items():
        assert main.get(name) == count, f"{case.label}: required mainboard signature {name!r}"
    for name in case.forbidden_main:
        assert name not in main, f"{case.label}: forbidden mainboard signature {name!r}"


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.label)
def test_chassis_artifact_is_parser_compatible(case: ChassisCase) -> None:
    main, side = parse_decklist(case.deck_path.read_text())
    assert main
    assert side
