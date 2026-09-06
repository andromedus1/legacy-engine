---
id: epic-recurrent-stable-era-evidence-future-validation
kind: feature
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence
depends_on: [epic-recurrent-stable-era-evidence-amplification]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Future-only recurrent and amplified methodology validation

## Brief

Create a new immutable benchmark protocol version that refits discovery, certification, interval
consumption, and every challenger strictly inside each historical origin. Compare current-only,
contiguous-era, recurrent-expanded, and amplified estimators over identical future events using
proper scores, calibration, coverage, interval behavior, and decision regret.

Define promotion as useful coverage gain without material degradation in predictive or decision
quality. Historical protocols and their exact estimator registries remain immutable; negative,
inconclusive, and support-censored results are valid outcomes. Promotion changes configuration only
through explicit operator authority and never occurs because a challenger merely reports more data.

## Epic context

- Parent epic: `epic-recurrent-stable-era-evidence`
- Position in epic: independent falsification and promotion gate over the shared challenger
  contracts; can proceed in parallel with report integration.

## Inherited design decisions

- Every origin discovers and certifies using only cutoff-available information.
- The objective is improved future calibration/proper score/decision regret, not nominal sample size.
- Sticky-state and other complex recurrence models participate only as explicit challengers.
- Methodology promotion is operator-controlled and creates a new versioned production configuration.

## Research briefs

- `.research/analysis/campaigns/recurrent-era-intervals/parent.md` — chained validation and promotion
  requirements.
- `.research/analysis/campaigns/recurrent-era-intervals/specialists/consume-validate.md` — cutoff-refit
  validation design.
- `.research/briefs/decision-useful-superarchetype-representation/validation-decision-utility.md` —
  common-case proper scores, selective-service accounting, event-block regret, and frozen promotion
  gates.
- `.work/active/features/epic-recurrent-stable-era-evidence-amplification.md` — exact challenger,
  all-case prediction, decomposition, concentration, and diagnostic-only authority contracts.
- `docs/analysis/best-call-ranking.md` — frozen benchmark protocol and current evidence status.

## Foundation references

- `docs/SPEC.md` — future-only ranking benchmark and recurrent promotion boundary.
- `docs/ARCHITECTURE.md` — immutable benchmark artifacts and cutoff-safe workflows.
- `docs/PRINCIPLES.md` — confidence gating and data-driven claims.

## Design decisions

- **A new protocol, not an edit to v1:** add `recurrent-evidence-future-v1` beside the shipped
  `BenchmarkProtocol` and its ten-estimator `ESTIMATOR_REGISTRY`. Existing protocol JSON, registry
  order, hashes, frozen predictions, evaluations, and aggregate artifacts remain byte-interpretable
  and immutable. Shared canonical hashing, origin snapshots, held-out loading, proper-score, and
  event-bootstrap primitives may be reused; their v1 models and semantics may not be widened until
  old artifact goldens prove byte identity.
- **Two clocks are mandatory at every origin:** `data_until` is the exclusive outcome cutoff and
  equals the fold origin; `knowledge_as_of` bounds taxonomy, legality, discovery calibration,
  certification calibration, certificate availability, interval configuration, amplification
  profile, and structure snapshots. `contemporaneous` requires actual dated inputs. A missing
  historical input may use `retrospective-policy-replay` only when rebuilt solely from the
  origin-frozen raw facts and labeled with the weaker claim; otherwise that origin is
  `not-evaluable`. Neither mode may load a latest/current derived table.
- **The whole evidence chain refits inside every origin:** the workflow constructs a pre-origin
  snapshot, then runs discovery, certification, exact interval consumption, and all amplification
  fits from that snapshot. Truncating a certificate or amplification run built on today's corpus is
  forbidden. Every stage records its run/config/input digest and clock in an `OriginRefitManifest`;
  a downstream digest or clock mismatch fails the origin before forecasts are frozen.
- **Four estimator classes, one frozen registry:** the registry contains `current-only-v1`,
  `contiguous-era-v1`, `recurrent-expanded-v1`, and each exact amplification `MethodId` exported by
  the amplification package. `contiguous-era-v1` is a benchmark comparator reconstructed at the
  origin through the interval layer's one-component scalar adapter; it is not restored as a second
  production authority. Amplification ranks/configurations remain separate candidates. No outer
  holdout, current-corpus score, or in-sample fit may choose, average, retune, or remove candidates.
- **Identical future cases mean a model-independent case manifest:** the origin action/opponent
  universe and frozen taxonomy rules are fixed before outcomes open. Later decisive non-mirror
  matches in `[data_until, evaluation_until)` are classified with those frozen rules and enter one
  common-case ledger when both entities belong to that universe. Mirrors, draws/byes, ambiguous,
  unclassified, emerging, unresolved-metadata, and outside-universe rows retain typed exclusions.
  Every estimator must issue an all-case probability for the complete pair universe before the
  holdout; a missing numeric prediction is a computational failure, never candidate-specific case
  deletion.
- **Prediction and service remain separate:** all-case forecasts feed log loss, Brier score, and
  calibration on identical rows. Frozen `served`/refusal state feeds coverage, risk-coverage, and
  the decision policy. A refused recurrent/amplified cell falls back to the unchanged current-only
  decision estimate, while the raw all-case candidate probability remains scoreable and never gains
  display authority. Report current-only, certified-history, borrowed, imputation, effective
  support, event/source/component/donor concentration, and typed refusal beside every forecast.
- **Intervals are scored as distributions, not rewarded for narrowness:** freeze aligned predictive
  draws (or a content-addressed deterministic joint-draw artifact) at the origin. For each common
  future event block, form the preregistered posterior-predictive interval for its decisive win count
  or rate, then evaluate empirical coverage, mean width, and proper interval score; action-level
  positioning intervals use the same aligned draws. Scoring a parameter interval directly against
  individual binary outcomes would be meaningless and is forbidden. A point estimate with a
  post-outcome interval, a Wilson interval over training rows, or independent marginal draws cannot
  satisfy this contract.
- **Decision comparison replays one policy:** every estimator supplies the same origin field weights,
  legal action set, structural `0.5` mirrors, stable tie-breaks, and shipped Best Call action rule.
  Refusal executes the frozen current-only fallback. Future utility and the uncertain oracle use the
  same held-out event set for all methods. Paired whole-event bootstrap produces regret differences;
  practical ties, unstable oracles, missing actions, and insufficient support are censors rather
  than forced wins or losses.
- **Evidence statuses are exhaustive and honest:** a candidate aggregate is `promotable`, `negative`,
  `inconclusive`, `support-censored`, or `invalid`. `negative` means an evaluable non-degradation or
  useful-coverage clause failed; `inconclusive` means bounds cross a frozen margin;
  `support-censored` means preregistered folds/events/calibration/field support are insufficient;
  `invalid` means leakage, artifact, registry, common-case, fit, or uncertainty integrity failed.
  Censored or inconclusive evidence is not failure evidence, but neither permits promotion.
- **Promotion is useful coverage plus simultaneous non-degradation:** the protocol preregisters a
  minimum lower-bound gain in safely served future field/event coverage and one-sided margins for
  log loss, Brier score, cumulative/global calibration, interval coverage/score, and decision regret.
  Bounds are paired by event and simultaneous across the frozen candidate-by-required-metric family;
  supported subgroups and era blocks use worst-case/unanimity rules. More rows, narrower intervals,
  or a current-corpus winner cannot satisfy the conjunction.
- **The benchmark has no promotion actuator:** it emits an immutable `PromotionAssessment` and an
  optional inert `OperatorPromotionProposal` naming one exact protocol/candidate/config/evidence
  hash. There is no `latest`, `best`, `winner`, config writer, or automatic selection API. A later
  explicitly authorized operator action must create a new versioned production configuration; the
  benchmark never edits the active config or feeds results back into discovery/certification.
- **No UI and standard review:** this is an offline CLI/JSON/Markdown evidence surface reusing the
  existing benchmark artifact conventions. No Best Call page authority or new visual interaction is
  introduced. Child stories close on verification; the integrated feature receives one independent
  standard review.

## Other agent review

- Invoked because: temporal refitting, uncertainty, and promotion authority are consequential.
- Skipped/degraded: the active AUTOPILOT assignment explicitly prohibits nested agents and
  peeragent, so no design-time advisory pass was run. This is non-blocking under the workflow.
- Receiver judgment: the approved research, shipped benchmark contracts, and completed evidence
  substrate resolve the direction; the integrated standard review remains required.

## Implementation summary

Implemented and corrected the complete future-validation lifecycle: append-only exact protocol and
registry; cutoff-built snapshots with an injected typed discovery/certification/interval/structure/
amplification refit chain; sealed common forecast/draw grids; a canonical estimator-independent
future-case and field-mass ledger; proper predictive and whole-event decision evidence; simultaneous
five-status promotion assessment; content-addressed origin/evaluation/bundle/proposal storage; and
the `advise recurrent-validation plan|freeze|evaluate|aggregate|proposal` CLI. Historical benchmark
contracts remain untouched, proposals remain inert, and `uv.lock` remains unrelated/uncommitted.

## Verification evidence

- Recurrent correction suite: 35 passed.
- Recurrent plus interval/amplification integration slice: 66 passed.
- Adjacent matchup/ranking/advisory CLI regression slice: 505 passed.
- Correction-owner pre-adjacent-refresh-fix repository suite: 3982 passed, 1 skipped.
- Ruff passed on all future-validation implementation/test files; the additive CLI surface passes
  with only the repository's existing `F821,F541` baseline ignored.
- Compileall passed for recurrent advisory/workflow and CLI modules.
- Knowledge-index regeneration completed with 0 errors, and the mandatory fresh documentation
  re-audit returned 0 Critical / 0 High.

## Standard review findings

The independent standard review at frozen commit `811b04b` requested changes. The first pass
established additive types but did not implement the acceptance surface behind them:

- origin freezing accepted arbitrary strings, ignored the source database and taxonomy snapshot,
  did not refit the typed evidence chain, and failed to enforce a strict pre-origin outcome bound;
- future-case construction crashed when sorting ordinary mapping rows and scoring did not bind the
  protocol, fold, horizon, case digest, support minima, or frozen action universe;
- decision evaluation fabricated zero regret, omitted shared field/oracle/draw mechanics, and did
  not execute the current-only fallback for refused challengers;
- aggregation ignored metric values and simultaneous paired bounds, so it could not produce honest
  `negative` or `promotable` outcomes, and the immutable store/workflow/CLI surface was absent;
- the checked-in protocol used placeholder identities and a fold plan inconsistent with its own
  declared support requirements; and
- focused tests asserted those permissive placeholders rather than the leakage, identity,
  multiplicity, draw, support, store, and end-to-end contracts.

Correction work is tracked by
`epic-recurrent-stable-era-evidence-future-validation-review-corrections`. The correction must
replace the placeholder execution path with the designed cutoff-local pipeline and adversarial
coverage; preserving the current shapes without executable evidence is not sufficient.

## Review resolution

Approved after correction. The replacement now executes and seals the cutoff-local typed stage
chain, binds canonical cases and aligned draws, scores proper predictive and whole-event decision
evidence, evaluates all five gate statuses from complete clauses, and exposes only content-addressed
evaluation artifacts plus inert operator proposals. Root reran the combined corrected publication
and recurrent acceptance suite (`95 passed in 9.71s`); the correction owner additionally verified
the final full repository (`3,983 passed, 1 skipped`, including the subsequently repaired manual
refresh entry-point regression). Every named standard-review blocker has a direct
regression, and the standard lifecycle requires no second independent implementation review.

## Review correction resolution

The correction story is complete. Every standard-review blocker now has an executable boundary and
direct adversarial regression coverage:

- origin freezing builds a real cutoff DuckDB or seals outputs from the explicit typed executor
  contract, and validates the complete clock/config/input/output/outcome/pair/draw chain;
- common future rows, exclusions, support ids, field mass, protocol/fold/horizon/action identities,
  and evaluation branches are canonical and fail closed on drift;
- predictive proper scores and posterior-predictive event intervals remain separate from service,
  while decision replay charges refusal through the frozen current-only action and bootstraps whole
  event blocks;
- every useful-coverage and non-degradation clause is value-bound under the frozen simultaneous
  family and yields exactly promotable/negative/inconclusive/support-censored/invalid;
- immutable artifact paths have no mutable alias or actuator, and only an exact all-pass assessment
  can create an operator-review-required proposal; and
- the new preregistered future protocol is internally feasible and exactly bound to an additive
  parent plan, with the historical v1 benchmark contract unchanged.

## Architectural choice

Three shapes were considered. Extending the shipped `BenchmarkProtocol` and estimator literal would
reuse the most code, but it would reinterpret old registry validation and risk changing historical
hashes. A wholly separate benchmark stack would isolate the experiment, but duplicate mature fold,
snapshot, held-out classification, hashing, scoring, and bootstrap behavior. A generic pluggable
benchmark framework would be flexible, but makes a one-off methodology test pay an abstraction cost
before a second consumer proves the need.

Choose an additive recurrent-validation domain that composes the existing benchmark's stable pure
primitives and snapshot adapter without modifying its v1 models or registry. Its own closed protocol
owns the chained-refit plan, exact estimator registry, thresholds, artifacts, and promotion verdict.
The workflow freezes one origin bundle before held-out outcomes are loaded, then scoring and decision
evaluation read only that bundle plus the shared future-case ledger.

The trickiest unit is the origin refit/freeze boundary: it must prove that discovery,
certification, interval selection, structure, and every challenger saw only origin-available facts.
The second hard boundary is joint predictive uncertainty. Marginal `PredictionSummary` values are
insufficient for event-block interval and decision comparisons, so amplification must retain aligned
origin-frozen draws or a deterministic content-addressed replay reference. Both boundaries land
before any promotion logic.

## Required amplification dependency contract

Implementation of `epic-recurrent-stable-era-evidence-amplification` must preserve these public
properties for this consumer:

- `AmplificationRun` binds the exact `IntervalEvidenceCorpus`, `AnalysisClock`, structure snapshot,
  diagnostic profile digest, method registry, baseline digests, target pair universe, and per-method
  `fit_id`; it must be constructible from an injected origin snapshot without reading current/latest
  state.
- Every `CandidateResult` retains a prediction for every common pair when numerically valid, while
  `ChallengerPrediction.served`, `service_state`, `imputation`, decomposition, concentration,
  effective support, ablations, and refusal reasons remain independent fields.
- The registry continues to export the separately named methods
  `component-hierarchical-v1`, `composition-kernel-v1`, `strategic-family-ladder-v1`, and
  `skew-low-rank-r{1,2,4}-v1` through one typed `AMPLIFICATION_METHOD_IDS` tuple from which consumers
  derive iteration and validation; amplification exposes no winner or promotion selector.
- Bootstrap/posterior draws used by `PredictionSummary` must be jointly aligned by declared draw id
  across cells for one fit and retained by value or immutable artifact digest with deterministic
  replay metadata. Future validation must be able to derive action-level draws without inventing
  independence from marginal intervals.
- Candidate failures and missing all-case predictions remain typed. They do not shrink the common
  case universe, substitute another method, or change the unchanged current/certified baselines.

## Implementation Units

### Unit 1: Append-only protocol, estimator registry, and artifact identity

**Files**: `src/legacy_engine/advisory/recurrent_validation.py`,
`src/legacy_engine/data/benchmark/recurrent-evidence-future-v1.json`,
`tests/advisory/test_recurrent_validation_protocol.py`
**Story**: `epic-recurrent-stable-era-evidence-future-validation-protocol-registry`

```python
from datetime import datetime
from pathlib import Path
from typing import Literal, TypeAlias

from legacy_engine.analytics.amplification import AMPLIFICATION_METHOD_IDS, MethodId
from legacy_engine.models.base import LegacyEngineModel

DirectEstimatorId = Literal[
    "current-only-v1", "contiguous-era-v1", "recurrent-expanded-v1",
]
EvidenceEstimatorId: TypeAlias = DirectEstimatorId | MethodId
DIRECT_ESTIMATOR_IDS: tuple[DirectEstimatorId, ...] = (
    "current-only-v1", "contiguous-era-v1", "recurrent-expanded-v1",
)
EVIDENCE_ESTIMATOR_REGISTRY = DIRECT_ESTIMATOR_IDS + AMPLIFICATION_METHOD_IDS
ReplayMode = Literal["contemporaneous", "retrospective-policy-replay"]

class PromotionMargins(LegacyEngineModel):
    alpha: float
    min_served_field_coverage_gain: float
    min_served_event_coverage_gain: float
    max_log_loss_delta: float
    max_brier_delta: float
    max_calibration_delta: float
    min_interval_coverage: float
    max_interval_score_delta: float
    max_regret_delta: float

class RecurrentEvaluationSupport(LegacyEngineModel):
    min_common_matches: int
    min_events: int
    min_event_dates: int
    min_origins: int
    min_regimes: int
    min_calibration_matches: int
    min_supported_actions: int
    min_action_matches: int
    min_future_field_coverage: float

class RecurrentBenchmarkProtocol(LegacyEngineModel):
    protocol_id: Literal["recurrent-evidence-future-v1"]
    registered_at: datetime
    authority: Literal["evaluation-only"]
    replay_mode: ReplayMode
    base_benchmark_protocol_sha256: str
    estimator_ids: tuple[EvidenceEstimatorId, ...]
    discovery_calibration_sha256: str
    certification_calibration_sha256: str
    amplification_profile_sha256: str
    structure_policy_sha256: str
    folds: tuple["RecurrentBenchmarkFold", ...]
    log_clip_epsilon: float
    interval_level: float
    bootstrap_draws: int
    seed: int
    support: RecurrentEvaluationSupport
    margins: PromotionMargins

def load_recurrent_protocol(path: Path | str) -> RecurrentBenchmarkProtocol: ...
def recurrent_protocol_sha256(protocol: RecurrentBenchmarkProtocol) -> str: ...
```

**Implementation notes**:

- Keep this model and registry out of `BenchmarkProtocol`, `BenchmarkEstimatorId`, and
  `ESTIMATOR_REGISTRY`. Reuse `canonical_json_bytes`/`content_sha256` without changing their old
  default omission behavior. A golden test loads every shipped historical protocol/artifact fixture
  and proves its bytes/hash/model interpretation are unchanged.
- The checked-in protocol is closed-schema at load even though shared project models normally ignore
  extras: reject unknown keys, duplicate/missing/reordered estimator ids, absent config hashes,
  non-finite margins, unseeded randomness, overlapping folds, registration after the first claimed
  predictive origin, and a base protocol whose fold/taxonomy/B&R plan does not match.
- Thresholds are calibration inputs fixed before outer evaluation. The file cannot carry outcome
  summaries, selected winners, promotion state, or mutable paths. Changing any registry/config/fold/
  margin creates a new protocol id and hash rather than overwriting v1.

**Acceptance criteria**:

- [x] The recurrent protocol enumerates all three direct comparators and every exact amplification
  method once; order and content are hash-bound and cannot be inferred from completed results.
- [x] Historical benchmark protocols, registries, frozen predictions, results, and checksums retain
  byte-identical golden behavior after the new protocol is installed.
- [x] Unknown methods/keys, duplicate ids, invalid margins, late registration, overlapping horizons,
  hash drift, or a mismatched base fold plan fail before any origin is built.
- [x] No protocol/result type exposes `winner`, `best`, `promoted`, active-config path, or current-
  corpus selection.

### Unit 2: Cutoff-safe chained refit and sealed origin forecast

**Files**: `src/legacy_engine/advisory/recurrent_validation.py`,
`src/legacy_engine/workflows/recurrent_validation.py`,
`src/legacy_engine/analytics/amplification/models.py`,
`src/legacy_engine/analytics/amplification/run.py`,
`tests/workflows/test_recurrent_validation_origin.py`,
`tests/workflows/test_recurrent_validation_leakage.py`
**Story**: `epic-recurrent-stable-era-evidence-future-validation-origin-refit`

```python
class RecurrentBenchmarkFold(LegacyEngineModel):
    fold_id: str
    data_until: str
    knowledge_as_of: datetime
    evaluation_until: str
    regime_id: str

class OriginRefitManifest(LegacyEngineModel):
    fold: RecurrentBenchmarkFold
    snapshot_manifest_sha256: str
    replay_mode: ReplayMode
    discovery_run_id: str
    certification_run_id: str
    interval_corpus_id: str
    amplification_run_id: str
    structure_snapshot_id: str
    stage_input_sha256: dict[str, str]
    stage_config_sha256: dict[str, str]
    max_outcome_date: str
    outcome_ids_sha256: str
    outcome_columns_accessed_by_discovery: tuple[()] = ()
    status: Literal["complete", "not-evaluable", "invalid"]
    reasons: tuple[str, ...]

class FrozenEvidencePrediction(LegacyEngineModel):
    estimator_id: EvidenceEstimatorId
    subject: str
    opponent: str
    probability: float | None
    interval: tuple[float, float] | None
    draw_artifact_sha256: str | None
    served: bool
    fallback_estimator_id: Literal["current-only-v1"] | None
    evidence_kind: Literal["current-only", "contiguous-era", "certified-expanded", "amplified"]
    current_match_ids_sha256: str
    historical_match_ids_sha256: str | None
    borrowed_match_ids_sha256: str | None
    imputation: Literal["none", "partial", "full"]
    fit_id: str
    reasons: tuple[str, ...]

class FrozenRecurrentOrigin(LegacyEngineModel):
    protocol_sha256: str
    manifest: OriginRefitManifest
    action_universe: tuple[str, ...]
    field_shares: dict[str, float]
    predictions: tuple[FrozenEvidencePrediction, ...]
    recommendation_actions: dict[EvidenceEstimatorId, str | None]
    common_pair_universe_sha256: str
    predictions_sha256: str
    code_commit: str

def refit_and_freeze_origin(
    source_db: Path,
    *,
    protocol: RecurrentBenchmarkProtocol,
    fold: RecurrentBenchmarkFold,
    taxonomy_snapshot: Path | None = None,
    knowledge_inputs: "OriginKnowledgeInputs",
) -> FrozenRecurrentOrigin: ...
```

**Implementation notes**:

- Reuse `build_origin_snapshot` for raw fact closure, but run all derived stages inside the snapshot:
  origin-safe labeling/legality, discovery, certification, interval matrix/corpus, structure snapshot,
  then amplification. Validate `max_outcome_date < data_until`; each artifact's
  `knowledge_as_of <= fold.knowledge_as_of`; and each stage input digest equals the prior output.
- Discovery receives its outcome-free typed corpus and proves no outcome columns accessed.
  Certification may use only training outcomes and its deterministic internal event partition.
  Interval consumption uses `AnalysisClock(data_until, knowledge_as_of)`, exact pair intersections,
  gap exclusion, and the exact certificate run. Amplification consumes that exact interval corpus.
- Construct `current-only-v1` and `recurrent-expanded-v1` directly from the interval evidence views.
  Rebuild `contiguous-era-v1` from the same snapshot and current origin's affectedness horizon via the
  one-component scalar adapter; record it as comparator-only. Never read a scalar-derived current
  table or use it to widen the recurrent corpus.
- Freeze the full ordered pair universe, all-case forecasts, intervals/draw references, service
  decisions, decompositions, concentration/support, fallback actions, and hashes before held-out
  outcomes are loaded. Write atomically to a content-addressed origin directory; identical replay is
  idempotent and divergent collision fails.

**Acceptance criteria**:

- [x] Changing any event, outcome, deck, label, ban, certificate, structure, or profile after the
  origin leaves the sealed forecast byte-identical; injecting it into a stage causes a clock/hash
  failure rather than a changed forecast.
- [x] Discovery accesses no outcome field; certification, interval, and amplification see only
  outcomes with event date `< data_until`; `knowledge_as_of` independently rejects later facts.
- [x] All candidates share exact action/pair/corpus/baseline digests. Camps remain current-only,
  recurrent gaps stay excluded, both pair sides govern history, and admitted rows never re-enter a
  prior or donor likelihood.
- [x] Each amplified fit retains jointly replayable aligned draws. Missing/corrupt draw artifacts or
  all-case probabilities mark that candidate/origin invalid without deleting its forecast cases.
- [x] No current-corpus or outer-holdout outcome can select rank, bandwidth, prior strength,
  thresholds, candidate membership, or active configuration.

### Unit 3: Common-case proper scores, calibration, intervals, and coverage

**Files**: `src/legacy_engine/advisory/recurrent_validation.py`,
`src/legacy_engine/workflows/recurrent_validation.py`,
`tests/advisory/test_recurrent_validation_scoring.py`,
`tests/workflows/test_recurrent_validation_cases.py`
**Story**: `epic-recurrent-stable-era-evidence-future-validation-common-case-scoring`

```python
EvaluationStatus = Literal["complete", "support-censored", "invalid"]

class FutureCaseManifest(LegacyEngineModel):
    fold_id: str
    eligible_match_ids: tuple[str, ...]
    eligible_event_ids: tuple[str, ...]
    eligible_deck_ids: tuple[str, ...]
    case_sha256: str
    field_mass_sha256: str
    exclusions: dict[str, int]

class PredictiveMetrics(LegacyEngineModel):
    estimator_id: EvidenceEstimatorId
    common_matches: int
    common_events: int
    log_loss: float | None
    brier: float | None
    calibration_intercept: float | None
    calibration_slope: float | None
    cumulative_calibration_error: float | None
    interval_coverage: float | None
    interval_mean_width: float | None
    interval_score: float | None
    served_match_coverage: float
    served_event_coverage: float
    served_field_coverage: float
    refusal_counts: dict[str, int]
    imputation_counts: dict[str, int]
    evidence_concentration: dict[str, float | None]
    status: EvaluationStatus
    reasons: tuple[str, ...]

class OriginPredictiveEvaluation(LegacyEngineModel):
    protocol_sha256: str
    origin_predictions_sha256: str
    future_cases: FutureCaseManifest
    metrics: tuple[PredictiveMetrics, ...]
    paired_event_differences: dict[str, dict[str, tuple[float, ...]]]
    status: EvaluationStatus
    reasons: tuple[str, ...]

def build_future_case_manifest(...) -> FutureCaseManifest: ...
def evaluate_recurrent_predictions(
    origin: FrozenRecurrentOrigin,
    cases: FutureCaseManifest,
    *,
    protocol: RecurrentBenchmarkProtocol,
) -> OriginPredictiveEvaluation: ...
```

**Implementation notes**:

- Extend the held-out loader with match/deck ids and reuse the origin-frozen taxonomy. Build cases
  once, independent of estimator service. Require every candidate to match the manifest's full pair
  universe and score every eligible decisive non-mirror row. `probability=None` is an invalid fit,
  not an exclusion. Clip probabilities identically by protocol.
- Log loss is primary and Brier secondary. Calibration reports intercept/slope only with both
  outcomes and sufficient support, plus bin-free cumulative observed-minus-expected error globally
  and for preregistered supported evidence/era groups. Unsupported calibration is explicitly null.
- Evaluate origin-frozen posterior-predictive intervals for each common future event block's
  decisive win count/rate using the protocol's declared interval score, coverage, and width. Use the
  aligned draw artifact for aggregated positioning intervals. Do not score a latent probability
  interval against individual `0/1` observations. Post-holdout refitting and training-row confidence
  intervals are rejected by identity.
- Publish all-case, common-served-intersection, and frozen served-policy views. Coverage denominators
  include eligible matches, events, pairs/actions, and classified future field mass. Risk-coverage
  curves apply common predeclared thresholds to frozen diagnostics; no candidate chooses thresholds
  from the scored horizon.
- Carry direct/certified-history/borrowed/imputation and event/source/component/donor concentration
  summaries into metric strata. These diagnose gain and support but never alter the common-case
  denominator or proper scores.

**Acceptance criteria**:

- [x] Swapping future outcomes changes scores but not origin predictions, case membership, service,
  evidence decompositions, intervals, or thresholds.
- [x] Every estimator has the same common match/event ids and denominator; refusing difficult cases
  cannot improve the primary all-case score by shrinking its case set.
- [x] Log loss, Brier, calibration, interval coverage/width/score, risk-coverage, exclusion counts,
  and support censoring match deterministic hand-computed fixtures and whole-event resamples.
- [x] Empty/thin calibration, interval, or subgroup support yields typed nulls/reasons. It never
  becomes zero, pass, or a dropped required row.
- [x] A future novel/unclassified/unresolved case is excluded once for every estimator and remains in
  the field/exclusion denominator; candidate-specific missing output invalidates the candidate.

### Unit 4: Frozen decision policy and paired event-block regret

**Files**: `src/legacy_engine/advisory/recurrent_validation.py`,
`tests/advisory/test_recurrent_validation_decision.py`
**Story**: `epic-recurrent-stable-era-evidence-future-validation-decision-regret`

```python
DecisionCensor = Literal[
    "insufficient-support", "practical-tie", "unstable-oracle",
    "missing-action", "invalid-joint-draws",
]

class DecisionEvaluation(LegacyEngineModel):
    estimator_id: EvidenceEstimatorId
    frozen_action: str | None
    fallback_used: bool
    future_oracle_actions: tuple[str, ...]
    realized_utility: float | None
    regret: float | None
    regret_interval: tuple[float, float] | None
    top_k_hit: bool | None
    event_blocks: int
    censor_reason: DecisionCensor | None
    reasons: tuple[str, ...]

class OriginDecisionEvaluation(LegacyEngineModel):
    fold_id: str
    field_mass_sha256: str
    action_universe_sha256: str
    evaluations: tuple[DecisionEvaluation, ...]
    paired_regret_differences: dict[str, dict[str, tuple[float, ...]]]
    status: EvaluationStatus
    reasons: tuple[str, ...]

def evaluate_recurrent_decisions(
    origin: FrozenRecurrentOrigin,
    cases: FutureCaseManifest,
    *,
    protocol: RecurrentBenchmarkProtocol,
) -> OriginDecisionEvaluation: ...
```

**Implementation notes**:

- Apply the same action universe, field shares, source gates, structural diagonal, candidate order,
  Agency calculation, and stable tie-break to each estimator's origin-frozen predictions/draws.
  A challenger refusal uses the exact current-only frozen recommendation; it is not free abstention.
- Estimate future action utility from the same case/event ledger and unrenormalized eligible future
  field target, with structural `0.5` same-archetype mass. Resample whole events with shared draw ids
  across all estimators, recompute the uncertain oracle per replicate, and retain paired regret
  differences. Never bootstrap matches independently or compare different future fields.
- Treat actions lacking preregistered future support, practical oracle ties, unstable oracle order,
  corrupt joint draws, and absent deployed fallback as named censors. Rank stability may be reported
  diagnostically but cannot replace regret or proper-score evidence.

**Acceptance criteria**:

- [x] All estimators face identical actions, future events, field mass, oracle draws, and tie rules;
  reversing input order cannot change a recommendation or regret distribution.
- [x] A refused amplified recommendation pays the current-only fallback result and retains its reason;
  refusing every difficult cell cannot create zero regret or a promotion advantage.
- [x] Duplicating matches within one event cannot create independent support or narrow paired bounds
  as if they were separate events.
- [x] Practical ties, unstable or under-supported oracles, missing actions, and invalid joint draws
  yield the exact censor with null regret rather than a forced winner.
- [x] A fixture can improve log loss while worsening regret, proving the two gates remain independent.

### Unit 5: Aggregate status, immutable evidence bundle, and operator-only proposal

**Files**: `src/legacy_engine/advisory/recurrent_validation.py`,
`src/legacy_engine/workflows/recurrent_validation.py`, `src/legacy_engine/cli.py`,
`tests/advisory/test_recurrent_validation_promotion.py`,
`tests/workflows/test_recurrent_validation_store.py`,
`tests/test_recurrent_validation_cli.py`
**Story**: `epic-recurrent-stable-era-evidence-future-validation-promotion-gate`

```python
PromotionStatus = Literal[
    "promotable", "negative", "inconclusive", "support-censored", "invalid",
]

class GateClause(LegacyEngineModel):
    clause_id: str
    comparator_id: EvidenceEstimatorId
    metric: str
    estimate: float | None
    lower_bound: float | None
    upper_bound: float | None
    threshold: float
    status: Literal["pass", "fail", "inconclusive", "censored", "invalid"]
    reasons: tuple[str, ...]

class PromotionAssessment(LegacyEngineModel):
    protocol_sha256: str
    candidate_id: EvidenceEstimatorId
    comparator_ids: tuple[EvidenceEstimatorId, ...]
    origin_evaluation_ids: tuple[str, ...]
    clauses: tuple[GateClause, ...]
    useful_coverage: bool | None
    predictive_non_degradation: bool | None
    interval_non_degradation: bool | None
    decision_non_degradation: bool | None
    status: PromotionStatus
    authority: Literal["evidence-only"]
    reasons: tuple[str, ...]

class OperatorPromotionProposal(LegacyEngineModel):
    proposal_id: str
    candidate_id: EvidenceEstimatorId
    candidate_config_sha256: str
    assessment_sha256: str
    target_config_version: str
    authority: Literal["operator-review-required"]

def aggregate_recurrent_validation(...) -> tuple[PromotionAssessment, ...]: ...
def build_operator_proposal(
    assessment: PromotionAssessment, *, target_config_version: str,
) -> OperatorPromotionProposal: ...
def write_recurrent_validation_bundle(path: Path, bundle: "ValidationBundle") -> str: ...
```

**Implementation notes**:

- Compare `recurrent-expanded-v1` with both current-only and contiguous-era. Compare every amplified
  method with current-only and recurrent-expanded on the same cases. A candidate is promotable only
  when the lower confidence bound clears both useful coverage gains and simultaneous one-sided upper
  bounds stay within every predictive, calibration, interval, and regret margin across required
  origins/regimes/subgroups. A failed supported clause is `negative`; bounds crossing a margin are
  `inconclusive`; missing preregistered support is `support-censored`; integrity failures are
  `invalid`. Precedence is `invalid > support-censored > negative > inconclusive > promotable` only
  after retaining every clause, so no failure is hidden.
- Use shared event-block resamples and a deterministic simultaneous maximum-statistic correction
  over the frozen candidate-by-required-metric family. Do not select the smallest p-value or best
  point estimate. Each candidate gets its own assessment; multiple promotable candidates remain
  separate operator choices.
- Write an append-only content-addressed bundle containing protocol, origins, cases, predictive and
  decision evaluations, raw paired replicates/digests, clauses, statuses, and Markdown summary.
  Existing paths accept byte-identical replay only. No latest alias is created.
- The CLI exposes explicit `plan`, `freeze`, `evaluate`, and `aggregate` operations under a new
  recurrent-validation group with required protocol/artifact paths. `proposal` accepts only a
  `promotable` exact assessment and writes an inert proposal; there is deliberately no apply,
  promote, config mutation, or report-authority command.

**Acceptance criteria**:

- [x] Useful served event and field coverage must clear their lower-bound margins while every
  required predictive/calibration/interval/regret upper bound is non-degrading; more nominal history
  or narrower intervals alone cannot pass.
- [x] Negative, inconclusive, support-censored, and invalid fixtures produce their exact statuses and
  complete clause ledgers. None emits a proposal or a production/config mutation.
- [x] Simultaneous bounds, status, and artifact bytes are deterministic under input/candidate order;
  adding a registered candidate cannot silently leave the multiplicity correction unchanged.
- [x] A candidate that wins on the current corpus, in-sample fit, or one outer fold cannot alter its
  registry/config or self-promote; outer outcomes are consumed exactly once by the aggregate gate.
- [x] Only an exact `promotable` assessment can create an operator-review proposal, and even that
  proposal cannot change active configuration without a separately authorized versioned workflow.
- [x] Existing v1 benchmark artifacts remain readable and unchanged after full recurrent-validation
  CLI integration.

## Implementation order

1. `protocol-registry` — freeze the append-only experiment, methods, support, and margins before any
   outcomes can influence choices.
2. `origin-refit` — build and seal the complete origin-local evidence chain and joint forecasts.
3. In parallel after origin freeze:
   - `common-case-scoring` — build the estimator-independent future ledger and predictive endpoints.
   - `decision-regret` — replay the shared decision policy and paired event-block oracle.
4. `promotion-gate` — aggregate both evidence branches, assign exhaustive statuses, and emit only an
   inert operator proposal.

## Testing

### Unit tests

- Protocol tables cover exact registry order, closed-schema rejection, finite threshold bounds,
  registration/fold boundaries, content hashes, and legacy byte/hash goldens.
- Origin fixtures inject future outcomes, decks, taxonomy changes, ban facts, certificates,
  structure snapshots, and config drift at each stage to prove the two-clock firewall and exact
  chained digests.
- Scoring fixtures hand-calculate log loss, Brier, cumulative calibration, interval score/coverage,
  service/risk coverage, imputation, and concentration under every support boundary.
- Decision fixtures cover structural mirrors, common field mass, stable ties, fallback, missing
  actions, oracle instability, paired event resampling, and prediction/regret divergence.
- Gate fixtures exercise every clause/status and simultaneous-bound boundary exactly at and on both
  sides of each frozen margin.

### Integration tests

- A file-backed corpus has an old compatible pocket, an outcome-rich excluded gap, a current pocket,
  and future events. Every historical origin reruns discovery/certification/interval/amplification;
  the gap never enters any baseline/challenger, while later outcomes affect evaluation only.
- A one-sided certificate and a parent/camp fixture prove exact pair intersection and camp
  current-only behavior through frozen predictions, scores, coverage, and regret.
- A donor/prior fixture proves each physical match enters one likelihood role, admitted history is
  never counted again as a prior, reverse cells are complements, and all estimators share the same
  cases.
- A support-starved sequence produces valid `support-censored` artifacts; an adverse sequence
  produces `negative`; a boundary-crossing sequence produces `inconclusive`; a leakage/hash failure
  produces `invalid`; only a fully supported safe coverage gain produces `promotable`.
- Run the new recurrent-validation suite plus existing benchmark, discovery, certification,
  interval, amplification, matchup/ranking, CLI, Ruff, and compileall checks before review.

## Risks

- **Historical knowledge inputs may not exist:** strict contemporaneous replay can be impossible for
  older origins. **Fallback:** use only explicitly labeled origin-fact `retrospective-policy-replay`
  where reconstructible; otherwise retain a valid support-censored/not-evaluable origin and lower the
  claim, never substitute today's derived artifact.
- **Marginal amplification summaries cannot support joint decisions:** current amplification design
  permits draws to live behind a digest but does not yet require a public aligned replay contract.
  **Fallback:** make aligned draw identity/replay part of the amplification handoff before this
  feature's origin story; if unavailable, score point forecasts but mark interval/decision clauses
  support-censored, which blocks promotion.
- **Few independent events/regimes may dominate power:** overlapping metagame conditions can make
  nominal folds look stronger than they are. **Fallback:** non-overlapping horizons, whole-event
  pairing, simultaneous bounds, explicit regime minima, and `support-censored` rather than recycling
  holdouts for tuning.
- **The contiguous comparator could resurrect scalar authority:** implementers may reuse it in
  production after rebuilding it for the benchmark. **Fallback:** expose it only through the
  benchmark adapter, label `comparator-only`, and test that no ranking/report authority consumes it.
- **Coverage can be gamed by abstention or imputation:** served-only performance can improve by
  refusing hard cases, while all-case output can look authoritative despite full imputation.
  **Fallback:** primary common-case scores, explicit fallback cost, lower-bound coverage gains, and
  typed imputation/refusal ledgers all remain separate required evidence.
- **Multiplicity can manufacture a winner:** six amplified candidates across many metrics invite
  cherry-picking. **Fallback:** freeze every candidate/config, use simultaneous family bounds, emit
  per-candidate statuses, and leave any choice among passing candidates to a later operator action.
