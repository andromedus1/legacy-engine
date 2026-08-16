from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path

import duckdb
import pytest

from legacy_engine.advisory.ranking_benchmark import content_sha256
from legacy_engine.advisory.recurrent_validation import (
    FrozenJointDraws,
    OriginForecastPayload,
    RefitStageArtifact,
    seal_recurrent_origin,
)
from legacy_engine.ingestion import store
from legacy_engine.workflows.recurrent_validation import (
    OriginRefitExecutor,
    OriginStageRequest,
    refit_and_freeze_origin,
)
from advisory.recurrent_validation_helpers import (
    base_protocol,
    forecast,
    origin,
    protocol,
    refit_stages,
)


class _FixtureExecutor(OriginRefitExecutor):
    def __init__(self, value, *, leak_date: str | None = None, drift_stage: str | None = None):
        self.value = value
        self.leak_date = leak_date
        self.drift_stage = drift_stage
        self.calls: list[str] = []

    def run_stage(self, request: OriginStageRequest) -> RefitStageArtifact:
        self.calls.append(request.stage)
        con = duckdb.connect(request.snapshot_db, read_only=True)
        try:
            events = con.execute("SELECT id, substr(date,1,10) FROM tournaments ORDER BY 1").fetchall()
        finally:
            con.close()
        max_date = max((row[1] for row in events), default=None)
        if self.leak_date and request.stage == "certification":
            max_date = self.leak_date
        output = content_sha256(
            {"stage": request.stage, "prior": request.prior_output_sha256, "events": events}
        )
        pair_sha = content_sha256(("a\0b", "b\0a"))
        return RefitStageArtifact(
            stage=request.stage,
            run_id=f"{request.stage}-{output}",
            input_sha256=(
                "1" * 64 if request.stage == self.drift_stage else request.prior_output_sha256
            ),
            output_sha256=output,
            config_sha256=request.expected_config_sha256,
            data_until=request.fold.data_until,
            knowledge_as_of=request.fold.knowledge_as_of,
            max_outcome_date=(
                None if request.stage in {"discovery", "structure"} else max_date
            ),
            outcome_ids_sha256=content_sha256(tuple(row[0] for row in events)),
            pair_universe_sha256=(
                pair_sha if request.stage in {"interval", "amplification"} else None
            ),
        )

    def freeze_forecast(self, snapshot_db, *, protocol, fold, stages) -> OriginForecastPayload:
        assert self.calls == [
            "discovery", "certification", "interval", "structure", "amplification"
        ]
        assert Path(snapshot_db).is_file()
        return forecast(protocol)


def _source_db(path: Path, *, future_result: str = "2-0") -> Path:
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
            "INSERT INTO rounds VALUES (?, 0, ?, ?, ?)",
            [event, f"{event}-a", f"{event}-b", "2-0" if event == "past" else future_result],
        )
    con.close()
    return path


@pytest.fixture
def pinned_rules(tmp_path, monkeypatch):
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


def test_real_file_backed_origin_runs_the_full_typed_chain_and_seals(pinned_rules, tmp_path):
    value = protocol()
    executor = _FixtureExecutor(value)
    artifact = refit_and_freeze_origin(
        _source_db(tmp_path / "source.duckdb"),
        protocol=value,
        base_protocol=base_protocol(),
        fold=value.folds[0],
        executor=executor,
        artifact_root=tmp_path / "artifacts",
        code_commit="fixture-commit",
    )
    assert executor.calls == [
        "discovery", "certification", "interval", "structure", "amplification"
    ]
    assert artifact.origin.manifest.max_outcome_date == "2026-08-01"
    assert artifact.origin.manifest.status == "complete"
    assert (tmp_path / "artifacts" / "origins" / content_sha256(
        artifact.origin.model_dump(mode="json")
    ) / "origin.json").is_file()


def test_future_source_mutation_cannot_change_sealed_origin_bytes(pinned_rules, tmp_path):
    value = protocol()
    first = refit_and_freeze_origin(
        _source_db(tmp_path / "one.duckdb", future_result="2-0"),
        protocol=value,
        base_protocol=base_protocol(),
        fold=value.folds[0],
        executor=_FixtureExecutor(value),
        artifact_root=tmp_path / "one-artifacts",
        code_commit="fixture-commit",
    )
    second = refit_and_freeze_origin(
        _source_db(tmp_path / "two.duckdb", future_result="0-2"),
        protocol=value,
        base_protocol=base_protocol(),
        fold=value.folds[0],
        executor=_FixtureExecutor(value),
        artifact_root=tmp_path / "two-artifacts",
        code_commit="fixture-commit",
    )
    assert first.origin.model_dump_json() == second.origin.model_dump_json()


def test_cutoff_leakage_and_disconnected_stage_identity_fail_before_seal(pinned_rules, tmp_path):
    value = protocol()
    source = _source_db(tmp_path / "source.duckdb")
    with pytest.raises(ValueError, match="at or after the origin"):
        refit_and_freeze_origin(
            source,
            protocol=value,
            base_protocol=base_protocol(),
            fold=value.folds[0],
            executor=_FixtureExecutor(value, leak_date=value.folds[0].data_until),
            artifact_root=tmp_path / "leak-artifacts",
            code_commit="fixture-commit",
        )
    with pytest.raises(ValueError, match="disconnected"):
        refit_and_freeze_origin(
            source,
            protocol=value,
            base_protocol=base_protocol(),
            fold=value.folds[0],
            executor=_FixtureExecutor(value, drift_stage="interval"),
            artifact_root=tmp_path / "drift-artifacts",
            code_commit="fixture-commit",
        )


def test_seal_rejects_discovery_outcomes_pair_drift_and_draw_tampering():
    value = protocol(small=True)
    snapshot = content_sha256({"snapshot": "identity-test"})
    stages = list(refit_stages(
        value,
        snapshot,
        max_outcome_date=(date.fromisoformat(value.folds[0].data_until) - timedelta(days=1)).isoformat(),
    ))
    stages[0] = stages[0].model_copy(update={"outcome_columns_accessed": ("result",)})
    with pytest.raises(ValueError, match="discovery accessed"):
        seal_recurrent_origin(
            value, value.folds[0], snapshot_manifest_sha256=snapshot,
            stages=stages, forecast=forecast(value), code_commit="fixture",
        )
    stages = list(refit_stages(value, snapshot, max_outcome_date="2026-08-01"))
    stages[-1] = stages[-1].model_copy(update={"pair_universe_sha256": "1" * 64})
    with pytest.raises(ValueError, match="pair universes differ"):
        seal_recurrent_origin(
            value, value.folds[0], snapshot_manifest_sha256=snapshot,
            stages=stages, forecast=forecast(value), code_commit="fixture",
        )
    sealed = origin(value)
    payload = sealed.joint_draws.model_dump(mode="json")
    payload["series"][0]["probabilities"][0] = 0.123456
    with pytest.raises(ValueError, match="draw value digest"):
        FrozenJointDraws.model_validate(payload)
