from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = ROOT / "decks/doomsday-variants/moxfield"
CASES = {
    "bug-veil-carpet.txt": ROOT
    / "decks/doomsday-variants/dated/bug-veil-carpet-reconstructed.txt",
    "esper-teferi-swords.txt": ROOT
    / "decks/doomsday-variants/current-esper-teferi-swords.txt",
    "turbo-dimir-personal-tutor.txt": ROOT
    / "decks/doomsday-personal-tutor-turbo-75.txt",
    "dimir-creature-juke.txt": ROOT
    / "decks/doomsday-variants/current-dimir-creature-transform.txt",
}


def _parse(path: Path) -> tuple[Counter[str], Counter[str]]:
    zones = {"main": Counter(), "side": Counter()}
    zone = "main"
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", "//")):
            continue
        if line == "Sideboard":
            zone = "side"
            continue
        count, name = line.split(" ", 1)
        zones[zone][name] += int(count)
    return zones["main"], zones["side"]


@pytest.mark.parametrize(("export_name", "canonical_path"), CASES.items())
def test_moxfield_export_is_clean_exact_copy(export_name: str, canonical_path: Path):
    export_path = EXPORT_DIR / export_name
    export_main, export_side = _parse(export_path)
    canonical_main, canonical_side = _parse(canonical_path)

    assert (export_main, export_side) == (canonical_main, canonical_side)
    assert sum(export_main.values()) == 60
    assert sum(export_side.values()) == 15
    assert not any(
        line.startswith(("#", "//")) for line in export_path.read_text().splitlines()
    )
