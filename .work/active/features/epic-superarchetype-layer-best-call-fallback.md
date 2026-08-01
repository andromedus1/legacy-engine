---
id: epic-superarchetype-layer-best-call-fallback
kind: feature
stage: drafting
tags: [advisory, analytics, docs]
parent: epic-superarchetype-layer
depends_on: [epic-superarchetype-layer-chain, feature-multi-split-matrix]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Per-cell superarchetype fallback + provenance chip on the best-call page

## Brief

Delivers the epic's payoff on the surface that motivated it. On the 2026-07-31 best-call page,
Cradle Control ranked #1 by adjusted field WR with **zero** displayable matchup cells, every Aluren
cell is n<30, and Energy — the #5 deck in the format — has exactly two; measured across the whole
matrix, only 4 of 1,190 directed cells reach n>=30 and thirty-one of thirty-five ranked archetypes
have none at all. This feature makes the page's per-cell ladder one rung deeper: use the
archetype-level cell when it clears its gate, fall back to the **superarchetype cell** when it does
not, and label every fallback with a provenance chip alongside the existing `era` / `BA <date>` /
`FC` chips. Every row gets coverage against every major strategy and every number stays auditable
back to the members behind it.

The honesty work is the substance, not the decoration. A superarchetype-sourced cell must be
visually and structurally distinguishable from a measured archetype cell at every point where the
page makes a claim: the per-opponent ledger row (chip + the member split behind the pooled number +
`m_eff` / `I²` / intra-cluster share), the `adj` field-WR aggregate (which superarchetype cells DO
feed), the `coverage` figure, and the stratum verdict. Two things they deliberately do **not** do in
v1: a superarchetype cell never sets the row's **floor** (the floor is the page's harshest claim —
"this deck has a proven hole" — and a pooled family cell is not proof of a specific hole), and a row
whose top-k opponents are covered only by fallback is **not** promoted into the `grounded` stratum;
it lands in its own labeled stratum and sorting never intermixes strata, exactly as the page already
treats leans. Cells the gates refuse render as the member split with a named reason (`dominated by
Show and Tell`, `heterogeneous pool I²=0.89`, `single-member cluster`), never as a blended number.
And the **I² one-sidedness caveat travels to the page's definitional card**: a low I² means "we
cannot see heterogeneity", not "there is none", and passing the gate never promotes a pooled estimate
to the status of a measured archetype cell.

Docs roll forward in the same stride: `docs/analysis/best-call-ranking.md` (the ladder's new rung,
the new chip vocabulary, the stratum rules, and `superarchetype run` added to the refresh cycle
before the page is regenerated), plus whatever the `ARCHITECTURE`/`SPEC` rows need once the surface
is real, then `/knowledge-index` regeneration.

**Not covered here.** No estimator, no clustering, no chain changes — those land in the three
sibling features and this one only reads their outputs. No lean view, no path-to-grounding, no rank
stability column, no floor-methodology fix: those are `feature-agency-page-methodology`, which edits
the same script and template and is a **co-editor to sequence against at implement time**, not a
substrate dependency.

## Epic context

- Parent epic: `epic-superarchetype-layer`
- Position in epic: **consumer feature, last** — validates the whole arc against the live corpus and
  is where the maintainer actually sees the change.
- **Composes with `feature-multi-split-matrix`** (declared `depends_on`): its
  `-best-call-onepass` child rewrites the exact per-parent camp loop and `make_cells` ladder this
  feature extends, and restores cross-camp `P(best)` from one shared-field MC. Extend the migrated
  one-pass script; do not re-introduce a per-parent build.

## Inherited design decisions

From the epic's `## Strategic decisions` and `## Design decisions`. Fixed inputs:

- **Per-cell fallback, labeled** — archetype cell when it clears its tier gate, superarchetype cell
  when it doesn't, provenance chip alongside the existing BA/FC/era chips. Not a global toggle, not
  a blended number.
- **Superarchetype cells feed `adj` and `coverage`, never `floor`.**
- **Fallback-only rows get their own stratum**, labeled, never intermixed in sorting with rows
  grounded on measured archetype cells. Passing the heterogeneity gate never promotes a pooled cell
  to measured status.
- **Refused pools render the member split** with a named reason (divergence-as-diagnostic), never a
  suppressed cell and never a blended number.
- **The I² one-sidedness caveat reaches the UI**, in the page's definitional prose, not only the
  code.
- **Intra-cluster edges are labeled on the page** ("most of this edge is against your own family") —
  the Aluren-vs-Show-and-Tell 73.9% case is the worked example that must read correctly after this
  ships.
- **The output page stays gitignored and regenerable**; the tracked artifacts are the script, the
  template, and the runbook — data changes go in the script, presentation changes in the template.

## Research briefs

- `docs/briefs/superarchetype-aggregation.md` — **primary**. §8 display-fallback-is-separate (finest
  rung whose `n_eff` clears `DISPLAY_GATE_N`; the displayed cluster cell includes the opponent's own
  matches and carries the intra-cluster flag), §6.3 the worked refusal case and the exact correct
  surface behaviour, §6.4 the one-sidedness caveat that must reach the UI, §5.2 the `dominated by
  <member>` label, §7 the intra-cluster share message, §1 the measured coverage problem this page
  exhibits.
- `docs/briefs/advisory-methods.md` — the positioning/ranking conventions the page's aggregates sit
  inside.

## Foundation references

- `docs/VISION.md` — the three-level-taxonomy decision, which names the per-cell labeled fallback as
  the consumption model.
- `docs/SPEC.md` — the honest-degrade NFR and the source-transparency NFR (no unlabeled headline
  numbers).
- `docs/ARCHITECTURE.md` — the honest-degrade policy decision and the `analytics/superarchetype/`
  rows.
- `docs/analysis/best-call-ranking.md` — the runbook + method spec this feature amends.
- `.agents/skills/patterns/` — `honest-degrade-marker`, `divergence-as-diagnostic-surface`,
  `audit-echo-comment-lines`, `hybrid-derived-curated-registry` (the curated-override provenance the
  page surfaces), `confidence-metadata`.
- Code to read before designing: `scripts/refresh_best_call_ranking.py` (`make_cells`, `row_stats`,
  `_floor_eligible`, `compute_blob`) — **after** `feature-multi-split-matrix-best-call-onepass` has
  migrated it — and `scripts/best_call_ranking_template.html`.

## Inherited addendum (2026-08-01): the display ladder
Locked by the epic's licensed-imputation addendum. Per cell: measured (clears gate) → pooled
opponent-cluster cell (existing design) → **family-imputed cell** (licensed; chip: "imputed from
<family>, k sibs, pool n"; rendered as a lean, never a grounded row) → **family-range chip**
(unlicensed/vetoed/refused pools: show the member split or range, no point estimate) →
marginal-imputed (last resort, quarantined — compose with feature-ranking-honesty-guards).
Copy discipline: the page promises "fewer blank cells and honest leans", not grounded coverage;
the I² one-sidedness caveat must appear wherever a pooled or imputed number does.

## Inherited addendum #2 (2026-08-01): era/freshness display (epic addendum #2 — binding)
Imputed/pooled cells inherit the page's not-current muting rules via their pool's
current-regime share; the provenance chip names the window mix; subjects whose family
membership churned on the latest `superarchetype run` carry a labeled churn flag. Seam with
feature-ranking-honesty-guards: its regime-currency warning treats pool composition identically.
