from __future__ import annotations

from pathlib import Path

import pytest

from legacy_engine.ingestion.card_coverage import CardCoverageReport
from legacy_engine.models.card import CardAliasManifest
from legacy_engine.ingestion.releases import SetRelease
from legacy_engine.workflows.decision_refresh import (
    CampApplyResult,
    EraRunResult,
    RefreshStepStatus,
    SourceRefreshResult,
    RankingUtilitySummary,
    decision_refresh_audit_lines,
    run_decision_refresh,
    validate_ranking_utility,
)


class RecordingPorts:
    def __init__(self, *, fail_at: str | None = None, degrade_sources: bool = False):
        self.calls: list[str] = []
        self.fail_at = fail_at
        self.degrade_sources = degrade_sources

    def _record(self, name: str):
        self.calls.append(name)
        if self.fail_at == name:
            raise RuntimeError(f"{name} broke")

    def refresh_sources(self, db_path: Path):
        self._record("sources")
        return SourceRefreshResult(
            new_card_names=frozenset({"New Card"}),
            upcoming_releases=("up: Upcoming",),
            recent_releases=("new: Recent",),
            recent_release_records=(SetRelease(
                code="new", name="Recent", released_at="2026-08-10",
            ),),
            release_scan_reason="scan offline" if self.degrade_sources else None,
            alias_manifest=(
                CardAliasManifest(
                    source_updated_at="2026-08-10T00:00:00Z",
                    built_at="2026-08-10T01:00:00Z",
                    release_codes=("eoe",),
                    alias_count=10,
                    ambiguous_key_count=0,
                ) if self.degrade_sources else None
            ),
            summary="sources current",
        )

    def reconcile_cards(self, db_path: Path, source_result: SourceRefreshResult):
        self._record("card_coverage")
        assert source_result.new_card_names == frozenset({"New Card"})
        return CardCoverageReport(
            distinct_names=2,
            affected_decks=1,
            alias_snapshot_degraded=source_result.alias_snapshot_reason is not None,
            alias_snapshot_reason=source_result.alias_snapshot_reason,
        )

    def label(self, db_path: Path):
        self._record("label")
        return 3

    def apply_staged_camps(self, db_path: Path):
        self._record("staged_camps")
        return CampApplyResult(parents=("A", "B"), labeled=2, incrementally_assigned=1)

    def run_eras(self, db_path: Path):
        self._record("eras")
        return EraRunResult(entities=4, alarms=("possible change",))

    def write_ranking(self, db_path: Path, out_path: Path):
        self._record("ranking")
        out_path.write_text("stable ranking")


class TestDecisionRefresh:
    def test_usefulness_contract_requires_practical_call_to_lead_status_ranking(self):
        with pytest.raises(ValueError, match="does not lead the practical ranking"):
            validate_ranking_utility(RankingUtilitySummary(
                observed_field_n=10, effective_field_n=10, prior_strength=0,
                affected_clamp_count=0, supported_rows=2, transition_prior_rows=0,
                grounded_rows=0, practical_call="Later", proof_grade_call=None,
                rendered_shortlist_rows=0, status="degraded",
                practical_ranked_actions=("First", "Later"),
            ))

    def test_usefulness_contract_rejects_useful_status_with_ungrounded_support(self):
        with pytest.raises(ValueError, match="unsupported grounded"):
            validate_ranking_utility(RankingUtilitySummary(
                observed_field_n=10, effective_field_n=10, prior_strength=0,
                affected_clamp_count=0, supported_rows=2, transition_prior_rows=0,
                grounded_rows=1, practical_call="First", proof_grade_call=None,
                rendered_shortlist_rows=1, status="useful",
                practical_ranked_actions=("First",),
            ))

    def test_unavailable_utility_degrades_but_keeps_written_artifact(self, tmp_path):
        ports = RecordingPorts()
        unavailable = RankingUtilitySummary(
            observed_field_n=0, effective_field_n=0, prior_strength=0,
            affected_clamp_count=0, supported_rows=0, transition_prior_rows=0,
            grounded_rows=0, practical_call=None, proof_grade_call=None,
            rendered_shortlist_rows=0, status="unavailable",
            reasons=("no supported rows",),
        )

        def write_ranking(db_path, out_path):
            ports._record("ranking")
            out_path.write_text("degraded ranking")
            return unavailable

        ports.write_ranking = write_ranking
        result = run_decision_refresh(
            ports, db_path=tmp_path / "tiny.duckdb", out_path=tmp_path / "ranking.html",
        )
        assert result.steps[-1].status is RefreshStepStatus.DEGRADED
        assert result.ranking_output == str(tmp_path / "ranking.html")
        assert result.ranking_utility == unavailable
    def test_usefulness_contract_rejects_supported_rows_without_practical_call(self):
        with pytest.raises(ValueError, match="supported rows but no practical call"):
            validate_ranking_utility(RankingUtilitySummary(
                observed_field_n=10, effective_field_n=10, prior_strength=0,
                affected_clamp_count=0, supported_rows=1, transition_prior_rows=0,
                grounded_rows=0, practical_call=None, proof_grade_call=None,
                rendered_shortlist_rows=0, status="unavailable",
            ))

    def test_usefulness_contract_accepts_degraded_but_actionable_summary(self):
        summary = RankingUtilitySummary(
            observed_field_n=26, effective_field_n=500, prior_strength=474,
            affected_clamp_count=2, supported_rows=4, transition_prior_rows=1,
            grounded_rows=0, practical_call="Control", proof_grade_call=None,
            rendered_shortlist_rows=0, status="degraded",
            reasons=("thin evidence",), practical_ranked_actions=("Control", "Tempo"),
        )
        validate_ranking_utility(summary)

    def test_runs_exact_order_and_writes_ranking_last_to_explicit_paths(self, tmp_path):
        ports = RecordingPorts()
        db_path = tmp_path / "tiny.duckdb"
        db_path.touch()
        out_path = tmp_path / "ranking.html"

        result = run_decision_refresh(ports, db_path=db_path, out_path=out_path)

        assert ports.calls == ["sources", "card_coverage", "label", "staged_camps", "eras", "ranking"]
        assert all(step.status is RefreshStepStatus.COMPLETED for step in result.steps)
        assert out_path.read_text() == "stable ranking"
        assert result.ranking_output == str(out_path)
        assert result.format_awareness.recent_releases == ("new: Recent",)
        assert result.source_observation is not None
        assert result.source_observation.new_card_names == frozenset({"New Card"})
        assert result.steps[0].status is RefreshStepStatus.COMPLETED
        assert result.format_awareness.era_alarms == ("possible change",)

    def test_required_failure_marks_all_dependents_not_run_and_preserves_last_good_output(self, tmp_path):
        ports = RecordingPorts(fail_at="label")
        out_path = tmp_path / "ranking.html"
        out_path.write_text("last good")

        result = run_decision_refresh(ports, db_path=tmp_path / "db.duckdb", out_path=out_path)

        assert ports.calls == ["sources", "card_coverage", "label"]
        assert [step.status for step in result.steps] == [
            RefreshStepStatus.COMPLETED,
            RefreshStepStatus.COMPLETED,
            RefreshStepStatus.FAILED,
            RefreshStepStatus.NOT_RUN,
            RefreshStepStatus.NOT_RUN,
            RefreshStepStatus.NOT_RUN,
        ]
        assert out_path.read_text() == "last good"
        assert result.ranking_output is None
        lines = decision_refresh_audit_lines(result)
        assert any("label — failed — label broke" in line for line in lines)
        assert any("ranking — not_run" in line for line in lines)

    def test_advisory_source_failure_degrades_but_continues(self, tmp_path):
        ports = RecordingPorts(degrade_sources=True)
        result = run_decision_refresh(
            ports, db_path=tmp_path / "db.duckdb", out_path=tmp_path / "ranking.html",
        )
        assert result.steps[0].status is RefreshStepStatus.DEGRADED
        assert result.card_coverage.alias_snapshot_degraded
        assert "currency uncertain" in result.card_coverage.alias_snapshot_reason
        assert "retained last-good aliases" in result.card_coverage.alias_snapshot_reason
        assert result.steps[-1].status is RefreshStepStatus.COMPLETED

    def test_source_failure_still_emits_real_operator_confirmed_ban_ledger(self, tmp_path):
        ports = RecordingPorts(fail_at="sources")

        result = run_decision_refresh(
            ports, db_path=tmp_path / "db.duckdb", out_path=tmp_path / "ranking.html",
        )

        line = next(line for line in decision_refresh_audit_lines(result) if "B&R ledger" in line)
        assert "unknown" not in line
        assert "operator-confirmed" in line
        assert result.format_awareness.latest_registered_ban_date is not None
        assert result.format_awareness.latest_registered_ban_card is not None
