from __future__ import annotations

import json

from legacy_engine.advisory.ranking_benchmark import (
    ESTIMATOR_REGISTRY,
    BenchmarkFold,
    BenchmarkProtocol,
    EvaluationSupport,
    FrozenMatchupPrediction,
    FrozenOriginPredictions,
    FrozenRecommendation,
    content_sha256,
)
from legacy_engine.analytics.players.diagnostic import IdentityAccessibility, PlayerDiagnosticProtocol
from legacy_engine.analytics.players.effect import (
    BaseDeckProbability,
    PenaltySelection,
    PlayerInnerFold,
    PlayerTrainingMatch,
    ScheduledPlayerMatch,
    PlayerEffectOutcome,
    aggregate_player_effect_evaluations,
    evaluate_player_effect_fold,
    render_player_effect_markdown,
    fit_player_effect_model,
    freeze_player_effect_predictions,
    select_penalties,
)


def _protocol(**updates) -> PlayerDiagnosticProtocol:
    values = {
        "protocol_id": "effect-test", "created_at": "2026-01-01T00:00:00Z",
        "benchmark_protocol_hash": "benchmark", "min_repeat_events": 2,
        "min_repeat_matches": 4, "min_familiarity_events": 2,
        "min_familiarity_matches": 2, "min_repeat_players": 2,
        "min_familiarity_pairs": 2, "min_inner_origins": 3,
        "deck_penalties": (1.0, 100.0), "player_penalties": (1.0, 100.0),
        "familiarity_penalties": (1.0, 100.0),
    }
    values.update(updates)
    return PlayerDiagnosticProtocol(**values)


def _rows() -> tuple[PlayerTrainingMatch, ...]:
    rows = []
    for index in range(20):
        p_subject = index % 2 == 0
        rows.append(PlayerTrainingMatch(
            match_id=f"m{index}", event_id=f"e{index % 4}", event_date="2025-12-01",
            provenance="online", subject="A", opponent="B",
            subject_player_key="repeat-player" if p_subject else "other-player",
            opponent_player_key="other-player" if p_subject else "repeat-player",
            subject_won=p_subject,
        ))
    return tuple(rows)


def _selection(estimator, penalty=1.0):
    return PenaltySelection(
        estimator=estimator, deck_penalty=penalty,
        player_penalty=penalty if estimator != "deck-residual-control" else None,
        familiarity_penalty=penalty if estimator == "player-familiarity" else None,
        inner_origins=3, mean_log_loss=0.5, status="selected", reason=None,
    )


def test_crossed_player_effect_is_antisymmetric_and_not_deck_residual():
    rows = _rows()
    base = {("A", "B"): 0.5, ("B", "A"): 0.5}
    control = fit_player_effect_model(
        rows, base, _protocol(), _selection("deck-residual-control"),
    )
    player = fit_player_effect_model(rows, base, _protocol(), _selection("player-intercept"))
    assert control.converged and player.converged
    assert abs(control.deck[("A", "B")]) < 1e-6
    assert player.player["repeat-player"] > 0
    forward = player.probability("A", "B", 0.5, "repeat-player", "other-player")
    reverse = player.probability("B", "A", 0.5, "other-player", "repeat-player")
    assert abs(forward + reverse - 1.0) < 1e-12


def test_registered_penalties_shrink_terms_and_repeated_fits_are_identical():
    rows = _rows()
    base = {("A", "B"): 0.5, ("B", "A"): 0.5}
    low = fit_player_effect_model(rows, base, _protocol(), _selection("player-intercept", 1.0))
    again = fit_player_effect_model(rows, base, _protocol(), _selection("player-intercept", 1.0))
    high = fit_player_effect_model(rows, base, _protocol(), _selection("player-intercept", 100.0))
    assert low.player == again.player
    assert abs(high.player["repeat-player"]) < abs(low.player["repeat-player"])
    assert high.support(None) == "cold-start"
    assert high.support("never-seen") == "cold-start"
    thin_row = rows[0].model_copy(update={
        "match_id": "thin", "event_id": "thin-event", "subject_player_key": "thin-player",
    })
    with_thin = fit_player_effect_model(
        rows + (thin_row,), base, _protocol(), _selection("player-intercept", 1.0),
    )
    assert with_thin.support("thin-player") == "below-repeat-floor"

    low_familiarity = fit_player_effect_model(
        rows, base, _protocol(), _selection("player-familiarity", 1.0),
    )
    high_familiarity = fit_player_effect_model(
        rows, base, _protocol(), _selection("player-familiarity", 100.0),
    )
    assert max(map(abs, high_familiarity.familiarity.values())) < max(
        map(abs, low_familiarity.familiarity.values())
    )

    deck_rows = tuple(row.model_copy(update={
        "subject_player_key": None, "opponent_player_key": None, "subject_won": True,
    }) for row in rows)
    low_deck = fit_player_effect_model(
        deck_rows, base, _protocol(), _selection("deck-residual-control", 1.0),
    )
    high_deck = fit_player_effect_model(
        deck_rows, base, _protocol(), _selection("deck-residual-control", 100.0),
    )
    assert abs(high_deck.deck[("A", "B")]) < abs(low_deck.deck[("A", "B")])


def test_inner_selection_requires_three_origins_and_uses_frozen_base_grids():
    rows = _rows()
    grid = (
        BaseDeckProbability(subject="A", opponent="B", probability=0.5),
        BaseDeckProbability(subject="B", opponent="A", probability=0.5),
    )
    fold = PlayerInnerFold(
        cutoff="2025-12-01", training_rows=rows[:12], validation_rows=rows[12:],
        base_predictions_sha256=content_sha256([
            item.model_dump(mode="json") for item in grid
        ]), base_deck_predictions=grid,
    )
    insufficient = select_penalties((fold, fold), _protocol(), estimator="player-intercept")
    assert insufficient.status == "not-evaluable"
    selected = select_penalties((fold, fold, fold), _protocol(), estimator="player-intercept")
    assert selected.status == "selected"
    assert selected.inner_origins == 3


def _base() -> FrozenOriginPredictions:
    fold = BenchmarkFold(
        fold_id="f", cutoff="2026-01-01", evaluation_until="2026-01-29",
        regime_start="2025-11-01", regime_end=None, event_dates=("2026-01-02",),
    )
    predictions = tuple(FrozenMatchupPrediction(
        estimator="production-ci-gated", subject=subject, opponent=opponent,
        probability=0.5, served=True, source_kind="fixture", imputed=False,
        refusal_reason=None,
    ) for subject in ("A", "B") for opponent in ("A", "B"))
    return FrozenOriginPredictions(
        protocol_hash="benchmark", snapshot_manifest_sha256="snapshot", fold=fold,
        taxonomy_mode="retrospective-fixed-parent", taxonomy_effective_at=None,
        taxonomy_sha256="taxonomy", rules_sha256="rules", generated_at="2026-01-01T00:00:00Z",
        code_commit="commit", estimator_registry=ESTIMATOR_REGISTRY,
        action_universe=("A", "B"), field_shares={"A": 0.5, "B": 0.5},
        matchup_predictions=predictions, recommendations=(FrozenRecommendation(
            estimator="production-ci-gated", chosen_action="A", ranked_actions=("A", "B"),
            scores={"A": 0.5, "B": 0.5}, served=True, refusal_reason=None,
        ),), methodology={}, seeds={"benchmark": 1},
    )


def test_frozen_artifact_is_deterministic_hashed_and_contains_no_identity_keys():
    base = _base()
    rows = _rows()
    grid = tuple(BaseDeckProbability(
        subject=subject, opponent=opponent, probability=0.5,
    ) for subject in ("A", "B") for opponent in ("A", "B"))
    inner = tuple(PlayerInnerFold(
        cutoff=f"2025-0{index + 9}-01", training_rows=rows[:12], validation_rows=rows[12:],
        base_predictions_sha256=content_sha256([
            item.model_dump(mode="json") for item in grid
        ]), base_deck_predictions=grid,
    ) for index in range(3))
    scheduled = (ScheduledPlayerMatch(
        match_id="future:0", event_id="future", event_date="2026-01-02",
        provenance="online", subject="A", opponent="B",
        subject_player_key="repeat-player", opponent_player_key="other-player",
        exclusion_reason=None,
    ),)
    first = freeze_player_effect_predictions(
        base, rows, scheduled, (), _protocol(), inner_folds=inner,
    )
    second = freeze_player_effect_predictions(
        base, rows, scheduled, (), _protocol(), inner_folds=inner,
    )
    assert first == second
    payload = json.loads(first.model_dump_json())
    serialized = json.dumps(payload)
    assert "repeat-player" not in serialized and "other-player" not in serialized
    assert first.schedule_sha256 == content_sha256([
        scheduled[0].model_dump(mode="json"),
    ])
    assert set(first.estimator_registry).isdisjoint(set(ESTIMATOR_REGISTRY))


def test_future_evaluation_changes_only_after_outcomes_open_and_keeps_all_strata():
    base = _base()
    rows = _rows()
    grid = tuple(BaseDeckProbability(
        subject=subject, opponent=opponent, probability=0.5,
    ) for subject in ("A", "B") for opponent in ("A", "B"))
    inner = tuple(PlayerInnerFold(
        cutoff=f"2025-0{index + 9}-01", training_rows=rows[:12], validation_rows=rows[12:],
        base_predictions_sha256=content_sha256([
            item.model_dump(mode="json") for item in grid
        ]), base_deck_predictions=grid,
    ) for index in range(3))
    scheduled = tuple(ScheduledPlayerMatch(
        match_id=f"future:{index}", event_id=f"future-{index}", event_date="2026-01-02",
        provenance="online" if index < 2 else "paper", subject="A", opponent="B",
        subject_player_key="repeat-player" if index % 2 == 0 else None,
        opponent_player_key="other-player" if index < 3 else None,
        exclusion_reason=None,
    ) for index in range(4))
    accessibility = (IdentityAccessibility(
        provenance="all", registrations=100, match_sides=200, nonempty_handle_rate=1.0,
        unambiguous_match_rate=1.0, dated_alias_rate=0.0, repeat_players=30,
        familiarity_pairs=30, effect_supported_match_rate=0.8, evaluable=True, reasons=(),
    ),)
    frozen = freeze_player_effect_predictions(
        base, rows, scheduled, accessibility, _protocol(), inner_folds=inner,
    )
    frozen_hash = content_sha256(frozen)
    outcomes = tuple(PlayerEffectOutcome(
        match_id=row.match_id, event_id=row.event_id, event_date=row.event_date,
        provenance=row.provenance, subject=row.subject, opponent=row.opponent,
        subject_player_key=row.subject_player_key, opponent_player_key=row.opponent_player_key,
        subject_won=index % 2 == 0, exclusion_reason=None,
    ) for index, row in enumerate(scheduled))
    benchmark = BenchmarkProtocol(
        protocol_id="benchmark", created_at="2026-01-01T00:00:00Z",
        taxonomy_mode="retrospective-fixed-parent", first_cutoff="2026-01-01",
        final_evaluation_until="2026-01-29", bootstrap_draws=20,
        support=EvaluationSupport(
            min_common_matches=2, min_events=2, min_event_dates=1,
                min_calibration_matches=10, min_supported_actions=2, min_action_matches=1,
            min_future_field_coverage=0.5, min_claim_folds=2, min_claim_regimes=1,
        ),
    )
    favorable = evaluate_player_effect_fold(frozen, outcomes, base, benchmark, _protocol())
    adverse = evaluate_player_effect_fold(
        frozen, tuple(row.model_copy(update={"subject_won": not row.subject_won}) for row in outcomes),
        base, benchmark, _protocol(),
    )
    assert favorable.outcomes_sha256 != adverse.outcomes_sha256
    assert content_sha256(frozen) == frozen_hash
    assert set(favorable.by_support_stratum) == {
        "known-known", "known-cold", "cold-cold", "below-repeat-floor",
    }
    assert set(favorable.by_provenance) == {"online", "paper"}
    summary = aggregate_player_effect_evaluations(
        (favorable,), benchmark_protocol=benchmark, player_protocol=_protocol(),
    )
    assert summary.status == "not-evaluable"
    assert summary.status != "candidate-for-promotion-study"
    assert summary.venue_gate is False
    assert "claim fold/regime support is insufficient" in summary.reasons
    assert "online/paper nonharm gate failed" in summary.reasons
    rendered = render_player_effect_markdown(summary)
    assert "support:known-cold" in rendered
    assert "venue:online" in rendered and "venue:paper" in rendered
    assert "deck q05/q50/q95" in rendered
    assert "repeat-player" not in rendered
    assert "Production ranking" in rendered
