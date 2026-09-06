from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from legacy_engine.cli import main
from legacy_engine.ingestion import store
from legacy_engine.models.card import Card


def _build_benchmark_db(tmp_path: Path) -> str:
    path = tmp_path / "benchmark.duckdb"
    con = store.connect(path)
    store.init_schema(con)
    con.executemany("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        ("Alpha Signal", "{1}", 1.0, "Artifact", "", "", "", "normal", False, None, None),
        ("Beta Signal", "{1}", 1.0, "Artifact", "", "", "", "normal", False, None, None),
    ])
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
            [
                (event, 0, "main", "Alpha Signal", 4),
                (event, 1, "main", "Beta Signal", 4),
            ],
        )
        con.execute(
            "INSERT INTO rounds VALUES (?, 0, ?, ?, '2-0')",
            [event, f"{event}-a", f"{event}-b"],
        )
    con.close()
    return str(path)


def test_benchmark_cli_two_phase_run_parity_and_tamper_guard(tmp_path, monkeypatch):
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
    preregistered = json.loads(protocol.read_text())
    assert [fold["fold_id"] for fold in preregistered["planned_folds"]] == [fold_id]
    assert "ban_events_as_of" in preregistered

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

    replay = runner.invoke(main, [
        "advise", "benchmark", "run", "--db", db, "--protocol", str(protocol),
        "--artifact-dir", str(composed),
    ])
    assert replay.exit_code == 0, replay.output

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

    con = store.connect(Path(db))
    con.execute("DELETE FROM cards WHERE name = 'Beta Signal'")
    con.close()
    failed_artifacts = tmp_path / "failed-artifacts"
    failed = runner.invoke(main, [
        "advise", "benchmark", "run", "--db", db, "--protocol", str(protocol),
        "--artifact-dir", str(failed_artifacts),
    ])
    assert failed.exit_code != 0
    failed_summary = json.loads((failed_artifacts / "summary.json").read_text())
    assert failed_summary["status"] == "not-evaluable"
    assert "deck-card rows without observed card metadata" in failed_summary["reasons"][0]
    assert "deck-card rows without observed card metadata" in (
        failed_artifacts / "summary.md"
    ).read_text()


def test_benchmark_cli_requires_explicit_db(tmp_path):
    result = CliRunner().invoke(main, [
        "advise", "benchmark", "plan", "--protocol-id", "x",
        "--created-at", "2026-01-01T00:00:00Z", "--first-cutoff", "2026-01-01",
        "--until", "2026-01-29", "--out", str(tmp_path / "protocol.json"),
    ])
    assert result.exit_code == 2
    assert "Missing option '--db'" in result.output


def test_benchmark_plan_exposes_quarantine_policy_and_claim_ceiling(tmp_path):
    db = _build_benchmark_db(tmp_path)
    protocol = tmp_path / "quarantine-protocol.json"
    result = CliRunner().invoke(main, [
        "advise", "benchmark", "plan", "--db", db,
        "--protocol-id", "quarantine", "--created-at", "2026-08-12T00:00:00Z",
        "--registered-at", "2026-08-12T00:00:00Z", "--claim-ceiling", "descriptive",
        "--card-metadata-policy", "quarantine-unresolved-decks",
        "--max-quarantined-deck-fraction", "0.005",
        "--max-quarantined-round-fraction", "0.02",
        "--first-cutoff", "2026-01-01", "--until", "2026-01-29", "--out", str(protocol),
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(protocol.read_text())
    assert payload["claim_ceiling"] == "descriptive"
    assert payload["card_metadata"]["mode"] == "quarantine-unresolved-decks"
    assert "card metadata: quarantine-unresolved-decks" in result.output


def test_card_coverage_preflight_handoff_preserves_frozen_protocol(tmp_path, monkeypatch):
    import legacy_engine.workflows.ranking_benchmark as benchmark_workflow

    rules = tmp_path / "rules" / "Formats" / "Legacy" / "Archetypes"
    rules.mkdir(parents=True)
    monkeypatch.setattr(benchmark_workflow, "RULES_DIR", tmp_path / "rules")
    db = _build_benchmark_db(tmp_path)
    protocol = tmp_path / "protocol.json"
    runner = CliRunner()
    planned = runner.invoke(main, [
        "advise", "benchmark", "plan", "--db", db,
        "--protocol-id", "preflight-handoff", "--created-at", "2026-01-01T00:00:00Z",
        "--first-cutoff", "2026-01-01", "--until", "2026-01-29", "--out", str(protocol),
    ])
    assert planned.exit_code == 0, planned.output
    frozen_protocol = protocol.read_bytes()

    con = store.connect(db)
    con.execute("INSERT INTO deck_cards VALUES ('past', 0, 'side', 'Unresolved Card', 1)")
    con.close()
    blocked = runner.invoke(main, [
        "refresh", "card-coverage", "--db", db, "--benchmark-protocol", str(protocol),
    ])
    assert blocked.exit_code != 0
    assert "observed=Unresolved Card" in blocked.output
    assert protocol.read_bytes() == frozen_protocol

    con = store.connect(db)
    store.load_cards(con, [Card(name="Unresolved Card")])
    con.close()
    cleared = runner.invoke(main, [
        "refresh", "card-coverage", "--db", db, "--benchmark-protocol", str(protocol),
    ])
    assert cleared.exit_code == 0, cleared.output
    assert "cutoff=2026-01-01; rows=0; names=0; decks=0" in cleared.output
    assert protocol.read_bytes() == frozen_protocol
