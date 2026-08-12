from __future__ import annotations

import json

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


def _write_protocol(path, cutoffs=("2026-01-01", "2026-02-01"), final="2026-03-01"):
    payload = {
        "planned_folds": [{"cutoff": cutoff} for cutoff in cutoffs],
        "final_evaluation_until": final,
    }
    path.write_text(json.dumps(payload))
    return path


def test_card_coverage_preflight_prints_all_cohorts_and_blocks_training_gaps(tmp_path):
    db_path = tmp_path / "coverage.duckdb"
    con = store.connect(db_path)
    store.init_schema(con)
    con.executemany(
        "INSERT INTO tournaments VALUES (?, 'T', ?, ?, 'Legacy', 'fixture', 'paper')",
        [
            ("before", "2025-12-31", "uri-before"),
            ("boundary", "2026-01-01", "uri-boundary"),
            ("tail", "2026-02-15", "uri-tail"),
        ],
    )
    con.executemany(
        "INSERT INTO deck_cards VALUES (?, 0, 'main', ?, 1)",
        [("before", "Before Gap"), ("boundary", "Boundary Gap"), ("tail", "Tail Gap")],
    )
    con.close()
    protocol = _write_protocol(tmp_path / "protocol.json")

    result = CliRunner().invoke(main, [
        "refresh", "card-coverage", "--db", str(db_path),
        "--benchmark-protocol", str(protocol),
    ])

    assert result.exit_code != 0
    assert "cutoff=2026-01-01; rows=1; names=1; decks=1; observed=Before Gap" in result.output
    assert "cutoff=2026-02-01; rows=1; names=1; decks=1; observed=Boundary Gap" in result.output
    assert "cutoff=no-later-training-cutoff; rows=1; names=1; decks=1; observed=Tail Gap" in result.output
    assert '"observed_name": "Before Gap"' in result.output
    assert '"providers": ["fixture"]' in result.output
    assert '"event_uris": ["uri-before"]' in result.output


def test_card_coverage_preflight_allows_post_last_cutoff_gap(tmp_path):
    db_path = tmp_path / "coverage.duckdb"
    con = store.connect(db_path)
    store.init_schema(con)
    con.execute(
        "INSERT INTO tournaments VALUES ('tail', 'T', '2026-02-15', 'uri', "
        "'Legacy', 'fixture', 'paper')"
    )
    con.execute("INSERT INTO deck_cards VALUES ('tail', 0, 'main', 'Tail Gap', 1)")
    con.close()
    protocol = _write_protocol(tmp_path / "protocol.json")

    result = CliRunner().invoke(main, [
        "refresh", "card-coverage", "--db", str(db_path),
        "--benchmark-protocol", str(protocol),
    ])

    assert result.exit_code == 0, result.output
    assert "cutoff=2026-01-01; rows=0; names=0; decks=0; observed=none" in result.output
    assert "cutoff=2026-02-01; rows=0; names=0; decks=0; observed=none" in result.output
    assert "no-later-training-cutoff; rows=1" in result.output


def test_card_coverage_preflight_rejects_mutable_schedule_shape(tmp_path):
    db_path = tmp_path / "coverage.duckdb"
    con = store.connect(db_path)
    store.init_schema(con)
    con.close()
    protocol = _write_protocol(
        tmp_path / "protocol.json", cutoffs=("2026-02-01", "2026-01-01")
    )

    result = CliRunner().invoke(main, [
        "refresh", "card-coverage", "--db", str(db_path),
        "--benchmark-protocol", str(protocol),
    ])

    assert result.exit_code != 0
    assert "requires non-empty ordered unique planned_folds cutoffs" in result.output


def test_invalid_preflight_protocol_is_rejected_before_reconciliation_mutates_db(tmp_path):
    db_path = tmp_path / "coverage.duckdb"
    con = store.connect(db_path)
    store.init_schema(con)
    store.load_cards(con, [Card(name="Brainstorm")])
    con.execute("INSERT INTO deck_cards VALUES ('t', 0, 'main', 'brainstorm', 4)")
    con.close()
    protocol = _write_protocol(
        tmp_path / "protocol.json", cutoffs=("2026-02-01", "2026-01-01")
    )

    result = CliRunner().invoke(main, [
        "refresh", "card-coverage", "--db", str(db_path),
        "--benchmark-protocol", str(protocol),
    ])

    assert result.exit_code != 0
    con = store.connect(db_path)
    assert con.execute("SELECT name FROM deck_cards").fetchone()[0] == "brainstorm"
    con.close()
