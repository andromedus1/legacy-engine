"""Privacy-safe identity accessibility and pilot-stickiness diagnostics."""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import Literal

import numpy as np
from pydantic import Field, model_validator

from legacy_engine.analytics.match_results import normalize_player
from legacy_engine.models.base import LegacyEngineModel

IdentityReplayMode = Literal["provenance-local-handle", "dated-curated-alias"]
IdentityBasis = Literal["provenance-local-handle", "curated-alias"]
PlayerEffectEstimatorId = Literal[
    "deck-residual-control", "player-intercept", "player-familiarity",
]
PLAYER_EFFECT_ESTIMATOR_REGISTRY: tuple[PlayerEffectEstimatorId, ...] = (
    "deck-residual-control", "player-intercept", "player-familiarity",
)


class PlayerIdentitySnapshotManifest(LegacyEngineModel):
    source: str
    effective_at: str
    aliases_file: str
    aliases_sha256: str


class PlayerDiagnosticProtocol(LegacyEngineModel):
    protocol_id: str
    created_at: str
    benchmark_protocol_hash: str
    identity_mode: IdentityReplayMode = "provenance-local-handle"
    min_identity_match_coverage: float = 0.80
    min_effect_supported_match_coverage: float = 0.60
    min_repeat_events: int = 3
    min_repeat_matches: int = 30
    min_familiarity_events: int = 3
    min_familiarity_matches: int = 15
    min_repeat_players: int = 30
    min_familiarity_pairs: int = 30
    stickiness_min_events: int = 2
    stickiness_min_identities_per_configuration: int = 10
    stickiness_min_repeat_identities: int = 5
    privacy_min_group: int = 5
    deck_penalties: tuple[float, ...] = (10.0, 30.0, 100.0)
    player_penalties: tuple[float, ...] = (10.0, 30.0, 100.0)
    familiarity_penalties: tuple[float, ...] = (30.0, 100.0, 300.0)
    min_inner_origins: int = 3
    min_stratum_matches: int = 50
    min_stratum_events: int = 3
    min_stratum_event_dates: int = 2
    seed: int = 730_021

    @model_validator(mode="after")
    def _validate_protocol(self) -> "PlayerDiagnosticProtocol":
        for value in (
            self.min_identity_match_coverage, self.min_effect_supported_match_coverage,
        ):
            if not 0 <= value <= 1:
                raise ValueError("coverage thresholds must be in [0, 1]")
        integer_floors = (
            self.min_repeat_events, self.min_repeat_matches, self.min_familiarity_events,
            self.min_familiarity_matches, self.min_repeat_players, self.min_familiarity_pairs,
            self.stickiness_min_events, self.stickiness_min_identities_per_configuration,
            self.stickiness_min_repeat_identities, self.privacy_min_group, self.min_inner_origins,
            self.min_stratum_matches, self.min_stratum_events, self.min_stratum_event_dates,
        )
        if any(value < 1 for value in integer_floors):
            raise ValueError("diagnostic support floors must be positive")
        if any(value <= 0 for grid in (
            self.deck_penalties, self.player_penalties, self.familiarity_penalties,
        ) for value in grid):
            raise ValueError("penalty grids must be positive")
        return self


class PilotRegistration(LegacyEngineModel):
    event_id: str
    event_date: str
    provenance: str
    parent: str
    configuration: str
    player_key: str | None
    identity_basis: IdentityBasis | None
    exclusion_reason: str | None


class IdentityAccessibility(LegacyEngineModel):
    provenance: str
    registrations: int
    match_sides: int
    nonempty_handle_rate: float
    unambiguous_match_rate: float
    dated_alias_rate: float
    repeat_players: int | None
    familiarity_pairs: int | None
    effect_supported_match_rate: float
    evaluable: bool
    reasons: tuple[str, ...]


class PilotStickinessCell(LegacyEngineModel):
    parent: str
    configuration_a: str
    configuration_b: str
    identities_a: int | None
    identities_b: int | None
    shared_identities: int | None
    repeat_identities: int | None
    jaccard: float | None
    overlap_coefficient: float | None
    switching_rate: float | None
    bootstrap_ci: tuple[float, float] | None
    identity_basis: tuple[IdentityBasis, ...]
    reason: str | None


class PlayerAccessibilityReport(LegacyEngineModel):
    protocol_hash: str
    identity_snapshot_sha256: str | None
    by_provenance: tuple[IdentityAccessibility, ...]
    stickiness: tuple[PilotStickinessCell, ...]
    limitations: tuple[str, ...] = Field(default_factory=tuple)


def scoped_player_key(
    handle: str | None,
    provenance: str,
    alias_map: dict[str, str],
) -> tuple[str | None, IdentityBasis | None]:
    """Return a curated alias or a provenance-local normalized observation key."""
    normalized = normalize_player(handle)
    if not normalized:
        return None, None
    if normalized in alias_map:
        return f"alias:{alias_map[normalized]}", "curated-alias"
    return f"handle:{provenance}:{normalized}", "provenance-local-handle"


def _eligibility(
    rows: tuple[object, ...], protocol: PlayerDiagnosticProtocol,
) -> tuple[set[str], set[tuple[str, str]]]:
    player_events: dict[str, set[str]] = defaultdict(set)
    player_matches: dict[str, int] = defaultdict(int)
    pair_events: dict[tuple[str, str], set[str]] = defaultdict(set)
    pair_matches: dict[tuple[str, str], int] = defaultdict(int)
    for row in rows:
        if getattr(row, "exclusion_reason", None) is not None:
            continue
        for key, parent in (
            (getattr(row, "subject_player_key"), getattr(row, "subject")),
            (getattr(row, "opponent_player_key"), getattr(row, "opponent")),
        ):
            if key is None:
                continue
            player_events[key].add(getattr(row, "event_id"))
            player_matches[key] += 1
            pair = (key, parent)
            pair_events[pair].add(getattr(row, "event_id"))
            pair_matches[pair] += 1
    repeat = {
        key for key in player_matches
        if len(player_events[key]) >= protocol.min_repeat_events
        and player_matches[key] >= protocol.min_repeat_matches
    }
    familiarity = {
        pair for pair in pair_matches
        if len(pair_events[pair]) >= protocol.min_familiarity_events
        and pair_matches[pair] >= protocol.min_familiarity_matches
    }
    return repeat, familiarity


def measure_player_accessibility(
    registrations: tuple[PilotRegistration, ...],
    match_rows: tuple[object, ...],
    protocol: PlayerDiagnosticProtocol,
) -> tuple[IdentityAccessibility, ...]:
    provenances = tuple(sorted(
        {row.provenance for row in registrations}
        | {row.provenance for row in match_rows}
        | {"all"}
    ))
    output: list[IdentityAccessibility] = []
    for provenance in provenances:
        regs = tuple(
            row for row in registrations if provenance == "all" or row.provenance == provenance
        )
        matches = tuple(
            row for row in match_rows if provenance == "all" or row.provenance == provenance
        )
        repeat, familiarity = _eligibility(matches, protocol)
        nonempty = sum(row.player_key is not None for row in regs)
        alias_n = sum(row.identity_basis == "curated-alias" for row in regs)
        sides = [
            key for row in matches
            for key in (row.subject_player_key, row.opponent_player_key)
        ]
        unambiguous = sum(key is not None for key in sides)
        supported = sum(
            row.subject_player_key in repeat and row.opponent_player_key in repeat
            for row in matches if getattr(row, "exclusion_reason", None) is None
        )
        eligible_matches = sum(
            getattr(row, "exclusion_reason", None) is None for row in matches
        )
        supported_rate = supported / eligible_matches if eligible_matches else 0.0
        repeat_here = {
            key for row in matches for key in (row.subject_player_key, row.opponent_player_key)
            if key in repeat
        }
        familiarity_here = {
            pair for row in matches for pair in (
                (row.subject_player_key, row.subject),
                (row.opponent_player_key, row.opponent),
            ) if pair in familiarity
        }
        identity_rate = unambiguous / len(sides) if sides else 0.0
        reasons: list[str] = []
        if identity_rate < protocol.min_identity_match_coverage:
            reasons.append(
                f"identity match-side coverage {identity_rate:.1%} < "
                f"{protocol.min_identity_match_coverage:.1%}"
            )
        if supported_rate < protocol.min_effect_supported_match_coverage:
            reasons.append(
                f"effect-supported match coverage {supported_rate:.1%} < "
                f"{protocol.min_effect_supported_match_coverage:.1%}"
            )
        repeat_count = len(repeat_here)
        familiarity_count = len(familiarity_here)
        if repeat_count < protocol.min_repeat_players:
            reasons.append(f"repeat players {len(repeat_here)} < {protocol.min_repeat_players}")
        output.append(IdentityAccessibility(
            provenance=provenance, registrations=len(regs), match_sides=len(sides),
            nonempty_handle_rate=nonempty / len(regs) if regs else 0.0,
            unambiguous_match_rate=identity_rate,
            dated_alias_rate=alias_n / nonempty if nonempty else 0.0,
            repeat_players=(
                repeat_count if repeat_count >= protocol.privacy_min_group else None
            ),
            familiarity_pairs=(
                familiarity_count if familiarity_count >= protocol.privacy_min_group else None
            ),
            effect_supported_match_rate=supported_rate, evaluable=not reasons,
            reasons=tuple(reasons),
        ))
    return tuple(output)


def _repeat_sets(
    rows: tuple[PilotRegistration, ...], minimum_events: int,
) -> dict[tuple[str, str], set[str]]:
    events: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for row in rows:
        if row.player_key is not None and row.exclusion_reason is None:
            events[(row.parent, row.configuration, row.player_key)].add(row.event_id)
    output: dict[tuple[str, str], set[str]] = defaultdict(set)
    for (parent, configuration, key), seen in events.items():
        if len(seen) >= minimum_events:
            output[(parent, configuration)].add(key)
    return output


def measure_pilot_stickiness(
    registrations: tuple[PilotRegistration, ...],
    protocol: PlayerDiagnosticProtocol,
) -> tuple[PilotStickinessCell, ...]:
    identities: dict[tuple[str, str], set[str]] = defaultdict(set)
    basis_by_pair: dict[tuple[str, str], set[IdentityBasis]] = defaultdict(set)
    for row in registrations:
        if row.player_key is not None and row.exclusion_reason is None:
            identities[(row.parent, row.configuration)].add(row.player_key)
            if row.identity_basis is not None:
                basis_by_pair[(row.parent, row.configuration)].add(row.identity_basis)
    repeated = _repeat_sets(registrations, protocol.stickiness_min_events)
    events = tuple(sorted({row.event_id for row in registrations}))
    rng = np.random.default_rng(protocol.seed)
    output: list[PilotStickinessCell] = []
    parents = sorted({row.parent for row in registrations})
    for parent in parents:
        configurations = sorted({row.configuration for row in registrations if row.parent == parent})
        for left, right in combinations(configurations, 2):
            left_all, right_all = identities[(parent, left)], identities[(parent, right)]
            left_repeat, right_repeat = repeated[(parent, left)], repeated[(parent, right)]
            union = left_repeat | right_repeat
            shared = left_repeat & right_repeat
            reason = None
            if (
                len(left_all) < protocol.stickiness_min_identities_per_configuration
                or len(right_all) < protocol.stickiness_min_identities_per_configuration
            ):
                reason = "configuration identity support below display floor"
            elif len(union) < protocol.stickiness_min_repeat_identities:
                reason = "repeat identity support below stickiness floor"
            elif 0 < len(shared) < protocol.privacy_min_group:
                reason = "shared identity group suppressed by privacy floor"
            interval = None
            if reason is None and events:
                draws: list[float] = []
                for _ in range(500):
                    sampled = rng.choice(events, len(events), replace=True)
                    sampled_rows = tuple(
                        row.model_copy(update={"event_id": f"bootstrap:{position}:{event_id}"})
                        for position, event_id in enumerate(sampled)
                        for row in registrations if row.event_id == str(event_id)
                    )
                    sample_sets = _repeat_sets(
                        sampled_rows,
                        protocol.stickiness_min_events,
                    )
                    a, b = sample_sets[(parent, left)], sample_sets[(parent, right)]
                    if a | b:
                        draws.append(len(a & b) / len(a | b))
                if draws:
                    low, high = np.quantile(draws, [0.025, 0.975])
                    interval = (float(low), float(high))
            denominator = min(len(left_repeat), len(right_repeat))
            output.append(PilotStickinessCell(
                parent=parent, configuration_a=left, configuration_b=right,
                identities_a=len(left_all) if reason is None else None,
                identities_b=len(right_all) if reason is None else None,
                shared_identities=len(shared) if reason is None else None,
                repeat_identities=len(union) if reason is None else None,
                jaccard=len(shared) / len(union) if reason is None and union else None,
                overlap_coefficient=len(shared) / denominator if reason is None and denominator else None,
                switching_rate=len(shared) / len(union) if reason is None and union else None,
                bootstrap_ci=interval,
                identity_basis=tuple(sorted(
                    basis_by_pair[(parent, left)] | basis_by_pair[(parent, right)]
                )),
                reason=reason,
            ))
    return tuple(output)
