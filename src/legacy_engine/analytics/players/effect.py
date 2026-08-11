"""Deterministic, partially pooled player-effect sensitivity model."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
from typing import Literal

import numpy as np
from scipy.optimize import minimize

from legacy_engine.advisory.ranking_benchmark import (
    BenchmarkFold,
    BenchmarkProtocol,
    FrozenOriginPredictions,
    HeldoutMatch,
    _calibration,
    _decision_metrics,
    content_sha256,
)
from legacy_engine.analytics.players.diagnostic import (
    PLAYER_EFFECT_ESTIMATOR_REGISTRY,
    IdentityAccessibility,
    IdentityReplayMode,
    PlayerDiagnosticProtocol,
    PlayerEffectEstimatorId,
)
from legacy_engine.models.base import LegacyEngineModel


class PlayerTrainingMatch(LegacyEngineModel):
    match_id: str
    event_id: str
    event_date: str
    provenance: str
    subject: str
    opponent: str
    subject_player_key: str | None
    opponent_player_key: str | None
    subject_won: bool


class ScheduledPlayerMatch(LegacyEngineModel):
    match_id: str
    event_id: str
    event_date: str
    provenance: str
    subject: str | None
    opponent: str | None
    subject_player_key: str | None
    opponent_player_key: str | None
    exclusion_reason: str | None
    subject_side: Literal["p1", "p2"] = "p1"


class PenaltySelection(LegacyEngineModel):
    estimator: PlayerEffectEstimatorId
    deck_penalty: float
    player_penalty: float | None
    familiarity_penalty: float | None
    inner_origins: int
    mean_log_loss: float | None
    status: Literal["selected", "not-evaluable", "fit-failed"]
    reason: str | None


class PlayerEffectFitSummary(LegacyEngineModel):
    estimator: PlayerEffectEstimatorId
    converged: bool
    penalty: PenaltySelection
    training_matches: int
    repeat_players: int
    familiarity_pairs: int
    effect_supported_rate: float
    deck_residual_quantiles: tuple[float, float, float] | None
    player_effect_quantiles: tuple[float, float, float] | None
    familiarity_quantiles: tuple[float, float, float] | None
    reason: str | None


class ExperimentalMatchPrediction(LegacyEngineModel):
    match_id: str
    estimator: PlayerEffectEstimatorId
    probability: float
    subject_support: Literal["eligible", "cold-start", "below-repeat-floor"]
    opponent_support: Literal["eligible", "cold-start", "below-repeat-floor"]
    familiarity_applied: bool


class ExperimentalDeckPrediction(LegacyEngineModel):
    estimator: PlayerEffectEstimatorId
    subject: str
    opponent: str
    probability: float


class BaseDeckProbability(LegacyEngineModel):
    subject: str
    opponent: str
    probability: float


class ExperimentalDeckRecommendation(LegacyEngineModel):
    estimator: PlayerEffectEstimatorId
    chosen_action: str | None
    ranked_actions: tuple[str, ...]
    expected_field_win_rate: dict[str, float | None]
    served: bool
    reason: str | None


class PlayerInnerFold(LegacyEngineModel):
    cutoff: str
    training_rows: tuple[PlayerTrainingMatch, ...]
    validation_rows: tuple[PlayerTrainingMatch, ...]
    base_predictions_sha256: str
    base_deck_predictions: tuple[BaseDeckProbability, ...]


class FrozenPlayerEffectPredictions(LegacyEngineModel):
    player_protocol_hash: str
    benchmark_protocol_hash: str
    base_predictions_sha256: str
    snapshot_manifest_sha256: str
    fold: BenchmarkFold
    identity_mode: IdentityReplayMode
    identity_snapshot_sha256: str | None
    schedule_sha256: str
    generated_at: str
    estimator_registry: tuple[PlayerEffectEstimatorId, ...]
    accessibility: tuple[IdentityAccessibility, ...]
    fit_summaries: tuple[PlayerEffectFitSummary, ...]
    match_predictions: tuple[ExperimentalMatchPrediction, ...]
    neutral_deck_predictions: tuple[ExperimentalDeckPrediction, ...]
    neutral_recommendations: tuple[ExperimentalDeckRecommendation, ...]
    limitations: tuple[str, ...]


PlayerSupportStratum = Literal[
    "known-known", "known-cold", "cold-cold", "below-repeat-floor",
]
PlayerDiagnosticStatus = Literal[
    "not-evaluable", "stop", "diagnostic-only", "candidate-for-promotion-study",
]


class PlayerEffectOutcome(LegacyEngineModel):
    match_id: str
    event_id: str
    event_date: str
    provenance: str
    subject: str | None
    opponent: str | None
    subject_player_key: str | None
    opponent_player_key: str | None
    subject_won: bool | None
    exclusion_reason: str | None


class PlayerEstimatorEvaluation(LegacyEngineModel):
    estimator: PlayerEffectEstimatorId
    estimand: Literal[
        "heldout-event-player-aware", "heldout-player-masked", "player-neutral-deck",
    ]
    common_matches: int
    supported_matches: int
    log_loss: float | None
    brier: float | None
    calibration_intercept: float | None
    calibration_slope: float | None
    cumulative_calibration: tuple[float, ...]
    regret: float | None
    regret_ci: tuple[float, float] | None
    paired_vs: dict[str, dict[str, float | None]]


class PlayerEffectFoldEvaluation(LegacyEngineModel):
    player_protocol_hash: str
    predictions_sha256: str
    outcomes_sha256: str
    fold: BenchmarkFold
    accessibility: tuple[IdentityAccessibility, ...]
    fit_summaries: tuple[PlayerEffectFitSummary, ...]
    by_estimator: tuple[PlayerEstimatorEvaluation, ...]
    by_support_stratum: dict[PlayerSupportStratum, tuple[PlayerEstimatorEvaluation, ...]]
    by_provenance: dict[str, tuple[PlayerEstimatorEvaluation, ...]]
    status: PlayerDiagnosticStatus
    reasons: tuple[str, ...]


class PlayerEffectEvaluationSummary(LegacyEngineModel):
    player_protocol_hash: str
    folds: tuple[PlayerEffectFoldEvaluation, ...]
    evaluable_folds: int
    represented_regimes: int
    support_gate: bool
    player_predictive_gate: bool
    neutral_deck_gate: bool
    familiarity_gate: bool
    venue_gate: bool
    status: PlayerDiagnosticStatus
    reasons: tuple[str, ...]


def _clip(value: float) -> float:
    return min(1.0 - 1e-6, max(1e-6, value))


def _logit(value: float) -> float:
    value = _clip(value)
    return math.log(value / (1.0 - value))


def _expit(value: float) -> float:
    if value >= 0:
        inverse = math.exp(-value)
        return 1.0 / (1.0 + inverse)
    exponential = math.exp(value)
    return exponential / (1.0 + exponential)


def _eligible_effects(
    rows: tuple[PlayerTrainingMatch, ...], protocol: PlayerDiagnosticProtocol,
) -> tuple[set[str], set[tuple[str, str]], set[str]]:
    events: dict[str, set[str]] = defaultdict(set)
    matches: dict[str, int] = defaultdict(int)
    pair_events: dict[tuple[str, str], set[str]] = defaultdict(set)
    pair_matches: dict[tuple[str, str], int] = defaultdict(int)
    observed: set[str] = set()
    for row in rows:
        for key, parent in (
            (row.subject_player_key, row.subject), (row.opponent_player_key, row.opponent),
        ):
            if key is None:
                continue
            observed.add(key)
            events[key].add(row.event_id)
            matches[key] += 1
            pair_events[(key, parent)].add(row.event_id)
            pair_matches[(key, parent)] += 1
    repeat = {
        key for key in observed
        if len(events[key]) >= protocol.min_repeat_events
        and matches[key] >= protocol.min_repeat_matches
    }
    familiarity = {
        pair for pair in pair_matches if pair[0] in repeat
        and len(pair_events[pair]) >= protocol.min_familiarity_events
        and pair_matches[pair] >= protocol.min_familiarity_matches
    }
    return repeat, familiarity, observed


@dataclass
class _PlayerEffectFit:
    estimator: PlayerEffectEstimatorId
    converged: bool
    deck: dict[tuple[str, str], float]
    player: dict[str, float]
    familiarity: dict[tuple[str, str], float]
    eligible_players: set[str]
    eligible_familiarity: set[tuple[str, str]]
    observed_players: set[str]
    reason: str | None = None

    def probability(
        self,
        subject: str,
        opponent: str,
        base: float,
        subject_player: str | None = None,
        opponent_player: str | None = None,
        *,
        neutral: bool = False,
    ) -> float:
        pair = tuple(sorted((subject, opponent)))
        sign = 1.0 if subject == pair[0] else -1.0
        value = _logit(base) + sign * self.deck.get(pair, 0.0)
        if not neutral:
            value += self.player.get(subject_player or "", 0.0)
            value -= self.player.get(opponent_player or "", 0.0)
            value += self.familiarity.get((subject_player or "", subject), 0.0)
            value -= self.familiarity.get((opponent_player or "", opponent), 0.0)
        return _expit(value)

    def support(self, key: str | None) -> Literal["eligible", "cold-start", "below-repeat-floor"]:
        if key is None or key not in self.observed_players:
            return "cold-start"
        return "eligible" if key in self.eligible_players else "below-repeat-floor"


def _coefficient_layout(
    rows: tuple[PlayerTrainingMatch, ...], protocol: PlayerDiagnosticProtocol,
    estimator: PlayerEffectEstimatorId,
):
    deck_keys = tuple(sorted({tuple(sorted((row.subject, row.opponent))) for row in rows}))
    repeat, familiarity, observed = _eligible_effects(rows, protocol)
    player_keys = tuple(sorted(repeat)) if estimator != "deck-residual-control" else ()
    familiarity_keys = tuple(sorted(familiarity)) if estimator == "player-familiarity" else ()
    return deck_keys, player_keys, familiarity_keys, repeat, familiarity, observed


def fit_player_effect_model(
    rows: tuple[PlayerTrainingMatch, ...],
    base_probabilities: dict[tuple[str, str], float],
    protocol: PlayerDiagnosticProtocol,
    selection: PenaltySelection,
) -> _PlayerEffectFit:
    """Fit the preregistered penalized-logistic sensitivity deterministically."""
    if selection.status != "selected" or not rows:
        return _PlayerEffectFit(
            estimator=selection.estimator, converged=False, deck={}, player={}, familiarity={},
            eligible_players=set(), eligible_familiarity=set(), observed_players=set(),
            reason=selection.reason or "penalty selection is not evaluable",
        )
    deck_keys, player_keys, familiarity_keys, repeat, familiarity, observed = _coefficient_layout(
        rows, protocol, selection.estimator,
    )
    indexes = {
        "deck": {key: index for index, key in enumerate(deck_keys)},
        "player": {
            key: len(deck_keys) + index for index, key in enumerate(player_keys)
        },
        "familiarity": {
            key: len(deck_keys) + len(player_keys) + index
            for index, key in enumerate(familiarity_keys)
        },
    }
    size = len(deck_keys) + len(player_keys) + len(familiarity_keys)

    def objective(coefficients: np.ndarray) -> float:
        loss = 0.0
        for row in rows:
            base = base_probabilities[(row.subject, row.opponent)]
            pair = tuple(sorted((row.subject, row.opponent)))
            sign = 1.0 if row.subject == pair[0] else -1.0
            linear = _logit(base) + sign * coefficients[indexes["deck"][pair]]
            if row.subject_player_key in indexes["player"]:
                linear += coefficients[indexes["player"][row.subject_player_key]]
            if row.opponent_player_key in indexes["player"]:
                linear -= coefficients[indexes["player"][row.opponent_player_key]]
            subject_pair = (row.subject_player_key, row.subject)
            opponent_pair = (row.opponent_player_key, row.opponent)
            if subject_pair in indexes["familiarity"]:
                linear += coefficients[indexes["familiarity"][subject_pair]]
            if opponent_pair in indexes["familiarity"]:
                linear -= coefficients[indexes["familiarity"][opponent_pair]]
            probability = _clip(_expit(linear))
            outcome = float(row.subject_won)
            loss -= outcome * math.log(probability) + (1.0 - outcome) * math.log(1.0 - probability)
        deck_values = coefficients[:len(deck_keys)]
        player_values = coefficients[len(deck_keys):len(deck_keys) + len(player_keys)]
        familiarity_values = coefficients[len(deck_keys) + len(player_keys):]
        loss += 0.5 * selection.deck_penalty * float(deck_values @ deck_values)
        if selection.player_penalty is not None:
            loss += 0.5 * selection.player_penalty * float(player_values @ player_values)
        if selection.familiarity_penalty is not None:
            loss += 0.5 * selection.familiarity_penalty * float(
                familiarity_values @ familiarity_values
            )
        return loss

    result = minimize(
        objective, np.zeros(size, dtype=float), method="L-BFGS-B",
        options={"ftol": 1e-12, "gtol": 1e-8, "maxiter": 2_000},
    )
    if not result.success or not np.all(np.isfinite(result.x)):
        return _PlayerEffectFit(
            estimator=selection.estimator, converged=False, deck={}, player={}, familiarity={},
            eligible_players=repeat, eligible_familiarity=familiarity,
            observed_players=observed, reason=f"fit failed: {result.message}",
        )
    deck = {key: float(result.x[indexes["deck"][key]]) for key in deck_keys}
    player = {key: float(result.x[indexes["player"][key]]) for key in player_keys}
    if player:
        center = float(np.mean(list(player.values())))
        player = {key: value - center for key, value in player.items()}
    familiarity_values = {
        key: float(result.x[indexes["familiarity"][key]]) for key in familiarity_keys
    }
    by_player: dict[str, list[tuple[tuple[str, str], float]]] = defaultdict(list)
    for key, value in familiarity_values.items():
        by_player[key[0]].append((key, value))
    for values in by_player.values():
        center = float(np.mean([value for _key, value in values]))
        for key, value in values:
            familiarity_values[key] = value - center
    return _PlayerEffectFit(
        estimator=selection.estimator, converged=True, deck=deck, player=player,
        familiarity=familiarity_values, eligible_players=repeat,
        eligible_familiarity=familiarity, observed_players=observed,
    )


def _selection_grid(protocol: PlayerDiagnosticProtocol, estimator: PlayerEffectEstimatorId):
    if estimator == "deck-residual-control":
        return tuple((deck, None, None) for deck in protocol.deck_penalties)
    if estimator == "player-intercept":
        return tuple(
            (deck, player, None)
            for deck in protocol.deck_penalties for player in protocol.player_penalties
        )
    return tuple(
        (deck, player, familiarity)
        for deck in protocol.deck_penalties for player in protocol.player_penalties
        for familiarity in protocol.familiarity_penalties
    )


def select_penalties(
    inner_folds: tuple[PlayerInnerFold, ...],
    protocol: PlayerDiagnosticProtocol,
    *,
    estimator: PlayerEffectEstimatorId,
) -> PenaltySelection:
    valid = tuple(fold for fold in inner_folds if fold.training_rows and fold.validation_rows)
    strongest = max(_selection_grid(protocol, estimator))
    if len(valid) < protocol.min_inner_origins:
        return PenaltySelection(
            estimator=estimator, deck_penalty=strongest[0], player_penalty=strongest[1],
            familiarity_penalty=strongest[2], inner_origins=len(valid), mean_log_loss=None,
            status="not-evaluable",
            reason=f"valid inner origins {len(valid)} < {protocol.min_inner_origins}",
        )
    results: list[tuple[tuple[float, float | None, float | None], float]] = []
    for parameters in _selection_grid(protocol, estimator):
        losses: list[float] = []
        selection = PenaltySelection(
            estimator=estimator, deck_penalty=parameters[0], player_penalty=parameters[1],
            familiarity_penalty=parameters[2], inner_origins=len(valid), mean_log_loss=None,
            status="selected", reason=None,
        )
        for fold in valid:
            base = {(item.subject, item.opponent): item.probability for item in fold.base_deck_predictions}
            fit = fit_player_effect_model(fold.training_rows, base, protocol, selection)
            if not fit.converged:
                losses = []
                break
            fold_losses = []
            for row in fold.validation_rows:
                probability = _clip(fit.probability(
                    row.subject, row.opponent, base[(row.subject, row.opponent)],
                    row.subject_player_key, row.opponent_player_key,
                ))
                outcome = float(row.subject_won)
                fold_losses.append(-(
                    outcome * math.log(probability) + (1.0 - outcome) * math.log(1.0 - probability)
                ))
            losses.append(float(np.mean(fold_losses)))
        if losses:
            results.append((parameters, float(np.mean(losses))))
    if not results:
        return PenaltySelection(
            estimator=estimator, deck_penalty=strongest[0], player_penalty=strongest[1],
            familiarity_penalty=strongest[2], inner_origins=len(valid), mean_log_loss=None,
            status="fit-failed", reason="every preregistered penalty fit failed",
        )
    best_loss = min(loss for _parameters, loss in results)
    tied = [item for item in results if item[1] <= best_loss + 1e-4]
    parameters, loss = max(tied, key=lambda item: (
        sum(value or 0.0 for value in item[0]), item[0],
    ))
    return PenaltySelection(
        estimator=estimator, deck_penalty=parameters[0], player_penalty=parameters[1],
        familiarity_penalty=parameters[2], inner_origins=len(valid), mean_log_loss=loss,
        status="selected", reason=None,
    )


def _quantiles(values: dict[object, float]) -> tuple[float, float, float] | None:
    if not values:
        return None
    return tuple(float(value) for value in np.quantile(list(values.values()), [0.05, 0.5, 0.95]))


def freeze_player_effect_predictions(
    base: FrozenOriginPredictions,
    training_rows: tuple[PlayerTrainingMatch, ...],
    scheduled_rows: tuple[ScheduledPlayerMatch, ...],
    accessibility: tuple[IdentityAccessibility, ...],
    protocol: PlayerDiagnosticProtocol,
    *,
    inner_folds: tuple[PlayerInnerFold, ...] = (),
    identity_snapshot_sha256: str | None = None,
) -> FrozenPlayerEffectPredictions:
    """Fit and freeze all three experimental estimators without serializing identity keys."""
    if protocol.benchmark_protocol_hash != base.protocol_hash:
        raise ValueError("player protocol benchmark hash does not match frozen base predictions")
    base_grid = {
        (item.subject, item.opponent): item.probability
        for item in base.matchup_predictions if item.estimator == "production-ci-gated"
    }
    selections = {
        estimator: select_penalties(inner_folds, protocol, estimator=estimator)
        for estimator in PLAYER_EFFECT_ESTIMATOR_REGISTRY
    }
    fits = {
        estimator: fit_player_effect_model(
            training_rows, base_grid, protocol, selections[estimator],
        ) for estimator in PLAYER_EFFECT_ESTIMATOR_REGISTRY
    }
    summaries: list[PlayerEffectFitSummary] = []
    match_predictions: list[ExperimentalMatchPrediction] = []
    deck_predictions: list[ExperimentalDeckPrediction] = []
    recommendations: list[ExperimentalDeckRecommendation] = []
    actions = base.action_universe
    for estimator in PLAYER_EFFECT_ESTIMATOR_REGISTRY:
        fit = fits[estimator]
        supported = sum(
            row.subject_player_key in fit.eligible_players
            and row.opponent_player_key in fit.eligible_players
            for row in training_rows
        )
        summaries.append(PlayerEffectFitSummary(
            estimator=estimator, converged=fit.converged, penalty=selections[estimator],
            training_matches=len(training_rows), repeat_players=len(fit.eligible_players),
            familiarity_pairs=len(fit.eligible_familiarity),
            effect_supported_rate=supported / len(training_rows) if training_rows else 0.0,
            deck_residual_quantiles=_quantiles(fit.deck),
            player_effect_quantiles=_quantiles(fit.player),
            familiarity_quantiles=_quantiles(fit.familiarity), reason=fit.reason,
        ))
        if not fit.converged:
            recommendations.append(ExperimentalDeckRecommendation(
                estimator=estimator, chosen_action=None, ranked_actions=(),
                expected_field_win_rate={}, served=False, reason=fit.reason,
            ))
            continue
        for row in scheduled_rows:
            if row.exclusion_reason is not None or row.subject is None or row.opponent is None:
                continue
            match_predictions.append(ExperimentalMatchPrediction(
                match_id=row.match_id, estimator=estimator,
                probability=fit.probability(
                    row.subject, row.opponent, base_grid[(row.subject, row.opponent)],
                    row.subject_player_key, row.opponent_player_key,
                ),
                subject_support=fit.support(row.subject_player_key),
                opponent_support=fit.support(row.opponent_player_key),
                familiarity_applied=(
                    (row.subject_player_key, row.subject) in fit.familiarity
                    or (row.opponent_player_key, row.opponent) in fit.familiarity
                ),
            ))
        scores: dict[str, float | None] = {}
        for subject in actions:
            for opponent in actions:
                deck_predictions.append(ExperimentalDeckPrediction(
                    estimator=estimator, subject=subject, opponent=opponent,
                    probability=fit.probability(
                        subject, opponent, base_grid[(subject, opponent)], neutral=True,
                    ),
                ))
            scores[subject] = sum(
                base.field_shares[opponent] * fit.probability(
                    subject, opponent, base_grid[(subject, opponent)], neutral=True,
                ) for opponent in actions
            )
        ranked = tuple(sorted(actions, key=lambda action: (-float(scores[action]), action)))
        recommendations.append(ExperimentalDeckRecommendation(
            estimator=estimator, chosen_action=ranked[0] if ranked else None,
            ranked_actions=ranked, expected_field_win_rate=scores, served=bool(ranked), reason=None,
        ))
    schedule_sha = content_sha256([row.model_dump(mode="json") for row in scheduled_rows])
    return FrozenPlayerEffectPredictions(
        player_protocol_hash=content_sha256(protocol),
        benchmark_protocol_hash=base.protocol_hash,
        base_predictions_sha256=content_sha256(base),
        snapshot_manifest_sha256=base.snapshot_manifest_sha256, fold=base.fold,
        identity_mode=protocol.identity_mode,
        identity_snapshot_sha256=identity_snapshot_sha256,
        schedule_sha256=schedule_sha, generated_at=protocol.created_at,
        estimator_registry=PLAYER_EFFECT_ESTIMATOR_REGISTRY,
        accessibility=accessibility, fit_summaries=tuple(summaries),
        match_predictions=tuple(sorted(
            match_predictions, key=lambda item: (item.estimator, item.match_id),
        )),
        neutral_deck_predictions=tuple(sorted(
            deck_predictions, key=lambda item: (item.estimator, item.subject, item.opponent),
        )),
        neutral_recommendations=tuple(sorted(recommendations, key=lambda item: item.estimator)),
        limitations=(
            "experimental sensitivity only; production ranking and P(best) are unchanged",
            "participant forecasts are outcome-blind historical replay, not proof of pre-event availability",
        ),
    )


def _paired_event_difference(
    rows: tuple[PlayerEffectOutcome, ...],
    candidate: dict[str, float],
    reference: dict[str, float],
    *,
    seed: int,
    draws: int,
) -> dict[str, float | None]:
    by_event: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        outcome = float(bool(row.subject_won))
        candidate_loss = -(
            outcome * math.log(_clip(candidate[row.match_id]))
            + (1.0 - outcome) * math.log(1.0 - _clip(candidate[row.match_id]))
        )
        reference_loss = -(
            outcome * math.log(_clip(reference[row.match_id]))
            + (1.0 - outcome) * math.log(1.0 - _clip(reference[row.match_id]))
        )
        by_event[row.event_id].append(candidate_loss - reference_loss)
    event_means = [float(np.mean(by_event[key])) for key in sorted(by_event)]
    if not event_means:
        return {"mean": None, "ci_low": None, "ci_high": None}
    rng = np.random.default_rng(seed)
    samples = [
        float(np.mean(rng.choice(event_means, len(event_means), replace=True)))
        for _ in range(draws)
    ]
    low, high = np.quantile(samples, [0.025, 0.975])
    return {"mean": float(np.mean(event_means)), "ci_low": float(low), "ci_high": float(high)}


def _score_player_rows(
    estimator: PlayerEffectEstimatorId,
    estimand: Literal[
        "heldout-event-player-aware", "heldout-player-masked", "player-neutral-deck",
    ],
    rows: tuple[PlayerEffectOutcome, ...],
    probabilities: dict[str, float],
    supported: set[str],
    references: dict[str, dict[str, float]],
    recommendation: ExperimentalDeckRecommendation | None,
    benchmark_protocol: BenchmarkProtocol,
    field_shares: dict[str, float],
    seed: int,
) -> PlayerEstimatorEvaluation:
    if not rows or any(row.match_id not in probabilities for row in rows):
        return PlayerEstimatorEvaluation(
            estimator=estimator, estimand=estimand, common_matches=0, supported_matches=0,
            log_loss=None, brier=None, calibration_intercept=None, calibration_slope=None,
            cumulative_calibration=(), regret=None, regret_ci=None, paired_vs={},
        )
    probability_array = np.asarray([probabilities[row.match_id] for row in rows], dtype=float)
    outcome_array = np.asarray([float(bool(row.subject_won)) for row in rows], dtype=float)
    clipped = np.clip(
        probability_array, benchmark_protocol.log_clip_epsilon,
        1.0 - benchmark_protocol.log_clip_epsilon,
    )
    log_loss = float(np.mean(-(
        outcome_array * np.log(clipped) + (1.0 - outcome_array) * np.log(1.0 - clipped)
    )))
    brier = float(np.mean((probability_array - outcome_array) ** 2))
    intercept, slope, cumulative = _calibration(
        probability_array, outcome_array, benchmark_protocol.support.min_calibration_matches,
    )
    regret = regret_ci = None
    if recommendation is not None and recommendation.served:
        heldout = tuple(HeldoutMatch(
            event_id=row.event_id, event_date=row.event_date, provenance=row.provenance,
            subject=row.subject, opponent=row.opponent, subject_player_key=None,
            opponent_player_key=None, subject_won=row.subject_won, exclusion_reason=None,
        ) for row in rows)
        counts = {
            action: max(1, round(share * 10_000)) for action, share in field_shares.items()
        }
        _tau, _top3, regret, regret_ci, _reason, _oracle = _decision_metrics(
            recommendation, heldout, benchmark_protocol, counts,
        )
    paired = {
        name: _paired_event_difference(
            rows, probabilities, reference, seed=seed,
            draws=benchmark_protocol.bootstrap_draws,
        ) for name, reference in references.items()
    }
    for name, reference in references.items():
        reference_array = np.asarray([reference[row.match_id] for row in rows], dtype=float)
        reference_brier = float(np.mean((reference_array - outcome_array) ** 2))
        ref_intercept, ref_slope, _ref_cumulative = _calibration(
            reference_array, outcome_array, benchmark_protocol.support.min_calibration_matches,
        )
        paired[name]["brier_difference"] = brier - reference_brier
        paired[name]["calibration_intercept_abs_difference"] = (
            None if intercept is None or ref_intercept is None
            else abs(intercept) - abs(ref_intercept)
        )
        paired[name]["calibration_slope_distance_difference"] = (
            None if slope is None or ref_slope is None
            else abs(slope - 1.0) - abs(ref_slope - 1.0)
        )
    return PlayerEstimatorEvaluation(
        estimator=estimator, estimand=estimand, common_matches=len(rows),
        supported_matches=sum(row.match_id in supported for row in rows),
        log_loss=log_loss, brier=brier, calibration_intercept=intercept,
        calibration_slope=slope, cumulative_calibration=cumulative,
        regret=regret, regret_ci=regret_ci, paired_vs=paired,
    )


def _support_stratum(prediction: ExperimentalMatchPrediction) -> PlayerSupportStratum:
    values = {prediction.subject_support, prediction.opponent_support}
    if "below-repeat-floor" in values:
        return "below-repeat-floor"
    eligible = sum(value == "eligible" for value in (
        prediction.subject_support, prediction.opponent_support,
    ))
    return ("known-known" if eligible == 2 else "known-cold" if eligible == 1 else "cold-cold")


def evaluate_player_effect_fold(
    frozen: FrozenPlayerEffectPredictions,
    outcomes: tuple[PlayerEffectOutcome, ...],
    base: FrozenOriginPredictions,
    benchmark_protocol: BenchmarkProtocol,
    player_protocol: PlayerDiagnosticProtocol,
) -> PlayerEffectFoldEvaluation:
    """Score experimental forecasts on the benchmark's identical decisive common cases."""
    if frozen.player_protocol_hash != content_sha256(player_protocol):
        raise ValueError("frozen player protocol hash mismatch")
    if frozen.benchmark_protocol_hash != base.protocol_hash:
        raise ValueError("frozen player benchmark hash mismatch")
    if frozen.base_predictions_sha256 != content_sha256(base):
        raise ValueError("frozen player base prediction hash mismatch")
    if frozen.fold != base.fold:
        raise ValueError("frozen player fold does not match base fold")
    scheduled_ids = {
        item.match_id for item in frozen.match_predictions
    }
    rows = tuple(
        row for row in outcomes
        if row.exclusion_reason is None and row.match_id in scheduled_ids
        and row.subject in base.action_universe and row.opponent in base.action_universe
    )
    production_grid = {
        (item.subject, item.opponent): item.probability
        for item in base.matchup_predictions if item.estimator == "production-ci-gated"
    }
    production = {
        row.match_id: production_grid[(row.subject, row.opponent)] for row in rows
    }
    aware_by_estimator = {
        estimator: {
            item.match_id: item.probability for item in frozen.match_predictions
            if item.estimator == estimator
        } for estimator in frozen.estimator_registry
    }
    neutral_by_estimator = {
        estimator: {
            row.match_id: grid[(row.subject, row.opponent)]
            for row in rows if (row.subject, row.opponent) in grid
        } for estimator in frozen.estimator_registry
        for grid in ({
            (item.subject, item.opponent): item.probability
            for item in frozen.neutral_deck_predictions if item.estimator == estimator
        },)
    }
    support_by_estimator = {
        estimator: {
            item.match_id for item in frozen.match_predictions
            if item.estimator == estimator and item.subject_support == "eligible"
            and item.opponent_support == "eligible"
        } for estimator in frozen.estimator_registry
    }
    recommendations = {item.estimator: item for item in frozen.neutral_recommendations}
    control = aware_by_estimator["deck-residual-control"]
    player_intercept = aware_by_estimator["player-intercept"]

    def score_subset(subset: tuple[PlayerEffectOutcome, ...]):
        evaluations = []
        for estimator in frozen.estimator_registry:
            references = {"production-ci-gated": production}
            if estimator != "deck-residual-control":
                references["deck-residual-control"] = control
            if estimator == "player-familiarity":
                references["player-intercept"] = player_intercept
            evaluations.append(_score_player_rows(
                estimator, "heldout-event-player-aware", subset,
                aware_by_estimator[estimator], support_by_estimator[estimator], references,
                None, benchmark_protocol, base.field_shares, player_protocol.seed,
            ))
            evaluations.append(_score_player_rows(
                estimator, "heldout-player-masked", subset,
                neutral_by_estimator[estimator], set(), {"production-ci-gated": production},
                None, benchmark_protocol, base.field_shares, player_protocol.seed,
            ))
            evaluations.append(_score_player_rows(
                estimator, "player-neutral-deck", subset,
                neutral_by_estimator[estimator], set(), {"production-ci-gated": production},
                recommendations.get(estimator), benchmark_protocol, base.field_shares,
                player_protocol.seed,
            ))
        return tuple(evaluations)

    all_scores = score_subset(rows)
    production_recommendation = next(
        (item for item in base.recommendations if item.estimator == "production-ci-gated"), None,
    )
    if production_recommendation is not None and rows:
        heldout_for_regret = tuple(HeldoutMatch(
            event_id=row.event_id, event_date=row.event_date, provenance=row.provenance,
            subject=row.subject, opponent=row.opponent, subject_player_key=None,
            opponent_player_key=None, subject_won=row.subject_won, exclusion_reason=None,
        ) for row in rows)
        counts = {
            action: max(1, round(share * 10_000)) for action, share in base.field_shares.items()
        }
        _tau, _top3, production_regret, production_ci, _reason, _oracle = _decision_metrics(
            production_recommendation, heldout_for_regret, benchmark_protocol, counts,
        )
        revised = []
        for item in all_scores:
            if (
                item.estimand == "player-neutral-deck" and item.regret is not None
                and item.regret_ci is not None and production_regret is not None
                and production_ci is not None
            ):
                paired = dict(item.paired_vs)
                paired["production-regret"] = {
                    "mean": item.regret - production_regret,
                    "ci_low": item.regret_ci[0] - production_ci[1],
                    "ci_high": item.regret_ci[1] - production_ci[0],
                }
                item = item.model_copy(update={"paired_vs": paired})
            revised.append(item)
        all_scores = tuple(revised)
    prediction_lookup = {
        (item.estimator, item.match_id): item for item in frozen.match_predictions
    }
    primary_predictions = {
        row.match_id: prediction_lookup.get(("player-intercept", row.match_id)) for row in rows
    }
    by_stratum = {
        stratum: score_subset(tuple(
            row for row in rows if primary_predictions[row.match_id] is not None
            and _support_stratum(primary_predictions[row.match_id]) == stratum
        )) for stratum in (
            "known-known", "known-cold", "cold-cold", "below-repeat-floor",
        )
    }
    by_provenance = {
        provenance: score_subset(tuple(row for row in rows if row.provenance == provenance))
        for provenance in sorted({row.provenance for row in rows} | {"online", "paper"})
    }
    reasons: list[str] = []
    all_access = next(
        (item for item in frozen.accessibility if item.provenance == "all"), None,
    )
    if all_access is None or not all_access.evaluable:
        reasons.append("aggregate identity/repeat support is not evaluable")
    if any(not summary.converged for summary in frozen.fit_summaries):
        reasons.append("one or more experimental fits are not evaluable")
    if not rows:
        reasons.append("no identical decisive scheduled cases are available")
    status: PlayerDiagnosticStatus = "not-evaluable" if reasons else "diagnostic-only"
    return PlayerEffectFoldEvaluation(
        player_protocol_hash=frozen.player_protocol_hash,
        predictions_sha256=content_sha256(frozen),
        outcomes_sha256=content_sha256([row.model_dump(mode="json") for row in outcomes]),
        fold=frozen.fold, accessibility=frozen.accessibility, by_estimator=all_scores,
        fit_summaries=frozen.fit_summaries,
        by_support_stratum=by_stratum, by_provenance=by_provenance,
        status=status, reasons=tuple(reasons),
    )


def _metric(
    fold: PlayerEffectFoldEvaluation,
    estimator: PlayerEffectEstimatorId,
    estimand: str,
) -> PlayerEstimatorEvaluation:
    return next(
        item for item in fold.by_estimator
        if item.estimator == estimator and item.estimand == estimand
    )


def aggregate_player_effect_evaluations(
    folds: tuple[PlayerEffectFoldEvaluation, ...],
    *,
    benchmark_protocol: BenchmarkProtocol,
    player_protocol: PlayerDiagnosticProtocol,
) -> PlayerEffectEvaluationSummary:
    """Apply the preregistered conjunction; never promote or mutate production."""
    protocol_hash = content_sha256(player_protocol)
    if any(fold.player_protocol_hash != protocol_hash for fold in folds):
        raise ValueError("cannot aggregate player-effect folds from another protocol")
    evaluable = tuple(fold for fold in folds if fold.status != "not-evaluable")
    regimes = {fold.fold.regime_start for fold in evaluable}
    all_access = [
        next((item for item in fold.accessibility if item.provenance == "all"), None)
        for fold in evaluable
    ]
    support_gate = bool(evaluable) and all(
        item is not None and item.unambiguous_match_rate >= player_protocol.min_identity_match_coverage
        and item.effect_supported_match_rate >= player_protocol.min_effect_supported_match_coverage
        and item.repeat_players >= player_protocol.min_repeat_players
        for item in all_access
    )

    def proper_gate(estimator: PlayerEffectEstimatorId, references: tuple[str, ...]) -> bool:
        if not evaluable:
            return False
        for fold in evaluable:
            metric = _metric(fold, estimator, "heldout-event-player-aware")
            if metric.brier is None or metric.calibration_intercept is None or metric.calibration_slope is None:
                return False
            for reference in references:
                comparison = metric.paired_vs.get(reference, {})
                if (
                    comparison.get("ci_high") is None or comparison["ci_high"] >= 0
                    or comparison.get("brier_difference") is None
                    or comparison["brier_difference"] > 0
                    or comparison.get("calibration_intercept_abs_difference") is None
                    or comparison["calibration_intercept_abs_difference"] > 0
                    or comparison.get("calibration_slope_distance_difference") is None
                    or comparison["calibration_slope_distance_difference"] > 0
                ):
                    return False
        return True

    player_predictive_gate = proper_gate(
        "player-intercept", ("production-ci-gated", "deck-residual-control"),
    )
    familiarity_gate = proper_gate("player-familiarity", ("player-intercept",)) and all(
        item is not None and item.familiarity_pairs >= player_protocol.min_familiarity_pairs
        for item in all_access
    )
    regret_differences = [
        _metric(fold, "player-intercept", "player-neutral-deck").paired_vs.get(
            "production-regret", {},
        ).get("mean") for fold in evaluable
    ]
    valid_regret = [value for value in regret_differences if value is not None]
    neutral_deck_gate = False
    if len(valid_regret) == len(evaluable) and valid_regret:
        rng = np.random.default_rng(player_protocol.seed)
        samples = [
            float(np.mean(rng.choice(valid_regret, len(valid_regret), replace=True)))
            for _ in range(benchmark_protocol.bootstrap_draws)
        ]
        _low, high = np.quantile(samples, [0.025, 0.975])
        neutral_deck_gate = (
            float(high) < 0
            and sum(value < 0 for value in valid_regret) / len(valid_regret) >= 0.60
        )

    def subset_nonharm(items: tuple[PlayerEstimatorEvaluation, ...]) -> bool:
        metric = next((item for item in items if (
            item.estimator == "player-intercept"
            and item.estimand == "heldout-event-player-aware"
        )), None)
        if metric is None or metric.common_matches == 0 or metric.log_loss is None:
            return False
        comparison = metric.paired_vs.get("production-ci-gated", {})
        return (
            comparison.get("mean") is not None and comparison["mean"] <= 0
            and comparison.get("brier_difference") is not None
            and comparison["brier_difference"] <= 0
        )

    venue_gate = bool(evaluable) and all(
        subset_nonharm(fold.by_provenance.get(provenance, ()))
        for fold in evaluable for provenance in ("online", "paper")
    ) and all(
        subset_nonharm(fold.by_support_stratum.get(stratum, ()))
        for fold in evaluable for stratum in ("known-cold", "cold-cold")
    )
    fold_gate = (
        len(evaluable) >= benchmark_protocol.support.min_claim_folds
        and len(regimes) >= benchmark_protocol.support.min_claim_regimes
    )
    reasons: list[str] = []
    for passed, reason in (
        (fold_gate, "claim fold/regime support is insufficient"),
        (support_gate, "identity/repeat support gate failed"),
        (player_predictive_gate, "player intercept proper-score/calibration gate failed"),
        (neutral_deck_gate, "player-neutral regret gate failed"),
        (venue_gate, "online/paper nonharm gate failed"),
    ):
        if not passed:
            reasons.append(reason)
    if not evaluable or not fold_gate or not support_gate:
        status: PlayerDiagnosticStatus = "not-evaluable"
    elif all((player_predictive_gate, neutral_deck_gate, venue_gate)):
        status = "candidate-for-promotion-study"
    else:
        comparisons = [
            _metric(fold, "player-intercept", "heldout-event-player-aware").paired_vs.get(
                "production-ci-gated", {},
            ).get("mean") for fold in evaluable
        ]
        status = "stop" if comparisons and all(
            value is not None and value >= 0 for value in comparisons
        ) else "diagnostic-only"
    return PlayerEffectEvaluationSummary(
        player_protocol_hash=protocol_hash, folds=folds, evaluable_folds=len(evaluable),
        represented_regimes=len(regimes), support_gate=support_gate,
        player_predictive_gate=player_predictive_gate, neutral_deck_gate=neutral_deck_gate,
        familiarity_gate=familiarity_gate, venue_gate=venue_gate, status=status,
        reasons=tuple(reasons),
    )


def render_player_effect_markdown(summary: PlayerEffectEvaluationSummary) -> str:
    lines = [
        "# Player-effect future-only diagnostic", "",
        f"- Status: **{summary.status}**",
        f"- Evaluable folds: {summary.evaluable_folds}/{len(summary.folds)}",
        f"- Regimes represented: {summary.represented_regimes}",
        "- Identity basis is provenance-local handles unless a dated curated alias snapshot is named.",
        "- Historical participant replay is outcome-blind; it does not prove pre-event pairing availability.",
        "- Production ranking, the ten-estimator registry, Agency, and P(best) are unchanged.", "",
        "## Stop/go gates", "",
        f"- Identity/repeat support: {summary.support_gate}",
        f"- Player predictive proper-score/calibration: {summary.player_predictive_gate}",
        f"- Player-neutral deck regret: {summary.neutral_deck_gate}",
        f"- Familiarity earns inclusion: {summary.familiarity_gate}",
        f"- Online/paper nonharm: {summary.venue_gate}", "",
    ]
    if summary.reasons:
        lines.extend(["## Limitations", "", *[f"- {reason}" for reason in summary.reasons], ""])
    lines.extend([
        "## Aggregate fold evidence", "",
        "| Fold | Estimator | Estimand | n | supported | log loss | Brier | calibration | regret |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for fold in summary.folds:
        for item in fold.by_estimator:
            calibration = (
                "n/a" if item.calibration_intercept is None else
                f"{item.calibration_intercept:.3f}/{item.calibration_slope:.3f}"
            )
            lines.append(
                f"| {fold.fold.fold_id} | {item.estimator} | {item.estimand} | "
                f"{item.common_matches} | {item.supported_matches} | "
                f"{'n/a' if item.log_loss is None else f'{item.log_loss:.4f}'} | "
                f"{'n/a' if item.brier is None else f'{item.brier:.4f}'} | {calibration} | "
                f"{'n/a' if item.regret is None else f'{item.regret:.4f}'} |"
            )
        lines.extend(["", f"### {fold.fold.fold_id} support and fit", ""])
        for access in fold.accessibility:
            lines.append(
                f"- `{access.provenance}`: registrations={access.registrations}, "
                f"match sides={access.match_sides}, identity={access.unambiguous_match_rate:.1%}, "
                f"repeat players={access.repeat_players}, familiarity pairs={access.familiarity_pairs}, "
                f"effect-supported={access.effect_supported_match_rate:.1%}; "
                f"reasons={list(access.reasons)}."
            )
        for fit in fold.fit_summaries:
            lines.append(
                f"- `{fit.estimator}` fit: converged={fit.converged}, "
                f"training matches={fit.training_matches}, repeat players={fit.repeat_players}, "
                f"familiarity pairs={fit.familiarity_pairs}, deck q05/q50/q95="
                f"{fit.deck_residual_quantiles}, player={fit.player_effect_quantiles}, "
                f"familiarity={fit.familiarity_quantiles}; reason={fit.reason}."
            )
        for label, items in (
            *[(f"support:{key}", value) for key, value in fold.by_support_stratum.items()],
            *[(f"venue:{key}", value) for key, value in fold.by_provenance.items()],
        ):
            metric = next((item for item in items if (
                item.estimator == "player-intercept"
                and item.estimand == "heldout-event-player-aware"
            )), None)
            if metric is not None:
                lines.append(
                    f"- `{label}`: n={metric.common_matches}, supported={metric.supported_matches}, "
                    f"log loss={metric.log_loss}, Brier={metric.brier}."
                )
        if fold.reasons:
            lines.append(f"- Fold limitations: {list(fold.reasons)}.")
    lines.extend([
        "", "> Even candidate-for-promotion-study requires a new preregistered reviewed feature; "
        "this diagnostic never changes or deploys the headline model.", "",
    ])
    return "\n".join(lines)
