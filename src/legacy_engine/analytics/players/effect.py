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
    FrozenOriginPredictions,
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
