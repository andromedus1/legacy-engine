---
id: feature-agency-page-methodology
kind: feature
stage: implementing
tags: [analytics, advisory]
parent: epic-best-deck-decision-trust
depends_on: [feature-ranking-measurement-integrity, feature-ranking-honesty-guards]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-11
---

# Agency-page methodology v2 — lean view, path-to-grounding, verdict stability, floor fix

## Epic alignment (2026-08-11)

Methodology presentation follows—not substitutes for—the measurement-integrity and ranking-honesty
features. The stability variants must reuse their reconciled row/cell primitives, and the lean view
must expose rather than erase disagreements between estimator families.

## Brief

Four methodology improvements to the best-deck/best-call agency ranking page (generator:
scripts/refresh_best_call_ranking.py; runbook: docs/analysis/best-call-ranking.md), all from
the 2026-07-28 session retro: (1) a soft-weighted "lean view" beside the gated view — every
cell contributes in proportion to its precision, agency becomes a posterior, no n>=8 /
coverage-80% cliffs (gated view stays the headline); (2) every ungrounded row shows its
path to grounding — which 2-3 cells need how many more matches to enter the grounded
stratum, converting discarded coverage into a data-acquisition agenda; (3) a per-row rank
STABILITY column computed across the page's own methodological variants (raw / CI-gated /
ban-scoped / era-only) — robustness-across-estimators beat any single metric's #1;
(4) the agency (worst-matchup floor) methodology fix. Full member texts below.

The released `feature-multi-split-matrix` supplies the one-pass camp matrix: camp-level ranking previously needed ~29 separate
per-parent split-matrix builds and P(best) is incomparable across them; the stability
column and lean view multiply that cost without the one-pass multi-split matrix.

## Member findings (absorbed from backlog)

---

### idea-lean-view-toggle


Add a soft-weighted "lean view" beside the agency page's gated view: no n>=8 /
coverage-80% cliffs — every cell contributes in proportion to its precision, agency
becomes a posterior rather than a hard min. The gated view stays the headline
(auditable, legible); the lean view recovers the graded middle the binary gates
discard (live stratum fell 24 -> 13 rows after the Nadu rule — much of the format now
lives between "proven" and "unknown"). Divergence between the two views is itself
diagnostic, per the divergence-as-diagnostic house pattern. the maintainer's framing: "we're
quite rigorous, but we sacrifice a lot of ability to view into the data."

---

### idea-path-to-grounding


Every ungrounded row on the agency page should show its path to grounding: which 2-3
cells need how many more matches (to reach n>=8 measured / top-8 coverage) for the row
to enter the grounded stratum. Converts discarded coverage into a concrete
data-acquisition agenda — "Cephalid needs X more matches vs Y" — and tells the user
what to watch as upstream data flows.

---

### idea-verdict-stability-column


Compute the agency ranking under all of the page's own methodological variants (raw /
CI-gated / ban-scoped / era-only) and surface per-row rank stability as a first-class
column. From the 2026-07-28 session: robustness-across-estimators beat any single
metric's #1 — Doomsday stayed #6-8 across every perturbation while Eldrazi, Cephalid,
and Mystic Forge each collapsed under one (n=8 noise, Nadu contamination, Candelabra
coverage). A deck that's #6 under every estimator beats a deck that's #1 under one.

---

### idea-agency-floor-methodology-fix


Patch the unsuppressed best-deck-best-call report's "agency" (worst-matchup floor)
methodology. Report: `decks/best-deck-best-call-ranking.html` (gitignored); generators
`rank_all.py` + `gen_best_call_html.py` were session-scratchpad (2026-07-21 session —
rebuild from the project-state memory description if lost).

**Context.** the maintainer caught two real holes in the floor analysis after it named Cephalid
Breakfast the top "agency" deck (high adjusted WR + high worst matchup):

1. **Coverage hole** — the floor and adjusted-WR columns silently exclude field opponents
   with NO era-windowed cell. Cephalid Breakfast was missing cells vs **26% of field
   share-mass** (incl. Mystic Forge Combo 6.3%, Dimir Midrange 5.1%), so a row's floor can
   look clean simply because its bad matchups are unmeasured.
2. **Prior-riding floor** — opponent-era windowing shrinks cells vs recently-disturbed
   opponents to n=1–2, which sit at their shrinkage prior near 50%, so a maximin/floor
   sort systematically **rewards ignorance**. Cephalid's cells vs Izzet/Azorius/Lands were
   all n=1; Tron's whole row is n≤18. Raw recent slices told the true story (Cephalid vs
   Lands 3/11 = 27% raw). Reinforces the 2026-07-11 shrinkage-floor-mirage lesson.

**Fixes to implement:**

- (a) **Per-row window fallback**: where the era window has no cell, fall back to the
  full-corpus cell LABELED as such (per-cell window provenance) — never silently drop the
  opponent.
- (b) **Coverage counts against the floor**: a floor claim is only as strong as its
  coverage — display "floor undefined over X% of field" or penalize the index.
- (c) **Grounding gate on the ROW, not just the single worst cell**: "grounded floor"
  should require the top-k field shares each measured at n≥threshold (Cephalid had only
  2/19 cells at n≥10 yet got the grounded label because its one worst cell was n=11).
- (d) **Re-rank agency tables under (a)–(c)** — verified outcome: **Eldrazi becomes the
  agency pick** (full-corpus floors: 44.4% vs Mystic Forge n=185, 46.2% vs S&T n=264,
  47.1% vs Izzet n=163; 95% coverage); Cephalid demoted to lean (no measured hole below
  ~44% but current-field form unmeasured); Tron demoted to speculative.

**Generalizes**: any maximin/floor ranking over shrunk cells needs a coverage-aware +
raw-corroborated basis. Candidate absorption target: the report regenerators, and possibly
a first-class `advise agency` floor surface in the engine where these gates live in code
instead of scratchpad scripts.

## Design decisions
<!-- --only-questions pass 2026-07-31: no user-facing ambiguities — direction is pinned by
the absorbed member texts, parent-epic decisions, and existing project patterns. Full
feature-design may proceed without an interactive round. -->

- **Authority stays gated**: the current reconciled, coverage-gated agency score remains the
  default headline and recommendation basis. The posterior lean and rank-stability views are
  diagnostic overlays until `feature-ranking-future-only-benchmark` supplies future-only evidence.
- **Lean source policy is outcome-blind and non-overlapping**: use an era candidate whenever one
  exists, regardless of `ground_n`; use the ban-scoped/full-corpus fallback only when the era
  candidate is absent. Never pool the two because the era observations are generally contained in
  the fallback window. An unresolved opponent receives a named weak prior rather than disappearing.
- **Lean agency is a posterior smooth floor**: sample resolved cells with the same Jeffreys-Beta
  convention as `rank_decks`; sample unresolved cells from the same weak row-centred prior; weight
  every opponent by current field share and continuous posterior precision; apply a fixed soft-min
  per draw. Report Q25 as the diagnostic score plus median and 95% interval. The fixed field shares,
  temperature, precision scale, draw count, and seed are serialized so the result is replayable.
- **Four stability perturbations are predeclared**: `raw` (page-selected source, raw rate, n>=1),
  `ci-gated` (the current selected/shrunk/gated score), `ban-scoped` (fallback candidate only,
  shrunk, page evidence gate), and `era-only` (era candidate only, shrunk, page evidence gate).
  Selection never depends on observed win rate. Each visible peer table ranks its own eligible rows;
  ties receive the same competition rank. A rank span is reported only when all four variants rank
  the row, otherwise the missing variants are named instead of implying stability.
- **Grounding paths are acquisition agendas, not promises**: all currently missing top-k cells are
  mandatory, then other cells are prioritized by field-share gain per additional match until the
  coverage target is reached. The page shows the first three actions plus the undisplayed action
  count and total match shortfall. New current matches accrue to both nested windows; the projected
  selected source still follows era-first precedence. Completing every listed action must replay as
  grounded under the existing row contract.
- **Existing floor work is prerequisite, not scope**: era-to-ban/full fallback, pair-window labels,
  selected-ledger replay, row-level top-k/coverage grounding, floor observability, concentration
  warnings, candidate presence, and evidence strata shipped in the two dependency features. This
  feature consumes those contracts. It does not recreate coverage definitions, change P(best), or
  assert the historical scratchpad outcome that Eldrazi must rank first.

## Other agent review

Design-time advisory review was skipped because the active autopilot delegation prohibits nested
delegation. This is non-blocking under the standard review policy; the implemented feature still
receives its normal independent feature review.

## UI decision

No new mockup is required. This is an extension of the established Best Call table controls,
evidence chips, and accessible row disclosures rather than a new surface or layout system. Add one
keyboard-operable `Gated headline / Posterior lean (diagnostic)` control, a stability column, and a
path-to-grounding block inside the existing disclosure. The gated view is selected on load. The
control exposes state with `aria-pressed` and an `aria-live` status; color is never the only carrier.
Strategic-plan rows receive grounding paths, but not era/fallback stability or lean scores because
their direct match-level, uniform-window evidence has no corresponding methodology variants.

## Architectural choice

Three approaches were considered:

1. **Recompute variants in browser JavaScript.** This makes the control responsive, but creates a
   second statistics implementation and cannot be reused by the future-only benchmark.
2. **Build a separate report-only methodology engine over the flattened JSON cells.** This is easy
   to splice into the generator, but bypasses typed pair-window/source validation and repeats the
   exact drift that measurement integrity just removed.
3. **Extend the package-owned ranking-measurement contract with typed projections, then serialize
   immutable results for the report.** The package owns source choice, posterior math, grounding,
   and rank spans; the generator only supplies rows and peer groups, while the template renders the
   result. Interactive `Minimum matchup n` continues to recompute only the existing gated view and
   labels generated stability evidence stale when the gate differs.

Choose option 3. It preserves one evidence ledger and gives the later benchmark reusable, seeded
methodology outputs without changing the current recommendation or Monte Carlo P(best) budget.

## Implementation Units

### Unit 1: Typed methodology projections and posterior lean

**Files**: `src/legacy_engine/advisory/ranking_measurement.py`,
`tests/test_ranking_measurement.py`
**Story**: `feature-agency-page-methodology-kernel`

```python
MethodologyVariantId = Literal["raw", "ci-gated", "ban-scoped", "era-only"]

class MethodologyVariantSpec(LegacyEngineModel):
    id: MethodologyVariantId
    label: str
    source_policy: Literal["selected", "fallback", "era"]
    rate_basis: Literal["raw", "shrunk"]
    evidence_n: int

class VariantRowMeasurement(LegacyEngineModel):
    variant: MethodologyVariantId
    adjusted_field_wr: float | None
    floor: float | None
    agency: float | None
    measured_coverage: float
    top_k_measured: bool
    resolved_cells: int

class LeanAgencyMeasurement(LegacyEngineModel):
    q25: float
    median: float
    ci_low: float
    ci_high: float
    resolved_share: float
    imputed_share: float
    draws: int
    seed: int
    temperature: float
    precision_scale: float
    source_policy: str

class RankStability(LegacyEngineModel):
    ranks: dict[MethodologyVariantId, int | None]
    rank_min: int | None
    rank_max: int | None
    rank_span: int | None
    missing_variants: tuple[MethodologyVariantId, ...]
    reason: str | None

def measure_variant_row(
    cells: Sequence[RankingCellMeasurement],
    *,
    spec: MethodologyVariantSpec,
    top_k: int,
    cover_min: float,
) -> VariantRowMeasurement: ...

def measure_lean_agency(
    cells: Sequence[RankingCellMeasurement],
    *,
    draws: int = 20_000,
    seed: int = 730_021,
    temperature: float = 0.05,
    precision_scale: float = DISPLAY_GATE_N,
) -> LeanAgencyMeasurement: ...

def rank_variant_rows(
    rows: Mapping[str, Mapping[MethodologyVariantId, VariantRowMeasurement]],
    *,
    eligible: Mapping[str, Mapping[MethodologyVariantId, bool]],
) -> dict[str, RankStability]: ...
```

**Implementation notes**:

- This is the trickiest unit and starts first. Extract one private projection summarizer from
  `measure_ranking_row`; the existing adaptive result and every variant must share its weighted
  adjusted-WR, measured-floor, top-k, and coverage arithmetic. Preserve serialized replay,
  strict-common diagnostics, floor observability, and public output exactly for existing callers.
- Define the four specs once as an immutable package registry. `ci-gated` must reproduce the
  existing row's score within floating tolerance; the report asserts parity before publishing.
- `raw` still uses the outcome-blind page-selected source, but uses `p_raw` and `evidence_n=1`.
  `ban-scoped` and `era-only` never substitute the other candidate when their named source is absent.
- For the lean posterior, select era-or-absent-fallback before looking at any rate. A resolved
  non-mirror cell draws `Beta(wins + 0.5, losses + 0.5)`. An unresolved opponent draws the existing
  weak strength-2 Beta centred on the row's mean resolved raw rate, or 0.5 when the whole row is
  unresolved. Each cell's smooth-floor weight is its normalized field share times
  `(posterior_strength / (posterior_strength + precision_scale))`; this is positive for the weak
  prior, so no opponent disappears. For each draw compute
  `-temperature * log(sum(weight * exp(-p / temperature)))` with stable log-sum-exp arithmetic.
- Reject empty rows, non-positive draws/temperature/precision scale, invalid shares, and cells with
  inconsistent subject/opponent ledger identity. Use a local NumPy generator; do not mutate global
  RNG state or call the matrix-based `rank_decks` implementation.
- Rank each peer group independently with standard competition ranks (`1 + count(scores > score)`).
  Active/presence and the existing 5% evidence floor are supplied by the caller per variant. Do not
  rank an honest-null and do not compress missing variants into a numeric span.

**Acceptance criteria**:

- [ ] Existing `measure_ranking_row` fixtures and serialized replay outputs are unchanged.
- [ ] `ci-gated` exactly reproduces each existing row score/coverage/top-k result; raw uses raw rates,
      and era-only/ban-scoped select only their declared source regardless of outcome.
- [ ] With a fixed seed, lean Q25/median/CI are deterministic, ordered, finite, and bounded [0, 1].
- [ ] An n=7 to n=8 threshold change does not switch the lean source or create a discontinuity;
      unresolved opponents contribute a non-zero prior weight and remain visible as imputed share.
- [ ] Rank ties receive equal ranks; a complete four-variant row reports its exact span; any missing
      variant yields a named honest-null span.

---

### Unit 2: Typed path-to-grounding planner

**Files**: `src/legacy_engine/advisory/ranking_measurement.py`,
`tests/test_ranking_measurement.py`, `tests/test_refresh_best_call_ranking.py`
**Story**: `feature-agency-page-methodology-grounding-path`
**Depends on**: `feature-agency-page-methodology-kernel`

```python
class GroundingCellState(LegacyEngineModel):
    opponent: str
    field_share: float
    era_n: int
    fallback_n: int
    measured: bool

class GroundingAction(LegacyEngineModel):
    opponent: str
    additional_matches: int
    projected_source: CellSourceKind
    field_share_gain: float
    mandatory_top_k: bool

class GroundingPath(LegacyEngineModel):
    grounded: bool
    actions: tuple[GroundingAction, ...]
    display_actions: tuple[GroundingAction, ...]
    undisplayed_actions: int
    total_additional_matches: int
    projected_coverage: float
    would_ground: bool
    reason: str | None

def grounding_cell_states(
    cells: Sequence[RankingCellMeasurement],
) -> tuple[GroundingCellState, ...]: ...

def plan_path_to_grounding(
    cells: Sequence[GroundingCellState],
    *,
    ground_n: int,
    top_k: int,
    cover_min: float,
    display_limit: int = 3,
) -> GroundingPath: ...
```

**Implementation notes**:

- Keep the planner independent of win rate. A future current-window match increments both nested
  era and fallback counts; therefore `additional_matches = max(0, ground_n - max(era_n,
  fallback_n))`, while projected source selection retains era-first precedence on a tie.
- Mandatory actions are every unmeasured opponent in the field-share top-k. Add remaining cells in
  descending `field_share / additional_matches`, then field share, then opponent name until
  projected coverage reaches `cover_min`. This is a deterministic priority agenda, not a claim of
  global combinatorial optimality.
- Keep all required actions in the payload. `display_limit` truncates presentation only and the
  payload explicitly carries the remainder and total shortfall. A grounded row returns no actions;
  an invalid/empty field returns a named honest-null instead of a fabricated zero-match path.
- The script adapts direct strategic-plan external cells into `GroundingCellState` with
  `era_n=fallback_n=observed_n`; exact-archetype mirrors and structural plan diagonals remain excluded.
  Archetype/camp rows adapt directly from their typed ranking ledgers.

**Acceptance criteria**:

- [ ] Every unmeasured top-k opponent appears in the full action list before optional coverage work.
- [ ] Completing all actions and replaying the existing source-selection/grounding contract makes
      `would_ground` true with projected coverage at or above the configured target.
- [ ] A path requiring more than three cells displays three, names the remainder, and reports the
      full additional-match total; a row already grounded reports no acquisition work.
- [ ] Era/fallback ties project to era, zero/negative configuration is rejected, and no rate field
      can affect action ordering.
- [ ] Strategic-plan paths exclude their structural diagonal and use only direct observed evidence.

---

### Unit 3: Best Call methodology payload and accessible diagnostic view

**Files**: `scripts/refresh_best_call_ranking.py`,
`scripts/best_call_ranking_template.html`, `docs/analysis/best-call-ranking.md`,
`tests/test_refresh_best_call_ranking.py`
**Story**: `feature-agency-page-methodology-report-surface`
**Depends on**: `feature-agency-page-methodology-kernel`,
`feature-agency-page-methodology-grounding-path`

```python
def methodology_payload(
    rows: Sequence[dict[str, object]],
    *,
    peer_key: str,
    ground_n: int,
    top_k: int,
    cover_min: float,
    lean_draws: int = 20_000,
    lean_seed: int = LEAN_SEED,
) -> dict[str, dict[str, object]]: ...
```

**Implementation notes**:

- Build archetype and camp methodology payloads from each row's serialized typed ledger. Compute
  variant eligibility from raw current presence plus the existing resolved-cell/5%-coverage rule;
  never reuse rounded display share. Run `rank_variant_rows` separately for the archetype and camp
  peer tables. Plans receive only the generic grounding path adapter.
- Add `methodology` beside existing row fields; do not overwrite `adj`, `floor`, `agency`,
  `coverage`, `ranking_evidence`, or P(best). Assert the `ci-gated` projection equals those canonical
  fields before rendering. Serialize the methodology registry, seed, draws, temperature, and
  precision scale in `meta` and echo them in audit lines.
- The template defaults to gated values. The opt-in lean control switches the displayed agency bar
  and within-stratum sort to lean Q25, labels the score `diagnostic posterior`, and exposes median,
  95% interval, resolved/imputed share, and gated-minus-lean divergence. It never changes P(best),
  evidence strata, candidacy, or the page's recommendation prose.
- Always show rank stability as `#min-#max (span N)` only when all four variants rank the row;
  otherwise show `n/a` plus missing variant names. Expanded ungrounded rows show up to three
  grounding actions, full total shortfall, projected coverage, and any remainder.
- Interactive `Minimum matchup n` continues to recompute the gated row from source candidates.
  Lean is gate-independent. Stability and grounding are labeled `generated n=<ground_n>` and
  disabled/stale while the interactive gate differs; do not recompute package methodology in JS.
- Update the runbook/frontmatter decisions with exact formulas, authority boundary, variant
  definitions, path heuristic, replay knobs, and the plan-row exception. Regenerate knowledge
  indexes through their owning workflow after the planning doc changes; never hand-edit them.

**Acceptance criteria**:

- [ ] Default page load preserves gated agency values, order, strata, P(best), and recommendation
      language; methodology fields are additive and the canonical-gated parity assertion passes.
- [ ] The lean control is keyboard operable, announces its state, re-sorts only within the existing
      honesty strata, and shows the seeded posterior diagnostics without changing candidacy.
- [ ] Stability uses the correct peer universe, reports exact four-variant spans, and names incomplete
      evidence rather than displaying a partial range.
- [ ] Every ungrounded archetype, camp, and strategic-plan row has an honest path or named unavailable
      reason; display truncation cannot hide the remaining action count or total matches required.
- [ ] Changing the interactive gate marks generated stability/path evidence stale while leaving the
      gate-independent lean posterior labeled and available.
- [ ] Focused package/generator/template tests and the full suite pass; regenerated knowledge indexes
      pass the normal linted workflow.

## Dependency order

1. `feature-agency-page-methodology-kernel`
2. `feature-agency-page-methodology-grounding-path`
3. `feature-agency-page-methodology-report-surface`

## Testing strategy

- **Kernel unit tests** pin source-policy truth tables, raw/shrunk projection parity, seeded posterior
  math, unresolved prior participation, threshold continuity, ties, and missing-variant honest nulls.
- **Planner unit tests** prove top-k inclusion, deterministic coverage prioritization, nested-window
  count projection, explicit display truncation, and replay-to-grounded behavior.
- **Generator contract tests** use small synthetic typed ledgers to verify canonical parity, separate
  peer universes, exact presence (not rounded share), additive serialization, plan adapters, and
  deterministic seeds without requiring the production database.
- **Template tests** assert accessible control/state text, unchanged default authority, within-stratum
  sorting, complete/incomplete stability labels, action remainder disclosure, and interactive-stale
  behavior. Avoid snapshots of the disposable generated HTML.
- **Integrated verification** runs `tests/test_ranking_measurement.py` and
  `tests/test_refresh_best_call_ranking.py`, then the full suite under the project's standard pytest
  command. No golden outcome asserts that a named deck must win.

## Failure pre-mortem

1. **Era and fallback samples get double-counted.** Signal: implausibly narrow lean intervals for
   thin eras. Prevention: fixed era-preferred/absent-fallback source policy and a source-truth-table
   regression.
2. **Unknown matchups make a deck look safer.** Signal: deleting a bad/uncertain cell raises lean
   agency with no imputation warning. Prevention: every field opponent retains positive weak-prior
   weight and the row reports imputed share; gated authority remains unchanged.
3. **Rank spans compare different candidate universes silently.** Signal: a narrow range when some
   variants could not score the row. Prevention: variant-specific eligibility and no numeric span
   unless all four ranks exist.
4. **Browser and Python methodology drift.** Signal: changing the interactive gate silently changes
   only part of a stability claim. Prevention: serialize package-owned outputs; JS only renders them
   and marks generated-gate evidence stale.
5. **A three-cell path hides a larger shortfall.** Signal: completing the visible actions still leaves
   the row ungrounded. Prevention: retain every action and total in payload, truncate display only,
   and replay the completed agenda in tests.

## Simplification pass

- Reuse the typed era/fallback ledger and one extracted projection summarizer; do not add another
  matrix builder, coverage definition, selected-source object, or benchmark-only ranking engine.
- Keep P(best), shared-field Monte Carlo, strategic-plan aggregation, superarchetype borrowing, and
  current evidence strata unchanged.
- Keep only four named perturbations and one pinned posterior lean; no user-configurable estimator
  builder, learned temperature, automatic calibration, or winner claim belongs before the benchmark.
- Store methodology only in the generated page blob; the generated HTML remains disposable and no
  database migration or persistent schema is required.
