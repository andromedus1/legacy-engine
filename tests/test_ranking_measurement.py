from __future__ import annotations

import pytest

from legacy_engine.advisory.ranking_measurement import (
    GroundingCellState,
    VariantRowMeasurement,
    RankingCellSource,
    grounding_cell_states,
    measure_lean_agency,
    measure_ranking_row,
    measure_variant_row,
    methodology_variant_specs,
    plan_path_to_grounding,
    rank_variant_rows,
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


class TestMethodologyVariants:
    def test_source_and_rate_policies_are_predeclared_and_outcome_blind(self):
        cells = [
            select_ranking_cell(
                "Deck", "A", 0.6,
                era=source("era", 1, 4, opponent="A"),
                fallback=source("ban-fallback", 12, 20, opponent="A"),
                ground_n=8,
            ),
            select_ranking_cell(
                "Deck", "B", 0.4,
                era=source("era", 7, 10, opponent="B"),
                fallback=source("ban-fallback", 2, 20, opponent="B"),
                ground_n=8,
            ),
        ]
        specs = {spec.id: spec for spec in methodology_variant_specs(8)}
        projections = {
            name: measure_variant_row(cells, spec=spec, top_k=1, cover_min=0.8)
            for name, spec in specs.items()
        }

        assert projections["raw"].adjusted_field_wr == pytest.approx(0.6 * 0.6 + 0.4 * 0.7)
        assert projections["ci-gated"].measured_coverage == 1.0
        assert projections["ban-scoped"].floor == cells[1].fallback.cell.p_shrunk
        assert projections["era-only"].floor == cells[1].era.cell.p_shrunk
        assert projections["ban-scoped"].floor != projections["era-only"].floor

    def test_ci_gated_projection_reproduces_canonical_row(self):
        cells = [
            select_ranking_cell(
                "Deck", opponent, share,
                era=source("era", wins, n, opponent=opponent),
                fallback=None, ground_n=8,
            )
            for opponent, share, wins, n in (("A", 0.7, 5, 10), ("B", 0.3, 2, 8))
        ]
        canonical = measure_ranking_row(
            "Deck", cells, top_k=1, cover_min=0.8, strict_common_sources={},
        )
        gated = measure_variant_row(
            cells, spec=methodology_variant_specs(8)[1], top_k=1, cover_min=0.8,
        )
        assert gated.adjusted_field_wr == canonical.adjusted_field_wr
        assert gated.floor == canonical.floor
        assert gated.agency == canonical.agency
        assert gated.measured_coverage == canonical.measured_coverage
        assert gated.top_k_measured == canonical.top_k_measured


class TestLeanAgency:
    def test_seeded_posterior_is_bounded_ordered_and_gate_independent(self):
        era = source("era", 4, 7, opponent="A")
        fallback = source("ban-fallback", 40, 80, opponent="A")
        at_seven = [select_ranking_cell(
            "Deck", "A", 1.0, era=era, fallback=fallback, ground_n=7,
        )]
        at_eight = [select_ranking_cell(
            "Deck", "A", 1.0, era=era, fallback=fallback, ground_n=8,
        )]

        first = measure_lean_agency(at_seven, draws=2_000, seed=17)
        second = measure_lean_agency(at_eight, draws=2_000, seed=17)
        assert first == second
        assert 0.0 <= first.ci_low <= first.q25 <= first.median <= first.ci_high <= 1.0
        assert first.resolved_share == 1.0
        assert first.imputed_share == 0.0

    def test_unresolved_opponent_remains_explicit_prior_mass(self):
        cells = [
            select_ranking_cell(
                "Deck", "Known", 0.6, era=source("era", 6, 10, opponent="Known"),
                fallback=None, ground_n=8,
            ),
            select_ranking_cell(
                "Deck", "Unknown", 0.4, era=None, fallback=None, ground_n=8,
            ),
        ]
        result = measure_lean_agency(cells, draws=1_000, seed=19)
        assert result.resolved_share == pytest.approx(0.6)
        assert result.imputed_share == pytest.approx(0.4)
        assert "weak prior" in result.source_policy

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"draws": 0}, "draws must be"),
            ({"temperature": 0.0}, "temperature must be"),
            ({"precision_scale": 0.0}, "precision_scale must be"),
        ],
    )
    def test_invalid_posterior_configuration_fails(self, kwargs, message):
        cell = select_ranking_cell(
            "Deck", "A", 1.0, era=source("era", 5, 10, opponent="A"),
            fallback=None, ground_n=8,
        )
        with pytest.raises(ValueError, match=message):
            measure_lean_agency([cell], **({"draws": 10} | kwargs))


class TestRankStability:
    @staticmethod
    def measurement(variant, score):
        return VariantRowMeasurement(
            variant=variant, adjusted_field_wr=score, floor=score, agency=score,
            measured_coverage=1.0, top_k_measured=True, resolved_cells=2,
        )

    def test_competition_ties_and_complete_span(self):
        variants = ("raw", "ci-gated", "ban-scoped", "era-only")
        rows = {
            "A": {variant: self.measurement(variant, 0.6) for variant in variants},
            "B": {variant: self.measurement(variant, 0.6) for variant in variants},
            "C": {variant: self.measurement(variant, 0.5) for variant in variants},
        }
        eligible = {label: {variant: True for variant in variants} for label in rows}
        result = rank_variant_rows(rows, eligible=eligible)
        assert result["A"].ranks == {variant: 1 for variant in variants}
        assert result["B"].ranks == {variant: 1 for variant in variants}
        assert result["C"].ranks == {variant: 3 for variant in variants}
        assert result["C"].rank_span == 0

    def test_missing_variant_never_becomes_partial_stability_range(self):
        variants = ("raw", "ci-gated", "ban-scoped", "era-only")
        rows = {"A": {variant: self.measurement(variant, 0.6) for variant in variants}}
        eligible = {"A": {variant: variant != "era-only" for variant in variants}}
        result = rank_variant_rows(rows, eligible=eligible)["A"]
        assert result.rank_min is None
        assert result.rank_max is None
        assert result.rank_span is None
        assert result.missing_variants == ("era-only",)
        assert result.reason == "not ranked by: era-only"


class TestPathToGrounding:
    def test_mandatory_top_k_precedes_efficient_coverage_actions(self):
        cells = (
            GroundingCellState(
                opponent="Top", field_share=0.35, era_n=2, fallback_n=4, measured=False,
            ),
            GroundingCellState(
                opponent="Covered", field_share=0.30, era_n=8, fallback_n=20, measured=True,
            ),
            GroundingCellState(
                opponent="Efficient", field_share=0.20, era_n=7, fallback_n=7, measured=False,
            ),
            GroundingCellState(
                opponent="Slow", field_share=0.15, era_n=0, fallback_n=0, measured=False,
            ),
        )
        path = plan_path_to_grounding(
            cells, ground_n=8, top_k=2, cover_min=0.8,
        )
        assert [action.opponent for action in path.actions] == ["Top", "Efficient"]
        assert path.actions[0].mandatory_top_k is True
        assert path.actions[0].additional_matches == 4
        assert path.actions[0].projected_source == "ban-fallback"
        assert path.actions[1].mandatory_top_k is False
        assert path.projected_coverage == pytest.approx(0.85)
        assert path.would_ground is True

        increments = {action.opponent: action.additional_matches for action in path.actions}
        replayed = tuple(
            cell.model_copy(update={
                "era_n": cell.era_n + increments.get(cell.opponent, 0),
                "fallback_n": cell.fallback_n + increments.get(cell.opponent, 0),
                "measured": (
                    max(cell.era_n, cell.fallback_n) + increments.get(cell.opponent, 0) >= 8
                ),
            })
            for cell in cells
        )
        assert plan_path_to_grounding(
            replayed, ground_n=8, top_k=2, cover_min=0.8,
        ).grounded is True

    def test_full_path_retains_remainder_and_total_shortfall(self):
        cells = tuple(
            GroundingCellState(
                opponent=f"Opp {index}", field_share=0.2, era_n=index,
                fallback_n=index, measured=False,
            )
            for index in range(5)
        )
        path = plan_path_to_grounding(
            cells, ground_n=8, top_k=5, cover_min=0.8, display_limit=3,
        )
        assert len(path.actions) == 5
        assert len(path.display_actions) == 3
        assert path.undisplayed_actions == 2
        assert path.total_additional_matches == sum(8 - index for index in range(5))
        assert path.would_ground is True

    def test_era_wins_projected_source_tie_and_grounded_row_needs_nothing(self):
        tied = GroundingCellState(
            opponent="Tie", field_share=1.0, era_n=0, fallback_n=0, measured=False,
            fallback_kind="full-corpus",
        )
        path = plan_path_to_grounding([tied], ground_n=8, top_k=1, cover_min=0.8)
        assert path.actions[0].projected_source == "era"

        grounded = GroundingCellState(
            opponent="Done", field_share=1.0, era_n=8, fallback_n=40, measured=True,
        )
        complete = plan_path_to_grounding(
            [grounded], ground_n=8, top_k=1, cover_min=0.8,
        )
        assert complete.grounded is True
        assert complete.actions == ()
        assert complete.reason == "already grounded"

    def test_typed_ledger_adapter_preserves_candidate_counts_and_source_kind(self):
        measurement = select_ranking_cell(
            "Deck", "A", 1.0,
            era=source("era", 2, 4, opponent="A"),
            fallback=source("full-corpus", 5, 10, opponent="A"),
            ground_n=8,
        )
        state = grounding_cell_states([measurement])[0]
        assert state == GroundingCellState(
            opponent="A", field_share=1.0, era_n=4, fallback_n=10,
            measured=True, fallback_kind="full-corpus",
        )

    @pytest.mark.parametrize(
        ("kwargs", "message"),
        [
            ({"ground_n": 0}, "ground_n"),
            ({"top_k": 0}, "top_k"),
            ({"cover_min": 1.1}, "cover_min"),
            ({"display_limit": 0}, "display_limit"),
        ],
    )
    def test_invalid_configuration_fails(self, kwargs, message):
        cell = GroundingCellState(
            opponent="A", field_share=1.0, era_n=8, fallback_n=8, measured=True,
        )
        defaults = {"ground_n": 8, "top_k": 1, "cover_min": 0.8, "display_limit": 3}
        with pytest.raises(ValueError, match=message):
            plan_path_to_grounding([cell], **(defaults | kwargs))
