---
id: feature-strategic-plan-best-call-viz
kind: feature
stage: implementing
tags: [analytics, viz, ui]
parent: null
depends_on: [epic-superarchetype-layer-three-level-page]
release_binding: null
gate_origin: null
created: 2026-08-02
updated: 2026-08-02
---

# Strategic-plan table in Best Deck / Best Call

## Brief

Add a curated semantic layer above composition-derived superarchetypes to the existing self-contained
Best Deck / Best Call HTML. Each archetype has one primary strategic plan for aggregation and may
carry secondary explanatory labels: Disrupt and pressure, Go off, Go over, Go wide, or Lock and
outlast. Recompute plan-versus-plan performance from decisive matches rather than averaging rendered
archetype percentages. Render the plans as the same sortable/filterable metric table used by
Archetypes and Camps; each row expands through an accessible semantic control into the selected-plan
portrait plus exact opponent-plan ledger. Remove the strategy-family agency map and camps × parent
opponents figure. Keep composition-derived superarchetypes as the internal statistical-borrowing
layer rather than conflating composition with strategic intent.

The arc ends in `decks/best-deck-best-call-ranking.html`; it does not create a separate archetype
page. The portrait/data contract should be reusable by the future `DeckDashboard`.

## Strategic decisions

- Primary strategic plan alone owns aggregation; secondary plans explain hybrids without double-counting.
- Same-plan matches contribute structural 50% to field expectation but cannot set the floor.
- Plan results come from underlying decisive matches and retain window/sample/provenance fields.
- Existing visual language is locked; selected mock direction is the Option 1 + 2 hybrid.

## Mockups

- Comparison: `.mockups/screens/epic-superarchetype-layer-three-level-page/index.html`
- Selected: hybrid of `strategy-option-1.html` and `strategy-option-2.html`, approved 2026-08-02.
- Accessibility contract: `strategy-option-1-sr.html`.

## Simplification

Delete the two low-value heatmap renderers and their DOM/CSS after the table replaces them. Reuse
the existing table sorting/filtering/ledger machinery instead of adding a parallel widget system.

## Design decisions

- The five primary-plan tokens are stable machine ids: `disrupt-pressure`, `go-off`, `go-over`,
  `go-wide`, and `lock-outlast`. Display labels and descriptions are registry data; aggregation
  never keys on prose.
- The registry is a package-shipped, purely curated JSON source of truth. This taxonomy expresses
  strategic intent, so deriving missing assignments from composition clusters would conflate the
  two layers. Every current-field archetype must be assigned exactly one primary plan; optional
  secondary plans use the same closed vocabulary and may not repeat the primary.
- Plan-versus-plan cells are rebuilt from one `compute_match_results` decisive-match scan over the
  report field window. Directed archetype tallies are remapped and summed by primary plan before
  rates are calculated; rendered archetype percentages and composition-family pools are never
  averaged into plan results.
- External cells use the report's measured gate (`n >= ground_n`) and existing beta-binomial
  shrinkage toward 50%. Same-plan matches are shown as a structural `50%` context cell and count at
  `50%` in adjusted field expectation, but are excluded from floor selection and external floor
  coverage. This makes floor coverage mean “share of other strategies measured,” not an inflated
  claim purchased by mirrors.
- Unassigned current-field archetypes fail the report refresh with a message naming every missing
  assignment. Unknown historical archetypes outside the current field are omitted from plan
  aggregation and reported in audit metadata rather than silently mapped.
- The strategic-plan table is the third peer table and inherits the archetype/camp sortable-header,
  sticky-header, minimum-floor-coverage, honesty-strata, and nulls-last contracts. A semantic button
  in the plan-name cell owns `aria-expanded`/`aria-controls`; expansion reveals one adjacent detail
  row containing the selected-plan portrait, exact opponent-plan ledger, member archetypes, and
  secondary labels.
- The completed composition-family hierarchy remains available only through the archetype/camp
  fallback evidence already used by the report. The visible strategy-family agency map and camps ×
  parent-opponents figure, including their dedicated renderer functions and CSS, are deleted.
- No separate archetype page is part of this arc. Typed registry and payload contracts live outside
  the template so a future `DeckDashboard` can consume them without scraping report HTML.

## Architectural choice

Choose a small domain module plus a presentation adapter. `analytics/strategy_plan.py` owns the
curated registry contract, validation, and match-level plan aggregation. The refresh script converts
that typed result into the additive JSON payload consumed by the existing self-contained template.
This puts the reusable semantic and statistical contract outside the one-off report while keeping
DOM concerns local to the report generator.

Two alternatives were considered. Building everything in `refresh_best_call_ranking.py` would be
the shortest patch, but would strand the future dashboard behind a script import and make taxonomy
validation a presentation concern. Reusing or relabeling the composition-derived superarchetype
registry would avoid a second registry, but it would encode the exact category error this feature is
meant to correct: card-composition similarity is not strategic intent. A general taxonomy framework
was also rejected as unearned abstraction; five curated plans and one consumer-facing aggregate do
not justify a plugin system.

The trickiest unit is the match-derived aggregate. It must preserve decisive-match attribution,
symmetry, sample counts, window provenance, structural same-plan semantics, and honest external
coverage without borrowing any rendered family/archetype statistic. It is designed and tested first;
the UI only renders its typed output.

## Implementation Units

### Unit 1: Curated strategic-plan registry

**Files**: `src/legacy_engine/analytics/strategy_plan.py`,
`src/legacy_engine/data/strategy_plans/legacy.json`
**Story**: `feature-strategic-plan-best-call-viz-data-contract`

```python
PLAN_IDS: frozenset[str]

@dataclass(frozen=True)
class StrategicPlan:
    id: str
    label: str
    description: str

@dataclass(frozen=True)
class ArchetypePlanAssignment:
    archetype: str
    primary: str
    secondary: tuple[str, ...] = ()

@dataclass(frozen=True)
class StrategicPlanRegistry:
    schema_version: int
    plans: tuple[StrategicPlan, ...]
    assignments: tuple[ArchetypePlanAssignment, ...]

    def assignment_for(self, archetype: str) -> ArchetypePlanAssignment | None: ...

def load_strategic_plan_registry(path: Path | str = STRATEGIC_PLANS_PATH) -> StrategicPlanRegistry: ...
def validate_current_plan_coverage(
    registry: StrategicPlanRegistry,
    current_archetypes: Collection[str],
) -> None: ...
```

The loader rejects unsupported schema versions, duplicate plan ids, plan ids outside `PLAN_IDS`,
duplicate archetype assignments, missing/blank labels, unknown primary/secondary ids, a secondary
equal to the primary, and repeated secondaries. `validate_current_plan_coverage` raises one
`ValueError` listing sorted unassigned current-field archetypes. Registry order is presentation
order; archetype identity matching is exact and case-sensitive, consistent with corpus labels.

**Acceptance Criteria**:

- [ ] The package resource declares all five plans and one primary assignment for every archetype
  in the production report's current field; hybrids may declare zero or more distinct secondaries.
- [ ] Invalid closed-vocabulary tokens and malformed/duplicate assignments fail loudly with the
  offending value and allowed values where applicable.
- [ ] Missing current-field assignments fail refresh rather than becoming “other,” zero, or a
  composition-derived fallback.
- [ ] Loading the same file is deterministic and has no import-time file I/O.

### Unit 2: Match-level strategic-plan aggregation (trickiest)

**File**: `src/legacy_engine/analytics/strategy_plan.py`
**Story**: `feature-strategic-plan-best-call-viz-data-contract`

```python
@dataclass(frozen=True)
class StrategicPlanCell:
    subject_id: str
    opponent_id: str
    wins: int
    losses: int
    n: int
    raw: float | None
    shrunk: float | None
    measured: bool
    structural_same_plan: bool

@dataclass(frozen=True)
class StrategicPlanResult:
    plans: tuple[StrategicPlan, ...]
    assignments: tuple[ArchetypePlanAssignment, ...]
    cells: Mapping[tuple[str, str], StrategicPlanCell]
    decisive_matches: int
    same_plan_matches: int
    omitted_matches: int
    since: str | None
    until: str | None
    provenance: str | None

def aggregate_strategic_plan_results(
    match_results: MatchResults,
    registry: StrategicPlanRegistry,
    *,
    current_archetypes: Collection[str],
    ground_n: int,
    since: str | None,
    until: str | None = None,
    provenance: str | None = None,
) -> StrategicPlanResult: ...
```

Sum the directed `MatchupTally` wins/losses after mapping both archetypes through their primary
assignments. For unlike plans, emit both directed cells and shrink each aggregate with
`beta_binomial_shrink_to(wins, n, prior_mean=0.5, strength=SHRINK_STRENGTH)`. Reconstruct same-plan
match counts from mapped archetype mirrors plus cross-archetype directed tallies exactly once; emit
one structural cell per plan with `raw=shrunk=0.5`, its observed `n`, and
`structural_same_plan=True`. Matches involving an archetype absent from the registry are counted once
in `omitted_matches`, never partially credited. Assert complementarity for every external pair
(`wins(A,B) == losses(B,A)`, equal `n`, shrunk rates summing to one within rounding tolerance).

**Acceptance Criteria**:

- [ ] Aggregating underlying decisive tallies produces exact W/L/n totals independent of rendered
  archetype or composition-family percentages.
- [ ] Each cross-plan match is counted once globally and contributes one directed result per side;
  plan cells remain complementary.
- [ ] Same-plan matches display as structural 50%, retain observed n, and cannot be mistaken for an
  empirical floor cell.
- [ ] `measured` is true only for external cells with `n >= ground_n`; absent external pairings have
  `raw=None`, `shrunk=None`, and `measured=False`, never zero.
- [ ] Window/provenance and omitted-match counts remain available to every consumer.

### Unit 3: Reusable report payload and plan metrics

**File**: `scripts/refresh_best_call_ranking.py`
**Story**: `feature-strategic-plan-best-call-viz-data-contract`

```python
def build_strategic_plan_payload(
    result: StrategicPlanResult,
    archetype_rows: Sequence[Mapping[str, object]],
    *,
    top_k: int,
    cover_min: float,
) -> list[dict[str, object]]: ...
```

Run `compute_match_results(con, since=field_since)` once for this layer, pass its typed result to
the aggregator, and join current field share/recent counts from `archetype_rows`. A plan row carries:
`id`, `label`, `description`, `field_share`, `recent_4wk`, `adj`, `floor`, `floor_opp`, `agency`,
`coverage`, `grounded`, `members`, `cells`, `decisive_matches`, and window/provenance. Members carry
`archetype`, `primary`, `secondary`, `field_share`, and `recent_4wk`.

`adj` is the plan-share-weighted mean of measured external shrunk cells plus the subject plan's own
field share at structural 50%. `floor` is the minimum measured external shrunk cell. `coverage` is
measured external opponent-plan share divided by all external opponent-plan share. `grounded`
requires every extant external plan cell measured and coverage >= `cover_min`; with only four
possible external opponents, `top_k` is capped to their count. `agency=min(adj, floor)` only when a
floor exists; otherwise it is null. All missing magnitudes remain null with named reasons in cells.

Replace the old `families` presentation payload with additive `plans`; keep composition registry
loading and `msa.cluster_cells` only where needed for ledger fallback. Add audit lines naming registry
version, assignment coverage, plan decisive/same-plan/omitted counts, and field window.

**Acceptance Criteria**:

- [ ] The data blob contains deterministic `plans` rows with the same appropriate headline metrics
  and field/window provenance as peer tables.
- [ ] Same-plan share contributes exactly 50% to adjusted expectation and never to floor or external
  coverage.
- [ ] A low-n external plan cell yields an explicit unmeasured cell and makes the row an upper bound;
  it never sorts as a numeric zero.
- [ ] Existing archetype/camp calculations and ledger-only composition-family fallbacks are unchanged.

### Unit 4: Sortable strategic-plan table and accessible portrait

**File**: `scripts/best_call_ranking_template.html`
**Story**: `feature-strategic-plan-best-call-viz-render-report`

```javascript
function planRowHtml(plan, rank) { /* peer metric columns + semantic disclosure button */ }
function planDetailHtml(plan) { /* portrait, opponent ledger, members + secondary labels */ }
function renderPlanTable() { /* coverage filter, strata, sorting, expansion restoration */ }
function togglePlanDetail(button) { /* aria-expanded + aria-controls */ }
```

Add `coverage-plan`, `count-plan`, and `t-plan` to the existing table-control/state scheme. Reuse the
peer column definitions and metrics, omitting camp-only `P(best)` and treating structural same-plan
as a labeled context row in the ledger. The portrait summarizes identity, share, agency honesty,
member archetypes, secondary-plan chips, observed decisive sample, and window. The exact ledger lists
all five opponent plans with raw/shrunk W/L/n and an explicit structural or unmeasured state.

Sorting/filtering rerenders table rows but preserves expansion by plan id when the row remains
visible. The disclosure is a real `<button>`; row clicks do not own expansion. Sticky headers remain
inside the existing scroll wrapper. Delete `renderFamilyHeatmap`, `renderCampHeatmap`,
`family-heatmap`, `camp-heatmap`, `family-maps`, `map-grid`, heatmap-specific CSS, and the old visible
taxonomy hierarchy. Do not delete composition-family ledger fallback rendering (`saCellHtml`).

**Acceptance Criteria**:

- [ ] Plans appear as a third peer table with sticky sortable headers, minimum floor-coverage filter,
  row count, nulls-last sorting, and honest grounded/upper-bound labels.
- [ ] Keyboard and pointer activation update `aria-expanded`; `aria-controls` targets a unique detail
  row and focus is not moved unexpectedly.
- [ ] Expansion shows the reusable portrait plus exact five-plan ledger and hybrid labels without
  double-counting secondary plans.
- [ ] The strategy-family agency map and camps × parent-opponents figure and their dead renderer/CSS
  code are absent; composition-family evidence remains in archetype/camp ledgers.
- [ ] Light/dark tokens, responsive overflow, and the approved Option 1 + 2 visual language match the
  committed mockups.

### Unit 5: Contract, renderer, and generated-artifact verification

**Files**: `tests/test_strategy_plan.py`, `tests/test_refresh_best_call_ranking.py`,
`decks/best-deck-best-call-ranking.html`
**Story**: `feature-strategic-plan-best-call-viz-render-report`

Use deterministic factory fixtures for registry and `MatchResults`, plus the existing file-backed
DuckDB report fixture. Tests derive expected plan totals directly from fixture match outcomes.

**Acceptance Criteria**:

- [ ] Registry tests cover valid load and every fail-fast validation class.
- [ ] Aggregate tests cover cross-plan complementarity, cross-archetype same-plan counting, omitted
  assignments, zero-match explicit nulls, `ground_n` boundaries, and window provenance.
- [ ] Payload tests pin adjusted WR, floor, external coverage, grounding, members/secondary labels,
  and unchanged archetype/camp rows.
- [ ] End-to-end HTML assertions prove the plan controls/portrait/ledger ship and both removed figures
  and their renderer names do not.
- [ ] Regenerated production HTML has no placeholder token, parses as JavaScript, and is inspected at
  desktop and narrow viewport widths with keyboard disclosure verified.

## Implementation Order

1. Unit 1 — pin semantic identities and complete current-field assignment coverage.
2. Unit 2 — prove match aggregation, same-plan accounting, and complementarity before presentation.
3. Unit 3 — derive the stable reusable payload and metric honesty rules.
4. Unit 4 — render the selected peer table and portrait, then remove superseded figures.
5. Unit 5 — regenerate and verify the actual Best Deck / Best Call document.

## Testing

### Unit tests: `tests/test_strategy_plan.py`

Use factory fixtures returning `StrategicPlanRegistry` and `MatchResults` builders. Pin the five-token
vocabulary, loader errors, exact mapped W/L totals, same-plan mirrors plus cross-archetype matches,
external `ground_n` boundary, complementarity, omitted-match audit, and provenance propagation.

### Generator tests: `tests/test_refresh_best_call_ranking.py`

Extend the current hero corpus with assignments spanning all five plans. Assert exact metric math
from fixture rounds, structural 50% contribution, external-only floor coverage, deterministic member
ordering, secondary labels, and unchanged `arch`/`camps` projections. Render the file-backed DB and
assert semantic controls, no placeholders, and absence of both superseded figures/renderers.

### Integration and manual verification

Run focused strategy/report tests, then the complete project suite. Regenerate
`decks/best-deck-best-call-ranking.html`, parse its embedded JavaScript with Node, run `git diff
--check`, and inspect the actual report in light/dark mode at desktop and narrow widths. Keyboard-test
sorting, coverage filtering, disclosure state, and detail-row relationships.

## Risks

- **Riskiest assumption — curated coverage stays synchronized with parser labels**: a newly observed
  archetype can halt refresh. **Fallback**: the error lists missing labels in one pass; update the
  registry deliberately. Do not add an “other” plan that hides drift.
- **Double-counting plan matches**: directed archetype tallies materialize both sides. **Fallback**:
  aggregate directed cells for display but compute global/same-plan audit counts through canonical
  unordered pairs and assert complementarity in tests.
- **Structural 50% looks empirical**: a same-plan sample could imply the displayed rate was estimated.
  **Fallback**: carry `structural_same_plan` as a typed flag and label it “structural 50%” in every
  consumer; show observed n only as context.
- **Current-window mismatch**: plan results could silently use a different horizon from the report
  field. **Fallback**: pass `field_since` explicitly, carry it in the result/payload, and echo it in
  the portrait and audit header.
- **A five-row table feels over-engineered**: peer-table machinery may dominate the content.
  **Fallback**: reuse current controls and CSS exactly; the portrait remains the information-rich
  surface, and no new widget framework is introduced.
- **Future dashboard contract pressure**: the eventual dashboard may want a different projection.
  **Fallback**: preserve typed registry/result contracts and treat the report payload as one adapter;
  evolve a future adapter additively rather than scraping or breaking this one.
