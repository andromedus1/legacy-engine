from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from legacy_engine.advisory.ranking_benchmark import (
    atomic_write_canonical,
    content_sha256,
)
from legacy_engine.advisory.recurrent_validation import GateClause, PromotionAssessment
from legacy_engine.cli import main
from legacy_engine.ingestion import store
from legacy_engine.workflows.ranking_benchmark import build_origin_snapshot
from advisory.recurrent_validation_helpers import (
    BASE_PROTOCOL_PATH,
    base_protocol,
    forecast,
    future_rows,
    protocol,
    refit_stages,
)


def _build_db(path: Path) -> Path:
    con = store.connect(path)
    store.init_schema(con)
    con.executemany("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        ("Alpha Signal", "{1}", 1.0, "Artifact", "", "", "", "normal", False, None, None),
        ("Beta Signal", "{1}", 1.0, "Artifact", "", "", "", "normal", False, None, None),
    ])
    con.executemany("INSERT INTO tournaments VALUES (?, ?, ?, ?, ?, ?, ?)", [
        ("past", "Past", "2026-08-01", "past-uri", "Legacy", "fixture", "online"),
        ("future", "Future", "2026-08-20", "future-uri", "Legacy", "fixture", "online"),
    ])
    for event in ("past", "future"):
        con.executemany("INSERT INTO decks VALUES (?, ?, ?, ?, ?, ?)", [
            (event, 0, f"{event}-a", "1st", None, None),
            (event, 1, f"{event}-b", "2nd", None, None),
        ])
        con.executemany("INSERT INTO deck_cards VALUES (?, ?, ?, ?, ?)", [
            (event, 0, "main", "Alpha Signal", 4),
            (event, 1, "main", "Beta Signal", 4),
        ])
        con.execute(
            "INSERT INTO rounds VALUES (?, 0, ?, ?, '2-0')",
            [event, f"{event}-a", f"{event}-b"],
        )
    con.close()
    return path


def _pin_rules(tmp_path, monkeypatch):
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


def test_recurrent_validation_cli_plan_freeze_evaluate_and_aggregate(tmp_path, monkeypatch):
    _pin_rules(tmp_path, monkeypatch)
    value = protocol(small=True)
    protocol_path = tmp_path / "protocol.json"
    atomic_write_canonical(protocol_path, value)
    artifact_root = tmp_path / "artifacts"
    runner = CliRunner()
    planned = runner.invoke(main, [
        "advise", "recurrent-validation", "plan",
        "--protocol", str(protocol_path),
        "--base-protocol", str(BASE_PROTOCOL_PATH),
        "--artifact-root", str(artifact_root),
    ])
    assert planned.exit_code == 0, planned.output
    assert "// recurrent protocol:" in planned.output

    source = _build_db(tmp_path / "source.duckdb")
    snapshot = tmp_path / "snapshot.duckdb"
    base = base_protocol()
    manifest = build_origin_snapshot(
        source,
        snapshot,
        fold=base.planned_folds[0],
        protocol_hash=content_sha256(value.model_dump(mode="json")),
        taxonomy_mode=base.taxonomy_mode,
        ban_events=base.ban_events_as_of,
        card_metadata_policy=base.card_metadata,
    )
    manifest_path = tmp_path / "snapshot-manifest.json"
    stages_path = tmp_path / "stages.json"
    forecast_path = tmp_path / "forecast.json"
    atomic_write_canonical(manifest_path, manifest)
    snapshot_sha = content_sha256(manifest.model_dump(mode="json"))
    atomic_write_canonical(
        stages_path,
        {"stages": [item.model_dump(mode="json") for item in refit_stages(
            value, snapshot_sha, max_outcome_date="2026-08-01"
        )]},
    )
    atomic_write_canonical(forecast_path, forecast(value))
    frozen = runner.invoke(main, [
        "advise", "recurrent-validation", "freeze",
        "--protocol", str(protocol_path),
        "--base-protocol", str(BASE_PROTOCOL_PATH),
        "--fold", value.folds[0].fold_id,
        "--snapshot-db", str(snapshot),
        "--snapshot-manifest", str(manifest_path),
        "--stages", str(stages_path),
        "--forecast", str(forecast_path),
        "--code-commit", "fixture-commit",
        "--artifact-root", str(artifact_root),
    ])
    assert frozen.exit_code == 0, frozen.output
    origin_path = next((artifact_root / "origins").glob("*/origin.json"))

    cases_path = tmp_path / "cases.json"
    counts_path = tmp_path / "counts.json"
    cases_path.write_text(json.dumps(future_rows(value)))
    counts_path.write_text(json.dumps({"a": 1, "b": 1}))
    evaluated = runner.invoke(main, [
        "advise", "recurrent-validation", "evaluate",
        "--protocol", str(protocol_path),
        "--base-protocol", str(BASE_PROTOCOL_PATH),
        "--origin", str(origin_path),
        "--cases", str(cases_path),
        "--field-counts", str(counts_path),
        "--artifact-root", str(artifact_root),
    ])
    assert evaluated.exit_code == 0, evaluated.output
    evaluation_path = next((artifact_root / "evaluations").glob("*/evaluation.json"))

    aggregated = runner.invoke(main, [
        "advise", "recurrent-validation", "aggregate",
        "--protocol", str(protocol_path),
        "--base-protocol", str(BASE_PROTOCOL_PATH),
        "--origin", str(origin_path),
        "--evaluation", str(evaluation_path),
        "--artifact-root", str(artifact_root),
    ])
    assert aggregated.exit_code == 0, aggregated.output
    assert "// recurrent bundle:" in aggregated.output
    assert len(list((artifact_root / "bundles").glob("*/bundle.json"))) == 1


def test_recurrent_cli_has_no_actuator_and_proposal_is_inert(tmp_path):
    help_result = CliRunner().invoke(main, ["advise", "recurrent-validation", "--help"])
    assert help_result.exit_code == 0
    for command in ("plan", "freeze", "evaluate", "aggregate", "proposal"):
        assert command in help_result.output
    assert " apply" not in help_result.output
    assert " promote" not in help_result.output

    candidate_config = content_sha256({"candidate": "recurrent-expanded-v1"})
    assessment = PromotionAssessment(
        protocol_sha256=content_sha256(protocol(small=True).model_dump(mode="json")),
        candidate_id="recurrent-expanded-v1",
        candidate_config_sha256=candidate_config,
        comparator_ids=("current-only-v1",),
        origin_evaluation_ids=("fixture",),
        clauses=(GateClause(
            clause_id="fixture-pass", comparator_id="current-only-v1", metric="log_loss",
            estimate=-0.1, lower_bound=-0.1, upper_bound=-0.1, threshold=0.02, status="pass",
        ),),
        useful_coverage=True,
        predictive_non_degradation=True,
        interval_non_degradation=True,
        decision_non_degradation=True,
        status="promotable",
    )
    assessment_path = tmp_path / "assessment.json"
    atomic_write_canonical(assessment_path, assessment)
    result = CliRunner().invoke(main, [
        "advise", "recurrent-validation", "proposal",
        "--assessment", str(assessment_path),
        "--target-config-version", "recurrent-production-v2",
        "--artifact-root", str(tmp_path / "artifacts"),
    ])
    assert result.exit_code == 0, result.output
    assert "operator review required" in result.output
    assert len(list((tmp_path / "artifacts" / "proposals").glob("*/proposal.json"))) == 1


def test_existing_benchmark_cli_surface_remains_available():
    result = CliRunner().invoke(main, ["advise", "benchmark", "--help"])
    assert result.exit_code == 0
    assert "plan" in result.output and "freeze" in result.output and "evaluate" in result.output
