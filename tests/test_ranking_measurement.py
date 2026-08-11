from __future__ import annotations

import pytest

from legacy_engine.advisory.ranking_measurement import (
    RankingCellSource,
    measure_ranking_row,
    select_ranking_cell,
)
from legacy_engine.analytics.matchup import build_cell
from legacy_engine.analytics.eras.consume import PairWindow, clamp_pair_window


def source(kind, wins, n, *, since=None, concentration=None, opponent="Opp"):
    return RankingCellSource(
        kind=kind,
        since=since,
        cell=build_cell("Deck", opponent, wins, n, concentration=concentration),
        pair_window=PairWindow(
            subject="Deck", opponent=opponent, requested_since=since,
            subject_since=None, opponent_since=None, effective_since=since,
            clamped=False, reason="test fixture",
        ),
    )


class TestSelectRankingCell:
    def test_truth_table_labels_real_source_kinds(self):
        era = source("era", 2, 4, since="2026-05-01")
        fallback = source("ban-fallback", 10, 20, since="2026-01-01")
        selected = select_ranking_cell(
            "Deck", "Opp", 0.4, era=era, fallback=fallback, ground_n=8,
        )
        assert selected.selected_kind == "ban-fallback"
        assert selected.measured is True

        absent_era = select_ranking_cell(
            "Deck", "Opp", 0.4, era=None, fallback=source("full-corpus", 2, 4), ground_n=8,
        )
        assert absent_era.selected_kind == "full-corpus"
        assert "era cell absent" in absent_era.selection_reason

        missing = select_ranking_cell(
            "Deck", "Opp", 0.4, era=None, fallback=None, ground_n=8,
        )
        assert missing.selected is None
        assert missing.selection_reason == "no era or fallback cell"

    def test_invalid_gate_fails(self):
        with pytest.raises(ValueError, match="ground_n must be >= 1"):
            select_ranking_cell("Deck", "Opp", 1.0, era=None, fallback=None, ground_n=0)


class TestMeasureRankingRow:
    def test_weighting_grounding_floor_observability_and_common_diagnostic(self):
        cells = [
            select_ranking_cell(
                "Deck", "A", 0.6, era=source("era", 18, 30, since="2026-03-01", opponent="A"),
                fallback=None, ground_n=8,
            ),
            select_ranking_cell(
                "Deck", "B", 0.4, era=source("era", 2, 10, since="2026-04-01", opponent="B"),
                fallback=None, ground_n=8,
            ),
        ]
        common = {
            "A": source("strict-common-era", 12, 30, since="2026-04-01", opponent="A"),
            "B": source("strict-common-era", 6, 10, since="2026-04-01", opponent="B"),
        }
        row = measure_ranking_row(
            "Deck", cells, top_k=1, cover_min=0.8, strict_common_sources=common,
        )
        assert row.reconciliation.parity_delta == 0.0
        assert row.reconciliation.headline_eligible is True
        assert row.adjusted_field_wr == pytest.approx(
            0.6 * cells[0].selected.cell.p_shrunk + 0.4 * cells[1].selected.cell.p_shrunk
        )
        assert row.reconciliation.strict_common_since == "2026-04-01"
        assert row.reconciliation.strict_common_contributing_coverage == 1.0
        assert row.reconciliation.strict_common_coverage == pytest.approx(0.6)
        assert row.reconciliation.estimator_delta is not None
        assert row.measured_coverage == 1.0
        assert row.grounded is True
        assert row.floor_opponent == "B"
        assert row.floor_observability.opponents_n10 == 2
        assert row.floor_observability.opponents_display_grade == 1
        assert row.floor_observability.display_grade_field_coverage == pytest.approx(0.6)

    def test_unobserved_floor_names_missing_evidence(self):
        cell = select_ranking_cell(
            "Deck", "A", 1.0, era=source("era", 2, 8, opponent="A"), fallback=None, ground_n=8,
        )
        row = measure_ranking_row(
            "Deck", [cell], top_k=1, cover_min=0.8, strict_common_sources={},
        )
        assert row.floor_observability.floor_observed is False
        assert "absence of bad cells" in row.floor_observability.reason

    def test_invalid_selected_pair_window_suppresses_headline(self):
        invalid = source("era", 6, 10, since="2026-04-01").model_copy(update={
            "pair_window": clamp_pair_window(
                "Other", "Opp", subject_since="2026-04-01", opponent_since=None,
            )
        })
        cell = select_ranking_cell(
            "Deck", "Opp", 1.0, era=invalid, fallback=None, ground_n=8,
        )
        row = measure_ranking_row(
            "Deck", [cell], top_k=1, cover_min=0.8, strict_common_sources={},
        )
        assert row.adjusted_field_wr is None
        assert row.reconciliation.headline_eligible is False
        assert "pair-window provenance" in row.reconciliation.reason

    def test_null_common_estimate_retains_explicit_start_and_zero_coverages(self):
        cell = select_ranking_cell(
            "Deck", "Opp", 1.0, era=source("era", 6, 10), fallback=None, ground_n=8,
        )
        row = measure_ranking_row(
            "Deck", [cell], top_k=1, cover_min=0.8, strict_common_sources={},
            strict_common_since="2026-07-01",
        )
        assert row.reconciliation.strict_common is None
        assert row.reconciliation.strict_common_since == "2026-07-01"
        assert row.reconciliation.strict_common_contributing_coverage == 0.0
        assert row.reconciliation.strict_common_coverage == 0.0
