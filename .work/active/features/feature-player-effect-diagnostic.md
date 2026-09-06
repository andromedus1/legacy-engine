---
id: feature-player-effect-diagnostic
kind: feature
stage: done
tags: [analytics, players, experimental]
parent: epic-best-deck-decision-trust
depends_on: [feature-ranking-future-only-benchmark]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Player-effect diagnostic — pilot stickiness and earned adjustment

## Brief

Measure whether player identity can clarify deck taxonomy and improve prediction without turning
thin or unstable handles into false precision. First report identity/alias/repeat-event coverage and
pilot overlap between candidate configurations. Then test a strictly pre-match, partially pooled
player effect—and, only where supported, player-by-archetype familiarity—inside the future-only
benchmark. Default ranking output remains unchanged unless the adjusted model demonstrates durable
out-of-sample improvement.

The pilot-stickiness interpretation references backlog item
`idea-decision-unit-taxonomy-heterogeneity-gate`: shared pilots suggest one deck with a tuning knob;
disjoint pilot populations support distinct decision units. This feature does not absorb or
implement the broader taxonomy gate.

## Strategic decisions

- Online and paper identity coverage are reported separately; an empty curated alias table is an
  explicit limitation, not an invitation to auto-merge people.
- Player ratings used for a match are snapshots from before that match.
- Divergence between adjusted and unadjusted deck estimates is diagnostic until future-only scores
  justify changing the headline.

## Simplification opportunity

Reuse the existing identity, strength, and archetype-history modules. Replace threshold-only
“strong player” use only if the new model proves superior; do not maintain two headline adjustment
systems.

## Design decisions

<!-- The operator already approved the directional sequence and autopilot. The choices below resolve
routine implementation ambiguity toward the least irreversible honest experiment. -->

- **Identity is a scoped observation, not a person claim.** A handle absent from a dated curated
  alias snapshot is keyed only as `provenance + normalized handle`; an identical unaliased string on
  MTGO and a paper provider is not merged. Curated aliases may merge handles only when supplied in a
  snapshot whose `effective_at <= fold.cutoff`; the tracked package alias file remains empty and is
  never back-projected into an old origin. Reports say `provenance-local handle` or `dated curated
  alias`, never “same human” when the evidence is only a handle.
- **Two repeat thresholds serve different questions.** Pilot stickiness needs the minimum observable
  recurrence—two distinct events under a configuration. A fitted player intercept requires at least
  3 distinct pre-cutoff events and 30 decisive pre-cutoff matches, matching the existing `evolving`
  confidence boundary. Player-by-parent familiarity additionally requires 3 events and 15 decisive
  matches on that parent. Below a threshold the effect is exactly zero and explicitly cold-start or
  ineligible, not an estimated weak coefficient.
- **The experimental estimand is split in two.** `player-aware` forecasts ask whether known repeat
  handles improve a particular match forecast. `player-neutral` forecasts set player terms to zero
  and ask whether jointly separating player and deck residuals improves the playable archetype
  decision. Only the neutral result can ever support a later headline-change proposal.
- **The production registry is immutable.** The existing ten benchmark estimators,
  `production-ci-gated` primary, page gates, P(best), and recommendation remain authoritative. This
  feature owns a separate experimental registry and emits at most `candidate-for-promotion-study`;
  promotion requires a new reviewed feature and never happens in the evaluator.
- **Temporal order is origin-frozen.** Each outer fold reuses the committed whole-date/B&R benchmark
  fold and snapshot. Model fitting, alias state, repeat eligibility, penalty selection, and neutral
  deck predictions use only `event_date < T`. No within-horizon updates occur. Historical
  player-aware forecasts may read event/pairing/participant fields but select no result column and
  are hashed before evaluation opens outcomes; they are labeled outcome-blind historical replay,
  not proof that the upstream feed exposed pairings before an event.
- **Player output is aggregate and pseudonymous.** Tracked reports never emit handles, canonical ids,
  individual coefficients, or per-person rankings. Cells with fewer than 5 scoped identities are
  suppressed. Disposable local forecast artifacts contain opaque match ids and predictions, not
  player keys; model metadata contains coefficient counts/quantiles and hashes only. Opaque hashes
  are not described as anonymization.
- **Pilot overlap cannot decide taxonomy here.** Pairwise overlap, switching, and event-bootstrap
  uncertainty are descriptive inputs to `idea-decision-unit-taxonomy-heterogeneity-gate`. No
  high/low threshold auto-labels configurations as one deck or two decks, and no registry is written.

## Architectural choice

Three shapes were considered. Reusing the existing `strong_player_set` as a binary filter is simple
but conditions on a selected winning cohort and cannot separate deck strength from pilot mixture.
Adding a post-hoc player win-rate offset to production probabilities preserves more data but treats
the deck surface as fixed, so the player-neutral deck call cannot change and the experiment cannot
answer whether pilot composition confounds it. A full Bayesian cross-classified model would express
uncertainty richly, but adds a sampler/dependency and more degrees of freedom than the current
identity support has earned.

The chosen shape is a deterministic penalized-logistic sensitivity anchored to the already-frozen
`production-ci-gated` matchup log odds. It fits an antisymmetric deck-pair residual, then optional
player intercepts and player-by-parent familiarity deviations, all shrunk toward zero. A deck-
residual-only control prevents ordinary refitting/regularization gains from being credited to player
identity. The finite penalty grid is selected only on inner chronological prefixes and freezes
before the outer holdout. Pure typed analytics own identity/support, fit, forecast, and evaluation;
DuckDB and file access remain workflow adapters; the Click surface composes those functions.

No mockup is needed: this is an offline CLI/JSON/Markdown diagnostic and introduces no graphical UI
or changed visual structure.

## Other agent review

No design-time advisory pass was required: the operator supplied the consequential direction, the
committed benchmark fixes the temporal/evaluation contracts, and direct code/research mapping left
no unresolved irreversible choice. The design remains eligible for the normal standard independent
feature review after implementation.

## Implementation Units

### Unit 1: Identity accessibility and pilot-stickiness ledger

**Files**:
- `src/legacy_engine/analytics/players/diagnostic.py`
- `src/legacy_engine/workflows/player_effect_diagnostic.py`
- `tests/analytics/players/test_diagnostic.py`
- `tests/test_player_effect_workflow.py`

**Story**: `feature-player-effect-diagnostic-coverage-stickiness`

```python
from typing import Literal

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
    seed: int = 730_021

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
    repeat_players: int
    familiarity_pairs: int
    effect_supported_match_rate: float
    evaluable: bool
    reasons: tuple[str, ...]

class PilotStickinessCell(LegacyEngineModel):
    parent: str
    configuration_a: str
    configuration_b: str
    identities_a: int
    identities_b: int
    shared_identities: int | None
    repeat_identities: int
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
    limitations: tuple[str, ...]

def scoped_player_key(
    handle: str | None,
    provenance: str,
    alias_map: dict[str, str],
) -> tuple[str | None, IdentityBasis | None]: ...

def measure_player_accessibility(
    registrations: tuple[PilotRegistration, ...],
    match_rows: tuple["PlayerTrainingMatch", ...],
    protocol: PlayerDiagnosticProtocol,
) -> tuple[IdentityAccessibility, ...]: ...

def measure_pilot_stickiness(
    registrations: tuple[PilotRegistration, ...],
    protocol: PlayerDiagnosticProtocol,
) -> tuple[PilotStickinessCell, ...]: ...

def load_player_identity_snapshot(
    path: Path | None,
    *,
    mode: IdentityReplayMode,
    cutoff: str,
) -> tuple[dict[str, str], str | None]: ...

def load_player_diagnostic_rows(
    db: Path,
    *,
    until: str,
    identity_mode: IdentityReplayMode,
    identity_snapshot: Path | None,
) -> tuple[tuple[PilotRegistration, ...], tuple["PlayerTrainingMatch", ...], str | None]: ...
```

**Implementation notes**:

- All shared records subclass `LegacyEngineModel`. `scoped_player_key` reuses
  `match_results.normalize_player` and `players.identity.load_alias_map`; a normalized key not
  explicitly present in the dated map becomes `handle:<provenance>:<normalized>`. It is an internal
  join key and never renders.
- A dated alias snapshot fails closed on missing manifest, future `effective_at`, hash mismatch,
  duplicate normalized handles, or an alias assigned to two ids. `provenance-local-handle` rejects a
  supplied alias snapshot so the evidence basis cannot be ambiguous.
- Registrations derive only current stored parent + variant subdivisions: configuration is
  `parent::variant` and null variants remain visible as `parent::unlabeled`. The pure function accepts
  arbitrary parent/configuration labels so the later taxonomy gate can reuse it, but this feature
  does not invent or promote partitions.
- Stickiness counts an identity as repeat-supported only after two distinct events in the
  configuration. It reports Jaccard, overlap coefficient, and the share of repeat identities seen in
  both configurations, with event-block bootstrap uncertainty. If either side has fewer than 10
  identities, fewer than 5 repeat identities exist, or a displayed group would fall below the
  privacy floor, magnitudes are null with a named reason.
- Accessibility is reported separately for `online` and `paper`, plus an all-source aggregate that
  still does not merge provenance-local handles. Nonempty handle coverage, within-event ambiguity,
  repeat eligibility, familiarity eligibility, rounds coverage, and curated-alias share are separate
  denominators; a high raw-handle rate cannot masquerade as cross-event identity quality.

**Acceptance criteria**:

- [x] Identical unaliased strings on online and paper produce different scoped keys; a valid dated
  curated mapping may merge them, and a future-dated or hash-invalid mapping fails loudly.
- [x] Empty shipped aliases remain a fully supported, explicitly provenance-local path with no
  automatic alias suggestions applied.
- [x] One-event handles never enter stickiness or model-repeat support; 3-event/30-match players and
  3-event/15-match player-parent pairs enter only their respective gates.
- [x] Pairwise pilot overlap is aggregate, deterministic, event-bootstrap annotated, privacy-
  suppressed when thin, and never emits a taxonomy verdict or player identifier.
- [x] Online/paper accessibility and every exclusion denominator reconcile exactly on a hermetic
  corpus containing blanks, duplicate within-event handles, aliases, repeat pilots, and variants.

---

### Unit 2: Partially pooled pre-match player model and frozen forecasts

**Files**:
- `src/legacy_engine/analytics/players/effect.py`
- `src/legacy_engine/workflows/player_effect_diagnostic.py`
- `tests/analytics/players/test_effect.py`
- `tests/test_player_effect_workflow.py`

**Story**: `feature-player-effect-diagnostic-frozen-model`

```python
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

def select_penalties(
    inner_folds: tuple[PlayerInnerFold, ...],
    protocol: PlayerDiagnosticProtocol,
    *,
    estimator: PlayerEffectEstimatorId,
) -> PenaltySelection: ...

def fit_player_effect_model(
    rows: tuple[PlayerTrainingMatch, ...],
    base_probabilities: dict[tuple[str, str], float],
    protocol: PlayerDiagnosticProtocol,
    selection: PenaltySelection,
) -> "_PlayerEffectFit": ...

def freeze_player_effect_predictions(
    base: FrozenOriginPredictions,
    training_rows: tuple[PlayerTrainingMatch, ...],
    scheduled_rows: tuple[ScheduledPlayerMatch, ...],
    accessibility: tuple[IdentityAccessibility, ...],
    protocol: PlayerDiagnosticProtocol,
) -> FrozenPlayerEffectPredictions: ...

def load_scheduled_player_matches(
    source_db: Path,
    fold: BenchmarkFold,
    *,
    identity_mode: IdentityReplayMode,
    identity_snapshot: Path | None,
    taxonomy_snapshot: Path | None = None,
) -> tuple[ScheduledPlayerMatch, ...]: ...

def build_player_inner_folds(
    source_db: Path,
    outer_fold: BenchmarkFold,
    *,
    benchmark_protocol: BenchmarkProtocol,
    player_protocol: PlayerDiagnosticProtocol,
    identity_snapshot: Path | None,
    taxonomy_snapshot: Path | None,
) -> tuple[PlayerInnerFold, ...]: ...
```

**Implementation notes**:

- This is the trickiest unit. For a canonical unordered deck pair `(a,b)`, the linear predictor is
  `logit(p_base[a,b]) + sign*delta_ab + u_subject - u_opponent + v_subject,a -
  v_opponent,b`. `delta_ba=-delta_ab`; player intercepts are centered at zero; each player's
  familiarity deviations are frequency-weighted to zero across parents. L2 penalties make every
  term partially pooled toward zero. The deck-residual control omits `u` and `v`; player-intercept
  adds `u`; player-familiarity adds `u` and eligible `v`.
- Optimize the penalized Bernoulli likelihood deterministically with SciPy L-BFGS-B. The finite grid
  is the protocol SSOT. `build_player_inner_folds` recreates the production base grid separately at
  every earlier cutoff through the benchmark snapshot/freeze seams; it may not reuse the outer
  origin's later-trained base probabilities. Each outer origin selects on at least 3 earlier
  whole-date inner origins;
  minimum mean log loss wins, a difference <= `1e-4` chooses the strongest shrinkage and then the
  lexicographically smallest parameter tuple. No outer result changes the grid or choice. Missing
  inner support or optimizer failure yields a typed not-evaluable fit; it does not fall back under
  the experimental estimator's name.
- Training rows are decisive, non-mirror, classified parent matches strictly before `T`. Repeat
  eligibility is computed from the same prefix. New or below-floor players receive zero terms;
  familiarity is zero unless its separate floor clears. The base offset is the hashed origin's
  `production-ci-gated` all-case grid and uses the same clipping epsilon.
- Neutral deck predictions set all player/familiarity terms to zero, preserve the base action
  universe and field shares, and rank by field-weighted expected match win probability. They do not
  manufacture Agency or P(best). Player-aware predictions use only frozen coefficients plus the
  outcome-free scheduled row.
- `load_scheduled_player_matches` must issue a query whose projection excludes `rounds.result`; a
  separate outcome loader owns results. Stable `match_id = event_id + ':' + match_idx` joins them.
  A result-only twin-corpus mutation must leave schedule and frozen forecast bytes identical.
- Individual coefficients and player keys remain transient. The artifact records aggregate
  coefficient quantiles/counts; per-match rows retain only opaque match ids and support states. It
  is written canonically and hash-checked with the benchmark artifact helpers.

**Acceptance criteria**:

- [x] Swapping training row orientation negates every side-specific term and preserves reciprocal
  probabilities; repeated identical fits/predictions are byte-identical.
- [x] Deck-residual, player-intercept, and familiarity terms shrink toward zero as their registered
  penalty increases; cold-start and below-floor players contribute exactly zero with different
  support labels.
- [x] Inner selection never sees the outer fold or its later-trained base grid and uses the
  documented strongest-shrinkage/stable-tuple tie break; fewer than 3 valid inner origins is
  not-evaluable.
- [x] A synthetic crossed corpus recovers the direction of a repeat-player effect without assigning
  it to the deck residual; a deck-only corpus does not invent player benefit.
- [x] Changing only future result strings changes no scheduled row, fit summary, neutral deck grid,
  or player-aware frozen match prediction.
- [x] Frozen artifacts contain no raw/canonical player identifiers or individual coefficient table,
  bind base/snapshot/identity/schedule hashes, and never extend the production estimator registry.

---

### Unit 3: Future-only evaluation, stop/go record, CLI, and runbook

**Files**:
- `src/legacy_engine/analytics/players/effect.py`
- `src/legacy_engine/workflows/player_effect_diagnostic.py`
- `src/legacy_engine/cli.py`
- `tests/analytics/players/test_effect.py`
- `tests/test_player_effect_cli.py`
- `docs/analysis/best-call-ranking.md`
- `docs/SPEC.md`
- `docs/ARCHITECTURE.md`
- generated `docs/knowledge-index-nav.yaml`, `docs/knowledge-index.yaml`, and
  `docs/knowledge-index-detail.yaml` if their source frontmatter changes

**Story**: `feature-player-effect-diagnostic-future-evaluation`

```python
PlayerSupportStratum = Literal["known-known", "known-cold", "cold-cold", "below-repeat-floor"]
PlayerDiagnosticStatus = Literal[
    "not-evaluable", "stop", "diagnostic-only", "candidate-for-promotion-study",
]

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

def evaluate_player_effect_fold(
    frozen: FrozenPlayerEffectPredictions,
    outcomes: tuple[HeldoutMatch, ...],
    base: FrozenOriginPredictions,
    benchmark_protocol: BenchmarkProtocol,
    player_protocol: PlayerDiagnosticProtocol,
) -> PlayerEffectFoldEvaluation: ...

def aggregate_player_effect_evaluations(
    folds: tuple[PlayerEffectFoldEvaluation, ...],
    *,
    benchmark_protocol: BenchmarkProtocol,
    player_protocol: PlayerDiagnosticProtocol,
) -> PlayerEffectEvaluationSummary: ...

def render_player_effect_markdown(summary: PlayerEffectEvaluationSummary) -> str: ...
```

**Implementation notes**:

- Evaluate exactly the benchmark's decisive non-mirror common-case matches and verify protocol,
  base prediction, identity, schedule, and outcome hashes before scoring. Every experimental
  candidate and `production-ci-gated` is compared on identical cases; served coverage is secondary.
  Use the existing log-loss clipping, Brier, calibration, event-block bootstrap, future utility,
  practical tie/null regret, and whole-fold aggregation helpers rather than creating a second metric
  definition.
- `heldout-event-player-aware` is the primary match sensitivity: apply only effects eligible at the
  origin to the later event. `heldout-player-masked` scores the identical later rows from the same
  fitted model after setting both participant and familiarity terms to zero, a deliberate
  identity-withheld/cold-start counterfactual that isolates whether benefit comes from remembered
  handles rather than a changed deck surface. Natural `known-known`, `known-cold`, `cold-cold`, and
  below-repeat-floor strata additionally show accessibility without deleting or selecting rows
  using future outcomes. Report online and paper separately; no cross-provenance claim is inferred
  from an aggregate.
- Candidate-for-later-promotion requires every conjunct: at least the benchmark's 6 evaluable folds
  and 2 regimes; identity coverage >=80%; effect-supported coverage >=60%; at least 30 repeat players
  and (for familiarity) 30 eligible player-parent pairs; player-intercept event-block log-loss 95%
  CI strictly below both production and deck-residual control, mean Brier no greater than either,
  and calibration no worse by both `abs(intercept)` and `abs(slope - 1)`; player-neutral
  recommendation regret has an aggregate paired 95% CI strictly below production and improves in
  >=60% of folds. Known-cold/cold-cold and each of online/paper must be evaluable and have mean log
  loss and Brier no greater than production; otherwise there is cold-start or venue harm. No
  required metric may be null, and every claim fold must meet its identity/repeat support floors.
  Familiarity earns inclusion only if it independently clears the same proper-score comparison
  against player-intercept. Otherwise familiarity stops while the simpler player model may remain
  diagnostic. Any missing support is `not-evaluable`; measured failure is `stop`; improvement short
  of every conjunct is `diagnostic-only`.
- Even `candidate-for-promotion-study` changes nothing in production. The report states that a new
  preregistered promotion feature must decide whether to replace the threshold-only strong-player
  surface; it never keeps two headline adjustment systems.
- Add `advise benchmark player-effect plan|freeze|evaluate|run`. Every leaf requires explicit
  `--db`; freeze also takes the committed benchmark protocol/base prediction+checksum/snapshot
  artifacts and optional dated identity/taxonomy snapshots. `plan` writes the player protocol plus
  aggregate accessibility/stickiness report; `freeze` writes canonical hashed experimental
  predictions; `evaluate` opens outcomes only after verifying bytes; `run` composes the same seams
  without weakening them. Audit lines name identity basis, support, hashes, historical participant-
  replay limitation, and status.
- Rolling docs describe the feature only after implementation: experimental, aggregate-only,
  production-neutral, and conditional on future-only stop/go evidence. No player-effect result is
  added to the Best Call page in this feature.

**Acceptance criteria**:

- [x] Proper scores compare identical common cases; dropping hard cases cannot improve the primary
  comparison, and player-aware heldout-event, player-masked heldout-player, every unsupported/
  cold-start stratum, and every venue remain visible.
- [x] A synthetic repeat-player signal improves the player-aware estimator while a deck-only signal
  credits the deck-residual control; outcome reversal changes evaluation but no frozen byte.
- [x] A model that wins on known-known players but harms cold-start, one venue, calibration, or
  neutral-deck regret cannot emit `candidate-for-promotion-study`.
- [x] Thin identity, repeat-player, familiarity, fold, or regime support yields typed
  `not-evaluable`; a completed adverse comparison yields `stop`, never an optimistic null fill.
- [x] `plan -> freeze -> evaluate` and composed `run` are hermetic and equivalent; checksum,
  future-dated alias, schedule/outcome join, or protocol mismatch fails loudly.
- [x] The Markdown/CLI report contains aggregate counts and coefficient distributions only, labels
  unaliased handles and historical pairing replay honestly, and states production is unchanged.

## Implementation Order

1. **Identity accessibility and pilot stickiness** — prove what the corpus can identify before
   allocating any player parameter.
2. **Partially pooled fit and outcome-free freeze** — highest-risk logic; establish orientation,
   shrinkage, temporal selection, privacy, and immutable forecast boundaries before evaluation.
3. **Future-only evaluator and operator surface** — consume the frozen contracts, apply the stop/go
   conjunction, integrate CLI/docs, and leave production untouched.

## Testing

### Unit tests

- `tests/analytics/players/test_diagnostic.py`: scoped-key collision boundaries, dated aliases,
  coverage denominators, repeat floors, pairwise stickiness, event bootstrap, privacy suppression.
- `tests/analytics/players/test_effect.py`: reciprocal design matrix, zero-centered effects,
  shrinkage monotonicity, finite-grid temporal selection, cold-start behavior, convergence failure,
  common-case scores, calibration, strata, and exhaustive statuses.

### Integration tests

- `tests/test_player_effect_workflow.py`: file-backed twin corpora, prefix-only training, schedule SQL
  with no outcome field, result-mutation invariance, hash binding, taxonomy/identity snapshot dates,
  and no identifier leakage in canonical JSON.
- `tests/test_player_effect_cli.py`: temp DuckDB with explicit `--db`; two-phase and composed parity;
  checksum/protocol/schedule mismatch failures; aggregate-only Markdown and audit-comment lines.
- Re-run benchmark/ranking/player suites plus full pytest. If foundation/frontmatter changes, run the
  normal linted knowledge-index workflow; never hand-edit indexes.

### Test data

- Deterministic crossed fixtures include repeat and one-event handles, the same raw string in online
  and paper, one dated curated alias, ambiguous within-event names, two parent/variant
  configurations, known-known/known-cold/cold-cold heldout matches, B&R-separated origins, and twin
  databases differing only in future outcomes.

## Risks

- **Stable-handle assumption is false.** Exact normalized handles can collide or change, and the
  shipped alias registry is intentionally empty. **Fallback:** provenance-local keys, separate
  coverage, dated opt-in aliases, no per-person output, and `not-evaluable` when repeat support fails.
- **Player terms absorb selection/event strength rather than skill.** Pairings, progression, venue,
  and deck choice are observational. **Fallback:** event-block uncertainty, deck-residual control,
  venue/cold-start strata, neutral-deck endpoint, and language restricted to predictive player
  effect—not causal skill.
- **Crossed model is weakly identified.** Loyal pilots may never cross decks, making player and deck
  effects inseparable. **Fallback:** strong L2 pooling, inner temporal selection, repeat/familiarity
  floors, convergence/support refusal, and stop at the descriptive ledger if the model cannot
  separate synthetic ground truth.
- **Historical pairings were not actually available pre-event.** The cache exposes rounds after the
  fact. **Fallback:** player-aware results stay a labeled outcome-blind historical sensitivity; only
  origin-frozen neutral deck predictions can support a later headline study.
- **A score win is mistaken for a product license.** More parameters can improve selected folds or
  only known pilots. **Fallback:** same-complexity deck control, proper-score/calibration/regret and
  recurrence conjunction, cold-start/venue non-harm, and a terminal status that requires a separate
  promotion feature.
- **Privacy leakage through tiny cells or coefficients.** Even public handles become identifying
  when linked across sources. **Fallback:** no handles/ids/coefficient rows, privacy floor 5,
  aggregate quantiles only, local disposable artifacts, and no automatic alias writes.

## Simplification pass

- Reuse the existing benchmark folds, snapshots, hashes, common-case evaluator, event bootstrap,
  future-utility/regret logic, `normalize_player`, and curated alias loader. Do not create a second
  temporal planner, outcome metric library, player table, or production ranking path.
- Keep one small experimental estimator registry. Do not add a sampler, learned embeddings, rating
  service, persistent coefficient table, personal recommendation, taxonomy mutation, or web page.
- Treat familiarity as an earned third rung: if the player-intercept model or support gate fails,
  do not fit/maintain the larger interaction model merely because the interface permits it.
- The descriptive stickiness ledger remains useful even if every model status is not-evaluable or
  stop; model failure does not justify expanding identity collection or weakening privacy/support
  gates automatically.

## Implementation summary

- Delivered the provenance-local identity/accessibility and privacy-suppressed pilot-stickiness
  ledger, including optional effective-dated curated aliases and independent repeat/familiarity
  eligibility.
- Delivered the separate deterministic three-estimator sensitivity with chronological
  strongest-shrinkage selection, antisymmetric deck residuals, pooled player/familiarity terms,
  neutral and participant-aware frozen forecasts, and no production-registry mutation.
- Delivered immutable future-only evaluation, heldout/masked/neutral estimands, support and venue
  strata, conservative proper-score/calibration/regret stop-go gates, aggregate Markdown/JSON, and
  hermetic `advise benchmark player-effect plan|freeze|evaluate|run` commands.
- Preserved the designed privacy and authority boundaries: frozen artifacts contain no player keys
  or coefficient rows; outputs make no identity or causal-skill claim; the maximum status remains
  `candidate-for-promotion-study`, with Agency, P(best), and headline recommendations unchanged.

## Verification evidence

- Story checkpoints: 5 focused accessibility tests, 10 focused model/freeze tests, and 13 focused
  end-to-end player-diagnostic tests passed at their respective boundaries.
- Integrated affected surface: 102 player, benchmark, ranking-measurement, and refresh tests passed.
- Full repository: 3705 passed, 1 skipped in 199.65 seconds.
- Owned Ruff, compile, diff, and canonical knowledge-index checks passed; index lint reported zero
  errors and 11 pre-existing advisory warnings.
- Implementation commits: `4bd7aa3`, `4de05b5`, and `90999a8`.

## Implementation deviations

- `PlayerEffectOutcome` carries a stable match id because the shared heldout benchmark row does not
  retain source identity; schedule rows retain subject orientation so the outcome join never uses
  player identity to infer sides.
- The pure freeze function receives already-built inner folds explicitly, keeping DuckDB/filesystem
  recomputation in the workflow adapter. These are boundary-preserving signature clarifications,
  not changes to the preregistered estimator, fold, privacy, or stop-go contracts.

## Review findings (2026-08-11)

**Effective weight**: standard — one same-harness fresh-context pass completed. Closure requires
verification of the named fix set only; no second independent pass.

**Blockers**: tracked by `feature-player-effect-diagnostic-review-fixes`.

- Reconcile all train/validation rows to the frozen action universe with explicit exclusions; real
  historical parents outside the current base grid may not crash fitting.
- Validate the loaded BenchmarkProtocol hash and identity-snapshot digest against the frozen
  experiment before selection/evaluation.
- Fit the declared centered model inside the penalized objective, including frequency-weighted-zero
  familiarity constraints; do not post-center into a different predictor.
- Apply the benchmark support verdict and proportionate cold/venue floors before folds/strata can
  count toward promotion evidence.
- Make accessibility denominators ambiguity-inclusive, compute repeat/familiarity support within
  each venue, and suppress all small-cell counts—not only rates.

**Important**: included in the same checkpoint because they are accepted model/uncertainty/status
contracts: enforce distinct chronological inner origins and base-prediction identity; preserve event
bootstrap multiplicity and use paired event-block neutral-regret differences; classify measured
calibration/cold/venue/regret harm as `stop` rather than merely `diagnostic-only`.

**Nits**: none.

**Rejected**: none.

**Notes**: The independent review passed the focused 13-test suite but reproduced each blocker with
hermetic probes. A read-only real-corpus probe found 66,309 pre-cutoff matches and 30,052 with at
least one parent outside the 71-action frozen grid, proving the end-to-end KeyError path.

## Review closure (2026-08-11)

- Closed the single standard review through
  `feature-player-effect-diagnostic-review-fixes`; no second independent pass was run.
- Real-corpus action-universe reconciliation now emits named outer/inner training and validation
  exclusions instead of indexing absent base probabilities. The representative hermetic DuckDB
  path covers a historical parent absent from the frozen grid.
- Benchmark, full/grid inner base, player protocol, identity snapshot, schedule, and outer artifact
  identities are verified at their owning boundaries. Inner origins are distinct, non-overlapping,
  chronological, row-date safe, and end before the outer cutoff.
- Weighted identifiability is fitted inside the objective; benchmark support and declared
  cold/venue floors govern evaluability; identity denominators retain ambiguity and recompute by
  venue; below-floor identity counts are suppressed.
- Event bootstrap preserves sampled-block multiplicity, neutral regret uses paired event-block
  differences, and supported calibration/cold/venue/regret harm returns `stop`.
- Verification: 18 focused player review probes passed; 107 affected player/benchmark/ranking tests
  passed; full repository verification passed with 3710 tests and 1 skip in 196.89 seconds. Owned
  Ruff, compile, diff, and canonical knowledge-index checks passed; index lint remained at zero
  errors and 11 pre-existing advisory warnings.
- Closure commit for the named fix story: `e6a7055`.
- Production ranking, Agency, P(best), and the ten-estimator registry remain unchanged.
