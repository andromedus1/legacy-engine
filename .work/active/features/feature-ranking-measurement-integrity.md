---
id: feature-ranking-measurement-integrity
kind: feature
stage: implementing
tags: [analytics, advisory, honesty]
parent: epic-best-deck-decision-trust
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Ranking measurement integrity — reconcile windows, rates, and observable floors

## Brief

Resolve the measurement disagreements that can reverse a best-deck conclusion before adding new
ranking views. Reproduce and explain the independent adjusted-field-WR divergence, clamp
build/camp comparisons to both the subject and opponent stable eras, surface event/month
concentration when one cluster dominates a cell, and state how much of every camp's matchup floor
is actually observable.

This feature absorbs the actionable scope of backlog items
`idea-adj-field-wr-recompute-divergence`, `idea-clamp-split-comparisons-to-opponent-era`, and
`feature-camp-floor-observability-banner`. Their original backlog files remain as evidence until
feature design maps each finding to an implementation checkpoint.

## Strategic decisions

- The page-used adaptive measure remains the headline only if the recomputation proves its window
  selection is unbiased and reproducible; divergence is surfaced, not averaged away.
- A comparison may narrow for either entity's era but may never widen past an opponent disturbance
  merely to buy sample size.
- Missing bad matchups are missing evidence, never a high floor.

## Simplification opportunity

Extract or reuse one typed row/cell measurement primitive across refresh, display, and benchmark
code. Delete hand-rolled duplicate formulas once parity is proven.

## Design decisions

- **The adaptive policy is outcome-blind and auditable.** A pair's era start is the later of the
  subject and opponent horizons. The page may fall back only by its fixed sample gate and the
  already-defined ban-affectedness rule; it never chooses a window by observed win rate. Every
  selected cell carries both candidates, the selected source, and a machine-readable reason.
- **Reconciliation has two separate checks.** Recomputing a row from its serialized selected-cell
  ledger must be numerically identical to the headline value (a hard invariant). A second,
  strict-common-era estimate deliberately applies one uniform start -- the latest horizon among
  the subject and current-field opponents -- and is shown as a labeled divergence diagnostic with
  its own coverage. The two estimates are never averaged.
- **A large adaptive/common-era delta is evidence to inspect, not proof of a bug.** The adaptive
  estimate remains headline-eligible only when its deterministic selection/provenance invariants
  pass. A failed parity or invalid window suppresses the headline with a named reason; an honest
  estimator disagreement remains visible for the methodology feature to evaluate.
- **Comparison windows cannot buy stale sample.** The reusable pair-window contract clamps a
  requested lower bound to `max(requested_since, subject_since, opponent_since)`. Ranking and
  camp/build comparison code must use it. Generic explicitly historical reports may still show a
  requested old window, but may not label that output a current build/camp comparison.
- **Concentration is evidence metadata, not a corrected rate.** Each selected cell records the
  largest event and calendar-month shares. The ranking surface warns when either contains at least
  40% of a cell with `n >= ground_n` (the dogfooded 6/14 failure shape); it never downweights or
  deletes the cluster automatically. The threshold is a reversible presentation constant.
- **Observed floor and page floor are distinct.** The existing interactive `ground_n` continues to
  decide the page floor until the methodology feature changes it. Separately, every row reports
  opponent counts at `n >= 10` and `n >= DISPLAY_GATE_N`, plus field-share coverage at the display
  gate. A camp with zero display-grade cells says `floor unobserved`; missing cells never imply a
  clean floor.
- **The typed measurement ledger is the shared contract.** The refresh script, HTML payload, and
  future benchmark consume one package-owned cell/row measurement API. The script stops owning a
  second implementation of source selection, adjusted field WR, floor, and coverage.
- **Advisory review.** The active epic and the absorbed findings already lock the consequential
  choices. A different model class is not available in this delegated host, so no cross-model
  advisory pass was run; standard feature review remains required after implementation.

## Architectural choice

Three shapes were considered:

1. **Patch the refresh script in place.** Add a same-window column, concentration SQL, and camp
   observability directly to `scripts/refresh_best_call_ranking.py`. This is the smallest diff but
   preserves the formula duplication that caused the disagreement and leaves the benchmark unable
   to reuse the exact production measurement.
2. **Introduce a package-owned measurement ledger over existing matrices (chosen).** Keep raw
   outcome extraction and matchup estimation in `analytics`, add only additive concentration
   evidence and a single pair-window primitive there, then let `advisory/ranking_measurement.py`
   own source selection and row summaries. The refresh page and future benchmark consume the same
   typed result.
3. **Replace `MatchupMatrix` with a universal ranking matrix.** Put fields, fallback candidates,
   row metrics, and benchmark concerns into the core matrix type. This centralizes everything but
   couples a reusable estimator to one report's `ground_n`, field weights, and honesty strata.

Option 2 keeps the statistical estimator and decision/report policy at their existing boundary.
It changes contracts additively: existing `MatchupCell` consumers ignore concentration metadata,
while the new ledger makes selection and recomputation explicit. It also gives the future-only
benchmark a production API without turning the benchmark into a second ranker.

## Implementation Units

### Unit 1: Pair-window and concentration evidence contracts

**Story**: `feature-ranking-measurement-integrity-evidence-contracts`

**Files**:

- `src/legacy_engine/models/matchup.py`
- `src/legacy_engine/analytics/match_results.py`
- `src/legacy_engine/analytics/matchup.py`
- `src/legacy_engine/analytics/eras/consume.py`
- `tests/test_match_results.py`
- `tests/test_matchup.py`
- `tests/test_matchup_multi_split.py`
- `tests/analytics/eras/test_consume.py`

```python
class CellConcentration(LegacyEngineModel):
    event_id: str | None
    event_n: int
    event_share: float
    month: str | None
    month_n: int
    month_share: float


class PairWindow(LegacyEngineModel):
    subject: str
    opponent: str
    requested_since: str | None
    subject_since: str | None
    opponent_since: str | None
    effective_since: str | None
    clamped: bool
    reason: str


def clamp_pair_window(
    subject: str,
    opponent: str,
    *,
    subject_since: str | None,
    opponent_since: str | None,
    requested_since: str | None = None,
) -> PairWindow: ...


def concentration_for_tallies(
    event_counts: Mapping[str, int],
    month_counts: Mapping[str, int],
    *,
    n: int,
) -> CellConcentration | None: ...
```

**Implementation notes**:

- Extend the cardinality-safe rounds query with tournament id and date and accumulate directed
  event/month counts beside wins/losses. Both directed cells receive the same event/month
  observation. Draws, mirrors, byes, ambiguous names, provenance, and half-open dates retain their
  existing semantics.
- Add `concentration: CellConcentration | None = None` to `MatchupCell` and an optional keyword to
  `build_cell`. Preserve byte-identical numeric fields for callers that omit it.
- Pool concentration buckets on the opponent side with the same explicit `camp_parent` map used by
  `_pool_opponent_tallies`; never parse camp prefixes. Adaptive builders select concentration from
  the exact same `mr_by_since[s_ab]` bucket as wins/n.
- Replace the duplicated `max(valid_since[a], valid_since[b])` expressions in both adaptive
  builders with `clamp_pair_window(...).effective_since`. This pure contract is also the required
  entry point for any ranking-time build/camp delta.

**Acceptance Criteria**:

- [ ] Pair windows choose the later subject/opponent horizon, never widen an explicit requested
      lower bound, and return a deterministic reason naming what clamped the window.
- [ ] Single-split and multi-split adaptive matrices retain full numeric parity and attach identical
      concentration metadata for equivalent cells.
- [ ] Event/month bucket counts sum to cell `n`; pooled camp-opponent buckets do not double-count.
- [ ] Missing observations return `None`, not zero-share concentration, and all existing matrix
      callers remain valid through additive defaults.

### Unit 2: Shared selected-cell ledger and row reconciliation

**Story**: `feature-ranking-measurement-integrity-ranking-ledger`

**Files**:

- `src/legacy_engine/advisory/ranking_measurement.py`
- `tests/test_ranking_measurement.py`
- `scripts/refresh_best_call_ranking.py`
- `tests/test_refresh_best_call_ranking.py`

```python
CellSourceKind = Literal["era", "ban-fallback", "full-corpus", "strict-common-era"]


class RankingCellSource(LegacyEngineModel):
    kind: CellSourceKind
    since: str | None
    cell: MatchupCell


class RankingCellMeasurement(LegacyEngineModel):
    subject: str
    opponent: str
    field_share: float
    era: RankingCellSource | None
    fallback: RankingCellSource | None
    selected_kind: CellSourceKind | None
    selected: RankingCellSource | None
    selection_reason: str
    measured: bool
    concentration_warning: str | None


class FloorObservability(LegacyEngineModel):
    opponents_total: int
    opponents_n10: int
    opponents_display_grade: int
    display_grade_field_coverage: float
    floor_observed: bool
    reason: str | None


class RowReconciliation(LegacyEngineModel):
    adaptive_selected: float | None
    serialized_recompute: float | None
    parity_delta: float | None
    strict_common_since: str | None
    strict_common: float | None
    strict_common_coverage: float
    estimator_delta: float | None
    headline_eligible: bool
    reason: str | None


class RankingRowMeasurement(LegacyEngineModel):
    subject: str
    cells: tuple[RankingCellMeasurement, ...]
    adjusted_field_wr: float | None
    floor: float | None
    floor_opponent: str | None
    agency: float | None
    measured_coverage: float
    top_k_measured: bool
    grounded: bool
    floor_observability: FloorObservability
    reconciliation: RowReconciliation


def select_ranking_cell(
    subject: str,
    opponent: str,
    field_share: float,
    *,
    era: RankingCellSource | None,
    fallback: RankingCellSource | None,
    ground_n: int,
    concentration_warn_share: float = 0.40,
) -> RankingCellMeasurement: ...


def measure_ranking_row(
    subject: str,
    cells: Sequence[RankingCellMeasurement],
    *,
    top_k: int,
    cover_min: float,
    strict_common_sources: Mapping[str, RankingCellSource],
    display_gate_n: int = DISPLAY_GATE_N,
) -> RankingRowMeasurement: ...
```

**Implementation notes**:

- Move `make_cells`, `_floor_eligible`, and `row_stats` policy into the typed module. Selection
  preserves today's fixed order: display-grade-at-`ground_n` era, then eligible ban fallback,
  then the thin era candidate, then fallback only when era is absent, else explicit missing.
- `measure_ranking_row` normalizes only over selected cells with `n >= 1`, exactly matching the
  current adjusted-WR definition. It recomputes once from the typed objects and once from the JSON
  projection; any non-floating-roundoff disagreement makes `headline_eligible=False`.
- Build one strict-common-era matrix per distinct common start, not per row. Its field-weighted
  value and coverage are diagnostic fields. Thin/missing strict-common cells yield explicit nulls
  or partial coverage; they never replace adaptive cells.
- Recreate the Cradle-shaped disagreement hermetically: exact agreement where windows coincide,
  a material adaptive/common delta where they do not, zero serialized parity delta, and an
  outcome-independent selection trace explaining every chosen source.

**Acceptance Criteria**:

- [ ] The selected-cell ledger reproduces every pre-feature archetype/camp numeric row field and
      ordering on the existing hermetic parity corpus before old formulas are deleted.
- [ ] A missing era cell with a present fallback is labeled by its true fallback kind (never
      mislabeled `era`), and a completely absent pair remains an explicit null.
- [ ] The strict-common diagnostic exposes estimate, coverage, start date, and delta without
      blending it into adjusted WR or agency.
- [ ] `headline_eligible` fails loudly on ledger/serialization mismatch or an invalid pair window,
      while estimator divergence alone remains a labeled diagnostic.
- [ ] Floor observability reports count-based `n>=10`/`n>=30` coverage and field-share-weighted
      display-grade coverage independently of the interactive page floor gate.

### Unit 3: Ranking-page honesty surface and rolling documentation

**Story**: `feature-ranking-measurement-integrity-page-surface`

**Files**:

- `scripts/refresh_best_call_ranking.py`
- `scripts/best_call_ranking_template.html`
- `tests/test_refresh_best_call_ranking.py`
- `docs/analysis/best-call-ranking.md`

```python
def ranking_row_payload(row: RankingRowMeasurement) -> dict[str, object]: ...
```

**Implementation notes**:

- Serialize the package model rather than rebuilding row metrics in script dictionaries. Preserve
  current field names during this feature so downstream template code and the honesty-guards
  feature can migrate additively.
- Add an adjusted-WR reconciliation chip/detail (`adaptive`, `strict common`, delta, both
  coverages), per-cell event/month concentration warning, and camp floor-observability line.
- If `headline_eligible` is false, render `n/a` plus its reason in headline fields; never emit a
  stale or zero placeholder. A divergent but valid row keeps adaptive as the headline and labels
  the strict-common disagreement.
- Update the runbook's metric definitions and audit output in the same change. The generated page
  remains disposable and gitignored.

**Acceptance Criteria**:

- [ ] Every camp row states display-grade floor coverage; zero display-grade cells visibly say
      `floor unobserved -- absence of bad cells is not evidence of none`.
- [ ] Concentrated cells name the dominant event/month, match count, share, and selected window.
- [ ] The page shows adaptive/common divergence without averaging and suppresses only invalid or
      non-reproducible headlines.
- [ ] Existing interactive `ground_n` behavior remains functional; changing it recomputes current
      row metrics while the generated-threshold reconciliation is clearly labeled as fixed.
- [ ] Script tests cover typed payload shape, honest-null rendering, concentration rendering,
      observability rendering, and deterministic whole-page output.

## Trickiest Unit

Unit 2 is the crux. The system currently has three subtly different concepts hiding in plain
dictionaries: the era candidate, the ban-scoped fallback candidate, and the chosen cell. A safe
reconciliation must preserve the current Nadu-rule behavior while making every choice replayable
from serialized evidence. The implementation should therefore land the source-selection truth
table as pure tests before changing the refresh script, then prove old/new row parity on the
multi-split fixture. Only after parity is green should the old script formulas be deleted.

The strict-common estimator must be computed from a real uniformly-windowed matrix using the same
match parser and shrinkage implementation, not by filtering already-aggregated adaptive cells. Its
purpose is independent recomputation. Caching by distinct common start keeps this honest without
reintroducing one scan per row.

## Implementation Order

1. Pair-window and concentration evidence contracts -- establish trustworthy inputs and preserve
   single/multi matrix parity.
2. Shared selected-cell ledger and row reconciliation -- land the pure truth table and Cradle-shaped
   diagnostic before migrating the consumer.
3. Ranking-page honesty surface and documentation -- switch the page to the shared contract, delete
   duplicate formulas after parity, and expose the new evidence.

## Testing

### Unit tests

- `tests/analytics/eras/test_consume.py`: null horizons, one-sided disturbance, both disturbed,
  requested bound earlier/later than the pair era, deterministic clamp reasons.
- `tests/test_match_results.py`: decisive directed event/month accumulation; draw/mirror/bye and
  ambiguous-name exclusion; half-open window and provenance behavior unchanged.
- `tests/test_matchup.py`: concentration shares, ties resolved deterministically, absent-data null,
  and numeric `MatchupCell` parity with additive defaults.
- `tests/test_ranking_measurement.py`: source-selection truth table, row weighting, grounding,
  floor observability, concentration warning threshold, common-era diagnostic, parity failure, and
  honest-null cases.

### Integration and regression tests

- `tests/test_matchup_multi_split.py`: single-parent/multi-parent parity includes concentration and
  pair-window provenance for full, era, and ban-only paths.
- `tests/test_refresh_best_call_ranking.py`: old/new row parity fixture before duplicate deletion;
  Cradle-shaped adaptive/common divergence; JSON/template/audit rendering; fixed-seed determinism.
- Proportionate verification: targeted files above, then the full suite because
  `compute_match_results` and `MatchupCell` are broad analytics contracts.

### Test data

- Extend the existing rounds-bearing two-parent fixtures with two event ids in one month and a
  third event in another month, creating known 40%-boundary and non-concentrated cells.
- Use hand-built typed sources for pure selection/observability tests. Do not require the mutable
  local production DuckDB for regression correctness.

## Risks

- **Riskiest assumption -- strict-common era is a useful independent diagnostic.** The latest
  opponent horizon may make the uniform matrix extremely thin. **Fallback:** retain the typed
  value as explicit null/low-coverage evidence and let the later methodology feature compare other
  predeclared estimators; never widen it for sample.
- **Aggregation drift while adding concentration.** Camp pooling could count one match twice or
  select buckets from a wider window than the cell. **Fallback:** keep concentration additive and
  non-scoring, gate release on `sum(bucket)==n` plus single/multi parity, and suppress the warning
  when invariants fail.
- **Payload migration breaks interactive recomputation.** The template currently expects mutable
  plain dictionaries. **Fallback:** preserve existing JSON keys and add typed fields alongside
  them for this feature; remove compatibility only after the methodology consumer migrates.
- **Performance regression from uniform recomputations.** A per-row rebuild would turn the refresh
  into an N-scan job. **Fallback:** cache by distinct strict-common start and print scan count/timing;
  if distinct starts still explode, emit the diagnostic only for current candidates in this pass.
- **40% concentration threshold over-warns tiny cells.** **Fallback:** require `n >= ground_n`, show
  the raw fraction, and keep the threshold as one named presentation constant that can be calibrated
  later without changing stored evidence.
- **Least sure -- whether adaptive/common divergence alone predicts future error.** This feature
  makes it measurable but does not claim it does. The future-only benchmark is the gate for that
  conclusion.

## Implementation summary

- Execution capability: inherited frontier model at high effort, selected by the autopilot caller
  for statistically consequential cross-module ranking work.
- Review weight: standard (caller); feature intentionally stops at `stage: review` for an
  independent pass.
- Delivered all three child checkpoints: outcome-blind pair windows and concentration evidence;
  the package-owned selected-cell ledger with serialized replay and strict-common diagnostics; and
  the ranking-page/runbook honesty surface.
- Integrated files: shared matchup extraction/model contracts, era window consumption, the new
  `advisory/ranking_measurement.py` boundary, refresh generator/template, focused tests, and the Best
  Call runbook.
- Simplification: adaptive pair-window logic and row measurement now each have one owner; duplicate
  report formulas were removed, and strict-common matrices are cached per distinct common start.
- Design deviations: serialized reconciliation re-validates the full typed JSON projection instead
  of maintaining a second hand-built report dictionary; concentration warnings render inline beside
  the exact selected cell rather than in a separate panel. Both preserve the designed contracts.
- Adjacent issues parked: none.

## Integrated verification

- Child-focused measurement/refresh/matchup suite: 227 passed.
- Full repository suite: `PYTHONPATH=. .venv/bin/pytest -q` — 3591 passed, 1 skipped in 192.60s.
- All children are `stage: done`; implementation commits: `e8ac67f`, `60cebbf`, `34cfce0`.

## Review findings (2026-08-11)

**Effective weight**: standard — one same-harness fresh-context pass completed. Closure requires
verification of the named fix set only; no second independent pass.

**Blockers**: tracked by `feature-ranking-measurement-integrity-review-fixes`.

- Reconcile against the canonical serialized projection consumed by browser row math, including
  awkward rounding and same-threshold idempotence evidence.
- Bind concentration evidence to each candidate source so interactive era/fallback changes select
  or clear the matching warning.
- Render both `n>=10` and display-grade floor observability for every row.
- Carry and validate pair-window provenance through selected ranking candidates and suppress an
  invalid window from headline eligibility.

**Important**: the strict-common diagnostic must distinguish contributing coverage from
display-grade coverage and render its exact start even when the estimate is null. This is included
in the same checkpoint because it corrects an accepted feature contract rather than creating a
separate roadmap item.

**Nits**: none.

**Rejected**: none.

**Notes**: The receiver reproduced the review's code-path evidence and accepts the findings as
current-cycle measurement-integrity defects. Security, concurrency, and migration lenses were not
applicable. Browser behavior was reviewed through deterministic payload/JavaScript flow because a
headless browser runtime was unavailable.
