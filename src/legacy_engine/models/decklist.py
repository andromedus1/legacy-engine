"""Plain-text decklist parser — shared low-layer utility.

Promoted from ``advisory.report._parse_decklist`` (private) to a public
function here so both ``collection/`` (a peer of ``ingestion/``) and
``advisory/`` can import *down* to this module without introducing a
``collection → advisory`` or ``advisory → collection`` sideways dependency.

This module is the **exact inverse** of ``generation.export.format_decklist``
so that ``parse_decklist(format_decklist(deck)) == deck`` for all non-dec
formats.  The round-trip test in ``tests/test_generation_export.py`` guards
against drift.
"""

from __future__ import annotations

import re

_COUNT_RE = re.compile(r"^(\d+)[xX]?\s+(.+)$")


def parse_decklist(text: str) -> tuple[dict[str, int], dict[str, int]]:
    """Parse a plain-text decklist into (mainboard, sideboard).

    Lines ``<count> <name>`` or ``<count>x <name>``; a line equal to
    ``Sideboard`` (case-insensitive) or a blank line after main cards starts
    the sideboard.  Ignores ``#``-prefixed comments and leading blank lines.
    Raises ``ValueError`` on a malformed line or an empty maindeck.
    """
    mainboard: dict[str, int] = {}
    sideboard: dict[str, int] = {}
    in_side = False
    seen_main_card = False

    for raw_line in text.splitlines():
        line = raw_line.strip()

        # Skip comments
        if line.startswith("#"):
            continue

        # Blank line: after we've seen at least one main card, switch to side
        if not line:
            if seen_main_card:
                in_side = True
            continue

        # "Sideboard" header (case-insensitive)
        if line.lower() == "sideboard":
            in_side = True
            continue

        m = _COUNT_RE.match(line)
        if m is None:
            raise ValueError(f"parse_decklist: malformed line {line!r}")

        count = int(m.group(1))
        name = m.group(2).strip()

        if in_side:
            sideboard[name] = sideboard.get(name, 0) + count
        else:
            mainboard[name] = mainboard.get(name, 0) + count
            seen_main_card = True

    if not mainboard:
        raise ValueError("parse_decklist: empty maindeck")

    return mainboard, sideboard
