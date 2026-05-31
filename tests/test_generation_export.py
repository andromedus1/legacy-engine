"""Tests for generation.export — Units 1–3 of epic-deck-generation-export.

Covers:
  - format_decklist: round-trip for all non-dec formats, .dec SB convention,
    empty-sideboard header omission, deterministic ordering.
  - moxfield_import_block: returns standard text + hint, no network.
  - CLI: `export deck` to stdout + --out file.

House style: ``TestX`` classes, deterministic fixtures, no mocks for network
(there is no network to mock — this module is pure formatting).
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from legacy_engine.advisory.report import _parse_decklist
from legacy_engine.cli import main
from legacy_engine.generation.export import ExportFormat, format_decklist, moxfield_import_block


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

MAINDECK: dict[str, int] = {
    "Brainstorm": 4,
    "Force of Will": 4,
    "Ponder": 4,
    "Wasteland": 4,
    "Dragon's Rage Channeler": 4,
    "Volcanic Island": 2,
    "Scalding Tarn": 4,
    "Daze": 4,
    "Murktide Regent": 2,
    "Flooded Strand": 4,
    "Preordain": 4,
    "Lightning Bolt": 4,
    "Mishra's Bauble": 4,
    "Polluted Delta": 4,
    "Arid Mesa": 4,
    "Misty Rainforest": 4,
}
# Sanity: fixture sums to 60.
assert sum(MAINDECK.values()) == 60, f"Fixture maindeck sums to {sum(MAINDECK.values())}, not 60"

SIDEBOARD: dict[str, int] = {
    "Pyroblast": 4,
    "Red Elemental Blast": 4,
    "Flusterstorm": 2,
    "Grafdigger's Cage": 2,
    "Force of Negation": 2,
    "Surgical Extraction": 1,
}
# Sanity: fixture sums to 15.
assert sum(SIDEBOARD.values()) == 15, f"Fixture sideboard sums to {sum(SIDEBOARD.values())}, not 15"


def _decklist_file(tmp_path, maindeck: dict[str, int], sideboard: dict[str, int] | None = None) -> str:
    """Write a decklist file and return its path."""
    lines = []
    for name, count in sorted(maindeck.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"{count} {name}")
    if sideboard:
        lines.append("")
        lines.append("Sideboard")
        for name, count in sorted(sideboard.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"{count} {name}")
    path = tmp_path / "deck.txt"
    path.write_text("\n".join(lines))
    return str(path)


# ---------------------------------------------------------------------------
# Unit 1 tests — format_decklist
# ---------------------------------------------------------------------------

class TestFormatDecklist:
    """Tests for the formatter — determinism, round-trip, format variants."""

    def test_round_trip_moxfield(self):
        text = format_decklist(MAINDECK, SIDEBOARD, fmt="moxfield")
        parsed_main, parsed_side = _parse_decklist(text)
        assert parsed_main == MAINDECK
        assert parsed_side == SIDEBOARD

    def test_round_trip_archidekt(self):
        text = format_decklist(MAINDECK, SIDEBOARD, fmt="archidekt")
        parsed_main, parsed_side = _parse_decklist(text)
        assert parsed_main == MAINDECK
        assert parsed_side == SIDEBOARD

    def test_round_trip_mtggoldfish(self):
        text = format_decklist(MAINDECK, SIDEBOARD, fmt="mtggoldfish")
        parsed_main, parsed_side = _parse_decklist(text)
        assert parsed_main == MAINDECK
        assert parsed_side == SIDEBOARD

    def test_round_trip_text(self):
        text = format_decklist(MAINDECK, SIDEBOARD, fmt="text")
        parsed_main, parsed_side = _parse_decklist(text)
        assert parsed_main == MAINDECK
        assert parsed_side == SIDEBOARD

    def test_dec_sb_prefix_convention(self):
        """`.dec` format uses 'SB: <count> <name>' for sideboard lines."""
        text = format_decklist(MAINDECK, SIDEBOARD, fmt="dec")
        lines = text.splitlines()
        sb_lines = [l for l in lines if l.startswith("SB: ")]
        non_sb_lines = [l for l in lines if not l.startswith("SB: ")]
        # All sideboard cards use SB: prefix.
        for name in SIDEBOARD:
            assert any(name in l for l in sb_lines), f"{name} not found in SB: lines"
        # All maindeck cards appear without SB: prefix.
        for name in MAINDECK:
            assert any(name in l for l in non_sb_lines), f"{name} not found in main lines"
        # No 'Sideboard' header line in .dec.
        assert "Sideboard" not in lines

    def test_dec_no_sideboard_header(self):
        text = format_decklist(MAINDECK, SIDEBOARD, fmt="dec")
        assert "Sideboard" not in text.splitlines()

    def test_empty_sideboard_omits_header(self):
        """When sideboard is empty (or None), no 'Sideboard' header appears."""
        text_none = format_decklist(MAINDECK, None, fmt="moxfield")
        text_empty = format_decklist(MAINDECK, {}, fmt="moxfield")
        for text in (text_none, text_empty):
            assert "Sideboard" not in text.splitlines(), "Empty sideboard should omit header"

    def test_deterministic_ordering_by_count_then_name(self):
        """Cards sorted count DESC then name ASC — two calls produce identical output."""
        text1 = format_decklist(MAINDECK, SIDEBOARD, fmt="moxfield")
        text2 = format_decklist(MAINDECK, SIDEBOARD, fmt="moxfield")
        assert text1 == text2

    def test_ordering_count_desc(self):
        """Higher-count cards appear before lower-count cards in the output."""
        text = format_decklist(MAINDECK, None, fmt="moxfield")
        lines = [l for l in text.splitlines() if l]
        counts = [int(l.split(" ")[0]) for l in lines]
        # counts should be non-increasing (DESC).
        assert counts == sorted(counts, reverse=True), f"Not sorted count-DESC: {counts}"

    def test_default_fmt_is_moxfield(self):
        """Default fmt is moxfield — matches an explicit moxfield call."""
        assert format_decklist(MAINDECK) == format_decklist(MAINDECK, fmt="moxfield")

    def test_maindeck_block_before_sideboard_block(self):
        """In header-based formats, all maindeck lines precede the Sideboard header."""
        text = format_decklist(MAINDECK, SIDEBOARD, fmt="moxfield")
        lines = text.splitlines()
        sideboard_idx = next(i for i, l in enumerate(lines) if l == "Sideboard")
        # Every line before the header should be a card line (no SB: prefix).
        for line in lines[:sideboard_idx]:
            if line:  # skip blank separator
                assert not line.startswith("SB:"), f"Unexpected SB: before header: {line}"

    def test_sideboard_lines_after_header(self):
        """After 'Sideboard' header, all card lines belong to the sideboard."""
        text = format_decklist(MAINDECK, SIDEBOARD, fmt="moxfield")
        lines = text.splitlines()
        sideboard_idx = next(i for i, l in enumerate(lines) if l == "Sideboard")
        after_header = [l for l in lines[sideboard_idx + 1:] if l]
        for line in after_header:
            count_str, name = line.split(" ", 1)
            assert name in SIDEBOARD, f"Card after Sideboard header not in sideboard: {name}"

    def test_maindeck_only_no_crash(self):
        """format_decklist with no sideboard must not raise."""
        text = format_decklist({"Force of Will": 4}, fmt="moxfield")
        assert "Force of Will" in text

    def test_dec_round_trip_main_only(self):
        """A dec-formatted main-only deck parses back correctly if SB: lines are stripped."""
        main = {"Brainstorm": 4, "Force of Will": 4}
        text = format_decklist(main, {}, fmt="dec")
        lines = [l for l in text.splitlines() if not l.startswith("SB:")]
        parsed_main, _ = _parse_decklist("\n".join(lines))
        assert parsed_main == main


# ---------------------------------------------------------------------------
# Unit 2 tests — moxfield_import_block
# ---------------------------------------------------------------------------

class TestMoxfieldImportBlock:
    def test_contains_decklist_text(self):
        block = moxfield_import_block(MAINDECK, SIDEBOARD)
        standard = format_decklist(MAINDECK, SIDEBOARD, fmt="moxfield")
        assert standard in block

    def test_contains_import_hint(self):
        block = moxfield_import_block(MAINDECK, SIDEBOARD)
        assert "moxfield" in block.lower() or "import" in block.lower()

    def test_no_network_call(self):
        """Calling moxfield_import_block makes zero network calls — pure text."""
        import socket
        original_connect = socket.socket.connect

        def _no_connect(self, *args, **kwargs):
            raise AssertionError("Network call detected — moxfield_import_block must be offline")

        socket.socket.connect = _no_connect
        try:
            block = moxfield_import_block(MAINDECK, SIDEBOARD)
            assert block  # non-empty
        finally:
            socket.socket.connect = original_connect

    def test_round_trips_through_parser(self):
        block = moxfield_import_block(MAINDECK, SIDEBOARD)
        # Strip hint lines (// comments) and parse the remaining text.
        card_lines = "\n".join(l for l in block.splitlines() if not l.startswith("//"))
        parsed_main, parsed_side = _parse_decklist(card_lines)
        assert parsed_main == MAINDECK
        assert parsed_side == SIDEBOARD


# ---------------------------------------------------------------------------
# Unit 3 tests — CLI export deck
# ---------------------------------------------------------------------------

class TestExportDeckCLI:
    def test_stdout_exit_zero(self, tmp_path):
        deck_path = _decklist_file(tmp_path, MAINDECK, SIDEBOARD)
        runner = CliRunner()
        result = runner.invoke(main, ["export", "deck", "--deck", deck_path])
        assert result.exit_code == 0, f"exit={result.exit_code}\n{result.output}"
        # Default fmt=moxfield — output should contain Sideboard header.
        assert "Sideboard" in result.output

    def test_archidekt_format(self, tmp_path):
        deck_path = _decklist_file(tmp_path, MAINDECK, SIDEBOARD)
        runner = CliRunner()
        result = runner.invoke(
            main, ["export", "deck", "--deck", deck_path, "--format", "archidekt"]
        )
        assert result.exit_code == 0, result.output
        assert "Sideboard" in result.output
        assert "Force of Will" in result.output

    def test_dec_format(self, tmp_path):
        deck_path = _decklist_file(tmp_path, MAINDECK, SIDEBOARD)
        runner = CliRunner()
        result = runner.invoke(
            main, ["export", "deck", "--deck", deck_path, "--format", "dec"]
        )
        assert result.exit_code == 0, result.output
        # .dec convention: SB: lines for sideboard, no header.
        assert "SB:" in result.output
        assert "Sideboard" not in result.output.splitlines()

    def test_out_writes_file(self, tmp_path):
        deck_path = _decklist_file(tmp_path, MAINDECK, SIDEBOARD)
        out_path = str(tmp_path / "output.txt")
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["export", "deck", "--deck", deck_path, "--format", "moxfield", "--out", out_path],
        )
        assert result.exit_code == 0, f"exit={result.exit_code}\n{result.output}"
        assert os.path.exists(out_path)
        content = open(out_path).read()
        # Output file should contain the standard decklist text.
        assert "Force of Will" in content
        assert "Sideboard" in content

    def test_out_message_when_writing_file(self, tmp_path):
        deck_path = _decklist_file(tmp_path, MAINDECK, SIDEBOARD)
        out_path = str(tmp_path / "output.txt")
        runner = CliRunner()
        result = runner.invoke(
            main, ["export", "deck", "--deck", deck_path, "--out", out_path]
        )
        assert result.exit_code == 0, result.output
        assert "Written to" in result.output

    def test_round_trip_via_cli(self, tmp_path):
        """export deck stdout → parse back → same deck."""
        deck_path = _decklist_file(tmp_path, MAINDECK, SIDEBOARD)
        runner = CliRunner()
        result = runner.invoke(
            main, ["export", "deck", "--deck", deck_path, "--format", "moxfield"]
        )
        assert result.exit_code == 0, result.output
        parsed_main, parsed_side = _parse_decklist(result.output)
        assert parsed_main == MAINDECK
        assert parsed_side == SIDEBOARD

    def test_generate_consensus_export_flag(self, tmp_path):
        """generate consensus --export moxfield produces Moxfield-importable text."""
        import duckdb as _duckdb
        from legacy_engine.ingestion import store
        from legacy_engine.ingestion.cache import parse_cache_item

        # Minimal 10-deck Delver fixture in the current regime (2026-05-25).
        def _card(name: str, count: int = 4) -> dict:
            return {"CardName": name, "Count": count}

        decks = []
        for i in range(10):
            mainboard = [
                _card("Brainstorm"), _card("Force of Will"), _card("Ponder"),
                _card("Wasteland"), _card("Dragon's Rage Channeler"),
                _card("Volcanic Island", 2), _card("Scalding Tarn"),
                _card("Mishra's Bauble"), _card("Polluted Delta"),
                _card("Arid Mesa"), _card("Misty Rainforest"),
            ]
            if i < 8:
                mainboard += [_card("Daze"), _card("Murktide Regent", 2), _card("Flooded Strand")]
            if i < 6:
                mainboard.append(_card("Preordain"))
            if i < 4:
                mainboard.append(_card("Lightning Bolt"))
            decks.append({
                "Player": f"p{i}", "Result": "1st Place",
                "Mainboard": mainboard, "Sideboard": [_card("Pyroblast"), _card("Red Elemental Blast")],
            })
        raw = {
            "Tournament": {
                "Name": "Delver T", "Date": "2026-05-25",
                "Uri": "https://www.mtgo.com/decklist/delver-t", "Formats": "Legacy",
            },
            "Decks": decks, "Rounds": [], "Standings": [],
        }

        db_path = tmp_path / "test.duckdb"
        file_con = _duckdb.connect(str(db_path))
        store.init_schema(file_con)
        store.load_tournament(file_con, parse_cache_item(raw, "MTGO"))
        file_con.execute("UPDATE decks SET archetype = 'Delver'")
        file_con.close()

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "generate", "consensus",
                "--archetype", "Delver",
                "--export", "moxfield",
                "--db", str(db_path),
            ],
        )
        assert result.exit_code == 0, f"exit={result.exit_code}\n{result.output}"
        assert "Export" in result.output
        # The export block should include card lines parseable by _parse_decklist.
        export_section = result.output.split("// --- Export ---", 1)[1].strip()
        parsed_main, _ = _parse_decklist(export_section)
        assert sum(parsed_main.values()) > 0
