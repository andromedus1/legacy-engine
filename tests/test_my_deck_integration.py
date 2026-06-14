"""Tests for --my-deck NAME integration on the 6 decklist-consuming CLI leaves.

Covers:
- Mutual exclusion: both --deck + --my-deck → ClickException
- Neither supplied → ClickException  (for the leaves where deck source is required)
- --my-deck NAME with unknown deck → ClickException (fail loud)
- --my-deck NAME happy path (mocked inner calls so no DB required)
- --deck FILE path still works (gated-additive regression check)

Leaves under test: advise positioning, advise sideboard, advise whattoplay,
advise report, advise refresh, generate tune, export deck.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main


# ---------------------------------------------------------------------------
# Shared fixture: redirect collection paths to tmp_path
# ---------------------------------------------------------------------------


@pytest.fixture
def deck_env(tmp_path, monkeypatch):
    """Set up an isolated collection dir with one saved deck, return (runner, deck_file)."""
    coll_dir = tmp_path / "collection"
    inv_path = coll_dir / "inventory.json"
    decks_dir = coll_dir / "decks"
    decks_dir.mkdir(parents=True, exist_ok=True)

    import legacy_engine.collection.persist as persist_mod
    import legacy_engine.config as config_mod

    monkeypatch.setattr(config_mod, "COLLECTION_DIR", coll_dir)
    monkeypatch.setattr(config_mod, "INVENTORY_PATH", inv_path)
    monkeypatch.setattr(config_mod, "DECKS_DIR", decks_dir)
    monkeypatch.setattr(persist_mod, "COLLECTION_DIR", coll_dir)
    monkeypatch.setattr(persist_mod, "INVENTORY_PATH", inv_path)
    monkeypatch.setattr(persist_mod, "DECKS_DIR", decks_dir)

    # Write a minimal UserDeck JSON directly so we don't depend on the CLI save path.
    deck_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())
    deck_data = {
        "id": deck_id,
        "owner": "local",
        "name": "Dimir Tempo",
        "archetype_hint": None,
        "versions": [
            {
                "id": version_id,
                "version": 1,
                "label": "",
                "cards": [
                    {"name": "Brainstorm", "count": 4, "board": "main", "printing": None},
                    {"name": "Force of Will", "count": 4, "board": "main", "printing": None},
                    {"name": "Island", "count": 12, "board": "main", "printing": None},
                    {"name": "Daze", "count": 3, "board": "side", "printing": None},
                ],
                "created": "2026-06-13T00:00:00Z",
                "note": "",
            }
        ],
        "current_version_id": version_id,
        "created": "2026-06-13T00:00:00Z",
        "updated": "2026-06-13T00:00:00Z",
    }
    (decks_dir / f"{deck_id}.json").write_text(json.dumps(deck_data))

    # Also write a plain-text deck file for the --deck FILE path.
    deck_file = tmp_path / "deck.txt"
    deck_file.write_text("4 Brainstorm\n4 Force of Will\n12 Island\n\nSideboard\n3 Daze\n")

    runner = CliRunner()
    return runner, deck_file


# ---------------------------------------------------------------------------
# _resolve_deck_boards — mutual exclusion + missing source
# ---------------------------------------------------------------------------


class TestResolveDeckBoardsGuards:
    """Test the mutual-exclusion and neither-supplied guards via export deck (lightest leaf)."""

    def test_both_deck_and_my_deck_raises(self, deck_env, tmp_path):
        runner, deck_file = deck_env
        result = runner.invoke(
            main,
            ["export", "deck", "--deck", str(deck_file), "--my-deck", "Dimir Tempo"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_neither_deck_nor_my_deck_raises(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["export", "deck"])
        assert result.exit_code != 0
        # The error message names the command and the requirement.
        assert "export deck" in result.output or "--deck" in result.output or "requires" in result.output.lower()

    def test_unknown_my_deck_fails_loud(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["export", "deck", "--my-deck", "No Such Deck"])
        assert result.exit_code != 0
        assert "No deck named" in result.output


# ---------------------------------------------------------------------------
# export deck — lightest leaf: no DB required, pure format pass-through
# ---------------------------------------------------------------------------


class TestExportDeckMyDeck:
    def test_my_deck_produces_same_output_as_deck_file(self, deck_env, tmp_path):
        runner, deck_file = deck_env

        # Via --deck FILE.
        r_file = runner.invoke(
            main, ["export", "deck", "--deck", str(deck_file), "--format", "text"]
        )
        assert r_file.exit_code == 0, r_file.output

        # Via --my-deck NAME.
        r_my = runner.invoke(
            main, ["export", "deck", "--my-deck", "Dimir Tempo", "--format", "text"]
        )
        assert r_my.exit_code == 0, r_my.output

        # Both paths produce output containing the same cards.
        for card in ["Brainstorm", "Force of Will", "Island"]:
            assert card in r_file.output
            assert card in r_my.output

    def test_my_deck_to_moxfield(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(
            main, ["export", "deck", "--my-deck", "Dimir Tempo", "--format", "moxfield"]
        )
        assert result.exit_code == 0, result.output
        assert "Brainstorm" in result.output

    def test_deck_file_path_unchanged(self, deck_env, tmp_path):
        """--deck FILE with no --my-deck: byte-identical baseline."""
        runner, deck_file = deck_env
        result = runner.invoke(
            main, ["export", "deck", "--deck", str(deck_file), "--format", "text"]
        )
        assert result.exit_code == 0, result.output
        assert "Brainstorm" in result.output


# ---------------------------------------------------------------------------
# advise positioning — requires DB; use monkeypatching to avoid it
# ---------------------------------------------------------------------------


class TestAdvisePositioningMyDeck:
    def test_my_deck_unknown_fails(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(
            main, ["advise", "positioning", "--my-deck", "Ghost Deck"]
        )
        assert result.exit_code != 0
        assert "No deck named" in result.output

    def test_both_flags_mutually_exclusive(self, deck_env, tmp_path):
        runner, deck_file = deck_env
        result = runner.invoke(
            main,
            ["advise", "positioning", "--deck", str(deck_file), "--my-deck", "Dimir Tempo"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_neither_flag_fails(self, deck_env):
        runner, _ = deck_env
        # No deck source at all — should fail before reaching DB.
        result = runner.invoke(main, ["advise", "positioning"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# advise sideboard — same guard tests
# ---------------------------------------------------------------------------


class TestAdviseSideboardMyDeck:
    def test_unknown_my_deck_fails(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["advise", "sideboard", "--my-deck", "Ghost"])
        assert result.exit_code != 0
        assert "No deck named" in result.output

    def test_both_flags_mutually_exclusive(self, deck_env, tmp_path):
        runner, deck_file = deck_env
        result = runner.invoke(
            main,
            ["advise", "sideboard", "--deck", str(deck_file), "--my-deck", "Dimir Tempo"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_neither_flag_fails(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["advise", "sideboard"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# advise whattoplay — same guard tests
# ---------------------------------------------------------------------------


class TestAdviseWhattoplayMyDeck:
    def test_unknown_my_deck_fails(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["advise", "whattoplay", "--my-deck", "Ghost"])
        assert result.exit_code != 0
        assert "No deck named" in result.output

    def test_both_flags_mutually_exclusive(self, deck_env, tmp_path):
        runner, deck_file = deck_env
        result = runner.invoke(
            main,
            ["advise", "whattoplay", "--deck", str(deck_file), "--my-deck", "Dimir Tempo"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_neither_flag_fails(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["advise", "whattoplay"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# advise report — same guard tests
# ---------------------------------------------------------------------------


class TestAdviseReportMyDeck:
    def test_unknown_my_deck_fails(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["advise", "report", "--my-deck", "Ghost"])
        assert result.exit_code != 0
        assert "No deck named" in result.output

    def test_both_flags_mutually_exclusive(self, deck_env, tmp_path):
        runner, deck_file = deck_env
        result = runner.invoke(
            main,
            ["advise", "report", "--deck", str(deck_file), "--my-deck", "Dimir Tempo"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_neither_flag_fails(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["advise", "report"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# advise refresh — same guard tests
# ---------------------------------------------------------------------------


class TestAdviseRefreshMyDeck:
    def test_unknown_my_deck_fails(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["advise", "refresh", "--my-deck", "Ghost"])
        assert result.exit_code != 0
        assert "No deck named" in result.output

    def test_both_flags_mutually_exclusive(self, deck_env, tmp_path):
        runner, deck_file = deck_env
        result = runner.invoke(
            main,
            ["advise", "refresh", "--deck", str(deck_file), "--my-deck", "Dimir Tempo"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_neither_flag_fails(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["advise", "refresh"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# generate tune — same guard tests
# ---------------------------------------------------------------------------


class TestGenerateTuneMyDeck:
    def test_unknown_my_deck_fails(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["generate", "tune", "--my-deck", "Ghost"])
        assert result.exit_code != 0
        assert "No deck named" in result.output

    def test_both_flags_mutually_exclusive(self, deck_env, tmp_path):
        runner, deck_file = deck_env
        result = runner.invoke(
            main,
            ["generate", "tune", "--deck", str(deck_file), "--my-deck", "Dimir Tempo"],
        )
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_neither_flag_fails(self, deck_env):
        runner, _ = deck_env
        result = runner.invoke(main, ["generate", "tune"])
        assert result.exit_code != 0
