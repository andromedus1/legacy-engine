"""Hermetic CLI tests for the `lint` group (`lint catalog`, epic-data-autonomy-catalog-lint).

File-backed-cli-test-db-builder pattern: `_build_lint_cli_db(tmp_path, cards=...) -> str` stands
up a tmp DuckDB seeded from the frozen catalog-lint card fixture, and every `runner.invoke` pins
`--db <that path>` — never the default DB. `lint catalog` always cross-checks the SHIPPED curated
JSON (there is no path-override flag), so the failure-path test drops one required card
(Wasteland) from the tmp fixture instead of mutating the curated files — a genuine, hermetic
name_exists error against real shipped data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.ingestion import store

_FIXTURE_CARDS: "list[dict]" = json.loads(
    (Path(__file__).parent / "data" / "catalog_lint_cards.json").read_text(encoding="utf-8")
)

_CARDS_COLS = (
    "name, mana_cost, cmc, type_line, colors, produced_mana, oracle_text, layout, is_land, "
    "power, toughness"
)


def _build_lint_cli_db(tmp_path, cards: "list[dict] | None" = None) -> str:
    db_path = str(tmp_path / "lint_cli.duckdb")
    con = store.connect(db_path)
    store.init_schema(con)
    rows = _FIXTURE_CARDS if cards is None else cards
    con.executemany(
        f"INSERT INTO cards ({_CARDS_COLS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                c["name"], c.get("mana_cost", ""), c.get("cmc", 0.0), c.get("type_line", ""),
                c.get("colors", ""), c.get("produced_mana", ""), c.get("oracle_text", ""),
                c.get("layout", "normal"), c.get("is_land", False), c.get("power"),
                c.get("toughness"),
            )
            for c in rows
        ],
    )
    con.close()
    return db_path


@pytest.fixture
def runner():
    return CliRunner()


class TestLintCatalog:
    def test_clean_catalog_exits_zero(self, tmp_path, runner):
        db_path = _build_lint_cli_db(tmp_path)
        result = runner.invoke(main, ["lint", "catalog", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert "// catalog lint: clean (0 errors, 0 warnings)" in result.output

    def test_missing_card_exits_nonzero_and_reports(self, tmp_path, runner):
        # Fixture minus Wasteland — a real name_exists error against the shipped hoser catalog.
        cards = [c for c in _FIXTURE_CARDS if c["name"] != "Wasteland"]
        db_path = _build_lint_cli_db(tmp_path, cards=cards)
        result = runner.invoke(main, ["lint", "catalog", "--db", db_path])
        assert result.exit_code != 0
        assert "Wasteland" in result.output
        assert "[error]" in result.output
        assert "name_exists" in result.output

    def test_never_touches_default_db(self, tmp_path, runner, monkeypatch):
        # Point the default DUCKDB_PATH at a location that would get mkdir'd if ever opened,
        # proving --db is honored end-to-end (mirrors tests/test_cli_eras.py's technique).
        db_path = _build_lint_cli_db(tmp_path)
        bad_default = tmp_path / "should_never_be_touched" / "legacy.duckdb"
        monkeypatch.setattr("legacy_engine.config.DUCKDB_PATH", bad_default)
        result = runner.invoke(main, ["lint", "catalog", "--db", db_path])
        assert result.exit_code == 0, result.output
        assert not bad_default.parent.exists()
