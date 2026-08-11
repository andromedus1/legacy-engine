---
id: feature-ranking-future-only-benchmark
kind: feature
stage: implementing
tags: [analytics, advisory, testing]
parent: epic-best-deck-decision-trust
depends_on: [feature-ranking-measurement-integrity, feature-ranking-honesty-guards, feature-agency-page-methodology]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Future-only ranking benchmark — test whether today's call predicts tomorrow

## Brief

Build a chronological walk-forward harness that freezes every ranking input at cutoff T, evaluates
against events after T, and compares legacy-engine with deliberately simple baselines. Report
match-probability calibration and loss, ranking quality, top-k usefulness, and decision regret
across multiple cutoffs and ban regimes. Prevent leakage from future era boundaries, taxonomy
promotions, player ratings, field composition, or card availability.

Support operator-supplied dated external ranking/matchup snapshots as an independent comparison
surface. External data is labeled by source and date and is not required for the core benchmark;
the feature must not depend on an unapproved scraper or silently treat external consensus as truth.

## Strategic decisions

- Primary evidence is match-level Brier/log loss and calibration; rank correlation and regret are
  decision-facing secondary metrics.
- Every derived feature is computed strictly from information available before the evaluated
  match/event.
- The benchmark compares against recent raw WR, field share, top-finish/conversion, and simple
  shrinkage baselines.
- A future “best deck” headline may claim predictive validation only after repeated windows beat
  the simple baselines; otherwise results remain descriptive positioning estimates.

## Simplification opportunity

Persist a small typed frozen-prediction artifact and reuse production ranking code. Do not create a
parallel benchmark-only ranking engine.

## Design decisions

<!-- Directional choices were already fixed by the epic/brief and the operator's approved
autopilot pass. No consequential ambiguity remained that required another question round. -->

- **One operational target, two honest replay modes**: the benchmark asks whether a ranking issued
  immediately before cutoff `T` helps select a playable parent archetype for the next 28 days.
  `contemporaneous` mode requires a taxonomy/classification snapshot whose effective date is no
  later than `T`. The immediately usable historical mode is explicitly named
  `retrospective-fixed-parent`: it replays the current parent-archetype ontology, pins its rules and
  label hashes for the whole run, and excludes camps and superarchetypes. It can validate the
  estimator under a fixed ontology, but cannot claim to reproduce exactly what the operator knew at
  old origins. A current staged/promoted camp or family registry is never projected backward.
- **Whole event-date batches are the temporal atom**: training is strictly `event_date < T`; the
  holdout is `[T, min(T + 28 days, next registered B&R date))`. All tournaments sharing a calendar
  date stay together, so provider ordering cannot move one same-day event into training while
  another is scored. Origins advance by 28 days from the latest origin; a B&R boundary starts a
  fresh origin and resets that cadence, so holdouts remain non-overlapping and never straddle a
  registered regime change. The ban ledger itself is filtered to entries effective at or before `T`
  before era and affectedness calculation.
- **A snapshot, not a query convention, enforces the freeze**: each origin gets a temporary/file-backed
  DuckDB containing only pre-cutoff event rows and their dependent facts. Entity eras are recomputed
  inside that snapshot. Field composition, candidates, taxonomy, card availability, B&R state,
  matchup cells, priors, and methodology projections are then read only from the snapshot. The
  prediction artifact contains no future counts or outcomes and is hash-checked before evaluation.
- **Player identity is not a predictor in this feature**: player names may be used after prediction
  only to construct dependence-aware uncertainty. Event-block bootstrap is the primary uncertainty
  unit. A player-component sensitivity is emitted only when a stable predeclared identity mapping
  covers at least 80% of scored matches; otherwise it is an explicit unavailable result. No alias
  discovered after `T`, future player record, or future event can affect a forecast. The dependent
  player-effect feature must add player predictors as a separately named estimator using strictly
  pre-match state.
- **Eligibility is frozen before outcomes are opened**: the public action universe is classified,
  origin-legal parent archetypes with positive current presence and field share at least `0.001`.
  Product service eligibility continues to use the shipped evidence strata and gates; the benchmark
  does not relax them. Proper scoring uses the common set of held-out decisive non-mirror matches
  whose two labels were in the frozen action/opponent universe. Unclassified, ambiguous, emerging,
  mirror, bye/draw, and out-of-universe rows are counted by typed reason rather than silently
  discarded. Future disappearance is not a zero win rate: an action without future support is
  censored from rank/regret and reported as such.
- **The estimator registry is preregistered**: `production-ci-gated` is the only primary production
  estimator. `production-raw`, `production-ban-scoped`, `production-era-only`, and
  `production-lean` are fixed diagnostic perturbations from the methodology handoff; results cannot
  select or retune them. Baselines are frozen as `coin-50`, `recent-raw-wr`, `field-share`,
  `top-finish-conversion`, and `simple-jeffreys-shrinkage`. The field-share and top-finish
  ranking-only baselines use `0.5` as their explicitly uninformative match forecast because they do
  not define a matchup probability. Any later estimator selection must happen on earlier
  development folds, produce a new protocol id/content hash, and leave a newest contiguous final
  block unopened.
- **Prediction quality and decision value stay separate**: common-case match log loss (probabilities
  clipped identically at `1e-6`) is primary; Brier score, cumulative calibration error,
  calibration slope/intercept, and risk/coverage are complementary. Kendall rank agreement, top-3
  usefulness, and playable-action regret are secondary decision endpoints. Recommendation regret
  compares each frozen action with the best origin-eligible action under event-bootstrap draws of
  the later realized known-field utility; mirror field mass is structural `0.5`, and unsupported or
  practically tied oracles yield `unresolved`, not a forced winner.
- **Minimum support is a protocol gate, not a result-driven choice**: a fold is predictively
  evaluable only with at least 250 common decisive matches across at least 10 events and 4 distinct
  event dates. Calibration slope/intercept additionally require both outcomes and 500 predictions.
  Decision endpoints require at least 5 origin-eligible actions, at least 5 future-supported actions
  with 8 decisive matches apiece, and at least 80% of future classified field mass represented by
  origin-known opponents. A claim-level aggregate requires at least 6 evaluable non-overlapping
  folds spanning 2 registered ban regimes. Every failed gate carries a named reason and null
  headline metric.
- **Evaluation cannot mutate the model**: the evaluator reads an immutable prediction artifact plus
  later outcome rows, verifies all recorded hashes and temporal bounds, and writes a separate result.
  It never feeds losses, calibration, rank, regret, external consensus, or chosen thresholds back
  into the ranking implementation. A new choice requires a new preregistration and future block.
- **External evidence is optional and dated**: an operator-supplied JSON snapshot names its source,
  observed-at timestamp, taxonomy, and either ranks/scores or matchup probabilities. It is accepted
  only when `observed_at <= T`, mapped without fuzzy guessing, and scored only on its common cases.
  It is a labeled comparator, never ground truth, and no scraper is introduced.

## Other agent review

The design-time cross-model advisory pass was skipped because this worker's active autopilot
delegation prohibits nested delegation. This is non-blocking under the workflow. The feature has a
normal independent review after implementation.

## UI decision

No mockup is required. The new operator surface is a nested CLI plus machine-readable JSON/JSONL and
a generated Markdown summary; it does not change the established Best Call page or introduce a new
interactive screen. The generated benchmark report is an analytical artifact, not a production UI.

## Architectural choice

Three shapes were considered:

1. **Add `until=T` to each existing SQL call.** This is superficially small, but persisted era rows,
   current registries, current B&R state, and any missed query remain leakage paths. Proving the
   negative across the ranking graph would be brittle.
2. **Build a separate benchmark ranking implementation over exported match rows.** This makes the
   temporal boundary easy to see, but duplicates the production source-selection, coverage,
   candidacy, and methodology contracts—the exact drift this epic has just removed.
3. **Create an origin-frozen corpus adapter, extract one typed production ranking handoff, and score
   immutable predictions later.** Infrastructure builds a cutoff-safe DuckDB and recomputes derived
   state; the shared advisory handoff issues both production rows and per-match probabilities; pure
   benchmark functions plan folds and evaluate artifacts.

Choose option 3. The filesystem/database adapter is outside the statistical core, production and
benchmark share one typed ledger, and the two-phase artifact provides a direct audit that future
rows were unavailable when predictions were issued. The trickiest unit is the snapshot boundary:
if it cannot prove era, B&R, taxonomy, and event closure, no later metric is meaningful, so it lands
first with adversarial leakage tests.

## Implementation Units

### Unit 1: Preregistered protocol, event folds, and leakage-safe origin snapshot

**Files**: `src/legacy_engine/advisory/ranking_benchmark.py`,
`src/legacy_engine/workflows/ranking_benchmark.py`, `src/legacy_engine/analytics/affectedness.py`,
`src/legacy_engine/analytics/eras/consume.py`, `tests/test_ranking_benchmark.py`,
`tests/test_ranking_benchmark_snapshot.py`
**Story**: `feature-ranking-future-only-benchmark-protocol-snapshot`

```python
BenchmarkEstimatorId = Literal[
    "coin-50", "recent-raw-wr", "field-share", "top-finish-conversion",
    "simple-jeffreys-shrinkage", "production-raw", "production-ci-gated",
    "production-ban-scoped", "production-era-only", "production-lean",
]
TaxonomyReplayMode = Literal["contemporaneous", "retrospective-fixed-parent"]

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

class BenchmarkProtocol(LegacyEngineModel):
    protocol_id: str
    created_at: str
    taxonomy_mode: TaxonomyReplayMode
    first_cutoff: str
    final_evaluation_until: str
    horizon_days: int = 28
    step_days: int = 28
    primary_estimator: BenchmarkEstimatorId = "production-ci-gated"
    estimator_ids: tuple[BenchmarkEstimatorId, ...]
    action_min_share: float = 0.001
    log_clip_epsilon: float = 1e-6
    bootstrap_draws: int = 2_000
    seed: int = 730_021
    support: EvaluationSupport = EvaluationSupport()

class BenchmarkFold(LegacyEngineModel):
    fold_id: str
    cutoff: str
    evaluation_until: str
    regime_start: str
    regime_end: str | None
    event_dates: tuple[str, ...]

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
    card_availability_sha256: str
    degraded: bool
    reasons: tuple[str, ...]

def plan_walk_forward_folds(
    event_dates: Sequence[str],
    ban_dates: Sequence[str],
    protocol: BenchmarkProtocol,
) -> tuple[BenchmarkFold, ...]: ...

def build_origin_snapshot(
    source_db: Path,
    destination_db: Path,
    *,
    fold: BenchmarkFold,
    protocol_hash: str,
    taxonomy_snapshot: Path | None = None,
) -> SnapshotManifest: ...

def archetype_valid_since(
    con: duckdb.DuckDBPyConnection,
    archetypes: list[str],
    *,
    provenance: str | None = None,
    affect_threshold: float = 0.25,
    ban_events: Sequence[tuple[date, str, str]] | None = None,
) -> dict[str, str | None]: ...
```

**Implementation notes**:

- `plan_walk_forward_folds` is pure. It uses half-open bounds, inserts registered B&R dates as
  origins, truncates a prior horizon at the boundary, resets the 28-day cadence, and
  includes/excludes entire date batches.
  Folds remain non-overlapping for claim aggregation; truncated windows shorter than the protocol's
  event support are retained as explicit not-evaluable folds rather than silently removed.
- `build_origin_snapshot` is the infrastructure adapter. It copies `tournaments` with date `< T`,
  then only dependent `decks`, `deck_cards`, `rounds`, `standings`, required card rows, and pinned
  classification inputs. It does not copy `entity_eras`, `superarchetype_members`, player-strength
  tables, or other derived future state. It runs origin-safe labeling where required, calls
  `run_eras(..., ban_events=events_as_of_T)`, validates referential closure, fsyncs, hashes, and
  atomically renames the complete snapshot.
- Parameterize the existing ban-only fallback seam rather than monkey-patching module globals.
  Default `None` stays byte-identical for production; the snapshot supplies its filtered ledger.
- `retrospective-fixed-parent` preserves current parent labels only after hashing the rule/label
  inputs, clears `decks.variant`, and disables staged splits/superarchetypes. It records the weaker
  claim. `contemporaneous` fails closed when its dated snapshot is absent, later than `T`, or hash
  mismatched. Its snapshot is a self-contained directory with a
  `TaxonomySnapshotManifest` plus the frozen MTGO-format rule payload; both prediction and later
  outcome classification use that same payload. Optional precomputed label assignments are
  accepted only when their canonical hash matches the manifest.
- Card availability is the set of card names observed in pre-cutoff decklists plus any authoritative
  dated release rows available by `T`; no post-cutoff oracle/card dimension row is available to
  labeling or legality. The current schema has no release-date column, so observed-by-`T` is the
  default and the limitation is recorded; it does not authorize a silent current-card fallback.

**Acceptance criteria**:

- [ ] Same-date tournaments are never divided across train/evaluation, and no holdout crosses a
  registered B&R boundary.
- [ ] Injecting a post-cutoff tournament that changes field share, eras, labels, or outcomes leaves
  the frozen snapshot manifest and predictions byte-identical.
- [ ] A deliberately future-dated era row, ban event, camp promotion, player alias/rating, and card
  row are absent from the snapshot or cause a fail-closed manifest error.
- [ ] Snapshot `max_training_event_date < cutoff`, all child rows resolve to a copied event, and all
  as-of ledgers/hashes are serialized.
- [ ] The normal production affectedness/era path remains unchanged when no `ban_events` override is
  provided.

### Unit 2: Shared production handoff, declared baselines, and immutable predictions

**Files**: `src/legacy_engine/advisory/ranking_measurement.py`,
`src/legacy_engine/advisory/ranking_benchmark.py`, `scripts/refresh_best_call_ranking.py`,
`tests/test_ranking_measurement.py`, `tests/test_ranking_benchmark.py`,
`tests/test_refresh_best_call_ranking.py`
**Story**: `feature-ranking-future-only-benchmark-prediction-freeze`

```python
class FrozenMatchupPrediction(LegacyEngineModel):
    estimator: BenchmarkEstimatorId
    subject: str
    opponent: str
    probability: float
    served: bool
    source_kind: str
    imputed: bool
    refusal_reason: str | None

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
    generated_at: str
    code_commit: str
    estimator_registry: tuple[BenchmarkEstimatorId, ...]
    action_universe: tuple[str, ...]
    field_shares: dict[str, float]
    matchup_predictions: tuple[FrozenMatchupPrediction, ...]
    recommendations: tuple[FrozenRecommendation, ...]
    methodology: dict[str, dict[str, object]]
    seeds: dict[str, int]

def project_matchup_probability(
    cell: RankingCellMeasurement,
    *,
    spec: MethodologyVariantSpec,
    unresolved_center: float = 0.5,
) -> FrozenMatchupPrediction: ...

def freeze_origin_predictions(
    snapshot_db: Path,
    *,
    protocol: BenchmarkProtocol,
    manifest: SnapshotManifest,
) -> FrozenOriginPredictions: ...

def write_frozen_predictions(
    path: Path, predictions: FrozenOriginPredictions,
) -> str: ...  # returns sha256 of canonical JSON bytes
```

**Implementation notes**:

- Extract only the archetype ranking-ledger assembly currently embedded in
  `refresh_best_call_ranking.py` into the package-owned handoff. The page and benchmark both consume
  it; the page's gated Agency/P(best)/candidate behavior and serialized blob remain exactly
  unchanged. Do not build a second matrix or coverage definition.
- The four hard methodology projections use `methodology_variant_specs`; `production-lean` uses the
  shipped seeded posterior. The all-case probability is the selected source's declared raw/shrunk
  point estimate; an unresolved cell receives the protocol's explicit `0.5` forecast with
  `imputed=True`, while product `served` remains false. This makes common-case proper scoring
  possible without converting imputation into display permission.
- Baselines use only snapshot data: `coin-50`; trailing-28-day pair/marginal raw WR;
  current field-share ordering; per-event top-quartile conversion; and Jeffreys pair shrinkage
  toward the snapshot marginal. Stable canonical ids break ranking ties. Each baseline declares
  whether its matchup probability is modeled or the explicit uninformative `0.5`.
- `production-ci-gated` recommendation reproduces the runbook's deployed ordering: first served
  row by grounded+current, grounded-but-not-current, then ungrounded; Agency descending and stable
  canonical id within a stratum. Diagnostics never replace it.
- Canonical JSON uses sorted keys, finite floats, explicit nulls/reasons, and an atomic write. The
  checksum is verified before evaluation. `generated_at` is the preregistered protocol timestamp,
  not the wall clock, so replay stays byte-reproducible. Prediction files contain neither future
  event ids nor evaluation counts.

**Acceptance criteria**:

- [ ] Refresh-page archetype payload is byte-identical before/after handoff extraction, including
  canonical gated rows, P(best), eligibility, and methodology outputs.
- [ ] Every preregistered estimator emits a deterministic recommendation and common-universe matchup
  probability/refusal record from snapshot-only inputs.
- [ ] Production variants equal direct projections of the shared typed ledger; missing cells are
  `0.5 + imputed + unserved`, never a fabricated measured cell.
- [ ] Re-running a freeze with the same protocol/snapshot/code/seeds produces identical canonical
  prediction bytes and hash.
- [ ] No score or recommendation changes when evaluation outcomes or optional external snapshots
  change after the freeze.

### Unit 3: Future-only evaluator, optional external comparators, CLI, and report

**Files**: `src/legacy_engine/advisory/ranking_benchmark.py`,
`src/legacy_engine/workflows/ranking_benchmark.py`, `src/legacy_engine/cli.py`,
`tests/test_ranking_benchmark.py`, `tests/test_ranking_benchmark_cli.py`,
`docs/analysis/best-call-ranking.md`, `docs/SPEC.md`, `docs/ARCHITECTURE.md`
**Story**: `feature-ranking-future-only-benchmark-evaluation-report`

```python
OutcomeExclusionReason = Literal[
    "outside-fold", "mirror", "bye-draw-invalid", "ambiguous-player",
    "unclassified", "emerging-label", "outside-frozen-universe",
]

class ExternalRankingSnapshot(LegacyEngineModel):
    source: str
    observed_at: str
    taxonomy: str
    ranks: dict[str, int] = {}
    scores: dict[str, float] = {}
    matchup_probabilities: dict[str, float] = {}

class HeldoutMatch(LegacyEngineModel):
    event_id: str
    event_date: str
    provenance: str
    subject: str | None
    opponent: str | None
    subject_player_key: str | None
    opponent_player_key: str | None
    subject_won: bool | None
    exclusion_reason: OutcomeExclusionReason | None

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

class BenchmarkEvaluationSummary(LegacyEngineModel):
    protocol_hash: str
    folds: tuple[BenchmarkEvaluation, ...]
    evaluable_folds: int
    represented_regimes: int
    paired_differences: dict[str, dict[str, float | None]]
    status: Literal["not-evaluable", "descriptive", "predictive-claim-supported"]
    reasons: tuple[str, ...]

def evaluate_origin(
    predictions: FrozenOriginPredictions,
    outcome_rows: Sequence[HeldoutMatch],
    *,
    protocol: BenchmarkProtocol,
    external: Sequence[ExternalRankingSnapshot] = (),
) -> BenchmarkEvaluation: ...

def aggregate_benchmark(
    protocol: BenchmarkProtocol,
    folds: Sequence[BenchmarkEvaluation],
) -> BenchmarkEvaluationSummary: ...

def render_benchmark_markdown(summary: BenchmarkEvaluationSummary) -> str: ...
```

**Implementation notes**:

- Rehydrate held-out matches with event/date and normalized player keys, orient them once by stable
  canonical action id, and score every estimator on the identical common set. Mirror rows never
  improve proper scores; their future field mass contributes structural `0.5` to decision utility.
- Clip all forecast probabilities only inside log-loss calculation. Report event-block bootstrap
  paired differences versus each baseline, fold-by-fold results, cumulative observed-minus-expected
  calibration, and risk/coverage. Do not compare one model's easy served subset with another's all
  cases.
- Rank/regret uses only the origin-frozen action universe and future-supported actions. Emerging
  opponent share remains in the coverage denominator. Event bootstrap recomputes the future utility
  and oracle on each draw; no-separated-oracle/tie bands produce a null endpoint with a reason.
- `predictive-claim-supported` is possible only for the preregistered primary estimator when all
  claim support gates pass, event-block 95% paired log-loss differences beat `coin-50`,
  `recent-raw-wr`, and `simple-jeffreys-shrinkage`, Brier is noninferior to the best of them, regret
  is lower than the declared ranking baselines, at least 60% of evaluable folds agree in direction,
  and no required calibration metric is unavailable. Otherwise status is `descriptive` or
  `not-evaluable`; the benchmark never changes production automatically.
- `advise benchmark plan` writes a canonical protocol after showing folds/support estimates;
  `freeze` builds and writes origin snapshots/predictions; `evaluate` verifies and scores later data;
  `run` composes historical replay without weakening the two-phase hashes. Every command requires
  explicit `--db`; artifacts default below ignored `data/benchmarks/<protocol-id>/`. Audit lines name
  cutoff, taxonomy mode, hashes, exclusions, support, and weaker-claim states.
- External snapshots fail if future-dated, malformed, or ambiguously mapped. Rank-only snapshots
  receive rank/top-k/regret results only; matchup probabilities additionally receive proper scores.
  Missing rows remain missing and are reported, never fuzzy-filled.
- Update the runbook and rolling foundations only for assertions changed by the implementation.
  Generated JSON/Markdown under `data/` remains disposable operator output and is not indexed.

**Acceptance criteria**:

- [x] A synthetic signal change after cutoff is detected as better by future-only scores without
  affecting any frozen byte; swapping future outcomes reverses evaluation only.
- [x] Proper scores use one identical decisive non-mirror common-case set, while served coverage and
  all exclusion/censoring reasons remain separately visible.
- [x] Event-block bootstrap is deterministic by seed; player identity is absent from predictions and
  used only by the optional coverage-gated sensitivity.
- [x] Thin folds, unsupported actions, emergent field mass, and tied/noisy future oracles emit honest
  nulls and named reasons; none can accidentally satisfy the claim gate.
- [x] An external snapshot dated after the fold cutoff fails loudly; a valid partial snapshot is
  labeled and scored only where supported.
- [x] Hermetic CLI tests pass `--db`, produce canonical artifacts, verify hash tampering fails, and
  prove `plan -> freeze -> evaluate` plus composed historical `run` parity.
- [x] Focused benchmark/ranking tests, normal documentation/index validation if knowledge-bearing
  docs change, and the full repository suite pass.

## Dependency order

1. `feature-ranking-future-only-benchmark-protocol-snapshot` — the leakage boundary and protocol
   must be testable before any forecast is considered valid.
2. `feature-ranking-future-only-benchmark-prediction-freeze` — consumes the frozen origin and
   establishes immutable production/baseline predictions.
3. `feature-ranking-future-only-benchmark-evaluation-report` — opens future outcomes only after the
   artifact exists, then integrates the CLI and docs.

## Testing strategy

- **Protocol/fold unit tests** pin validation, half-open event-date batching, 28-day stepping, B&R
  truncation, deterministic fold ids, and preservation of not-evaluable folds.
- **Snapshot adversarial tests** build two file-backed corpora differing only after `T` and assert
  identical manifests/predictions. Dedicated fixtures seed future era rows, promoted variants,
  aliases/ratings, bans, and cards to prove they cannot cross the boundary.
- **Ranking handoff tests** protect exact page parity and verify every baseline/production estimator
  against hand-calculated tiny ledgers, including imputed-but-unserved cases.
- **Evaluator unit tests** derive log loss/Brier/calibration/exclusions from hand-built forecasts;
  bootstrap by event; verify support gates, ties, censoring, and common-case comparability.
- **Integration/CLI tests** use the file-backed hermetic DB pattern, explicit `--db`, canonical JSON
  hashes, tamper detection, dated external fixtures, and two-phase/composed-run parity.
- **Integrated verification** runs benchmark, ranking-measurement, refresh-page, matchup/era, and CLI
  focused suites before the full standard pytest command. No golden asserts that a named real deck
  or production variant must win.

## Failure pre-mortem

1. **Derived state leaks despite date filters.** Signal: adding a future era/promotion changes an old
   forecast. Prevention: copy only raw pre-cutoff facts, recompute eras, clear non-authoritative
   taxonomy/player caches, and compare adversarial twin snapshots.
2. **Retrospective taxonomy is mistaken for contemporaneous knowledge.** Signal: an old camp appears
   in a report before its promotion. Prevention: parent-only retrospective mode, typed weaker-claim
   reason, dated snapshot requirement for richer taxonomy, and manifest hashes.
3. **Censoring makes a weak model look good.** Signal: a model's log loss improves as its served
   coverage falls. Prevention: identical all-case set with explicit uninformative fallback,
   served-risk as secondary, and typed exclusion/field-mass ledgers.
4. **One huge online event supplies the apparent win.** Signal: row-level intervals are tight while
   fold results disagree. Prevention: event-block bootstrap, whole date batches, per-fold direction,
   and minimum event/date/regime support.
5. **Future results become another tuning set.** Signal: variant/threshold ids change after evaluation.
   Prevention: content-hashed protocol and prediction artifacts, one primary estimator, no evaluator
   mutation path, and a new protocol/future block for every later choice.
6. **Regret crowns a noisy oracle.** Signal: a best action changes across most bootstrap draws or has
   little direct support. Prevention: action/support/field-coverage gates, bootstrap oracle per draw,
   practical tie state, and honest null regret/top-k.

## Simplification pass

- Evaluate parent archetypes first; camps/families require dated taxonomy evidence and remain outside
  the default claim. This avoids rebuilding the already-delivered typed three-level ledger or
  granting exploratory families decision authority.
- Reuse the production ranking measurement/methodology handoff and extract only the archetype
  assembly seam needed by both callers. Do not add a benchmark matrix, a fifth production variant,
  a learned calibrator, or a replacement P(best).
- Use one compact canonical JSON artifact family plus a generated Markdown view—no database schema,
  service, web page, notebook, scraper, or artifact migration/version ladder.
- Keep estimator ids/thresholds in one protocol registry. Evaluation reports disagreement; it does
  not blend estimators, tune them, or write back into production.

## Implementation summary

- Delivered the preregistered protocol, whole-date/B&R-aware fold planner, cutoff-safe raw-fact
  snapshot, recomputed eras, dated taxonomy replay, and adversarial leakage guards in `c4735c4`.
- Delivered immutable predictions for the five production variants and five declared baselines,
  explicit unserved `0.5` forecasts, canonical hashes, and the shared typed ranking-measurement
  contract in `605b03a`.
- Delivered proper/calibration/rank/regret evaluation, support and censoring ledgers, event-block and
  coverage-gated player-component uncertainty, dated external comparators, Markdown evidence, and
  hermetic `advise benchmark plan|freeze|evaluate|run` commands in `815c08f`.
- Closed a documentation-review finding by binding taxonomy mode/effective-at/taxonomy/rules hashes
  into frozen predictions and rejecting a different evaluation snapshot before held-out outcomes
  are classified. Aggregate predictive claims require both calibration intercept and slope.
- Design deviations stayed within the declared boundaries: snapshot/freeze/held-out extraction are
  filesystem/DuckDB workflow adapters; the existing package-owned ranking-measurement contract made
  a page-script extraction unnecessary; event uncertainty is retained per fold and aggregated over
  preregistered non-overlapping folds; contemporaneous replay requires a strict rules directory.
- Verification: integrated focused suite — 232 passed in 16.53s; full repository suite — 3688
  passed, 1 skipped in 198.15s; focused Ruff, compilation, and diff checks passed. Canonical
  knowledge-index regeneration reported 0 errors and 11 pre-existing warnings. The required
  post-fix documentation re-audit reported 0 Critical/High/Medium/Low findings.
- Review handoff: standard independent feature review remains required. Production ranking remains
  authoritative and unchanged; benchmark output is evaluation evidence only and never tunes or
  promotes an estimator automatically.

## Review findings (2026-08-11)

**Effective weight**: standard — one same-harness fresh-context pass completed. Closure requires
verification of the named fix set only; no second independent pass.

**Blockers**: tracked by `feature-ranking-future-only-benchmark-review-fixes`.

- Make B&R-reset origins freeze a non-empty, cutoff-safe field or censor them explicitly without
  preventing the required multi-regime evaluation.
- Freeze and validate retrospective parent taxonomy so post-freeze label changes cannot alter
  held-out identity.
- Bind the exact fold schedule and as-of B&R ledger into preregistration identity; freeze/run may not
  silently recompute a different experiment from mutable state.
- Measure future-field claim coverage from a classified deck/field-mass ledger, not match-row share.
- Include structural mirror utility and require a stable, uncertainty-aware oracle for regret;
  tied/unstable/null regret needs a named censor reason and cannot feed the aggregate claim gate.

**Important**: included in the same checkpoint because each is an accepted evidence-output or
immutability contract: render the full promised operator evidence; validate external taxonomy and
missing/common-case coverage; refuse overwrite of a different frozen artifact at a deterministic
path.

**Nits**: none.

**Rejected**: none.

**Notes**: Independent affected-surface verification passed 325 tests and hermetic probes reproduced
the five blockers. The review was same-harness fresh-context and did not rerun the recorded full
suite.
