"""CLI smoke tests for collection and deck command groups.

Uses CliRunner with tmp_path-scoped data paths (monkeypatched) so we never
touch real data.  Tests: collection import → deck save → deck buildable
end-to-end; fail-loud on unknown deck name.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main


# ---------------------------------------------------------------------------
# Fixture: redirect all collection paths to tmp_path
# ---------------------------------------------------------------------------


@pytest.fixture
def cli_collection_env(tmp_path, monkeypatch):
    """Redirect collection paths + return a CliRunner."""
    coll_dir = tmp_path / "collection"
    inv_path = coll_dir / "inventory.json"
    decks_dir = coll_dir / "decks"

    import legacy_engine.collection.persist as persist_mod
    import legacy_engine.config as config_mod

    monkeypatch.setattr(config_mod, "COLLECTION_DIR", coll_dir)
    monkeypatch.setattr(config_mod, "INVENTORY_PATH", inv_path)
    monkeypatch.setattr(config_mod, "DECKS_DIR", decks_dir)
    monkeypatch.setattr(persist_mod, "COLLECTION_DIR", coll_dir)
    monkeypatch.setattr(persist_mod, "INVENTORY_PATH", inv_path)
    monkeypatch.setattr(persist_mod, "DECKS_DIR", decks_dir)

    return CliRunner(), tmp_path


# ---------------------------------------------------------------------------
# collection import
# ---------------------------------------------------------------------------


class TestCollectionImport:
    def test_import_plain_text(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env
        deck_file = base / "binder.txt"
        deck_file.write_text("4 Brainstorm\n4 Force of Will\n")

        result = runner.invoke(main, ["collection", "import", "--file", str(deck_file)])
        assert result.exit_code == 0, result.output
        assert "Merged inventory" in result.output or "Replaced inventory" in result.output
        assert "entries" in result.output

    def test_import_merge_adds_cards(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env
        f1 = base / "batch1.txt"
        f2 = base / "batch2.txt"
        f1.write_text("4 Brainstorm\n")
        f2.write_text("4 Force of Will\n")

        runner.invoke(main, ["collection", "import", "--file", str(f1)])
        result2 = runner.invoke(main, ["collection", "import", "--file", str(f2), "--merge"])
        assert result2.exit_code == 0, result2.output
        # After two merges, 2 distinct entries, 8 total cards.
        assert "2 entries" in result2.output

    def test_import_replace_resets_inventory(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env
        f1 = base / "old.txt"
        f2 = base / "new.txt"
        f1.write_text("4 Brainstorm\n4 Force of Will\n")
        f2.write_text("2 Island\n")

        runner.invoke(main, ["collection", "import", "--file", str(f1)])
        result2 = runner.invoke(main, ["collection", "import", "--file", str(f2), "--replace"])
        assert result2.exit_code == 0, result2.output
        assert "1 entries" in result2.output


# ---------------------------------------------------------------------------
# collection show
# ---------------------------------------------------------------------------


class TestCollectionShow:
    def test_show_empty(self, cli_collection_env):
        runner, _ = cli_collection_env
        result = runner.invoke(main, ["collection", "show"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "Inventory" in result.output

    def test_show_after_import(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env
        f = base / "cards.txt"
        f.write_text("4 Brainstorm\n")
        runner.invoke(main, ["collection", "import", "--file", str(f)])

        result = runner.invoke(main, ["collection", "show"])
        assert result.exit_code == 0, result.output
        assert "Brainstorm" in result.output


# ---------------------------------------------------------------------------
# deck save + list + show + versions
# ---------------------------------------------------------------------------


_DECK_TEXT = """\
4 Brainstorm
4 Force of Will
12 Island

Sideboard
3 Daze
"""


class TestDeckSave:
    def test_save_new_deck(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env
        f = base / "deck.txt"
        f.write_text(_DECK_TEXT)

        result = runner.invoke(
            main, ["deck", "save", "--name", "my Dimir Tempo", "--deck", str(f)]
        )
        assert result.exit_code == 0, result.output
        assert "my Dimir Tempo" in result.output
        assert "v1" in result.output

    def test_save_appends_version(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env
        f = base / "deck.txt"
        f.write_text(_DECK_TEXT)
        f2 = base / "deck2.txt"
        f2.write_text("4 Brainstorm\n12 Island\n\nSideboard\n3 Daze\n")

        # First save.
        r1 = runner.invoke(main, ["deck", "save", "--name", "my Dimir Tempo", "--deck", str(f)])
        assert r1.exit_code == 0, r1.output

        # Second save (same name → auto-append).
        r2 = runner.invoke(main, ["deck", "save", "--name", "my Dimir Tempo", "--deck", str(f2)])
        assert r2.exit_code == 0, r2.output
        assert "v2" in r2.output


class TestDeckList:
    def test_list_empty(self, cli_collection_env):
        runner, _ = cli_collection_env
        result = runner.invoke(main, ["deck", "list"])
        assert result.exit_code == 0
        assert "no decks" in result.output.lower()

    def test_list_after_save(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env
        f = base / "deck.txt"
        f.write_text(_DECK_TEXT)
        runner.invoke(main, ["deck", "save", "--name", "Dimir Tempo", "--deck", str(f)])

        result = runner.invoke(main, ["deck", "list"])
        assert result.exit_code == 0, result.output
        assert "Dimir Tempo" in result.output


class TestDeckLoad:
    def test_load_outputs_decklist(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env
        f = base / "deck.txt"
        f.write_text("4 Brainstorm\n12 Island\n\nSideboard\n3 Daze\n")
        runner.invoke(main, ["deck", "save", "--name", "Test Deck", "--deck", str(f)])

        result = runner.invoke(main, ["deck", "load", "--name", "Test Deck"])
        assert result.exit_code == 0, result.output
        assert "Brainstorm" in result.output
        assert "Daze" in result.output

    def test_load_unknown_deck_fails_loud(self, cli_collection_env):
        runner, _ = cli_collection_env
        result = runner.invoke(main, ["deck", "load", "--name", "Nonexistent Deck"])
        assert result.exit_code != 0
        assert "No deck named" in result.output


class TestDeckShow:
    def test_show_deck(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env
        f = base / "deck.txt"
        f.write_text("4 Brainstorm\n12 Island\n\nSideboard\n3 Daze\n")
        runner.invoke(main, ["deck", "save", "--name", "Show Test", "--deck", str(f)])

        result = runner.invoke(main, ["deck", "show", "--name", "Show Test"])
        assert result.exit_code == 0, result.output
        assert "Show Test" in result.output
        assert "Brainstorm" in result.output


class TestDeckVersions:
    def test_versions_log(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env
        f = base / "deck.txt"
        f.write_text("4 Brainstorm\n12 Island\n")
        runner.invoke(main, ["deck", "save", "--name", "Versioned Deck", "--deck", str(f)])

        result = runner.invoke(main, ["deck", "versions", "--name", "Versioned Deck"])
        assert result.exit_code == 0, result.output
        assert "v1" in result.output
        assert "current" in result.output.lower()


# ---------------------------------------------------------------------------
# deck buildable — end-to-end: import → save → buildable
# ---------------------------------------------------------------------------


class TestDeckBuildable:
    def test_buildable_when_owned(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env

        # Import a binder with 4 Brainstorm + 12 Island + 3 Daze.
        binder = base / "binder.txt"
        binder.write_text("4 Brainstorm\n12 Island\n3 Daze\n")
        runner.invoke(main, ["collection", "import", "--file", str(binder)])

        # Save a deck that uses exactly those cards.
        deck_file = base / "deck.txt"
        deck_file.write_text("4 Brainstorm\n12 Island\n\nSideboard\n3 Daze\n")
        runner.invoke(main, ["deck", "save", "--name", "Budget Blue", "--deck", str(deck_file)])

        result = runner.invoke(main, ["deck", "buildable", "--name", "Budget Blue"])
        assert result.exit_code == 0, result.output
        assert "OK" in result.output or "can build" in result.output.lower()

    def test_not_buildable_when_missing(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env

        # Empty binder.
        binder = base / "binder.txt"
        binder.write_text("1 Island\n")
        runner.invoke(main, ["collection", "import", "--file", str(binder)])

        deck_file = base / "deck.txt"
        deck_file.write_text("4 Force of Will\n4 Brainstorm\n12 Island\n")
        runner.invoke(main, ["deck", "save", "--name", "Pricey Blue", "--deck", str(deck_file)])

        result = runner.invoke(main, ["deck", "buildable", "--name", "Pricey Blue"])
        assert result.exit_code == 0, result.output
        assert "MISSING" in result.output

    def test_buildable_unknown_deck_fails_loud(self, cli_collection_env):
        runner, _ = cli_collection_env
        result = runner.invoke(main, ["deck", "buildable", "--name", "Ghost Deck"])
        assert result.exit_code != 0
        assert "No deck named" in result.output


# ---------------------------------------------------------------------------
# collection status
# ---------------------------------------------------------------------------


class TestCollectionStatus:
    def test_status_no_decks(self, cli_collection_env):
        runner, _ = cli_collection_env
        result = runner.invoke(main, ["collection", "status"])
        assert result.exit_code == 0
        assert "no decks" in result.output.lower()

    def test_status_with_deck(self, cli_collection_env, tmp_path):
        runner, base = cli_collection_env
        binder = base / "binder.txt"
        binder.write_text("4 Brainstorm\n")
        runner.invoke(main, ["collection", "import", "--file", str(binder)])
        deck_file = base / "deck.txt"
        deck_file.write_text("4 Brainstorm\n")
        runner.invoke(main, ["deck", "save", "--name", "Solo", "--deck", str(deck_file)])

        result = runner.invoke(main, ["collection", "status"])
        assert result.exit_code == 0, result.output
        assert "Solo" in result.output
