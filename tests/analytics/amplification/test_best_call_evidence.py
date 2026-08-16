from __future__ import annotations

import copy
from datetime import UTC, date, datetime
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest

from legacy_engine.advisory.best_call_evidence import (
    build_report_evidence,
    canonical_json,
)
from legacy_engine.advisory.best_call_targets import ReportTarget
from legacy_engine.analytics.amplification import (
    AMPLIFICATION_METHOD_IDS,
    amplification_run_identity,
    pair_key,
)


def _script_module():
    path = Path(__file__).resolve().parents[3] / "scripts" / "refresh_best_call_ranking.py"
    spec = importlib.util.spec_from_file_location("exact_best_call_refresh", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _exact_target(interval_matrix, amplification_run) -> ReportTarget:
    return ReportTarget(
        target_id="current",
        label="Current",
        mode="current",
        mode_label="Current",
        data_until=None,
        effective_data_until=date(2026, 4, 1),
        knowledge_as_of=datetime(2026, 8, 1, tzinfo=UTC),
        field_since=date(2025, 11, 10),
        regime_card="Entomb",
        certificate_run_id=interval_matrix.certificate_run_id,
        amplification_run_id=amplification_run.run_id,
    )


def _patch_ranking_inputs(monkeypatch, module, interval_matrix, run, template_path=None):
    monkeypatch.setattr(module, "staged_split_parents", lambda: ())
    monkeypatch.setattr(module, "read_superarchetype_members", lambda _con: None)
    monkeypatch.setattr(
        module,
        "compute_blob",
        lambda *_args, **_kwargs: {
            "meta": {"current_4wk": "2026-03-01"},
            "arch": [{"subject": "A", "agency": 0.5}],
            "camps": [],
            "plans": [],
        },
    )
    monkeypatch.setattr(
        module, "build_interval_adaptive_matrix", lambda *_args, **_kwargs: interval_matrix
    )
    monkeypatch.setattr(
        module,
        "read_amplification_run",
        lambda _con, run_id: run if run_id == run.run_id else None,
    )
    monkeypatch.setattr(
        module,
        "_report_data_audit",
        lambda *_args, **_kwargs: SimpleNamespace(
            model_dump=lambda **_dump_kwargs: {"audit_sha256": "a" * 64}
        ),
    )
    if template_path is not None:
        template_path.write_text("<script>const D = __D_BLOB__;</script>")
        monkeypatch.setattr(module, "TEMPLATE_PATH", template_path)


class TestBestCallEvidenceProjection:
    def test_exact_run_projects_components_and_preserves_authority(
        self, interval_matrix, amplification_run
    ):
        authority = {"arch": [{"subject": "A", "agency": 0.5}], "plans": []}
        frozen = canonical_json(authority)

        result = build_report_evidence(
            interval_matrix, amplification_run, authority_payload=authority
        )

        assert result.status == "available"
        assert result.method_ids == AMPLIFICATION_METHOD_IDS
        assert result.amplification_run_id == amplification_run.run_id
        assert type(result).model_validate_json(result.model_dump_json()) == result
        assert canonical_json(authority) == frozen
        pair = result.pairs[pair_key("A", "B")]
        assert pair.interval_components
        assert len(pair.challengers) == len(AMPLIFICATION_METHOD_IDS)
        assert tuple(item.method_id for item in pair.challengers) == AMPLIFICATION_METHOD_IDS
        assert all(item.current_match_ids_sha256 for item in pair.challengers)
        assert pair.current_only.n + pair.added_history.n == pair.certified_expanded.n
        assert set(pair.current_only.component_ids) <= {
            item.component_id for item in pair.interval_components
        }

    def test_no_run_is_typed_not_assessed_with_six_named_slots(self, interval_matrix):
        result = build_report_evidence(
            interval_matrix, None, authority_payload={"ranking": ["A", "B"]}
        )
        assert result.status == "not-assessed"
        assert result.reasons == ("no exact amplification run requested",)
        assert all(
            pair.status == "not-assessed"
            and tuple(item.method_id for item in pair.challengers)
            == AMPLIFICATION_METHOD_IDS
            and all(item.served is None for item in pair.challengers)
            for pair in result.pairs.values()
        )

    def test_tampered_exact_identity_fails_closed(
        self, interval_matrix, amplification_run
    ):
        tampered = copy.deepcopy(amplification_run)
        tampered.corpus.corpus_id = "0" * 64
        with pytest.raises(ValueError):
            build_report_evidence(interval_matrix, tampered, authority_payload={})


class TestGeneratorExactRunComposition:
    def test_generator_reads_and_projects_the_requested_exact_run(
        self, tmp_path, monkeypatch, interval_matrix, amplification_run
    ):
        module = _script_module()
        database = tmp_path / "ranking.duckdb"
        con = duckdb.connect(database)
        con.execute("CREATE TABLE tournaments (date VARCHAR)")
        con.execute("INSERT INTO tournaments VALUES ('2026-03-31')")
        con.close()
        _patch_ranking_inputs(
            monkeypatch, module, interval_matrix, amplification_run, tmp_path / "template.html"
        )

        blob = module.generate_ranking(
            db_path=database,
            out_path=tmp_path / "ranking.html",
            target=_exact_target(interval_matrix, amplification_run),
        )

        assert blob["evidence"]["amplification_run_id"] == amplification_run.run_id
        assert blob["evidence"]["status"] == "available"
        assert len(blob["evidence"]["pairs"][pair_key("A", "B")]["challengers"]) == 6

    def test_mismatched_requested_run_preserves_the_last_good_page(
        self, tmp_path, monkeypatch, interval_matrix, amplification_run
    ):
        module = _script_module()
        database = tmp_path / "ranking.duckdb"
        con = duckdb.connect(database)
        con.execute("CREATE TABLE tournaments (date VARCHAR)")
        con.execute("INSERT INTO tournaments VALUES ('2026-03-31')")
        con.close()
        tampered = copy.deepcopy(amplification_run)
        tampered.corpus.corpus_id = "0" * 64
        _patch_ranking_inputs(
            monkeypatch, module, interval_matrix, tampered, tmp_path / "template.html"
        )
        output = tmp_path / "ranking.html"
        output.write_text("last-good")

        with pytest.raises(ValueError, match="differs"):
            module.generate_ranking(
                db_path=database,
                out_path=output,
                target=_exact_target(interval_matrix, amplification_run),
            )

        assert output.read_text() == "last-good"

    def test_valid_degraded_run_keeps_typed_reason_in_the_rendered_artifact(
        self, tmp_path, monkeypatch, interval_matrix, amplification_run
    ):
        module = _script_module()
        database = tmp_path / "ranking.duckdb"
        con = duckdb.connect(database)
        con.execute("CREATE TABLE tournaments (date VARCHAR)")
        con.execute("INSERT INTO tournaments VALUES ('2026-03-31')")
        con.close()
        degraded = copy.deepcopy(amplification_run)
        degraded.status = "degraded"
        degraded.reasons = ("guardrail <thin> support",)
        degraded.run_id = amplification_run_identity(degraded)
        _patch_ranking_inputs(monkeypatch, module, interval_matrix, degraded)

        output = tmp_path / "ranking.html"
        blob = module.generate_ranking(
            db_path=database,
            out_path=output,
            target=_exact_target(interval_matrix, degraded),
        )

        assert blob["evidence"]["status"] == "degraded"
        assert blob["evidence"]["reasons"] == ["guardrail <thin> support"]
        rendered = output.read_text()
        assert "guardrail <thin> support" not in rendered
        assert "guardrail \\u003cthin\\u003e support" in rendered
