from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.ingestion import store


def _build_benchmark_db(tmp_path: Path) -> str:
    path = tmp_path / "benchmark.duckdb"
    con = store.connect(path)
    store.init_schema(con)
    con.execute("INSERT INTO cards (name) VALUES ('Brainstorm')")
    con.executemany(
        "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            ("past", "Past", "2025-12-20", "u1", "Legacy", "fixture", "online"),
            ("future", "Future", "2026-01-10", "u2", "Legacy", "fixture", "online"),
        ],
    )
    for event in ("past", "future"):
        con.executemany(
            "INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)",
            [
                (event, 0, f"{event}-a", "1st", "Alpha", None),
                (event, 1, f"{event}-b", "2nd", "Beta", None),
            ],
        )
        con.executemany(
            "INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)",
            [(event, 0, "main", "Brainstorm", 4), (event, 1, "main", "Brainstorm", 4)],
        )
        con.execute(
            "INSERT INTO rounds VALUES (?, 0, ?, ?, '2-0')",
            [event, f"{event}-a", f"{event}-b"],
        )
    con.close()
    return str(path)


def test_benchmark_cli_two_phase_run_parity_and_tamper_guard(tmp_path):
    db = _build_benchmark_db(tmp_path)
    protocol = tmp_path / "protocol.json"
    artifacts = tmp_path / "artifacts"
    runner = CliRunner()
    planned = runner.invoke(main, [
        "advise", "benchmark", "plan", "--db", db,
        "--protocol-id", "cli-test", "--created-at", "2026-01-01T00:00:00Z",
        "--first-cutoff", "2026-01-01", "--until", "2026-01-29",
        "--out", str(protocol),
    ])
    assert planned.exit_code == 0, planned.output
    assert "// benchmark protocol:" in planned.output
    fold_id = "2026-01-01--2026-01-29"

    frozen = runner.invoke(main, [
        "advise", "benchmark", "freeze", "--db", db, "--protocol", str(protocol),
        "--fold", fold_id, "--artifact-dir", str(artifacts),
    ])
    assert frozen.exit_code == 0, frozen.output
    predictions = artifacts / f"{fold_id}.predictions.json"
    checksum = artifacts / f"{fold_id}.predictions.sha256.json"
    evaluated_path = tmp_path / "evaluation.json"
    report = tmp_path / "report.md"
    evaluated = runner.invoke(main, [
        "advise", "benchmark", "evaluate", "--db", db, "--protocol", str(protocol),
        "--predictions", str(predictions), "--checksum", str(checksum),
        "--out", str(evaluated_path), "--report", str(report),
    ])
    assert evaluated.exit_code == 0, evaluated.output
    assert "// verified frozen predictions:" in evaluated.output
    assert json.loads(evaluated_path.read_text())["status"] == "not-evaluable"
    assert "Evaluation is read-only" in report.read_text()

    composed = tmp_path / "composed"
    run = runner.invoke(main, [
        "advise", "benchmark", "run", "--db", db, "--protocol", str(protocol),
        "--artifact-dir", str(composed),
    ])
    assert run.exit_code == 0, run.output
    assert json.loads((composed / f"{fold_id}.evaluation.json").read_text()) == json.loads(
        evaluated_path.read_text()
    )

    tampered = json.loads(predictions.read_text())
    tampered["field_shares"]["Alpha"] = 0.9
    predictions.write_text(json.dumps(tampered))
    rejected = runner.invoke(main, [
        "advise", "benchmark", "evaluate", "--db", db, "--protocol", str(protocol),
        "--predictions", str(predictions), "--checksum", str(checksum),
        "--out", str(tmp_path / "bad.json"), "--report", str(tmp_path / "bad.md"),
    ])
    assert rejected.exit_code != 0
    assert "artifact hash mismatch" in str(rejected.exception)


def test_benchmark_cli_requires_explicit_db(tmp_path):
    result = CliRunner().invoke(main, [
        "advise", "benchmark", "plan", "--protocol-id", "x",
        "--created-at", "2026-01-01T00:00:00Z", "--first-cutoff", "2026-01-01",
        "--until", "2026-01-29", "--out", str(tmp_path / "protocol.json"),
    ])
    assert result.exit_code == 2
    assert "Missing option '--db'" in result.output
