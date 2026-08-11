---
id: feature-ranking-honesty-guards
kind: feature
stage: implementing
tags: [advisory, analytics]
parent: epic-best-deck-decision-trust
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-11
---

# Ranking honesty guards — imputation quarantine + regime-currency warning

## Epic alignment (2026-08-11)

This feature now owns the verified cross-camp P(best) coverage/key defect from backlog item
`bug-pbest-coverage-zero-for-most-camps` in addition to the existing imputation quarantine. Its
design must repair the false-zero coverage path first, make zero-cell degradation loud, and exclude
zero-current-presence camps from “best right now” candidacy while keeping them visibly inactive.
The regime-currency warning remains in scope and shares the focused currency contract with
`feature-decision-data-currency`; do not duplicate refresh/card-dimension implementation here.

## Brief

Two honest-degrade gaps in the ranking/field surfaces, both dogfooding-verified: (1)
`rank_decks`' headline sort can crown a deck on pure marginal-winrate imputation
(Mystic Forge #1 with data_coverage=0.00) — ranking needs an imputation quarantine so
imputation-dominated rows are partitioned/labeled, not silently blended; (2) field-load
should surface a regime-currency % and warn when a custom field's implied window is
dominated by a prior ban regime (the maintainer's "last 4 months" local field was only ~29%
current-regime). Also absorbs the residual of roadmap-young-regime-data-strategy — the
young-regime serving posture (the weeks between disturbance and era confirmation are
where the engine serves its worst data with its most confident face); the structural spine
shipped in epic-stable-era-windows, this feature owns the remaining presentation-layer
honesty. Full member texts below.

## Member findings (absorbed from backlog)

---

### idea-ranking-imputation-quarantine


**Ranking surfaces need an imputation quarantine.** `rank_decks`' headline Q25 sort put Mystic
Forge Combo #1 overall (S=0.83 at min_row_share default / 0.68 at 0.003, P(best)=0.85) with
`data_coverage=0.00` — pure marginal-winrate imputation, zero measured cells vs the current
field. The CLI suppresses P(best) below 5% coverage but S itself carries the same noise. Any
ranking surface (`advise positioning --candidates-file`, future reports) should split measured
vs imputation-only rows (the hand-built `decks/best-deck-best-call-ranking.html` from the
2026-07-13 session did this manually), and surface n<30 thin cells as labeled leans instead of
hiding them entirely — at camp level only 4 of 92 camps have any display-grade cell vs the
young post-ban field, so thin-cell leans are most of the available signal.

---

### idea-regime-currency-warning


**Surface a "regime-currency %" on field-load, and warn when a custom field's implied
window is dominated by a *prior* ban regime.**

Found dogfooding (2026-06-27): the maintainer's "last 4 months" local organizer data spans two ban
regimes — only **~29%** of it is the current (Undercity Informer, 2026-05-18→) regime;
**71%** is the prior post-Entomb/Nadu regime. We built a custom `--field` file from that
4-month aggregate and ran best-deck/best-call on it. The conclusion **flipped** under
regime correction: Dimir Tempo ranked *above* Doomsday on the polluted field (0.507 vs
0.488) but *below* it on a regime-clean current field (0.483 vs 0.501). Nothing in the
tool flagged that the field was ~1/3 quality.

What to add:
- When `_load_field` ingests a custom field with per-line counts (or when building the
  global field over a window), compute and print a **regime-currency %**: the share of
  the contributing data that falls in the current ban regime (use the same
  `regime_windows()` the trends/affectedness code already uses).
- **Emit an honest-degrade warning** when regime-currency < ~50% (e.g.
  `// [warn] field is 29% current-regime (71% prior regime 'after Entomb...'); composition
  may not reflect the current meta — consider windowing to the current regime`).
- Reinforce the existing guardrail in docs/help: **window the FIELD composition to the
  current regime, but keep the MATCHUP MATRIX adaptive** — `--regime current` on the matrix
  collapses coverage to ~0% (26-day window starves n≥30 cells). The two windows are
  independent and should be set independently.
- Stretch: a `--regime-window` flag on field-load that reweights a multi-regime custom
  field toward the current regime using the engine's own composition movers, for cases
  where the user only has a blended aggregate (the maintainer's local-meta data can't be split).

Related honesty gaps from the same session: [[idea-archetype-conditioned-card-winrate]],
idea-acquire-color-identity-filter. Methodology lives in the user-memory
`analysis-statistical-context-gates`.

---

### roadmap-young-regime-data-strategy


**Young-regime / post-disturbance data strategy.** Theme from the 2026-07-13 dogfooding
session: the gap between "disturbance happens" and "era detection confirms" (~weeks) is where
the engine serves its worst data with its most confident face — Mystic Forge's hot marginal
(55.4%, era since 04-20) straddled the Candelabra ban and blended two different decks; camp
coverage collapsed to 4/92 display-grade; the consensus generator averaged a mid-rebuild pool
into a Franken-list. Six related arcs, roughly ordered by leverage:

1. **Provisional eras from registered events** — BAN_EVENTS is ground truth on day one;
   affectedness is mechanically computable (fraction of entity's recent decks playing the
   banned card). Affected entities get a provisional boundary at the ban date immediately
   (marginals + cells split, pre-ban side demoted to prior); detection later confirms or
   dissolves. Pieces exist: report affectedness, flex-band attribution, boundary registry.
2. **Shape-break detection at n=5** — per-deck distance from the pre-event consensus 75 as a
   leading indicator (all 5 post-ban Mystic Forge lists were radically far from the Candelabra
   consensus — knowable at n=2). Gates consensus generation ("pool mid-rebuild, refusing to
   average"), powers the not-current chip, proposes provisional boundaries. Discover machinery
   already vectorizes decklists.
3. **Never print a straddling number unblended** — any marginal/cell whose window crosses a
   registered event renders split: "era 55.4% = pre-ban 52% (n=180) · post-ban 71% (n=33,
   speculative)". Divergence-as-diagnostic applied to time.
4. **Imputation-share on every ranked row** — decompose S into measured-cells vs prior
   contribution: "S=0.68 (92% imputed)". Self-labeling; replaces hand-built measured/quarantine
   table splits (see decks/best-deck-best-call-ranking.html, built manually 2026-07-13).
5. **Graded prior handoff** — extend the existing pre-disturbance-value anchoring with
   affectedness-weighted decay: untouched decks carry pre-ban cells at near-full weight into a
   new era; rebuilt decks discounted hard. Attacks the post-ban coverage collapse (most of the
   field wasn't changed by the ban).
6. **`report early-regime` surface** — per archetype post-event: placement-weighted record,
   shape-break flag, provisional era status. One command replacing the hand-assembly done for
   Mystic Forge (Challenge 6-2 3rd + 4-2 10th, three shells).

Arcs 1-3 are one coherent unit: "let registered events do immediately what detection does
eventually." Related parked items: [[idea-eras-alarm-stale-after-registration]],
[[idea-ranking-imputation-quarantine]], [[idea-consensus-ban-aware-shell-coherent]].

## Design decisions
<!-- captured 2026-07-31 via feature-design --only-questions; treat as fixed inputs -->
- **Quarantine presentation**: label-only single ranking is the DEFAULT (prominent
  coverage/imputation column), PLUS an opt-in partitioned view that splits grounded vs
  imputation-dominated rows into labeled strata — both views are useful (the maintainer).
  Follows the opt-in-analytics-overlay pattern: the default body stays byte-identical
  except for the new label column; the strata view sits behind an explicit flag.
- **Coverage basis**: the ranking API gains an explicit sample gate. Its default remains the
  engine display gate (`MatchupCell.display`, currently n>=30), while the Best Call generator
  passes its generated `ground_n` so displayed coverage and P(best) candidacy are measured on
  the same page-used cells. The report asserts parity instead of silently tolerating a second
  coverage definition.
- **Candidacy**: a candidate must have at least 5% measured field-share coverage and non-zero
  presence in the selected current-field window. An inactive camp remains in the table with its
  historical evidence, `P(best)=n/a`, and a typed reason; it cannot consume headline probability
  mass. Recent-four-week count remains context, not a second candidacy gate.
- **Evidence strata**: rows are classified in precedence order as `inactive`, `unscorable`,
  `imputation-dominated` (>50% of field share imputed), `grounded` (the page's existing top-k and
  coverage rule), or `lean`. The strata view groups by these labels without recalculating scores.
- **Zero-cell handling**: a potential candidate with no resolved page-used cells is an honest-null,
  not zero evidence. It receives a reason on the row and a `// [warn]` audit line; unexpected
  camp-key mismatches fail fast before Monte Carlo runs.
- **Regime currency**: exact dated observations are required. Global fields compute currency from
  their actual deck window. Custom aggregate fields may provide `# current_regime_n: N` alongside
  counts; otherwise currency is explicitly unavailable rather than inferred from shares or elapsed
  time. Below 50% emits a warning. Reweighting blended fields is deferred.
- **Data-currency boundary**: this feature owns the typed regime-currency measurement and its
  presentation only. Refresh orchestration, card-dimension repair, release monitoring, and data
  acquisition remain owned by `feature-decision-data-currency`.

## Other agent review

Design-time advisory review was skipped because the autopilot delegation explicitly prohibited
nested delegation. This is non-blocking under the standard review policy; the feature still receives
its normal independent implementation review.

## UI decision

No mockup is required. The Best Call page already has evidence columns, table controls, and labeled
chips; this feature adds one evidence label/column and an opt-in grouping control to that established
surface. The default scan order and sortable row table remain intact, while the partitioned view uses
real headings and preserves keyboard-focusable rows.

## Architectural choice

Three approaches were considered:

1. **Patch only the report script** by copying its displayed `coverage` into `s_cov`. This is small,
   but leaves `rank_decks` sampling and candidacy on a different implicit evidence contract and does
   not protect the CLI or future benchmark consumers.
2. **Make the ranking evidence basis explicit and let each consumer declare its gate**. The core
   ranking result carries measured/imputed shares; the Best Call page passes `ground_n`, asserts its
   serialized coverage agrees, and adds report-specific presence/status metadata. This retains one
   Monte Carlo implementation without pretending every surface has the same display threshold.
3. **Create a separate Best Call ranking engine** over serialized page rows. That would align the
   page mechanically, but duplicates the central estimator and violates the epic's simplification
   decision that production and benchmark ranking share one implementation.

Choose option 2. It fixes the verified false-zero path at the point where the hidden n>=30 gate
diverges from the page's n>=8 gate, makes the contract reusable by the future-only benchmark, and
keeps presence (a property of the current decision surface) out of the generic ranking primitive.
The core change is additive: callers that omit `coverage_min_n` preserve today's n>=30 behavior.

The regime-currency half follows the same shape: `FieldDistribution` carries typed evidence computed
from dated observations, while CLI/report adapters decide how to render it. It does not reach into
refresh orchestration or invent a time distribution for undated custom aggregates.

## Implementation Units

### Unit 1: Explicit ranking evidence contract and false-zero regression

**Files**: `src/legacy_engine/advisory/positioning.py`, `tests/test_positioning.py`,
`tests/test_matchup_multi_split.py`
**Story**: `feature-ranking-honesty-guards-ranking-evidence-contract`

```python
def _is_covered_cell(
    matrix: MatchupMatrix,
    deck_archetype: str,
    opp: str,
    *,
    min_n: int | None = None,
) -> bool: ...

def _compute_data_coverage(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    deck_archetype: str,
    *,
    min_n: int | None = None,
) -> float: ...

def rank_decks(
    matrix: MatchupMatrix,
    field: FieldDistribution,
    candidates: list[str],
    *,
    n_draws: int = _DEFAULT_DRAWS,
    gamma: float = _DIRICHLET_GAMMA,
    robust: bool = False,
    risk_averse: bool = False,
    risk_quantile: float = _DEFAULT_RISK_QUANTILE,
    min_coverage: float = 0.0,
    coverage_min_n: int | None = None,
    seed: int | None = None,
) -> DeckRanking: ...

@dataclass
class DeckRanking:
    # existing fields remain
    imputation_share: dict[str, float]
```

**Implementation Notes**:
- This is the trickiest unit. The verified bug fingerprint comes from `row_stats` treating n>=8
  cells as measured while `_compute_data_coverage` treats only `cell.display` (n>=30) as covered;
  the apparent key miss is the silent `.get(..., {})` symptom, not sufficient proof of the root.
- `min_n=None` means the existing `cell.display and not cell.is_mirror` contract. A positive
  `min_n` means `cell.n >= min_n and not cell.is_mirror`. Reject `min_n < 1` with `ValueError`.
- Mirror handling remains unchanged: excluded from the coverage ratio denominator and included only
  in the restriction keep-set. `imputation_share` is exactly `1.0 - data_coverage`, clamped only for
  floating-point epsilon.
- Score sampling remains full-field. This unit labels evidence; it does not change Beta priors,
  shared Dirichlet draws, tie handling, risk quantiles, or score sorting.

**Acceptance Criteria**:
- [ ] Default callers reproduce existing coverage, scores, ordering, P(best), and caveat sets.
- [ ] Passing `coverage_min_n=8` counts n=8..29 non-mirror cells and excludes n<8 cells.
- [ ] Every candidate has complementary measured and imputed shares summing to 1 within tolerance.
- [ ] A multi-split camp label with n>=the supplied gate has non-zero coverage and enters the shared
      P(best) budget; fixed-seed output remains deterministic and sums to 1.
- [ ] Invalid gates fail before sampling with a specific error.

---

### Unit 2: Best Call candidacy, quarantine, and CLI/report presentation

**Files**: `scripts/refresh_best_call_ranking.py`,
`scripts/best_call_ranking_template.html`, `src/legacy_engine/cli.py`,
`tests/test_refresh_best_call_ranking.py`, `tests/test_positioning.py`
**Story**: `feature-ranking-honesty-guards-report-quarantine`

```python
from typing import Literal, TypedDict

RankingEvidenceStratum = Literal[
    "grounded", "lean", "imputation-dominated", "inactive", "unscorable"
]

class RankingEvidencePayload(TypedDict):
    stratum: RankingEvidenceStratum
    measured_share: float
    imputed_share: float
    eligible: bool
    reason: str | None

def ranking_evidence_payload(
    *,
    field_share: float,
    measured_share: float,
    resolved_cells: int,
    grounded: bool,
    suppress_coverage: float = _PBEST_SUPPRESS_COVERAGE,
) -> RankingEvidencePayload: ...
```

**Implementation Notes**:
- Build `camp_used[lbl]` for every emitted camp and assert its keys exactly cover `camp_labels` before
  assembling `rank_cells`. Zero resolved cells after that assertion is legitimate missing evidence,
  not a lookup failure.
- Call `rank_decks(..., coverage_min_n=ground_n)` once. For every camp, assert `s_cov` equals the
  server-generated row `coverage` within serialization tolerance. A divergence fails refresh with
  the subject named; it never becomes another misleading page.
- Candidate precedence is inactive (`field_share <= 0`) first, then unscorable/coverage below 5%.
  Only eligible labels enter Monte Carlo. The row carries `ranking_evidence`; `p_best` and `s_q`
  remain explicit nulls for excluded rows.
- Add one audit warning per zero-resolved-cell subject plus a summary of eligible, inactive, and
  quarantined counts. Use the literal `// [warn]` comment-line convention.
- Default HTML remains one sortable table and adds a prominent `measured / imputed` evidence column
  plus the stratum chip. An opt-in control groups the same rows under labeled stratum headings; it
  must not recompute scores, change candidacy, or hide inactive rows. `aria-pressed`/native controls
  expose state, and generated headings are not sortable data rows.
- `advise positioning --candidates-file` adds `imputed=<percent>` and the same
  imputation-dominated label. Add `--ranking-strata` as an opt-in grouping flag valid only with
  `--candidates-file`; the default preserves the existing row order apart from the additive label.

**Acceptance Criteria**:
- [ ] The regression fixture contains a camp whose page coverage is >=30% and whose old `s_cov` was
      zero; after the fix the two coverage values agree and P(best) is populated when present.
- [ ] A zero-presence camp remains visible, is labeled inactive with a named reason, and receives no
      P(best)/Q score or shared argmax mass.
- [ ] A genuine zero-cell camp emits `P(best)=n/a`, an unscorable reason, and a named audit warning.
- [ ] P(best) across eligible camps plus eligible unsplit candidates remains one shared budget <=1
      for the camp subset and exactly 1 across all candidates.
- [ ] Default and partitioned HTML views contain identical row identities and numeric values;
      partitioning changes grouping only and remains keyboard/screen-reader operable.
- [ ] CLI default and `--ranking-strata` outputs expose measured/imputed evidence without presenting
      an excluded candidate's probability as zero.

---

### Unit 3: Typed regime-currency measurement and honest warning

**Files**: `src/legacy_engine/advisory/field.py`, `src/legacy_engine/advisory/report.py`,
`src/legacy_engine/cli.py`, `tests/test_field_model.py`, `tests/test_advise_report.py`,
`tests/test_advise_field.py`
**Story**: `feature-ranking-honesty-guards-regime-currency`

```python
@dataclass(frozen=True)
class RegimeCurrency:
    current_regime_since: str
    current_regime_label: str
    current_n: int | None
    total_n: int | None
    share: float | None
    reason: str | None

def compute_regime_currency(
    con: duckdb.DuckDBPyConnection,
    *,
    provenance: str | None = None,
    since: str | None = None,
    until: str | None = None,
) -> RegimeCurrency: ...

def custom_regime_currency(
    *,
    current_n: int | None,
    total_n: int | None,
) -> RegimeCurrency: ...

@dataclass
class FieldDistribution:
    # existing fields remain
    regime_currency: RegimeCurrency | None = None
```

**Implementation Notes**:
- Use `analytics.trends.regime_windows()` as the only regime partition. Global numerator and
  denominator count the same positionable deck population and provenance/window bounds used by the
  global field; the numerator additionally clamps `since` to the current regime start.
- Extend custom field parsing with optional `# current_regime_n: N`. Its denominator is the sum of
  actual per-line counts (or explicit `# effective_n` after allocation). Validate non-negative
  numerator, `current_n <= total_n`, and reject the header when no count basis exists.
- A custom field without dated/current-regime counts receives `share=None` and a reason saying
  regime currency is unavailable for an undated aggregate. Do not estimate from the field shares,
  the requested matchup window, or uniform arrival assumptions.
- Render `// field regime currency: X% current (...)` before ranking/report data. At share <0.50,
  render `// [warn] field is X% current-regime ...; composition may not reflect the current meta`.
  At unavailable, render a non-numeric `// [warn] regime currency unavailable: <reason>`.
- The refresh/data-currency feature may later call this contract, but this unit does not add refresh
  commands, schedules, card coverage, B&R polling, or reweighting.

**Acceptance Criteria**:
- [ ] Global full/multi-regime fields report exact current/total deck counts and share; current-only
      windows report 100% when non-empty.
- [ ] A <50% field emits the action-oriented warning and a >=50% field emits the informational line
      without the stale-composition warning.
- [ ] Custom counts plus `# current_regime_n` produce exact currency; malformed or impossible counts
      fail at field parsing.
- [ ] Undated custom shares/counts never receive a fabricated percentage and always name why the
      metric is unavailable.
- [ ] Existing field builders and direct `FieldDistribution(...)` fixtures remain source-compatible
      through the defaulted additive field.

## Implementation Order

1. **Explicit ranking evidence contract** — first because every presentation and regression depends
   on fixing the hidden coverage basis at the estimator boundary.
2. **Best Call candidacy and quarantine** — consumes the repaired contract, then establishes the
   parity assertion, inactive exclusion, typed reasons, and both views.
3. **Regime-currency measurement** — independent of the Monte Carlo repair and may proceed in
   parallel, but should land before feature-level verification so ranking output has both honesty
   dimensions.

Dispatch rationale: three child stories expose one dependent ranking chain plus one independent
field-currency lane, but implementation should remain one feature-owned bundle because Unit 2 shares
the positioning/CLI contracts with both neighboring units.

## Testing

### Unit tests: `tests/test_positioning.py`

- Pin default n>=30 compatibility, explicit gate behavior at n=7/8/29/30, invalid gates,
  imputation-share complements, deterministic shared-field P(best), and honest nulls.

### Report integration: `tests/test_refresh_best_call_ranking.py`

- Extend the hermetic multi-split fixture with the verified mismatch shape, then assert page/ranker
  coverage parity, presence-gated candidacy, typed exclusion reasons, audit lines, shared-budget
  conservation, and byte-stable fixed-seed regeneration.
- Inspect/render both JavaScript modes and assert row identity/value parity plus semantic control and
  heading attributes.

### Field integration: `tests/test_field_model.py`, `tests/test_advise_report.py`,
`tests/test_advise_field.py`

- Use tournaments on both sides of the live latest ban boundary for exact numerator/denominator
  checks. Cover global window clamps, provenance filters, custom header parsing, unavailable custom
  aggregates, threshold rendering, and existing field warning propagation.

### Focused verification

```text
PYTHONPATH=. .venv/bin/pytest -q \
  tests/test_positioning.py \
  tests/test_matchup_multi_split.py \
  tests/test_refresh_best_call_ranking.py \
  tests/test_field_model.py \
  tests/test_advise_report.py \
  tests/test_advise_field.py
```

Then run the project-standard broader suite before advancing the feature to review.

## Risks

- **Riskiest assumption — one threshold can serve two consumers**: the page intentionally uses n>=8
  while generic engine displays use n>=30. Making the gate explicit preserves both; a global constant
  replacement would silently weaken other surfaces. **Fallback**: keep the parameter private to the
  ranking call until another consumer demonstrates a need.
- **Probability renormalization surprise**: excluding inactive/unsupported candidates necessarily
  redistributes P(best) among eligible candidates. **Fallback**: audit eligible/excluded counts and
  retain inactive evidence in the table so the changed comparison set is visible.
- **Custom-field currency false precision**: shares or aggregate counts do not encode time.
  **Fallback**: require an exact current-regime numerator or return an explicit unavailable reason;
  never infer it.
- **Interactive partition drift**: client-side grouping could accidentally recalculate or filter
  rows differently than the generated contract. **Fallback**: serialize the stratum once and make the
  browser a pure grouping renderer with identity/value parity tests.
- **Least sure — current-regime count provenance in hand-authored files**: the header is only as true
  as operator input. It is therefore labeled custom evidence and never treated as corpus-derived.

## Simplification pass

- Replace the page's implicit second P(best) coverage definition with the ranking primitive's explicit
  gate plus a parity assertion; do not keep a report-only workaround.
- Reuse existing `coverage_caveated`/field warning paths where their semantics match; add typed
  evidence only where a named exclusion reason is currently impossible.
- Do not implement blended-field reweighting, a second ranking estimator, refresh scheduling, or
  future methodology variants in this feature.

## Implementation summary

- `69a7f99` made the ranking coverage gate explicit and added complementary measured/imputed
  shares while preserving the existing n>=30 default contract.
- `7a49191` aligned Best Call coverage with page-used cells, quarantined inactive/unscorable and
  imputation-dominated rows with typed reasons, and kept default/grouped page values identical.
- `d431611` added exact global/custom regime-currency evidence and the named informational,
  below-50%, and unavailable audit paths.
- No design deviations. In particular, no blended-field reweighting, refresh orchestration,
  card-dimension work, or second ranking estimator was introduced.
- Integrated verification: `uv run --no-sync python -m pytest -q` — 3634 passed, 1 skipped.

## Review findings (2026-08-11)

**Effective weight**: standard — one same-harness fresh-context pass completed. Closure requires
verification of the named fix set only; no second independent pass.

**Blockers**: tracked by `feature-ranking-honesty-guards-review-fixes`.

- `# current_regime_n` may claim exact currency only when every custom row has a real count (or an
  explicitly complete alternative basis); partial counts must fail or report currency unavailable.
- Interactive sample-gate changes must not leave generated-gate evidence percentages/strata and row
  grouping presented as current.
- Zero-presence candidacy must use raw presence/count evidence before display rounding, so a tiny
  positive share cannot become inactive.
- Roll the CLI help and current runbook/foundation assertions forward to the shipped currency,
  evidence-strata, inactive, and unscorable contracts; regenerate the knowledge index.

**Important**: none deferred. The receiver elevated the review's interactive, rounding, and stale
assertion findings because they directly govern evidence honesty in the current feature.

**Nits**: none.

**Rejected**: P(best) parity/budget, global regime-window provenance, and default ranking-order
regression proposals were rejected by the reviewer after focused evidence confirmed those paths.

**Notes**: Focused review verification passed 379 tests. The pass was same-harness fresh-context,
not cross-model; browser interaction was inspected statically because no browser runtime was
available.
