from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.ingestion import store


def _db(path: Path) -> str:
    con = store.connect(path)
    store.init_schema(con)
    con.executemany("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        ("Alpha Signal", "{1}", 1.0, "Artifact", "", "", "", "normal", False, None, None),
        ("Beta Signal", "{1}", 1.0, "Artifact", "", "", "", "normal", False, None, None),
    ])
    events = [
        ("sep", "2025-09-01", "online"),
        ("oct", "2025-10-01", "paper"),
        ("nov", "2025-11-01", "online"),
        ("dec", "2025-12-01", "paper"),
        ("future", "2026-01-10", "online"),
    ]
    for event, event_date, provenance in events:
        con.execute(
            "INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)",
            [event, event, event_date, "u", "Legacy", "fixture", provenance],
        )
        con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", [
            (event, 0, "Alice", "1", "Alpha", None),
            (event, 1, "Bob", "2", "Beta", None),
        ])
        con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [
            (event, 0, "main", "Alpha Signal", 4),
            (event, 1, "main", "Beta Signal", 4),
        ])
        con.executemany("INSERT INTO rounds VALUES (?, ?, ?, ?, ?)", [
            (event, index, "Alice", "Bob", "2-0" if index % 2 == 0 else "0-2")
            for index in range(10)
        ])
    con.close()
    return str(path)


def test_player_effect_cli_plan_freeze_evaluate_and_run_are_hermetic(tmp_path, monkeypatch):
    import legacy_engine.workflows.ranking_benchmark as benchmark_workflow

    rules = tmp_path / "rules" / "Formats" / "Legacy" / "Archetypes"
    rules.mkdir(parents=True)
    (rules / "Alpha.json").write_text(json.dumps({
        "Name": "Alpha", "Conditions": [{"Type": "InMainboard", "Cards": ["Alpha Signal"]}],
    }))
    (rules / "Beta.json").write_text(json.dumps({
        "Name": "Beta", "Conditions": [{"Type": "InMainboard", "Cards": ["Beta Signal"]}],
    }))
    monkeypatch.setattr(benchmark_workflow, "RULES_DIR", tmp_path / "rules")
    db = _db(tmp_path / "diagnostic.duckdb")
    runner = CliRunner()
    benchmark_protocol = tmp_path / "benchmark.json"
    result = runner.invoke(main, [
        "advise", "benchmark", "plan", "--db", db, "--protocol-id", "benchmark",
        "--created-at", "2025-08-01T00:00:00Z", "--first-cutoff", "2026-01-01",
        "--until", "2026-01-29", "--out", str(benchmark_protocol),
    ])
    assert result.exit_code == 0, result.output
    fold_id = "2026-01-01--2026-01-29"
    benchmark_artifacts = tmp_path / "benchmark-artifacts"
    result = runner.invoke(main, [
        "advise", "benchmark", "freeze", "--db", db,
        "--protocol", str(benchmark_protocol), "--fold", fold_id,
        "--artifact-dir", str(benchmark_artifacts),
    ])
    assert result.exit_code == 0, result.output

    player_protocol = tmp_path / "player.json"
    accessibility = tmp_path / "accessibility.json"
    result = runner.invoke(main, [
        "advise", "benchmark", "player-effect", "plan", "--db", db,
        "--benchmark-protocol", str(benchmark_protocol), "--protocol-id", "player",
        "--created-at", "2025-08-01T00:00:00Z", "--out", str(player_protocol),
        "--report", str(accessibility),
    ])
    assert result.exit_code == 0, result.output
    assert "provenance-local-handle" in result.output
    assert "player_key" not in accessibility.read_text()

    base = benchmark_artifacts / f"{fold_id}.predictions.json"
    base_checksum = benchmark_artifacts / f"{fold_id}.predictions.sha256.json"
    predictions = tmp_path / "player-predictions.json"
    checksum = tmp_path / "player-checksum.json"
    result = runner.invoke(main, [
        "advise", "benchmark", "player-effect", "freeze", "--db", db,
        "--benchmark-protocol", str(benchmark_protocol), "--player-protocol", str(player_protocol),
        "--base-predictions", str(base), "--base-checksum", str(base_checksum),
        "--out", str(predictions), "--checksum-out", str(checksum),
    ])
    assert result.exit_code == 0, result.output
    assert "outcome-blind" in result.output
    assert "Alice" not in predictions.read_text() and "Bob" not in predictions.read_text()

    evaluation = tmp_path / "evaluation.json"
    report = tmp_path / "report.md"
    result = runner.invoke(main, [
        "advise", "benchmark", "player-effect", "evaluate", "--db", db,
        "--benchmark-protocol", str(benchmark_protocol), "--player-protocol", str(player_protocol),
        "--base-predictions", str(base), "--base-checksum", str(base_checksum),
        "--predictions", str(predictions), "--checksum", str(checksum),
        "--out", str(evaluation), "--report", str(report),
    ])
    assert result.exit_code == 0, result.output
    assert "production ranking unchanged" in result.output
    assert "Production ranking" in report.read_text()

    composed = tmp_path / "composed"
    result = runner.invoke(main, [
        "advise", "benchmark", "player-effect", "run", "--db", db,
        "--benchmark-protocol", str(benchmark_protocol), "--player-protocol", str(player_protocol),
        "--benchmark-artifact-dir", str(benchmark_artifacts),
        "--artifact-dir", str(composed),
    ])
    assert result.exit_code == 0, result.output
    assert json.loads((composed / f"{fold_id}.player-effect.evaluation.json").read_text()) == json.loads(
        evaluation.read_text()
    )
    assert json.loads((composed / "player-effect.summary.json").read_text())["status"] != (
        "candidate-for-promotion-study"
    )


def test_every_player_effect_leaf_requires_explicit_db(tmp_path):
    for command in ("plan", "freeze", "evaluate", "run"):
        result = CliRunner().invoke(main, ["advise", "benchmark", "player-effect", command])
        assert result.exit_code == 2
        assert "Missing option '--db'" in result.output
