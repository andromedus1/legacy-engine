---
id: epic-superarchetype-layer-chain
kind: feature
stage: drafting
tags: [analytics, advisory]
parent: epic-superarchetype-layer
depends_on: [epic-superarchetype-layer-aggregation, feature-multi-split-matrix]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Superarchetype rung — cluster-pooled cells in the matrix and in the shrinkage chain

## Brief

Wires the taxonomy and the estimator into the matchup machinery. Two deliverables, one seam.

**(1) Cluster-pooled cells.** The opponent axis gains one more level of coarsening:
`camp → parent → cluster`. This is deliberately the *same* seam
`feature-multi-split-matrix` already generalized — `_pool_opponent_tallies` pools a maximal
camp×camp tally's opponent side back to parent level via an explicit `camp_parent` map, and the
cluster rung is that operation applied once more with a `cluster_of` map from `-clustering`'s
registry. Composing here rather than forking matters: the subject axis (camp rows, unsplit
archetype rows, force-inclusion, `min_row_share`, era-windowed scans, cross-era priors) is
`MultiSplitMatrix`/`AdaptiveMultiSplitMatrix`'s job and stays exactly as it is; the superarchetype
layer only coarsens the opponent axis on top of the tally those builders already produce, so it
inherits every existing windowing and honesty guarantee instead of re-deriving them. Pooling of
member *cells* is `-aggregation`'s random-effects estimator, not a sum of tallies — the pooled
cluster cell carries `n_eff`, `m_eff`, `I^2`, the intra-cluster flag, and its gate verdict.

**(2) The new rung in the shrinkage chain.** Today `_cell_prior` implements
`camp cell → leave-camp-out parent cell → parent's shrunk marginal → 0.5`, with
`build_adaptive_matrix`'s cross-era prior overriding for thin era-truncated cells. The
superarchetype inserts a rung **between the LCO parent cell and the subject marginal**, computed
**leave-opponent-out** — the (S, O) tally itself is subtracted out of the pooled aggregate so the
cell's own data never appears inside the prior it shrinks toward. That is the direct analogue of the
existing LCO construction, and it carries the same subtraction discipline: assert non-negative,
never clamp, because a negative result means the member counts are not a partition. The prior
strength for the rung is the moment-matched `[5, 30]` value from `-aggregation`, so a coherent
cluster anchors harder than an incoherent one, and a rung that fails its concentration or
heterogeneity gate is **skipped** — the chain simply falls through to the next rung. The existing
`prior_source` string is where all of this becomes auditable (e.g.
`superarchetype cell (leave-opponent-out; m_eff 3.9, I²=0.11)`). `beta_binomial_shrink_to` is not
touched. The **cross-era prior keeps precedence** where it applies: a cell's own pre-disturbance
value is more specific to that cell than any cluster aggregate, and the superarchetype rung applies
only where no cross-era prior exists.

**Rung 2 (cluster × cluster, coarsening the subject too) ships as a PRIOR rung only in v1** — it
buys real estimation quality for the thinnest cells, but coarsening the subject changes *whose* win
rate is being reported, and the display ladder's row is the user's own deck. Display therefore stops
at rung 1 (subject × opponent-cluster). The **display ladder** is the other half of this feature and
is separate from the prior chain by the epic's locked decision: walk the same ladder and take the
**finest rung whose `n_eff` clears `DISPLAY_GATE_N`**, with two differences from the prior path —
the displayed cluster cell **includes** the opponent's own matches (it is the best estimate of "S vs
this family", not a prior that must stay independent) and it carries the intra-cluster flag. The
ladder resolution and its provenance token are produced here as data; rendering is
`-best-call-fallback`'s job.

**Not covered here.** No page, no template, no chip markup, no runbook. Also: **the no-registry path
must be byte-identical** to today's behavior (gated-additive-augmentation — an absent or empty
superarchetype registry means no rung, no ladder, no field changes), which is what keeps the ~15
advisory-window call sites, the freshness-stripped CLI body goldens, and the multi-split parity
tests green without modification.

## Epic context

- Parent epic: `epic-superarchetype-layer`
- Position in epic: **integration feature** — the consumer of `-clustering`'s registry and
  `-aggregation`'s estimator, and the producer of the cell/ladder data `-best-call-fallback`
  renders. This is where the epic's numbers first change.
- **Composes with `feature-multi-split-matrix`** (declared `depends_on`): the cluster rung extends
  the `build_multi_split_*` entry points and the `_pool_opponent_tallies` seam that feature owns.
  Its `-adaptive-window` child (adaptive multi-split builder + `build_multi_split_inputs`) is the
  specific entry point this feature needs and is still open — do not fork the matrix build, and do
  not re-implement per-parent split matrices.

## Inherited design decisions

From the epic's `## Strategic decisions` and `## Design decisions`. Fixed inputs:

- **Chain position is fixed, not chosen per cell.** `camp → LCO parent' → superarchetype cell
  (leave-opponent-out) → cluster × cluster (leave-S-out, leave-O-out, prior only) → marginal' →
  0.5`. The order is fixed so the audit trail is deterministic; the gates decide whether a rung is
  *allowed*, never which rung comes *first*.
- **Rung 2 is a prior rung in v1; the display ladder stops at rung 1.** Promoting rung 2 to a
  display rung is a follow-up gated on dogfooding rung 1.
- **Opponent-axis coarsening only.** The subject axis is whatever the host matrix already carries
  (camp label or parent label) — the cluster layer never rewrites subject rows.
- **Registry is read, never computed.** No clustering in a matrix build; a window mismatch between
  registry and matrix is a loud `//` audit line.
- **Cross-era prior keeps precedence** over the superarchetype rung.
- **Gated-additive:** no/empty registry ⇒ byte-identical output; existing goldens and the multi-split
  parity tests stay green untouched.
- **`n_eff`, not raw pooled n**, is what reaches `tier_for_sample` and the display gate for any
  cluster-sourced cell.

## Research briefs

- `docs/briefs/superarchetype-aggregation.md` — **primary**. §8 (the exact rung position, the
  monotone-coarsening argument, why opponent-side coarsening comes first, prior strength per rung,
  gate-failure fallthrough, `prior_source` label shape, display-fallback-is-separate, cross-era
  precedence), §7 (leave-opponent-out discipline and its analogy to
  `matchup._camp_hierarchy_inputs`), §10 (`beta_binomial_shrink_to` untouched; `n_eff` is the
  integration seam; everything degrades with a name).
- `docs/briefs/change-point-detection.md` — the era-windowing contract the adaptive builders honor
  and this rung must not disturb.
- `docs/briefs/advisory-methods.md` — the shrinkage/tier conventions the new rung sits inside.

## Foundation references

- `docs/SPEC.md` — the hierarchical + cross-era cell-shrinkage capability bullet (extended with the
  superarchetype rung) and the confidence-gated-stats NFR.
- `docs/ARCHITECTURE.md` — the `analytics/matchup.py` row (chain + multi-split entry points) and the
  `analytics/superarchetype/` rows.
- `.agents/skills/patterns/` — `gated-additive-augmentation` (the no-registry no-op path),
  `two-level-empirical-bayes`, `honest-degrade-marker`, `audit-echo-comment-lines`,
  `divergence-as-diagnostic-surface`, `file-backed-cli-test-db-builder` (hermetic tests only —
  never the default DB).
- Code to read before designing: `src/legacy_engine/analytics/matchup.py` (`_cell_prior`,
  `_camp_hierarchy_inputs`, `_multi_hierarchy_inputs`, `_pool_opponent_tallies`,
  `MultiSplitMatrix`, `build_multi_split_matrix`, `build_adaptive_matrix`'s `_cross_era_prior`),
  `src/legacy_engine/analytics/match_results.py` (`MatchResults.camp_parent`, `mirror_n`,
  `effective_label`), `src/legacy_engine/advisory/window.py`,
  `.work/active/features/feature-multi-split-matrix.md` (its `## Architectural choice` and Units
  2-4 — the seams this feature extends).

## Inherited addendum (2026-08-01): subject-axis imputation consumption
The epic's licensed-imputation decision (see epic body) lands partly here: for an EMPTY or
sub-display archetype cell (S vs O), consume `aggregate.impute_cell` — sibling tallies drawn
era-windowed through the multi-split machinery (never raw full-corpus) — and emit it as a distinct
cell kind (`imputed`), NEVER blended into measured cells and never a prior-only ghost. The existing
prior rungs stay as designed; this ADDS a displayable, licensed value for cells the rungs alone
would leave hidden. prior_source/provenance must name the family, sibling count, pool n, and license.

## Inherited addendum #2 (2026-08-01): era discipline (epic addendum #2 — binding)
- Sibling tallies: from the adaptive multi-split build ONLY (cells already pairwise era-windowed,
  cell_windows/horizon_meta attached); member tallies only from the member's current stable era.
- Contribute vs receive: definers + curated contribute; assignees receive.
- Taxonomy consumption: the WINDOWED registry (regenerated 2026-08-01, `--since 2026-05-11`,
  churn 0.933 flagged) is the serving artifact; full-corpus runs are exploratory. See also the
  era-core-pools story for the per-entity endpoint.
- Freshness provenance: every pooled/imputed cell carries window mix + current-regime share
  (computed here, passed through the kernel).
- **Ladder-order decision this feature OWNS**: own-pre-disturbance anchor vs family-current
  imputation for young-era cells, decided per attribution kind by a LOO harness over historical
  disturbances (predict held-out early-era cells both ways). Hypothesis: family-first for
  composition-disturbed subjects, anchor-first for drift-only. Do not assert; measure.
