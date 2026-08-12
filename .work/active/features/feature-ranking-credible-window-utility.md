---
id: feature-ranking-credible-window-utility
kind: feature
stage: review
tags: [analytics, advisory, ui, testing]
parent: null
depends_on: [feature-ranking-honesty-guards, feature-agency-page-methodology]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Credible-window ranking utility

## Brief

Restore the Best Deck / Best Call HTML page as a useful decision surface without weakening its
evidence honesty. A newly confirmed B&R event currently resets the entire field to a tiny post-ban
sample, while the page can simultaneously let an older stored era override the new ban boundary for
archetypes that actually played the banned card. The proof-grade `grounded` contract then acts as a
speaking gate, leaving nearly every row silent even when it has an admissible, uncertainty-bearing
historical window.

Separate three concerns that the page currently conflates: which historical observations remain
admissible after a B&R event, how to estimate a cold-start current field, and how strongly the page
may characterize each ranking. Directly affected archetypes must never borrow pre-ban matchup
results; unaffected archetypes retain their credible entity-era history. During a thin post-ban
field, current observations remain visible but are stabilized by an explicit prior credible field
rather than either replacing it wholesale or pretending nothing changed. Every supported row should
receive a comparable estimate and uncertainty tier; `grounded` remains a valuable high-confidence
badge, not the difference between a recommendation and `n/a`.

The feature also owns a causal postmortem and durable regression contract. Tests must reproduce the
August 10 failure shape and fail if a refreshed page becomes honest-but-vacuous again, if a confirmed
ban fails to clamp a directly affected archetype, or if an unaffected archetype loses valid history
merely because another deck was banned. No estimator may be promoted as predictively validated by
this corrective work; the completed benchmark remains descriptive.

## Strategic decisions

- **Utility and honesty are separate obligations**: serve estimates for admissible evidence with
  visible uncertainty; reserve suppression for truly unscorable rows.
- **B&R affectedness is a hard lower bound**: a newer confirmed material-impact boundary cannot be
  overridden by an older detected/stored era.
- **Cold-start fields are stabilized, never concealed**: show observed post-ban counts and the
  explicit influence of prior credible field evidence.
- **Grounded remains a badge, not an inclusion gate**: high-confidence status still matters, while
  lower-confidence supported rows remain comparable and interesting.
- **The process must test usefulness**: correctness tests alone are insufficient when the output can
  legally collapse into a non-answer.

## Simplification opportunity

Replace the page's independent global-ban default, era-first matchup selection, and candidacy/
grounding suppression decisions with one typed evidence-policy projection consumed by ranking,
recommendation, audit copy, and browser rendering. Remove duplicated interpretations rather than
adding another diagnostic ranking beside the existing ones.

## UI surface

This is an existing single-page HTML surface. Preserve its established visual language, but redesign
the first-read hierarchy so a reader sees: the actionable ranking, confidence/credibility tier, how
the cold-start field was formed, and which evidence was reset by the ban. Advanced ledger and
methodology details remain progressively disclosed.

## Design decisions

- **A ban is an entity-level evidence boundary, not a global history eraser.** For every parent
  archetype and camp, the effective matchup horizon is the later of its stored/detected era and
  the newest confirmed ban where `archetype_valid_since` finds material direct impact. An older
  stored row, including an explicit `stable_since: null`, may not override that lower bound.
- **The transition field is an explicit empirical-Bayes projection.** The observed slice is the
  current confirmed ban regime. When it contains fewer than the existing 500-deck field floor, the
  immediately preceding confirmed regime contributes at most `500 - observed_n` deterministic
  pseudo-decks. Prior mass is renormalized over archetypes not materially affected by the new ban;
  affected archetypes receive no carry-forward mass. At 500 observed decks the prior is exactly
  zero. If no qualifying prior slice exists, the page honestly uses the thin observed field.
- **Observed presence and decision weight remain separate.** Every row carries its exact post-ban
  count/share, prior contribution, and effective decision share. Prior-only archetypes are labeled
  `transition-prior`; they are never described as post-ban sightings. New and affected archetypes
  compete through observations only.
- **The practical shortlist uses the existing posterior lean, not a new estimator.** All eligible
  rows are ordered by the already-defined lean `q25`, then median, then label. This is the page's
  uncertainty-aware practical view. The existing ci-gated Agency ordering remains the
  proof-grade/benchmark authority and is shown beside it; this corrective feature makes no
  predictive-validation claim.
- **Grounding changes presentation, not existence.** `grounded`, `lean`, `imputation-dominated`,
  `transition-prior`, `inactive`, and `unscorable` remain visible evidence strata. The first read
  shows the top practical rows with tier, interval, observed/prior field provenance, and whether a
  ban clamped their matchup history.
- **Usefulness is a typed publication contract.** Generation records observed/effective field
  sizes, affected clamps, supported/prior-only/grounded counts, both top calls, rendered shortlist
  count, and named degraded reasons. A contradiction such as supported rows with no practical call
  or no rendered shortlist fails before atomic replacement; a genuinely evidence-empty run may
  publish only as explicitly unavailable.
- **No mockup is required.** This reorganizes the existing page from its current cards, badges,
  table rows, disclosures, and typography; it introduces no new visual language or interaction
  model. The implementation must preserve keyboard/ARIA behavior and responsive table semantics.

## Architectural choice

Three shapes were considered:

1. **Widen the global `field_since`.** This restores candidates quickly but re-admits pre-ban
   evidence for decks that actually changed and still leaves `grounded` as the de facto speaking
   gate.
2. **Relax the grounding threshold.** More rows receive a badge, but the threshold merely moves the
   sample cliff and does not repair the field or horizon semantics.
3. **One typed credible-window policy with two honest views (chosen).** Clamp matchup history per
   entity, form a transparent transition field for cold-start composition, keep ci-gated Agency as
   proof-grade authority, and promote the existing posterior lean into a practical shortlist.

Option 3 repairs the causal boundary and the user-facing failure independently. It reuses existing
affectedness, field-floor, measurement-ledger, and lean contracts rather than adding a third matrix
or a hand-tuned score in the template.

## Implementation units

### Unit 1: Confirmed-ban lower bound for entity horizons

**Story**: `feature-ranking-credible-window-utility-horizon-clamp`

**Files**:

- `src/legacy_engine/analytics/eras/consume.py`
- `src/legacy_engine/analytics/affectedness.py`
- `tests/analytics/eras/test_consume.py`

```python
class EraHorizon(LegacyEngineModel):
    since: str | None
    source: str
    trigger: str | None
    alarm: str | None
    attribution_kind: str
    stored_since: str | None = None
    affected_since: str | None = None
    clamped_by_confirmed_ban: bool = False


def era_horizons(
    con: duckdb.DuckDBPyConnection,
    archetypes: Sequence[str],
    *,
    provenance: ProvenanceFilter | None = None,
    ban_events: Sequence[BanEvent] | None = None,
) -> tuple[dict[str, EraHorizon], tuple[str, ...]]: ...
```

Implementation notes:

- Resolve the stored exact/parent candidate exactly as today, independently compute the affected
  lower bound against confirmed bans, then choose the later non-null date. Preserve the existing
  source/trigger when it wins; otherwise identify the ban and direct affectedness as the winner.
- An unaffected entity retains its stored date or full-history `None`. Thin pre-ban data remains
  conservative per `affectedness.py`; do not infer indirect field effects.
- Camps inherit the parent clamp unless camp-specific evidence establishes a later boundary. Pair
  windows continue to apply the later subject/opponent horizon after this resolution.

Acceptance criteria:

- [ ] An exact or parent stored era older than a materially affecting confirmed ban is clamped to
      that ban, including when the stored date is `None`.
- [ ] An unaffected entity keeps its existing admissible history; one deck's ban does not reset it.
- [ ] Horizon provenance states both candidates and which one won, and adaptive single/multi
      matrix paths remain numerically consistent.

### Unit 2: Cold-start transition field

**Story**: `feature-ranking-credible-window-utility-transition-field`

**Files**:

- `src/legacy_engine/advisory/field.py`
- `src/legacy_engine/analytics/eras/consume.py`
- `scripts/refresh_best_call_ranking.py`
- `tests/test_field_model.py`
- `tests/analytics/eras/test_consume.py`
- `tests/test_refresh_best_call_ranking.py`

```python
FieldEvidenceKind = Literal["observed", "transition-stabilized", "observed-thin"]


class FieldSlice(LegacyEngineModel):
    since: str
    until: str | None
    deck_n: int
    counts: dict[str, int]


class TransitionField(LegacyEngineModel):
    kind: FieldEvidenceKind
    observed: FieldSlice
    prior: FieldSlice | None
    affected_archetypes: tuple[str, ...]
    prior_strength: int
    effective_counts: dict[str, int]
    shares: dict[str, float]
    reason: str


def build_transition_field(
    con: duckdb.DuckDBPyConnection,
    *,
    current_ban_since: str,
    until: str | None,
    affected_since: Mapping[str, str | None],
    target_n: int = 500,
    provenance: ProvenanceFilter | None = None,
) -> TransitionField: ...
```

Implementation notes:

- Use exact integer observed counts. Allocate prior pseudo-counts by deterministic largest-remainder
  rounding after removing affected archetypes and renormalizing the surviving previous-regime
  distribution. Effective counts sum to `observed_n + prior_strength` and can safely drive the
  existing Dirichlet field-share uncertainty.
- Preserve zero post-ban observations separately from effective shares. Camp fractions remain
  based on post-ban observations when present; prior-only parents use their preceding-regime camp
  composition and are labeled as such rather than blended invisibly.
- The ranking field uses effective shares, but matchup matrices and strategic-plan results continue
  to use each entity's clamped `PairWindow`; field stabilization may never widen matchup evidence.

Acceptance criteria:

- [ ] Prior strength is `min(prior.deck_n, max(0, 500 - observed.deck_n))`; it is zero at or above
      500 observed decks and absent when no valid preceding regime exists.
- [ ] Affected archetypes receive zero prior pseudo-counts; unaffected, absent archetypes can carry
      explicitly labeled prior support; observed new decks retain their exact counts.
- [ ] Counts, shares, and serialized provenance reconcile exactly and deterministically.

### Unit 3: Practical shortlist and first-read hierarchy

**Story**: `feature-ranking-credible-window-utility-practical-surface`

**Files**:

- `src/legacy_engine/advisory/positioning.py`
- `src/legacy_engine/advisory/ranking_measurement.py`
- `scripts/refresh_best_call_ranking.py`
- `scripts/best_call_ranking_template.html`
- `tests/test_positioning.py`
- `tests/test_ranking_measurement.py`
- `tests/test_refresh_best_call_ranking.py`

```python
RankingEvidenceStratum = Literal[
    "grounded", "lean", "imputation-dominated", "transition-prior",
    "inactive", "unscorable",
]


def practical_recommendation_order(
    rows: Mapping[str, Mapping[str, object]],
) -> tuple[str, ...]: ...
```

Implementation notes:

- Extend evidence classification with separate `observed_field_share` and
  `decision_field_share`; default the former to the latter for non-transition callers.
- `practical_recommendation_order` includes eligible rows only and sorts by lean `q25`, lean
  median, then stable label. It never substitutes an Agency upper bound for missing posterior
  output. Keep `production_recommendation_order` unchanged and render its call as proof-grade.
- Move a compact first-read panel ahead of methodology: practical top rows, proof-grade call,
  interval/tier badges, observed/effective field counts, prior strength, and affected clamp count.
  Existing detail tables and methodology variants remain progressive disclosure.

Acceptance criteria:

- [ ] A thin-ban fixture with zero grounded rows still renders a non-empty practical shortlist when
      supported rows exist, with no row mislabeled as observed.
- [ ] Practical ordering is deterministic and uncertainty-aware; proof-grade ordering and benchmark
      parity remain unchanged.
- [ ] Keyboard, ARIA, responsive layout, generated-gate controls, and stale-state behavior remain
      functional.

### Unit 4: Usefulness publication contract and causal postmortem

**Story**: `feature-ranking-credible-window-utility-usefulness-contract`

**Files**:

- `src/legacy_engine/workflows/decision_refresh.py`
- `src/legacy_engine/ops/status.py`
- `scripts/refresh_best_call_ranking.py`
- `tests/test_decision_refresh.py`
- `tests/test_ops_status.py`
- `tests/test_refresh_best_call_ranking.py`
- `docs/analysis/best-call-ranking.md`
- `docs/ARCHITECTURE.md`

```python
class RankingUtilitySummary(LegacyEngineModel):
    observed_field_n: int
    effective_field_n: int
    prior_strength: int
    affected_clamp_count: int
    supported_rows: int
    transition_prior_rows: int
    grounded_rows: int
    practical_call: str | None
    proof_grade_call: str | None
    rendered_shortlist_rows: int
    status: Literal["useful", "degraded", "unavailable"]
    reasons: tuple[str, ...]


def validate_ranking_utility(summary: RankingUtilitySummary) -> None: ...
```

Implementation notes:

- Return the summary from the generator and thread it through decision-refresh and scheduled status
  as additive artifact metadata. The HTML audit block serializes the same object.
- Fail before atomic replacement when the summary is internally contradictory: supported rows but
  no practical call, a practical call omitted from the rendered shortlist, or effective counts that
  do not reconcile. Low grounded count is a named degraded state, not a publication failure.
- Add the August 10 failure-shape fixture and an end-to-end first-read assertion. Document the causal
  chain: global field reset, era precedence inversion, proof badge promoted into visual silence, and
  file-exists operational success. Record the preventive contracts, not a historical changelog.

Acceptance criteria:

- [ ] Refresh/status distinguishes useful, degraded, and unavailable output and preserves last-good
      output on a contradictory generation.
- [ ] Regression tests prove affected clamp, unaffected history retention, transition provenance,
      supported-row visibility, and a present top call without hard-coding live archetype totals.
- [ ] Foundation/runbook text describes the current dual-view contract and does not claim the
      practical shortlist has passed future-only validation.

## Dependency order

1. Horizon clamp establishes admissible matchup evidence.
2. Transition field depends on that affectedness identity.
3. Practical surface depends on the transition projection and preserves proof-grade authority.
4. Usefulness/status depends on the final generated payload and render contract.

## Test strategy

- Pure unit fixtures cover date precedence, pseudo-count allocation, evidence strata, deterministic
  ordering, and contradiction validation.
- File-backed DuckDB fixtures reproduce a confirmed-ban cold start with affected, unaffected, new,
  and prior-only archetypes; no test uses the mutable default database.
- Generator integration executes the browser behavior harness and verifies that displayed first-read
  rows, serialized policy, and Python ordering agree.
- Decision-refresh tests inject writer failures and contradictory summaries to prove atomic
  last-good behavior; scheduled status tests verify additive backward-compatible decoding.
- The feature closes only after focused analytics/ranking/refresh tests and the authoritative full
  repository suite pass.

## Risks and pre-mortem

- **Riskiest assumption — preceding-regime composition remains useful for unaffected decks.** The
  prior is deliberately capped, decays to zero, excludes directly affected archetypes, and is fully
  visible. If it proves misleading, the fallback is the same typed projection with
  `prior_strength=0`; no matchup history or stored data migration is involved.
- **Affectedness is intentionally direct, not causal omniscience.** Indirect rebuilds may survive the
  prior. The page must expose the affected set and prior influence; later detection can add a newer
  entity era without changing this contract.
- **Pseudo-counts could be mistaken for observations.** Names, types, audit copy, and UI must never
  call effective counts observed decks. Exact observed counts remain adjacent everywhere.
- **Practical and proof-grade calls can disagree.** That disagreement is valuable evidence and must
  be shown, never reconciled by averaging or hidden behind one label.
- **Operational schema drift.** Status additions are optional on read and mandatory on new ranking
  writes so old status artifacts remain readable while new contradictions fail fast.

## Simplification target

After integration, the refresh script no longer independently decides global field scope, current
presence, ranking inclusion, and first-read recommendation. One package-owned transition/evidence
projection feeds scoring, audit, rendering, and operational usefulness checks. Existing diagnostic
variants remain; no fifth estimator or browser-only ranking is added.

## Implementation summary

The feature is implemented across the four dependency-ordered checkpoints:

1. `EraHorizon` is now a typed candidate boundary. Direct confirmed ban affectedness is resolved
   per entity/parent and can clamp an older stored era as `ban-clamped`, retaining both candidate
   dates; unaffected and no-era fallback paths remain compatible.
2. `build_transition_field` projects an exact observed post-ban field plus a preceding-regime prior
   capped at the 500-deck floor. Affected archetypes receive no pseudo-counts, integer allocation
   is deterministic, and effective shares never widen matchup pair windows.
3. The existing posterior lean now has a deterministic practical order (Q25, median, label), and
   the page first read shows that shortlist, intervals, evidence strata, observed/effective field
   provenance, prior strength, clamp count, and the separate proof-grade production call. The
   `production_recommendation_order` and benchmark authority are unchanged.
4. `RankingUtilitySummary` is validated and threaded through generation, refresh, and scheduled
   status. Contradictory output fails before acceptance; low grounded support is named degraded,
   while evidence-empty output is explicitly unavailable. The causal postmortem and preventive
   contract are recorded in the ranking runbook and architecture.

## Implementation verification

- Child commits: `469262b`, `2ae3758`, `755400e`, `1b3c79e`.
- Focused checks: era/field (103 passed), ranking refresh (44 passed), refresh/status (38 passed),
  positioning evidence/practical order (50 passed).
- Authoritative suite: `PYTHONPATH=. uv run --no-sync python -m pytest -q` — 3838 passed, 1 skipped.
- Knowledge index regenerated and linted: 0 errors, 6 existing warnings (decision-count and README
  orphan warnings).

## Scope / deviations

- No benchmark estimator, protocol, production ordering, Modern port, sideboard advisor, or rules
  engine was changed. `uv.lock` remains user-owned and unmodified.
- Camp row payload parity remains intact; transition field provenance is carried at archetype/meta
  level and camp fractions continue to reflect exact observed current presence.
- The validator carries an additive ranked-action tuple so it can prove a practical call is present
  in the rendered shortlist, which the minimal design sketch could not establish from a count alone.
