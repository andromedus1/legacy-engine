from __future__ import annotations

from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.ingestion import store
from legacy_engine.models.card import Card


def test_card_coverage_cli_uses_explicit_file_db_and_emits_zero_gap(tmp_path):
    db_path = tmp_path / "coverage.duckdb"
    con = store.connect(db_path)
    store.init_schema(con)
    store.load_cards(con, [Card(name="Brainstorm")])
    con.execute("INSERT INTO deck_cards VALUES ('t', 0, 'main', 'Brainstorm', 4)")
    con.close()

    result = CliRunner().invoke(main, ["refresh", "card-coverage", "--db", str(db_path)])

    assert result.exit_code == 0, result.output
    assert "// card dimension: 1 distinct names" in result.output
    assert "gaps ambiguous=0, suspected_truncated=0, unresolved=0" in result.output
