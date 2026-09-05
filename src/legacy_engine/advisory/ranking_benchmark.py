"""Pure contracts and chronological planning for the future-only ranking benchmark."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import Field, model_validator
from scipy.stats import kendalltau

from legacy_engine.models.base import LegacyEngineModel
from legacy_engine.advisory.ranking_measurement import (
    MethodologyVariantSpec,
    RankingCellMeasurement,
)

BenchmarkEstimatorId = Literal[
    "coin-50", "recent-raw-wr", "field-share", "top-finish-conversion",
    "simple-jeffreys-shrinkage", "production-raw", "production-ci-gated",
    "production-ban-scoped", "production-era-only", "production-lean",
]
TaxonomyReplayMode = Literal["contemporaneous", "retrospective-fixed-parent"]
OutcomeExclusionReason = Literal[
    "outside-fold", "mirror", "bye-draw-invalid", "ambiguous-player",
    "unclassified", "emerging-label", "outside-frozen-universe", "card-metadata-unresolved",
]
CardMetadataPolicyMode = Literal["require-complete", "quarantine-unresolved-decks"]
BenchmarkClaimCeiling = Literal["descriptive", "predictive-claim-supported"]

ESTIMATOR_REGISTRY: tuple[BenchmarkEstimatorId, ...] = (
    "coin-50", "recent-raw-wr", "field-share", "top-finish-conversion",
    "simple-jeffreys-shrinkage", "production-raw", "production-ci-gated",
    "production-ban-scoped", "production-era-only", "production-lean",
)
PRODUCTION_ESTIMATORS = frozenset({
    "production-raw", "production-ci-gated", "production-ban-scoped",
    "production-era-only", "production-lean",
})


class EvaluationSupport(LegacyEngineModel):
    min_common_matches: int = 250
    min_events: int = 10
    min_event_dates: int = 4
    min_calibration_matches: int = 500
    min_supported_actions: int = 5
    min_action_matches: int = 8
    min_future_field_coverage: float = 0.80
    min_claim_folds: int = 6
    min_claim_regimes: int = 2


class BenchmarkFold(LegacyEngineModel):
    fold_id: str
    cutoff: str
    evaluation_until: str
    regime_start: str
    regime_end: str | None
    event_dates: tuple[str, ...]


class CardMetadataPolicy(LegacyEngineModel):
    """Explicit, protocol-bound handling for unresolved deck-card metadata."""

    mode: CardMetadataPolicyMode = "require-complete"
    max_deck_fraction: float = 0.0
    max_round_fraction: float = 0.0

    @model_validator(mode="after")
    def _validate_policy(self) -> "CardMetadataPolicy":
        if self.mode == "require-complete":
            if self.max_deck_fraction != 0.0 or self.max_round_fraction != 0.0:
                raise ValueError("require-complete card metadata policy requires zero ceilings")
        elif not 0.0 < self.max_deck_fraction <= 0.005:
            raise ValueError("quarantine max_deck_fraction must be in (0, 0.005]")
        elif not 0.0 < self.max_round_fraction <= 0.02:
            raise ValueError("quarantine max_round_fraction must be in (0, 0.02]")
        return self


class QuarantinedDeck(LegacyEngineModel):
    tournament_id: str
    deck_idx: int
    player_key: str | None
    event_date: str
    source: str
    event_uri: str
    unresolved_names: tuple[str, ...]
    identity_ambiguous: bool = False


class CardMetadataQuarantineLedger(LegacyEngineModel):
    policy: CardMetadataPolicy
    raw_decks: int
    retained_decks: int
    raw_rounds: int
    retained_rounds: int
    excluded_decks: tuple[QuarantinedDeck, ...]
    excluded_round_keys: tuple[tuple[str, int], ...]
    deck_fraction: float
    round_fraction: float
    counts_by_source: dict[str, dict[str, int]]
    within_ceiling: bool
    reasons: tuple[str, ...]
    snapshot_source_fingerprint: str | None = None
    retained_facts_sha256: str | None = None

    @property
    def digest(self) -> str:
        # The ledger identity is deliberately pre-outcome.  The retained-corpus hash is
        # a separate coherence check and may legitimately change when labels/results change.
        return content_sha256(self.model_dump(mode="json", exclude={"retained_facts_sha256"}))


class BenchmarkProtocol(LegacyEngineModel):
    protocol_id: str
    created_at: str
    taxonomy_mode: TaxonomyReplayMode
    first_cutoff: str
    final_evaluation_until: str
    horizon_days: int = 28
    step_days: int = 28
    primary_estimator: BenchmarkEstimatorId = "production-ci-gated"
    estimator_ids: tuple[BenchmarkEstimatorId, ...] = ESTIMATOR_REGISTRY
    action_min_share: float = 0.001
    log_clip_epsilon: float = 1e-6
    bootstrap_draws: int = 2_000
    seed: int = 730_021
    support: EvaluationSupport = Field(default_factory=EvaluationSupport)
    planned_folds: tuple[BenchmarkFold, ...] = ()
    ban_events_as_of: tuple[tuple[str, str, str], ...] = ()
    registered_at: str | None = None
    claim_ceiling: BenchmarkClaimCeiling = "predictive-claim-supported"
    card_metadata: CardMetadataPolicy = Field(default_factory=CardMetadataPolicy)

    @model_validator(mode="after")
    def _validate_protocol(self) -> "BenchmarkProtocol":
        first = date.fromisoformat(self.first_cutoff)
        final = date.fromisoformat(self.final_evaluation_until)
        created = datetime.fromisoformat(self.created_at.replace("Z", "+00:00"))
        if created.date() > first and self.card_metadata.mode == "require-complete":
            raise ValueError("created_at must be no later than first_cutoff")
        if self.card_metadata.mode == "quarantine-unresolved-decks":
            if self.registered_at is None:
                raise ValueError("quarantine protocols require registered_at")
            registered = datetime.fromisoformat(self.registered_at.replace("Z", "+00:00"))
            if registered.tzinfo is None:
                raise ValueError("registered_at must include an explicit timezone")
            first_instant = datetime.combine(first, datetime.min.time(), tzinfo=registered.tzinfo)
            if registered >= first_instant and self.claim_ceiling != "descriptive":
                raise ValueError(
                    "quarantine protocols registered at or after first_cutoff must have descriptive claim ceiling"
                )
        if final <= first:
            raise ValueError("final_evaluation_until must be after first_cutoff")
        if self.horizon_days < 1 or self.step_days < 1:
            raise ValueError("horizon_days and step_days must be positive")
        if self.bootstrap_draws < 1:
            raise ValueError("bootstrap_draws must be positive")
        if not 0.0 <= self.action_min_share <= 1.0:
            raise ValueError("action_min_share must be in [0, 1]")
        if not 0.0 < self.log_clip_epsilon < 0.5:
            raise ValueError("log_clip_epsilon must be in (0, 0.5)")
        if tuple(self.estimator_ids) != ESTIMATOR_REGISTRY:
            raise ValueError("estimator_ids must equal the preregistered estimator registry")
        if self.primary_estimator != "production-ci-gated":
            raise ValueError("primary_estimator must be production-ci-gated")
        if self.planned_folds:
            if tuple(fold.fold_id for fold in self.planned_folds) != tuple(
                dict.fromkeys(fold.fold_id for fold in self.planned_folds)
            ):
                raise ValueError("planned fold ids must be unique")
            if self.planned_folds[0].cutoff != self.first_cutoff:
                raise ValueError("planned folds must begin at first_cutoff")
            if self.planned_folds[-1].evaluation_until != self.final_evaluation_until:
                raise ValueError("planned folds must end at final_evaluation_until")
        return self


class TaxonomySnapshotManifest(LegacyEngineModel):
    source: str
    effective_at: str
    action_level: Literal["parent"] = "parent"
    rules_manifest: str
    rules_sha256: str
    labels_sha256: str | None = None


class SnapshotManifest(LegacyEngineModel):
    protocol_hash: str
    fold: BenchmarkFold
    training_source_fingerprint: str
    training_facts_sha256: str
    training_event_ids_sha256: str
    training_events: int
    training_decks: int
    training_decisive_matches: int
    max_training_event_date: str
    ban_ledger_sha256: str
    ban_events_as_of: tuple[tuple[str, str, str], ...]
    taxonomy_mode: TaxonomyReplayMode
    taxonomy_effective_at: str | None
    taxonomy_sha256: str
    rules_sha256: str
    color_splits_sha256: str | None = None
    card_availability_sha256: str
    degraded: bool
    reasons: tuple[str, ...]
    card_metadata_quarantine: CardMetadataQuarantineLedger | None = None
    card_metadata_quarantine_sha256: str | None = None


class FrozenMatchupPrediction(LegacyEngineModel):
    estimator: BenchmarkEstimatorId
    subject: str
    opponent: str
    probability: float
    served: bool
    source_kind: str
    imputed: bool
    refusal_reason: str | None

    @model_validator(mode="after")
    def _validate_probability(self) -> "FrozenMatchupPrediction":
        if not math.isfinite(self.probability) or not 0.0 <= self.probability <= 1.0:
            raise ValueError("frozen matchup probability must be finite and in [0, 1]")
        return self


class FrozenRecommendation(LegacyEngineModel):
    estimator: BenchmarkEstimatorId
    chosen_action: str | None
    ranked_actions: tuple[str, ...]
    scores: dict[str, float | None]
    served: bool
    refusal_reason: str | None


class FrozenOriginPredictions(LegacyEngineModel):
    protocol_hash: str
    snapshot_manifest_sha256: str
    fold: BenchmarkFold
    taxonomy_mode: TaxonomyReplayMode
    taxonomy_effective_at: str | None
    taxonomy_sha256: str
    rules_sha256: str
    generated_at: str
    code_commit: str
    estimator_registry: tuple[BenchmarkEstimatorId, ...]
    action_universe: tuple[str, ...]
    field_shares: dict[str, float]
    matchup_predictions: tuple[FrozenMatchupPrediction, ...]
    recommendations: tuple[FrozenRecommendation, ...]
    methodology: dict[str, dict[str, object]]
    seeds: dict[str, int]


class ExternalRankingSnapshot(LegacyEngineModel):
    source: str
    observed_at: str
    taxonomy: str
    ranks: dict[str, int] = Field(default_factory=dict)
    scores: dict[str, float] = Field(default_factory=dict)
    matchup_probabilities: dict[str, float] = Field(default_factory=dict)


class HeldoutMatch(LegacyEngineModel):
    event_id: str
    match_idx: int | None = None
    event_date: str
    provenance: str
    subject: str | None
    opponent: str | None
    subject_player_key: str | None
    opponent_player_key: str | None
    subject_won: bool | None
    exclusion_reason: OutcomeExclusionReason | None


class HeldoutDeck(LegacyEngineModel):
    event_id: str
    event_date: str
    provenance: str
    archetype: str | None
    exclusion_reason: Literal[
        "unclassified", "emerging-label", "outside-frozen-universe", "card-metadata-unresolved",
    ] | None


class HeldoutOutcomes(LegacyEngineModel):
    matches: tuple[HeldoutMatch, ...]
    decks: tuple[HeldoutDeck, ...]
    card_metadata_quarantine: CardMetadataQuarantineLedger | None = None
    card_metadata_quarantine_sha256: str | None = None


class FieldCoverageLedger(LegacyEngineModel):
    eligible_decks: int
    classified_decks: int
    covered_decks: int
    future_field_coverage: float
    counts_by_action: dict[str, int]
    exclusions: dict[str, int]


class SupportVerdict(LegacyEngineModel):
    evaluable: bool
    reasons: tuple[str, ...]
    matches: int
    events: int
    event_dates: int
    supported_actions: int
    future_field_coverage: float


class EstimatorEvaluation(LegacyEngineModel):
    estimator: str
    common_matches: int
    served_matches: int
    log_loss: float | None
    brier: float | None
    calibration_intercept: float | None
    calibration_slope: float | None
    cumulative_calibration: tuple[float, ...]
    rank_tau: float | None
    top3_hit: bool | None
    regret: float | None
    regret_ci: tuple[float, float] | None
    regret_censor_reason: Literal[
        "insufficient-support", "practical-tie", "unstable-oracle", "unavailable-recommendation",
    ] | None = None
    oracle_action: str | None = None
    eligible_matches: int = 0
    common_case_coverage: float = 0.0
    missing_actions: tuple[str, ...] = ()
    support: SupportVerdict


class BenchmarkEvaluation(LegacyEngineModel):
    protocol_hash: str
    predictions_sha256: str
    evaluation_data_sha256: str
    fold: BenchmarkFold
    exclusions: dict[OutcomeExclusionReason, int]
    estimators: tuple[EstimatorEvaluation, ...]
    external: tuple[EstimatorEvaluation, ...]
    status: Literal["not-evaluable", "descriptive", "predictive-claim-supported"]
    reasons: tuple[str, ...]
    player_sensitivity_reason: str | None = None
    player_sensitivity: dict[str, float] | None = None
    paired_log_loss_differences: dict[str, dict[str, float | None]] = Field(default_factory=dict)
    field_coverage: FieldCoverageLedger | None = None
    card_metadata_quarantine: CardMetadataQuarantineLedger | None = None


class BenchmarkEvaluationSummary(LegacyEngineModel):
    protocol_hash: str
    folds: tuple[BenchmarkEvaluation, ...]
    evaluable_folds: int
    represented_regimes: int
    paired_differences: dict[str, dict[str, float | None]]
    status: Literal["not-evaluable", "descriptive", "predictive-claim-supported"]
    reasons: tuple[str, ...]
    claim_ceiling: BenchmarkClaimCeiling = "predictive-claim-supported"

    @model_validator(mode="after")
    def _validate_claim_ceiling(self) -> "BenchmarkEvaluationSummary":
        if self.claim_ceiling == "descriptive" and self.status == "predictive-claim-supported":
            raise ValueError("summary status exceeds descriptive claim ceiling")
        return self


def canonical_json_bytes(value: object) -> bytes:
    """Stable, finite JSON encoding used by every benchmark hash boundary."""
    if isinstance(value, LegacyEngineModel):
        value = value.model_dump(mode="json")
        # Additive quarantine fields must not perturb strict/v1 artifact bytes when absent.
        if isinstance(value, dict):
            if value.get("card_metadata_quarantine") is None:
                value.pop("card_metadata_quarantine", None)
            if value.get("card_metadata_quarantine_sha256") is None:
                value.pop("card_metadata_quarantine_sha256", None)
            if value.get("color_splits_sha256") is None:
                value.pop("color_splits_sha256", None)
            if value.get("match_idx") is None:
                value.pop("match_idx", None)
            if value.get("claim_ceiling") == "predictive-claim-supported":
                value.pop("claim_ceiling", None)
    return (json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False,
    ) + "\n").encode()


def content_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def protocol_sha256(protocol: BenchmarkProtocol) -> str:
    # v1 protocol bytes predate the additive quarantine fields.  Omitting only their
    # defaults preserves the v1 digest while any declared policy/ceiling still binds
    # the protocol hash as a new immutable experiment.
    payload = protocol.model_dump(mode="json")
    if (
        protocol.registered_at is None
        and protocol.claim_ceiling == "predictive-claim-supported"
        and protocol.card_metadata == CardMetadataPolicy()
    ):
        payload.pop("registered_at", None)
        payload.pop("claim_ceiling", None)
        payload.pop("card_metadata", None)
    return content_sha256(payload)


def validate_quarantine_ledger(
    ledger: CardMetadataQuarantineLedger | None,
    *,
    policy: CardMetadataPolicy,
    declared_digest: str | None = None,
    retained_facts_sha256: str | None = None,
) -> None:
    """Validate the typed ledger/policy and its independent retained-corpus binding."""
    if policy.mode == "quarantine-unresolved-decks":
        if ledger is None:
            raise ValueError("quarantine protocol requires a card metadata ledger")
        if ledger.policy != policy:
            raise ValueError("card metadata ledger policy does not match protocol")
        if not ledger.within_ceiling:
            raise ValueError("card metadata quarantine ledger failed its declared ceilings")
        if declared_digest is not None and declared_digest != ledger.digest:
            raise ValueError("card metadata quarantine ledger digest mismatch")
        if retained_facts_sha256 is not None and ledger.retained_facts_sha256 != retained_facts_sha256:
            raise ValueError("card metadata quarantine retained-corpus hash mismatch")
    elif ledger is not None:
        raise ValueError("strict protocol cannot carry a card metadata quarantine ledger")


def plan_card_metadata_quarantine(
    con,
    *,
    start: str | None,
    end: str,
    policy: CardMetadataPolicy,
) -> CardMetadataQuarantineLedger:
    """Plan whole-deck exclusions from card closure, before labels or outcomes are read."""
    if policy.mode == "require-complete":
        unresolved = con.execute(
            """SELECT count(*) FROM deck_cards dc JOIN decks d
               ON d.tournament_id=dc.tournament_id AND d.deck_idx=dc.deck_idx
               JOIN tournaments t ON t.id=d.tournament_id
               LEFT JOIN cards c ON c.name=dc.name
               WHERE substr(t.date,1,10) < ?
                 AND (? IS NULL OR substr(t.date,1,10) >= ?)
                 AND c.name IS NULL""", [end, start, start],
        ).fetchone()[0]
        if unresolved:
            raise ValueError(
                f"benchmark has {unresolved} deck-card rows without observed card metadata"
            )
        return CardMetadataQuarantineLedger(
            policy=policy, raw_decks=0, retained_decks=0, raw_rounds=0, retained_rounds=0,
            excluded_decks=(), excluded_round_keys=(), deck_fraction=0.0, round_fraction=0.0,
            counts_by_source={}, within_ceiling=True, reasons=(),
        )

    date_clause = "substr(t.date,1,10) < ? AND (? IS NULL OR substr(t.date,1,10) >= ?)"
    deck_rows = con.execute(
        f"""SELECT d.tournament_id, d.deck_idx, d.player, substr(t.date,1,10),
                   coalesce(t.source,''), coalesce(t.uri,'')
            FROM decks d JOIN tournaments t ON t.id=d.tournament_id
            WHERE {date_clause} ORDER BY t.date, d.tournament_id, d.deck_idx""",
        [end, start, start],
    ).fetchall()
    card_rows = con.execute(
        f"""SELECT dc.tournament_id, dc.deck_idx, dc.name
            FROM deck_cards dc JOIN tournaments t ON t.id=dc.tournament_id
            LEFT JOIN cards c ON c.name=dc.name
            WHERE {date_clause} AND c.name IS NULL
            ORDER BY dc.tournament_id, dc.deck_idx, dc.name""",
        [end, start, start],
    ).fetchall()
    unresolved_by_deck: dict[tuple[str, int], set[str]] = {}
    for tournament_id, deck_idx, name in card_rows:
        unresolved_by_deck.setdefault((str(tournament_id), int(deck_idx)), set()).add(str(name))

    duplicate_rows = con.execute(
        f"""SELECT d.tournament_id, lower(trim(d.player)) AS player_key
            FROM decks d JOIN tournaments t ON t.id=d.tournament_id
            WHERE {date_clause}
            GROUP BY d.tournament_id, lower(trim(d.player)) HAVING count(*) > 1
            ORDER BY d.tournament_id, player_key""",
        [end, start, start],
    ).fetchall()
    duplicate_keys = {(str(event), str(player)) for event, player in duplicate_rows}
    affected_event_ids: set[str] = set()
    affected_keys = {
        (event, str(player).strip().lower())
        for (event, deck_idx), names in unresolved_by_deck.items()
        for _event, _idx, player, _date, _source, _uri in deck_rows
        if _event == event and int(_idx) == deck_idx and str(player or "").strip()
    }
    excluded_decks: list[QuarantinedDeck] = []
    for event, deck_idx, player, event_date, source, event_uri in deck_rows:
        key = (str(event), int(deck_idx))
        names = unresolved_by_deck.get(key)
        if not names:
            continue
        player_key = str(player).strip().lower() or None
        player_key = str(player or "").strip().lower() or None
        identity_ambiguous = player_key is None or (str(event), player_key) in duplicate_keys
        if identity_ambiguous:
            # No tournament-local identity can safely join this deck to one round.  Remove
            # every event round rather than allowing a blank/ambiguous key to understate support.
            affected_event_ids.add(str(event))
        excluded_decks.append(QuarantinedDeck(
            tournament_id=str(event), deck_idx=int(deck_idx), player_key=player_key,
            event_date=str(event_date), source=str(source), event_uri=str(event_uri),
            unresolved_names=tuple(sorted(names)),
            identity_ambiguous=identity_ambiguous,
        ))
    # Any duplicate key touching a quarantined deck is unsafe for every round using it.
    affected_keys |= {
        (deck.tournament_id, deck.player_key)
        for deck in excluded_decks if deck.player_key is not None and deck.identity_ambiguous
    }
    round_rows = con.execute(
        f"""SELECT r.tournament_id, r.match_idx, lower(trim(coalesce(r.player1,''))),
                   lower(trim(coalesce(r.player2,''))), coalesce(t.source,'')
            FROM rounds r JOIN tournaments t ON t.id=r.tournament_id
            WHERE {date_clause} ORDER BY t.date, r.tournament_id, r.match_idx""",
        [end, start, start],
    ).fetchall()
    excluded_round_keys = tuple(sorted(
        (str(event), int(match_idx)) for event, match_idx, player1, player2, _source in round_rows
        if str(event) in affected_event_ids
        or (str(event), str(player1)) in affected_keys
        or (str(event), str(player2)) in affected_keys
    ))
    raw_decks, raw_rounds = len(deck_rows), len(round_rows)
    deck_fraction = len(excluded_decks) / raw_decks if raw_decks else 0.0
    round_fraction = len(excluded_round_keys) / raw_rounds if raw_rounds else 0.0
    reasons: list[str] = []
    if deck_fraction > policy.max_deck_fraction:
        reasons.append(
            f"quarantined deck fraction {deck_fraction:.3%} exceeds ceiling {policy.max_deck_fraction:.3%}"
        )
    if round_fraction > policy.max_round_fraction:
        reasons.append(
            f"quarantined round fraction {round_fraction:.3%} exceeds ceiling {policy.max_round_fraction:.3%}"
        )
    counts_by_source: dict[str, dict[str, int]] = {}
    excluded_deck_keys = {(d.tournament_id, d.deck_idx) for d in excluded_decks}
    excluded_round_set = set(excluded_round_keys)
    for event, _idx, _player, _date, source, _uri in deck_rows:
        stats = counts_by_source.setdefault(str(source), {
            "raw_decks": 0, "retained_decks": 0, "raw_rounds": 0, "retained_rounds": 0,
        })
        stats["raw_decks"] += 1
        if (str(event), int(_idx)) not in excluded_deck_keys:
            stats["retained_decks"] += 1
    for event, match_idx, _p1, _p2, source in round_rows:
        stats = counts_by_source.setdefault(str(source), {
            "raw_decks": 0, "retained_decks": 0, "raw_rounds": 0, "retained_rounds": 0,
        })
        stats["raw_rounds"] += 1
        if (str(event), int(match_idx)) not in excluded_round_set:
            stats["retained_rounds"] += 1
    return CardMetadataQuarantineLedger(
        policy=policy, raw_decks=raw_decks, retained_decks=raw_decks - len(excluded_decks),
        raw_rounds=raw_rounds, retained_rounds=raw_rounds - len(excluded_round_keys),
        excluded_decks=tuple(excluded_decks), excluded_round_keys=excluded_round_keys,
        deck_fraction=deck_fraction, round_fraction=round_fraction,
        counts_by_source=dict(sorted(counts_by_source.items())), within_ceiling=not reasons,
        reasons=tuple(reasons), snapshot_source_fingerprint=content_sha256({
            # Only card/deck/event/player dimensions enter the ledger identity.  Results,
            # standings, stored labels, and any parsed outcome are intentionally absent.
            "events": [
                [row[0], row[1], row[2], row[3]]
                for row in con.execute(
                    f"SELECT t.id, substr(t.date,1,10), coalesce(t.uri,''), coalesce(t.source,'') "
                    f"FROM tournaments t WHERE {date_clause} ORDER BY 1",
                    [end, start, start],
                ).fetchall()
            ],
            "decks": [[row[0], row[1], row[2]] for row in deck_rows],
            "deck_cards": [list(row) for row in con.execute(
                f"SELECT dc.tournament_id, dc.deck_idx, dc.board, dc.name, dc.count "
                f"FROM deck_cards dc JOIN tournaments t ON t.id=dc.tournament_id "
                f"WHERE {date_clause} ORDER BY 1,2,3,4,5", [end, start, start],
            ).fetchall()],
            "rounds": [list(row[:4]) for row in round_rows],
            "cards": [row[0] for row in con.execute(
                f"SELECT DISTINCT dc.name FROM deck_cards dc JOIN tournaments t "
                f"ON t.id=dc.tournament_id WHERE {date_clause} ORDER BY dc.name",
                [end, start, start],
            ).fetchall()],
        }),
    )


_VARIANT_ESTIMATOR: dict[str, BenchmarkEstimatorId] = {
    "raw": "production-raw",
    "ci-gated": "production-ci-gated",
    "ban-scoped": "production-ban-scoped",
    "era-only": "production-era-only",
}


def project_matchup_probability(
    cell: RankingCellMeasurement,
    *,
    spec: MethodologyVariantSpec,
    unresolved_center: float = 0.5,
) -> FrozenMatchupPrediction:
    """Project one typed production cell without turning imputation into serving authority."""
    if not 0.0 <= unresolved_center <= 1.0:
        raise ValueError("unresolved_center must be in [0, 1]")
    source = {
        "selected": cell.selected,
        "fallback": cell.fallback,
        "era": cell.era,
    }[spec.source_policy]
    estimator = _VARIANT_ESTIMATOR[spec.id]
    value = None
    if source is not None:
        value = source.cell.p_raw if spec.rate_basis == "raw" else source.cell.p_shrunk
    resolved = source is not None and source.cell.n > 0 and value is not None
    served = resolved and source.cell.n >= spec.evidence_n
    return FrozenMatchupPrediction(
        estimator=estimator, subject=cell.subject, opponent=cell.opponent,
        probability=float(value) if resolved else unresolved_center,
        served=served,
        source_kind=source.kind if source is not None else "unresolved",
        imputed=not resolved,
        refusal_reason=None if served else (
            f"source evidence n={source.cell.n} below n={spec.evidence_n}"
            if resolved else "no frozen matchup evidence; explicit 0.5 forecast"
        ),
    )


def write_frozen_predictions(path: Path, predictions: FrozenOriginPredictions) -> str:
    return atomic_write_canonical(path, predictions)


def atomic_write_text(path: Path, text: str) -> None:
    payload = text.encode()
    if path.exists():
        if path.read_bytes() == payload:
            return
        raise FileExistsError(f"refusing to overwrite different artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        import os
        os.fsync(handle.fileno())
    temporary.replace(path)


def _field_coverage_ledger(
    decks: Sequence[HeldoutDeck], universe: set[str],
) -> FieldCoverageLedger:
    exclusions = {
        "unclassified": 0, "emerging-label": 0, "outside-frozen-universe": 0,
        "card-metadata-unresolved": 0,
    }
    counts: dict[str, int] = {}
    classified = covered = 0
    for deck in decks:
        if deck.exclusion_reason == "card-metadata-unresolved":
            exclusions["card-metadata-unresolved"] += 1
            continue
        if deck.archetype is None:
            exclusions["unclassified"] += 1
            continue
        classified += 1
        if deck.archetype in universe:
            covered += 1
            counts[deck.archetype] = counts.get(deck.archetype, 0) + 1
        else:
            reason = deck.exclusion_reason or "outside-frozen-universe"
            exclusions[reason] += 1
    return FieldCoverageLedger(
        eligible_decks=len(decks), classified_decks=classified, covered_decks=covered,
        future_field_coverage=covered / classified if classified else 0.0,
        counts_by_action=dict(sorted(counts.items())), exclusions=exclusions,
    )


def _support_verdict(
    matches: Sequence[HeldoutMatch], protocol: BenchmarkProtocol,
    field_coverage: FieldCoverageLedger | None = None,
) -> SupportVerdict:
    common = [match for match in matches if match.exclusion_reason is None]
    events = {match.event_id for match in common}
    dates = {match.event_date for match in common}
    action_n: dict[str, int] = {}
    for match in common:
        for action in (match.subject, match.opponent):
            if action is not None:
                action_n[action] = action_n.get(action, 0) + 1
    supported = sum(value >= protocol.support.min_action_matches for value in action_n.values())
    if field_coverage is None:
        # Compatibility for direct pure-function callers. Workflow evaluation always supplies
        # the deck ledger, whose denominator is independent of match activity.
        classified = [
            match for match in matches
            if match.subject is not None and match.opponent is not None
            and match.exclusion_reason not in {"bye-draw-invalid", "ambiguous-player", "unclassified"}
        ]
        future_coverage = len(common) / len(classified) if classified else 0.0
    else:
        future_coverage = field_coverage.future_field_coverage
    reasons: list[str] = []
    if len(common) < protocol.support.min_common_matches:
        reasons.append(f"common decisive matches {len(common)} < {protocol.support.min_common_matches}")
    if len(events) < protocol.support.min_events:
        reasons.append(f"events {len(events)} < {protocol.support.min_events}")
    if len(dates) < protocol.support.min_event_dates:
        reasons.append(f"event dates {len(dates)} < {protocol.support.min_event_dates}")
    if supported < protocol.support.min_supported_actions:
        reasons.append(f"future-supported actions {supported} < {protocol.support.min_supported_actions}")
    if future_coverage < protocol.support.min_future_field_coverage:
        reasons.append(
            f"future classified field coverage {future_coverage:.1%} < "
            f"{protocol.support.min_future_field_coverage:.1%}"
        )
    return SupportVerdict(
        evaluable=not reasons, reasons=tuple(reasons), matches=len(common), events=len(events),
        event_dates=len(dates), supported_actions=supported, future_field_coverage=future_coverage,
    )


def _calibration(probabilities: np.ndarray, outcomes: np.ndarray, minimum: int):
    cumulative: list[float] = []
    order = np.argsort(probabilities)
    for indexes in np.array_split(order, min(10, len(order))):
        if len(indexes):
            cumulative.append(float(np.mean(outcomes[indexes] - probabilities[indexes])))
    if len(probabilities) < minimum or len(set(outcomes.tolist())) < 2:
        return None, None, tuple(cumulative)
    clipped = np.clip(probabilities, 1e-6, 1.0 - 1e-6)
    logits = np.log(clipped / (1.0 - clipped))
    if float(np.ptp(logits)) == 0.0:
        return None, None, tuple(cumulative)
    # A deterministic logistic calibration fit; failures remain honest nulls.
    try:
        import statsmodels.api as sm
        fitted = sm.GLM(
            outcomes, sm.add_constant(logits), family=sm.families.Binomial(),
        ).fit(disp=0)
        return float(fitted.params[0]), float(fitted.params[1]), tuple(cumulative)
    except (IndexError, ValueError, np.linalg.LinAlgError):
        return None, None, tuple(cumulative)


def _realized_utilities(
    matches: Sequence[HeldoutMatch], field_counts: Mapping[str, int] | None = None,
) -> tuple[dict[str, float], dict[str, int]]:
    pair_wins: dict[tuple[str, str], int] = {}
    pair_totals: dict[tuple[str, str], int] = {}
    totals: dict[str, int] = {}
    for match in matches:
        if match.exclusion_reason is not None or match.subject is None or match.opponent is None:
            continue
        for action in (match.subject, match.opponent):
            totals[action] = totals.get(action, 0) + 1
        for subject, opponent, won in (
            (match.subject, match.opponent, bool(match.subject_won)),
            (match.opponent, match.subject, not bool(match.subject_won)),
        ):
            key = (subject, opponent)
            pair_totals[key] = pair_totals.get(key, 0) + 1
            pair_wins[key] = pair_wins.get(key, 0) + int(won)
    field = dict(field_counts or {action: count for action, count in totals.items()})
    field_total = sum(field.values())
    utilities: dict[str, float] = {}
    if field_total:
        for action in totals:
            weighted = 0.5 * field.get(action, 0)  # structural mirror utility
            mass = field.get(action, 0)
            for opponent, count in field.items():
                if opponent == action:
                    continue
                pair_n = pair_totals.get((action, opponent), 0)
                if pair_n:
                    weighted += (pair_wins.get((action, opponent), 0) / pair_n) * count
                    mass += count
            if mass:
                utilities[action] = weighted / mass
    return utilities, totals


def _decision_metrics(
    recommendation: FrozenRecommendation,
    matches: Sequence[HeldoutMatch],
    protocol: BenchmarkProtocol,
    field_counts: Mapping[str, int] | None = None,
) -> tuple[
    float | None, bool | None, float | None, tuple[float, float] | None, str | None, str | None,
]:
    utilities, totals = _realized_utilities(matches, field_counts)
    supported = {
        action: utility for action, utility in utilities.items()
        if totals[action] >= protocol.support.min_action_matches
    }
    if len(supported) < protocol.support.min_supported_actions:
        return None, None, None, None, "insufficient-support", None
    ordered_oracle = sorted(supported, key=lambda action: (-supported[action], action))
    if len(ordered_oracle) > 1 and supported[ordered_oracle[0]] - supported[ordered_oracle[1]] <= 0.01:
        return None, None, None, None, "practical-tie", None
    oracle = ordered_oracle[0]
    predicted = [action for action in recommendation.ranked_actions if action in supported]
    if len(predicted) < 2 or recommendation.chosen_action not in supported:
        return None, None, None, None, "unavailable-recommendation", oracle
    predicted_positions = {action: index for index, action in enumerate(predicted)}
    common_actions = sorted(set(predicted) & set(supported))
    tau = kendalltau(
        [predicted_positions[action] for action in common_actions],
        [-supported[action] for action in common_actions],
    ).statistic
    rank_tau = float(tau) if math.isfinite(float(tau)) else None
    top3 = oracle in predicted[:3]
    regret = supported[oracle] - supported[recommendation.chosen_action]

    blocks: dict[str, list[HeldoutMatch]] = {}
    for match in matches:
        if match.exclusion_reason is None:
            blocks.setdefault(match.event_id, []).append(match)
    rng = np.random.default_rng(protocol.seed)
    event_ids = sorted(blocks)
    regrets: list[float] = []
    oracle_winners: list[str] = []
    for _ in range(protocol.bootstrap_draws):
        sampled_ids = rng.choice(event_ids, size=len(event_ids), replace=True)
        sample = [match for event_id in sampled_ids for match in blocks[str(event_id)]]
        sample_utilities, sample_totals = _realized_utilities(sample, field_counts)
        sample_supported = {
            action: utility for action, utility in sample_utilities.items()
            if sample_totals[action] >= protocol.support.min_action_matches
        }
        chosen = recommendation.chosen_action
        if chosen in sample_supported and sample_supported:
            sample_oracle = min(
                sample_supported, key=lambda action: (-sample_supported[action], action),
            )
            oracle_winners.append(sample_oracle)
            regrets.append(sample_supported[sample_oracle] - sample_supported[chosen])
    interval = None
    if regrets:
        low, high = np.quantile(regrets, [0.025, 0.975])
        interval = (float(low), float(high))
    stable_share = oracle_winners.count(oracle) / len(oracle_winners) if oracle_winners else 0.0
    if interval is None or stable_share < 0.80:
        return rank_tau, top3, None, None, "unstable-oracle", oracle
    return rank_tau, top3, regret, interval, None, oracle


def _evaluate_estimator(
    estimator: str,
    lookup: Mapping[tuple[str, str], FrozenMatchupPrediction],
    recommendation: FrozenRecommendation,
    matches: Sequence[HeldoutMatch],
    protocol: BenchmarkProtocol,
    support: SupportVerdict,
    field_counts: Mapping[str, int] | None = None,
) -> EstimatorEvaluation:
    common = [match for match in matches if match.exclusion_reason is None]
    probabilities: list[float] = []
    outcomes: list[float] = []
    served = 0
    for match in common:
        prediction = lookup[(match.subject, match.opponent)]
        probabilities.append(prediction.probability)
        outcomes.append(1.0 if match.subject_won else 0.0)
        served += prediction.served
    if probabilities:
        p = np.asarray(probabilities, dtype=float)
        y = np.asarray(outcomes, dtype=float)
        clipped = np.clip(p, protocol.log_clip_epsilon, 1.0 - protocol.log_clip_epsilon)
        log_loss = float(np.mean(-(y * np.log(clipped) + (1.0 - y) * np.log(1.0 - clipped))))
        brier = float(np.mean((p - y) ** 2))
        intercept, slope, cumulative = _calibration(p, y, protocol.support.min_calibration_matches)
    else:
        log_loss = brier = intercept = slope = None
        cumulative = ()
    tau, top3, regret, regret_ci, regret_reason, oracle = _decision_metrics(
        recommendation, common, protocol, field_counts,
    )
    return EstimatorEvaluation(
        estimator=estimator, common_matches=len(common), served_matches=served,
        log_loss=log_loss, brier=brier, calibration_intercept=intercept,
        calibration_slope=slope, cumulative_calibration=cumulative, rank_tau=tau,
        top3_hit=top3, regret=regret, regret_ci=regret_ci, support=support,
        regret_censor_reason=regret_reason, oracle_action=oracle,
        eligible_matches=len(common), common_case_coverage=1.0 if common else 0.0,
    )


def _paired_event_log_loss(
    predictions: FrozenOriginPredictions,
    matches: Sequence[HeldoutMatch],
    protocol: BenchmarkProtocol,
) -> dict[str, dict[str, float | None]]:
    common = [match for match in matches if match.exclusion_reason is None]
    lookup = {
        (item.estimator, item.subject, item.opponent): item.probability
        for item in predictions.matchup_predictions
    }

    def loss(estimator: str, match: HeldoutMatch) -> float:
        probability = np.clip(
            lookup[(estimator, match.subject, match.opponent)],
            protocol.log_clip_epsilon, 1.0 - protocol.log_clip_epsilon,
        )
        outcome = 1.0 if match.subject_won else 0.0
        return float(-(outcome * np.log(probability) + (1.0 - outcome) * np.log(1.0 - probability)))

    blocks: dict[str, list[HeldoutMatch]] = {}
    for match in common:
        blocks.setdefault(match.event_id, []).append(match)
    output: dict[str, dict[str, float | None]] = {}
    for baseline in ("coin-50", "recent-raw-wr", "simple-jeffreys-shrinkage"):
        event_differences = [
            float(np.mean([
                loss(protocol.primary_estimator, match) - loss(baseline, match)
                for match in blocks[event_id]
            ])) for event_id in sorted(blocks)
        ]
        if not event_differences:
            output[baseline] = {"mean": None, "ci_low": None, "ci_high": None}
            continue
        rng = np.random.default_rng(protocol.seed)
        draws = [
            float(np.mean(rng.choice(event_differences, size=len(event_differences), replace=True)))
            for _ in range(protocol.bootstrap_draws)
        ]
        low, high = np.quantile(draws, [0.025, 0.975])
        output[baseline] = {
            "mean": float(np.mean(event_differences)),
            "ci_low": float(low), "ci_high": float(high),
        }
    return output


def _player_component_sensitivity(
    predictions: FrozenOriginPredictions,
    matches: Sequence[HeldoutMatch],
    protocol: BenchmarkProtocol,
) -> dict[str, float] | None:
    eligible = [
        match for match in matches if match.exclusion_reason is None
        and match.subject_player_key is not None and match.opponent_player_key is not None
    ]
    if not eligible:
        return None
    parent: dict[str, str] = {}

    def find(value: str) -> str:
        parent.setdefault(value, value)
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    for match in eligible:
        union(match.subject_player_key, match.opponent_player_key)
    blocks: dict[str, list[HeldoutMatch]] = {}
    for match in eligible:
        blocks.setdefault(find(match.subject_player_key), []).append(match)
    lookup = {
        (item.subject, item.opponent): item.probability
        for item in predictions.matchup_predictions
        if item.estimator == protocol.primary_estimator
    }

    def mean_loss(rows: Sequence[HeldoutMatch]) -> float:
        values = []
        for match in rows:
            probability = np.clip(
                lookup[(match.subject, match.opponent)],
                protocol.log_clip_epsilon, 1.0 - protocol.log_clip_epsilon,
            )
            outcome = 1.0 if match.subject_won else 0.0
            values.append(-(outcome * np.log(probability) + (1.0 - outcome) * np.log(1.0 - probability)))
        return float(np.mean(values))

    block_ids = sorted(blocks)
    rng = np.random.default_rng(protocol.seed)
    draws = []
    for _ in range(protocol.bootstrap_draws):
        sampled = rng.choice(block_ids, size=len(block_ids), replace=True)
        draws.append(mean_loss([row for block_id in sampled for row in blocks[str(block_id)]]))
    low, high = np.quantile(draws, [0.025, 0.975])
    return {
        "identity_coverage": len(eligible) / max(1, sum(match.exclusion_reason is None for match in matches)),
        "components": float(len(blocks)),
        "primary_log_loss_ci_low": float(low),
        "primary_log_loss_ci_high": float(high),
    }


def _external_evaluation(
    snapshot: ExternalRankingSnapshot,
    predictions: FrozenOriginPredictions,
    matches: Sequence[HeldoutMatch],
    protocol: BenchmarkProtocol,
    field_counts: Mapping[str, int] | None = None,
) -> EstimatorEvaluation:
    observed = datetime.fromisoformat(snapshot.observed_at.replace("Z", "+00:00")).date()
    if observed > date.fromisoformat(predictions.fold.cutoff):
        raise ValueError(f"external snapshot {snapshot.source!r} is future-dated")
    if snapshot.taxonomy != "parent":
        raise ValueError(
            f"external snapshot {snapshot.source!r} taxonomy must be 'parent', got {snapshot.taxonomy!r}"
        )
    known = set(predictions.action_universe)
    supplied = set(snapshot.ranks) | set(snapshot.scores)
    pairs: dict[tuple[str, str], float] = {}
    for key, probability in snapshot.matchup_probabilities.items():
        if "|||" not in key:
            raise ValueError(f"external matchup key must be 'subject|||opponent': {key!r}")
        subject, opponent = key.split("|||", 1)
        pairs[(subject, opponent)] = probability
        supplied.update((subject, opponent))
    unknown = supplied - known
    if unknown:
        raise ValueError(f"external snapshot has unmapped actions: {sorted(unknown)!r}")
    if any(not 0.0 <= probability <= 1.0 for probability in pairs.values()):
        raise ValueError("external matchup probabilities must be in [0, 1]")

    scores = snapshot.scores or {
        action: -float(rank) for action, rank in snapshot.ranks.items()
    }
    recommendation = _rank_external(snapshot.source, scores)
    supported_matches = [
        match for match in matches
        if match.exclusion_reason is None and (match.subject, match.opponent) in pairs
    ]
    support = _support_verdict(supported_matches, protocol)
    eligible_matches = sum(match.exclusion_reason is None for match in matches)
    coverage = len(supported_matches) / eligible_matches if eligible_matches else 0.0
    missing_actions = tuple(sorted(known - supplied))
    coverage_reasons = tuple(
        reason for reason in support.reasons
        if not reason.startswith("future classified field coverage")
    )
    if coverage < protocol.support.min_future_field_coverage:
        coverage_reasons += (
            f"external common-case coverage {coverage:.1%} < "
            f"{protocol.support.min_future_field_coverage:.1%}",
        )
    support = support.model_copy(update={
        "evaluable": not coverage_reasons,
        "reasons": coverage_reasons,
        "future_field_coverage": coverage,
    })
    if not pairs:
        tau, top3, regret, regret_ci, regret_reason, oracle = _decision_metrics(
            recommendation, matches, protocol, field_counts,
        )
        return EstimatorEvaluation(
            estimator=f"external:{snapshot.source}", common_matches=0, served_matches=0,
            log_loss=None, brier=None, calibration_intercept=None, calibration_slope=None,
            cumulative_calibration=(), rank_tau=tau, top3_hit=top3, regret=regret,
            regret_ci=regret_ci, regret_censor_reason=regret_reason, oracle_action=oracle,
            eligible_matches=eligible_matches, common_case_coverage=coverage,
            missing_actions=missing_actions, support=support,
        )
    lookup = {
        pair: FrozenMatchupPrediction(
            estimator="coin-50", subject=pair[0], opponent=pair[1], probability=probability,
            served=True, source_kind=f"external:{snapshot.source}", imputed=False,
            refusal_reason=None,
        ) for pair, probability in pairs.items()
    }
    result = _evaluate_estimator(
        f"external:{snapshot.source}", lookup, recommendation, supported_matches, protocol, support,
        field_counts,
    )
    return result.model_copy(update={
        "eligible_matches": eligible_matches,
        "common_case_coverage": coverage,
        "missing_actions": missing_actions,
    })


def _rank_external(source: str, scores: Mapping[str, float]) -> FrozenRecommendation:
    ranked = tuple(sorted(scores, key=lambda action: (-scores[action], action)))
    return FrozenRecommendation(
        estimator="coin-50", chosen_action=ranked[0] if ranked else None,
        ranked_actions=ranked, scores=dict(scores), served=bool(ranked),
        refusal_reason=None if ranked else f"external snapshot {source!r} has no ranks or scores",
    )


def evaluate_origin(
    predictions: FrozenOriginPredictions,
    outcome_rows: Sequence[HeldoutMatch] | HeldoutOutcomes,
    *,
    protocol: BenchmarkProtocol,
    external: Sequence[ExternalRankingSnapshot] = (),
) -> BenchmarkEvaluation:
    """Score immutable forecasts on one common future-only match set."""
    if predictions.protocol_hash != protocol_sha256(protocol):
        raise ValueError("prediction protocol hash does not match evaluation protocol")
    if predictions.estimator_registry != protocol.estimator_ids:
        raise ValueError("prediction estimator registry does not match protocol")
    if protocol.planned_folds and predictions.fold not in protocol.planned_folds:
        raise ValueError("prediction fold is not in the preregistered fold schedule")
    cutoff = date.fromisoformat(predictions.fold.cutoff)
    until = date.fromisoformat(predictions.fold.evaluation_until)
    universe = set(predictions.action_universe)
    if isinstance(outcome_rows, HeldoutOutcomes):
        raw_matches = outcome_rows.matches
        field_coverage = _field_coverage_ledger(outcome_rows.decks, universe)
        heldout_decks = outcome_rows.decks
        retained_hash = content_sha256({
            "decks": [deck.model_dump(mode="json") for deck in outcome_rows.decks],
            "matches": [match.model_dump(mode="json") for match in outcome_rows.matches],
        })
        validate_quarantine_ledger(
            outcome_rows.card_metadata_quarantine,
            policy=protocol.card_metadata,
            declared_digest=outcome_rows.card_metadata_quarantine_sha256,
            retained_facts_sha256=(
                retained_hash if protocol.card_metadata.mode == "quarantine-unresolved-decks" else None
            ),
        )
    else:
        validate_quarantine_ledger(None, policy=protocol.card_metadata)
        raw_matches = outcome_rows
        field_coverage = None
        heldout_decks = ()
    normalized: list[HeldoutMatch] = []
    exclusions: dict[OutcomeExclusionReason, int] = {
        reason: 0 for reason in (
            "outside-fold", "mirror", "bye-draw-invalid", "ambiguous-player",
            "unclassified", "emerging-label", "outside-frozen-universe", "card-metadata-unresolved",
        )
    }
    for match in raw_matches:
        reason = match.exclusion_reason
        event_date = date.fromisoformat(match.event_date)
        if not cutoff <= event_date < until:
            reason = "outside-fold"
        elif reason is None and (match.subject is None or match.opponent is None):
            reason = "unclassified"
        elif reason is None and match.subject == match.opponent:
            reason = "mirror"
        elif reason is None and (match.subject not in universe or match.opponent not in universe):
            reason = (
                "emerging-label" if match.subject not in universe and match.opponent not in universe
                else "outside-frozen-universe"
            )
        updated = match.model_copy(update={"exclusion_reason": reason})
        normalized.append(updated)
        if reason is not None:
            exclusions[reason] += 1
    support = _support_verdict(normalized, protocol, field_coverage)
    field_counts = field_coverage.counts_by_action if field_coverage is not None else None
    prediction_lookup = {
        (item.estimator, item.subject, item.opponent): item
        for item in predictions.matchup_predictions
    }
    recommendations = {item.estimator: item for item in predictions.recommendations}
    evaluations: list[EstimatorEvaluation] = []
    for estimator in protocol.estimator_ids:
        lookup = {
            (subject, opponent): prediction_lookup[(estimator, subject, opponent)]
            for subject in predictions.action_universe for opponent in predictions.action_universe
        }
        evaluations.append(_evaluate_estimator(
            estimator, lookup, recommendations[estimator], normalized, protocol, support,
            field_counts,
        ))
    external_results = tuple(
        _external_evaluation(snapshot, predictions, normalized, protocol, field_counts)
        for snapshot in external
    )
    player_keys = [
        key for match in normalized if match.exclusion_reason is None
        for key in (match.subject_player_key, match.opponent_player_key)
    ]
    player_coverage = sum(key is not None for key in player_keys) / len(player_keys) if player_keys else 0.0
    reasons = list(support.reasons)
    player_reason = None
    player_sensitivity = None
    if player_coverage < 0.80:
        player_reason = f"player-component sensitivity unavailable: identity coverage {player_coverage:.1%} < 80%"
        reasons.append(player_reason)
    else:
        player_sensitivity = _player_component_sensitivity(predictions, normalized, protocol)
    evaluation_payload: dict[str, object] = {
        "matches": [match.model_dump(mode="json") for match in normalized],
        "decks": [deck.model_dump(mode="json") for deck in heldout_decks],
    }
    if isinstance(outcome_rows, HeldoutOutcomes) and outcome_rows.card_metadata_quarantine is not None:
        evaluation_payload["card_metadata_quarantine"] = (
            outcome_rows.card_metadata_quarantine.model_dump(mode="json")
        )
    return BenchmarkEvaluation(
        protocol_hash=predictions.protocol_hash,
        predictions_sha256=content_sha256(predictions),
        evaluation_data_sha256=content_sha256(evaluation_payload),
        fold=predictions.fold, exclusions=exclusions, estimators=tuple(evaluations),
        external=external_results, status="descriptive" if support.evaluable else "not-evaluable",
        reasons=tuple(reasons), player_sensitivity_reason=player_reason,
        player_sensitivity=player_sensitivity,
        paired_log_loss_differences=_paired_event_log_loss(predictions, normalized, protocol),
        field_coverage=field_coverage,
        card_metadata_quarantine=(
            outcome_rows.card_metadata_quarantine if isinstance(outcome_rows, HeldoutOutcomes) else None
        ),
    )


def aggregate_benchmark(
    protocol: BenchmarkProtocol,
    folds: Sequence[BenchmarkEvaluation],
) -> BenchmarkEvaluationSummary:
    """Aggregate preregistered folds without tuning production variants."""
    if any(fold.protocol_hash != protocol_sha256(protocol) for fold in folds):
        raise ValueError("cannot aggregate folds from another protocol")
    evaluable = [fold for fold in folds if fold.status != "not-evaluable"]
    regimes = {fold.fold.regime_start for fold in evaluable}
    paired: dict[str, dict[str, float | None]] = {}
    for baseline in ("coin-50", "recent-raw-wr", "simple-jeffreys-shrinkage"):
        differences: list[float] = []
        for fold in evaluable:
            difference = fold.paired_log_loss_differences.get(baseline, {}).get("mean")
            if difference is not None:
                differences.append(difference)
        if differences:
            rng = np.random.default_rng(protocol.seed)
            samples = [
                float(np.mean(rng.choice(differences, size=len(differences), replace=True)))
                for _ in range(protocol.bootstrap_draws)
            ]
            low, high = np.quantile(samples, [0.025, 0.975])
            paired[baseline] = {
                "mean_log_loss_difference": float(np.mean(differences)),
                "ci_low": float(low), "ci_high": float(high),
            }
        else:
            paired[baseline] = {
                "mean_log_loss_difference": None, "ci_low": None, "ci_high": None,
            }
    reasons: list[str] = []
    if len(evaluable) < protocol.support.min_claim_folds:
        reasons.append(f"evaluable folds {len(evaluable)} < {protocol.support.min_claim_folds}")
    if len(regimes) < protocol.support.min_claim_regimes:
        reasons.append(f"represented regimes {len(regimes)} < {protocol.support.min_claim_regimes}")
    required_beats = all(
        paired[baseline]["ci_high"] is not None and paired[baseline]["ci_high"] < 0
        for baseline in paired
    )
    if not required_beats:
        reasons.append("primary log-loss advantage is not established against every required baseline")
    metrics_by_fold = [
        {item.estimator: item for item in fold.estimators} for fold in evaluable
    ]
    brier_noninferior = bool(metrics_by_fold) and (
        np.mean([metrics[protocol.primary_estimator].brier for metrics in metrics_by_fold])
        <= min(np.mean([metrics[baseline].brier for metrics in metrics_by_fold]) for baseline in (
            "coin-50", "recent-raw-wr", "simple-jeffreys-shrinkage",
        ))
    )
    if not brier_noninferior:
        reasons.append("primary Brier score is not noninferior to the required baselines")
    regret_better = bool(metrics_by_fold) and all(
        metrics[protocol.primary_estimator].regret_censor_reason is None
        and metrics[baseline].regret_censor_reason is None
        and metrics[protocol.primary_estimator].regret_ci is not None
        and metrics[baseline].regret_ci is not None
        and metrics[protocol.primary_estimator].regret_ci[1] < metrics[baseline].regret_ci[0]
        for metrics in metrics_by_fold
        for baseline in ("field-share", "top-finish-conversion")
    )
    if not regret_better:
        reasons.append(
            "stable event-block regret advantage is not established against both ranking baselines"
        )
    directional = bool(metrics_by_fold) and all(
        sum(
            metrics[protocol.primary_estimator].log_loss < metrics[baseline].log_loss
            for metrics in metrics_by_fold
        ) / len(metrics_by_fold) >= 0.60
        for baseline in ("coin-50", "recent-raw-wr", "simple-jeffreys-shrinkage")
    )
    if not directional:
        reasons.append("fewer than 60% of evaluable folds agree on every required log-loss direction")
    calibration_available = all(
        (
            metric := next(
                item for item in fold.estimators
                if item.estimator == protocol.primary_estimator
            )
        ).calibration_intercept is not None
        and metric.calibration_slope is not None
        for fold in evaluable
    ) if evaluable else False
    if not calibration_available:
        reasons.append("required primary calibration metrics are unavailable")
    if protocol.claim_ceiling == "descriptive":
        reasons.append("protocol claim ceiling is descriptive; no predictive validation claim is permitted")
    status = (
        "predictive-claim-supported" if not reasons and protocol.claim_ceiling == "predictive-claim-supported"
        else ("descriptive" if evaluable else "not-evaluable")
    )
    return BenchmarkEvaluationSummary(
        protocol_hash=protocol_sha256(protocol), folds=tuple(folds),
        evaluable_folds=len(evaluable), represented_regimes=len(regimes),
        paired_differences=paired, status=status, reasons=tuple(reasons),
        claim_ceiling=protocol.claim_ceiling,
    )


def render_benchmark_markdown(summary: BenchmarkEvaluationSummary) -> str:
    lines = [
        "# Future-only ranking benchmark", "",
        f"- Status: **{summary.status}**",
        f"- Protocol hash: `{summary.protocol_hash}`",
        f"- Claim ceiling: **{summary.claim_ceiling}**",
        f"- Evaluable folds: {summary.evaluable_folds}/{len(summary.folds)}",
        f"- Registered regimes represented: {summary.represented_regimes}", "",
    ]
    if summary.reasons:
        lines.extend(["## Claim limitations", "", *[f"- {reason}" for reason in summary.reasons], ""])
    lines.extend([
        "## Fold results", "",
        "| Fold | Status | Common | Log loss | Brier | Cal. int./slope | Coverage | Rank τ | Top 3 | Regret (95% interval) | Exclusions |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for fold in summary.folds:
        primary = next(item for item in fold.estimators if item.estimator == "production-ci-gated")
        loss = "n/a" if primary.log_loss is None else f"{primary.log_loss:.4f}"
        brier = "n/a" if primary.brier is None else f"{primary.brier:.4f}"
        calibration = (
            "n/a" if primary.calibration_intercept is None else
            f"{primary.calibration_intercept:.3f}/{primary.calibration_slope:.3f}"
        )
        coverage = f"{primary.support.future_field_coverage:.1%}"
        rank = "n/a" if primary.rank_tau is None else f"{primary.rank_tau:.3f}"
        top3 = "n/a" if primary.top3_hit is None else str(primary.top3_hit)
        regret = primary.regret_censor_reason or (
            "n/a" if primary.regret is None else
            f"{primary.regret:.4f} [{primary.regret_ci[0]:.4f}, {primary.regret_ci[1]:.4f}]"
        )
        lines.append(
            f"| {fold.fold.fold_id} | {fold.status} | {primary.common_matches} | {loss} | "
            f"{brier} | {calibration} | {coverage} | {rank} | {top3} | {regret} | "
            f"{sum(fold.exclusions.values())} |"
        )
    for fold in summary.folds:
        primary = next(item for item in fold.estimators if item.estimator == "production-ci-gated")
        lines.extend([
            "", f"### {fold.fold.fold_id} evidence", "",
            f"- Support: {'evaluable' if primary.support.evaluable else 'not evaluable'}; "
            f"matches={primary.support.matches}, events={primary.support.events}, "
            f"dates={primary.support.event_dates}, supported actions={primary.support.supported_actions}.",
            f"- Exclusions: {', '.join(f'{key}={value}' for key, value in fold.exclusions.items())}.",
            f"- Cumulative calibration residuals: {list(primary.cumulative_calibration)}.",
            f"- Player sensitivity: {fold.player_sensitivity or fold.player_sensitivity_reason or 'unavailable'}.",
        ])
        if fold.field_coverage is not None:
            lines.append(
                f"- Classified field ledger: covered={fold.field_coverage.covered_decks}/"
                f"{fold.field_coverage.classified_decks}; exclusions={fold.field_coverage.exclusions}."
            )
        if fold.card_metadata_quarantine is not None:
            ledger = fold.card_metadata_quarantine
            lines.append(
                f"- Card metadata ledger: decks {ledger.retained_decks}/{ledger.raw_decks} retained "
                f"({ledger.deck_fraction:.3%} excluded), rounds {ledger.retained_rounds}/"
                f"{ledger.raw_rounds} retained ({ledger.round_fraction:.3%} excluded); "
                f"sources={ledger.counts_by_source}; digest=`{ledger.digest}`."
            )
            for deck in ledger.excluded_decks:
                lines.append(
                    f"- Quarantined deck `{deck.tournament_id}:{deck.deck_idx}`: "
                    f"player={deck.player_key or '(blank)'}; ambiguous={deck.identity_ambiguous}; "
                    f"event_date={deck.event_date}; source={deck.source or '(missing)'}; "
                    f"event_uri={deck.event_uri or '(missing)'}; "
                    f"unresolved_names={list(deck.unresolved_names)}; "
                    f"ledger_reasons={list(ledger.reasons)}; digest=`{ledger.digest}`."
                )
        for external in fold.external:
            lines.append(
                f"- External `{external.estimator}`: common={external.common_matches}/"
                f"{external.eligible_matches} ({external.common_case_coverage:.1%}); "
                f"missing actions={list(external.missing_actions)}; log loss={external.log_loss}; "
                f"regret censor={external.regret_censor_reason}."
            )
    lines.extend(["", "## Paired primary-minus-baseline log loss", "", "| Baseline | Mean | 95% interval |", "|---|---:|---:|"])
    for baseline, values in summary.paired_differences.items():
        mean = values["mean_log_loss_difference"]
        low, high = values["ci_low"], values["ci_high"]
        lines.append(
            f"| {baseline} | {'n/a' if mean is None else f'{mean:.4f}'} | "
            f"{'n/a' if low is None else f'[{low:.4f}, {high:.4f}]'} |"
        )
    lines.extend(["", "> Evaluation is read-only: this report does not select, tune, or deploy an estimator.", ""])
    return "\n".join(lines)


def _fold_id(cutoff: date, until: date) -> str:
    return f"{cutoff.isoformat()}--{until.isoformat()}"


def plan_walk_forward_folds(
    event_dates: Sequence[str],
    ban_dates: Sequence[str],
    protocol: BenchmarkProtocol,
) -> tuple[BenchmarkFold, ...]:
    """Plan non-overlapping, whole-date folds reset and truncated at B&R boundaries."""
    first = date.fromisoformat(protocol.first_cutoff)
    final = date.fromisoformat(protocol.final_evaluation_until)
    events = tuple(sorted({date.fromisoformat(value) for value in event_dates}))
    all_bans = tuple(sorted({date.fromisoformat(value) for value in ban_dates}))
    bans = tuple(ban for ban in all_bans if first < ban < final)

    folds: list[BenchmarkFold] = []
    origin = first
    while origin < final:
        next_ban = next((ban for ban in bans if ban > origin), None)
        until = min(origin + timedelta(days=protocol.horizon_days), final)
        if next_ban is not None and next_ban < until:
            until = next_ban
        regime_start = max((ban for ban in all_bans if ban <= origin), default=first)
        regime_end = next((ban for ban in bans if ban > origin), None)
        heldout_dates = tuple(d.isoformat() for d in events if origin <= d < until)
        folds.append(BenchmarkFold(
            fold_id=_fold_id(origin, until), cutoff=origin.isoformat(),
            evaluation_until=until.isoformat(), regime_start=regime_start.isoformat(),
            regime_end=regime_end.isoformat() if regime_end is not None else None,
            event_dates=heldout_dates,
        ))
        if next_ban is not None and until == next_ban:
            origin = next_ban
        else:
            origin += timedelta(days=protocol.step_days)
            if next_ban is not None and origin > next_ban:
                origin = next_ban
    return tuple(folds)


def validate_snapshot_manifest(manifest: SnapshotManifest) -> None:
    cutoff = date.fromisoformat(manifest.fold.cutoff)
    if manifest.training_events < 1:
        raise ValueError("origin snapshot has no training events")
    if date.fromisoformat(manifest.max_training_event_date) >= cutoff:
        raise ValueError("origin snapshot contains an event at or after cutoff")
    if any(date.fromisoformat(event[0]) > cutoff for event in manifest.ban_events_as_of):
        raise ValueError("origin snapshot contains a future ban event")


def atomic_write_canonical(path: Path, value: object) -> str:
    """Write canonical JSON atomically and return its digest."""
    payload = canonical_json_bytes(value)
    digest = hashlib.sha256(payload).hexdigest()
    if path.exists():
        if path.read_bytes() == payload:
            return digest
        raise FileExistsError(f"refusing to overwrite different artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        import os
        os.fsync(handle.fileno())
    temporary.replace(path)
    return digest


def load_hashed_model(path: Path, model_type: type[LegacyEngineModel], expected_sha256: str | None = None):
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError(f"artifact hash mismatch for {path}: expected {expected_sha256}, got {digest}")
    return model_type.model_validate_json(payload), digest
