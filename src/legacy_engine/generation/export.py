"""Portable decklist export — multi-target import text formatter.

One formatter handles all target platforms because Moxfield, Archidekt,
MTGGoldfish, and ``.dec`` share the ``<qty> <Card Name>`` + ``Sideboard``-header
shape.  Per-target differences are limited to the sideboard notation (the ``.dec``
``SB:`` prefix) — a thin ``fmt`` enum, not separate code paths.

This module is the **exact inverse** of ``advisory.report._parse_decklist`` so
that ``parse(format(deck)) == deck`` for all non-.dec formats.  The round-trip
test in ``tests/test_generation_export.py`` is the guard against drift.

Zero network calls; pure formatting; no new external dependencies.
"""

from __future__ import annotations

from typing import Literal

ExportFormat = Literal["moxfield", "archidekt", "mtggoldfish", "text", "dec"]

# Platforms that use the "Sideboard" section header (all except .dec).
_HEADER_FORMATS: frozenset[str] = frozenset({"moxfield", "archidekt", "mtggoldfish", "text"})


def _sort_board(board: dict[str, int]) -> list[tuple[str, int]]:
    """Return board items sorted by count DESC, then name ASC for stable output."""
    return sorted(board.items(), key=lambda kv: (-kv[1], kv[0]))


def format_decklist(
    maindeck: dict[str, int],
    sideboard: dict[str, int] | None = None,
    *,
    fmt: ExportFormat = "moxfield",
) -> str:
    """Format a decklist as import text for the given target platform.

    Output is deterministic: cards sorted by count DESC then name ASC within each
    section.  The ``sideboard`` section is omitted entirely when empty.

    For all formats except ``"dec"``:
        Maindeck block, blank line, ``Sideboard`` header, sideboard block.
    For ``"dec"``:
        Maindeck as ``<count> <name>`` lines, sideboard as ``SB: <count> <name>`` lines
        (interleaved — no section header, as is convention for .dec files).

    ``parse(format(deck)) == deck`` for all non-dec formats when parsed by
    ``advisory.report._parse_decklist``.

    AC: a 60+15 deck round-trips through the existing parser back to the same
    board maps; ``dec`` uses the ``SB:`` convention; empty sideboard omits the header.
    """
    sideboard = sideboard or {}
    lines: list[str] = []

    main_entries = _sort_board(maindeck)
    side_entries = _sort_board(sideboard)

    if fmt == "dec":
        # .dec convention: main and side interleaved, side prefixed with "SB: "
        for name, count in main_entries:
            lines.append(f"{count} {name}")
        for name, count in side_entries:
            lines.append(f"SB: {count} {name}")
    else:
        # All header-based formats: moxfield, archidekt, mtggoldfish, text
        for name, count in main_entries:
            lines.append(f"{count} {name}")
        if side_entries:
            lines.append("")
            lines.append("Sideboard")
            for name, count in side_entries:
                lines.append(f"{count} {name}")

    return "\n".join(lines)


def moxfield_import_block(
    maindeck: dict[str, int],
    sideboard: dict[str, int] | None = None,
) -> str:
    """Return the Moxfield-importable text with a one-line import hint.

    No network call — pure text formatting.  The import text is the standard
    ``format_decklist(..., fmt="moxfield")`` output; the hint guides the user
    through the Moxfield New Deck → Import flow.

    AC: returns the standard text plus the hint; no network call.
    """
    deck_text = format_decklist(maindeck, sideboard, fmt="moxfield")
    hint = (
        "// To import: go to moxfield.com → New Deck → Import → paste the text below."
    )
    return f"{hint}\n\n{deck_text}"
