"""Contracts for the shared production/evaluator ranking projection."""

from __future__ import annotations

import pytest

from legacy_engine.advisory.deck_ranking import rank_matchup_rows
from legacy_engine.advisory.field import build_custom_field
from legacy_engine.advisory.plan_borrowing import PlanBorrowingPrior
from legacy_engine.advisory.deck_ranking_projection import project_ranking_rows
from legacy_engine.advisory.ranking_measurement import RankingCellMeasurement, RankingCellSource
from legacy_engine.analytics.matchup import build_cell


def _measurement(
    subject: str,
    opponent: str,
    *,
    era: RankingCellSource | None = None,
    fallback: RankingCellSource | None = None,
) -> RankingCellMeasurement:
    selected = era or fallback
    return RankingCellMeasurement(
        subject=subject,
        opponent=opponent,
        field_share=1.0,
        era=era,
        fallback=fallback,
        selected_kind=selected.kind if selected else None,
        selected=selected,
        selection_reason="fixture",
        measured=bool(selected and selected.cell.n),
        concentration_warning=None,
    )


def _source(subject: str, opponent: str, wins: int, n: int, *, kind: str = "era", strength: float = 15):
    return RankingCellSource(
        kind=kind,
        since=None,
        cell=build_cell(
            subject, opponent, wins, n, prior_mean=0.7,
            prior_strength=strength,
        ),
    )


def test_default_projection_matches_rank_kernel_and_preserves_ledger() -> None:
    era = _source("A", "B", 1, 3, strength=20)
    fallback = _source("A", "B", 3, 4, kind="ban-fallback", strength=5)
    measurement = _measurement("A", "B", era=era, fallback=fallback)
    direct = rank_matchup_rows(
        {"A": [measurement]}, {"A": 0.4, "B": 0.6}, draws=100, seed=11,
    )
    projected = project_ranking_rows(
        {"A": [measurement]}, {"A": 0.4, "B": 0.6}, draws=100, seed=11,
    )
    direct_cells = {
        cell["opponent"]: cell for cell in direct["rows"]["A"]["cells"]
    }
    projected_cells = {
        cell["opponent"]: cell for cell in projected["rows"]["A"]["cells"]
    }
    for opponent in direct_cells:
        for key in ("mean", "ci_low", "ci_high", "wins", "n", "prior_strength", "source_kind"):
            assert projected_cells[opponent][key] == direct_cells[opponent][key]
    assert projected_cells["B"]["source_identity"]["kind"] == "era"
    assert measurement.era.cell.prior_strength == 20


def test_prior_scale_changes_only_prior_weight_and_scales_absent_named_prior() -> None:
    source = _source("A", "B", 1, 3, strength=20)
    rows = {"A": [_measurement("A", "B", era=source)]}
    baseline = project_ranking_rows(rows, {"A": 0.3, "B": 0.7}, draws=50, seed=7)
    lighter = project_ranking_rows(
        rows, {"A": 0.3, "B": 0.7}, prior_scale=0.5, draws=50, seed=7,
    )
    base_cells = {cell["opponent"]: cell for cell in baseline["rows"]["A"]["cells"]}
    light_cells = {cell["opponent"]: cell for cell in lighter["rows"]["A"]["cells"]}
    assert base_cells["B"]["wins"] == light_cells["B"]["wins"] == 1
    assert base_cells["B"]["n"] == light_cells["B"]["n"] == 3
    assert base_cells["B"]["prior_strength_original"] == 20
    assert light_cells["B"]["prior_strength_effective"] == 10
    assert light_cells["B"]["prior_contribution_fraction"] == pytest.approx(10 / 13)
    assert light_cells["B"]["mean"] != base_cells["B"]["mean"]
    assert light_cells["A"]["prior_strength_original"] == 2
    assert light_cells["A"]["prior_strength_effective"] == 1


def test_interval_override_is_resolved_before_kernel_for_every_scale() -> None:
    era = _source("A", "B", 0, 8)
    override = build_cell("A", "B", 8, 8, prior_mean=0.5, prior_strength=15)
    projected = project_ranking_rows(
        {"A": [_measurement("A", "B", era=era)]},
        {"A": 0.5, "B": 0.5},
        cell_overrides={("A", "B"): override},
        override_sources={("A", "B"): "localized-interval"},
        draws=30,
        seed=3,
    )
    cell = next(cell for cell in projected["rows"]["A"]["cells"] if cell["opponent"] == "B")
    assert cell["source_kind"] == "localized-interval"
    assert cell["wins"] == 8 and cell["n"] == 8
    assert cell["mean"] == pytest.approx((15 * 0.5 + 8) / 23)


def test_prior_overlay_preserves_selected_observations_and_source_identity() -> None:
    source = _source("A", "B", 1, 3, strength=20)
    prior = PlanBorrowingPrior(
        mean=0.9, strength=4, donor_wins=3, donor_n=4, donor_events=2,
        donor_opponents=2, history_donor_n=1, source="plan donor",
        selection_sha256="selection", corpus_id="corpus",
    )
    projected = project_ranking_rows(
        {"A": [_measurement("A", "B", era=source)]},
        {"A": 0.5, "B": 0.5}, prior_overrides={("A", "B"): prior}, draws=30, seed=3,
    )
    cell = next(cell for cell in projected["rows"]["A"]["cells"] if cell["opponent"] == "B")
    assert (cell["wins"], cell["n"]) == (1, 3)
    assert cell["source_identity"]["kind"] == "era"
    assert cell["selected_prior_strength"] == 20
    assert cell["borrowed_prior"]["selection_sha256"] == "selection"
    assert cell["mean"] == pytest.approx((1 + 4 * 0.9) / 7)


def test_prior_overlay_can_replace_absent_cell_weak_prior_without_observations() -> None:
    prior = PlanBorrowingPrior(
        mean=0.8, strength=5, donor_wins=4, donor_n=5, donor_events=3,
        donor_opponents=2, history_donor_n=2, source="plan donor",
        selection_sha256="selection", corpus_id="corpus",
    )
    projected = project_ranking_rows(
        {"A": []}, {"A": 0.5, "B": 0.5},
        prior_overrides={("A", "B"): prior}, draws=30, seed=3,
    )
    cell = next(cell for cell in projected["rows"]["A"]["cells"] if cell["opponent"] == "B")
    assert (cell["wins"], cell["n"]) == (0, 0)
    assert cell["source_kind"] == "missing"
    assert cell["mean"] == pytest.approx(0.8)


def test_field_override_reweights_cells_without_changing_global_candidate_presence() -> None:
    source = _source("Absent locally", "Room", 9, 10, strength=2)
    scenario = build_custom_field(
        {"Room": 1.0}, known_archetypes=frozenset({"Room"}), counts={"Room": 20}
    )
    projected = project_ranking_rows(
        {"Absent locally": [_measurement("Absent locally", "Room", era=source)]},
        {"Other global deck": 1.0},
        field_override=scenario,
        candidate_presence={"Absent locally": 0.25},
        draws=30,
        seed=3,
    )

    row = projected["rows"]["Absent locally"]
    cell = row["cells"][0]
    assert row["eligible"] is True
    assert row["subject_field_share"] == pytest.approx(0.25)
    assert projected["field"]["shares"] == {"Room": 1.0}
    assert projected["global_field"]["shares"] == {"Other global deck": 1.0}
    assert projected["field_override"]["counts"] == {"Room": 20}
    assert cell["field_share"] == pytest.approx(1.0)


@pytest.mark.parametrize("scale", (0, -1, float("inf"), float("nan")))
def test_invalid_prior_scale_fails_loudly(scale: float) -> None:
    with pytest.raises(ValueError, match="prior_scale"):
        project_ranking_rows({"A": []}, {"A": 1.0}, prior_scale=scale, draws=1)
