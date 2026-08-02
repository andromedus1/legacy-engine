---
id: epic-superarchetype-layer-chain
kind: feature
stage: done
tags: [analytics, advisory]
parent: epic-superarchetype-layer
depends_on: [epic-superarchetype-layer-aggregation, feature-multi-split-matrix]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-02
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

## Architectural choice (2026-08-01 design pass)

Three options weighed; Option A chosen.

**Option A (chosen) — explicit registry param on the adaptive builder + a DB-free chain kernel.**
`build_multi_split_adaptive` gains `superarchetypes: SuperarchetypeRegistry | None = None`
(opt-in-analytics-overlay: the off path is the literal identity of today's code — the parameter
defaults to `None` and every new branch is behind `if view is not None`); an empty registry (no
clusters) is ALSO a no-op with a named audit line (gated-additive data-presence). All pure logic —
registry adapter, member-tally drawing from plain pooled dicts, rung resolution, ladder resolution
— lives in a new DB-free module `analytics/superarchetype/chain.py` (objective-search-split: the
builder computes windowed dicts once; the kernel is unit-testable with hand-built dicts, no DB).
The builder wires the prior rung at cell construction (prior_mean/prior_source/strength feed
`build_cell`) and assembles pooled/imputed/ladder maps after cell assembly. `beta_binomial_shrink_to`
untouched; `build_cell` gains an additive `prior_strength: float = SHRINK_STRENGTH` param.

**Option B — all logic inline in `matchup.py`.** Rejected: matchup.py is already 1124 lines; the
overlay is ~450 lines of typed pure logic whose tests want hand-built dicts (no DB); and
`aggregate.py` deliberately never imports matchup — the chain kernel belongs beside it.

**Option C — post-hoc overlay wrapper (build first, re-anchor cells afterwards).** Rejected: the
prior rung changes `p_shrunk` at cell construction; a wrapper would have to rebuild cells, forking
`build_cell` semantics and double-computing — the exact fork the epic forbids.

**Why the adaptive builder only** (not `build_multi_split_matrix`): era addendum #2 rule 2 is
binding — member tallies enter pools only from the member's current stable era, i.e. from the
pairwise-windowed cells only the adaptive build has. A uniform build has one window for every
cell; pooling there would violate the rule. `build_multi_split_inputs` passes the registry through
in adaptive mode and emits a named skip line in uniform mode (honest-degrade, not a crash — the
refresh script builds both adaptive and uniform fallbacks from one arg set).

## Design decisions (resolved with judgment; autopilot mode — logged, not asked)

1. **Gating shape**: explicit `superarchetypes` object param (caller intent), `None` default;
   empty/clusterless registry no-ops with `// superarchetype: registry empty — layer off`. The
   registry READ stays at the call site (`read_superarchetype_members(con)`) per epic decision 3.
2. **Where the rung engages**: on `_cell_prior`'s marginal-fallthrough branch. A camp cell WITH an
   LCO parent reference keeps today's anchor untouched (the finer rung wins — that is what the
   fixed order `camp -> LCO parent' -> superarchetype` means as anchor precedence). The literal
   nested form (re-anchoring the LCO value's own interior prior onto the superarchetype cell) is
   deferred: it moves the LCO' value by at most `strength/(strength+lco_n)` (second-order on
   well-fed parent pools) and would require parent-level pool plumbing for camp subjects. Named
   here so nobody reads the narrowing as an accident.
3. **Rung 1 (S vs cluster-of-O, leave-opponent-out)**: DL pool (`aggregate_cluster_cell`) over the
   opponent cluster's contributor tallies, LOO by MEMBER EXCLUSION (drop O's tally from the member
   list) — structurally exact, nothing to clamp; the count-subtraction discipline lives where
   counts are actually summed (split-parent row tallies reuse the partition sums that carry the
   existing non-negativity asserts). Member tallies at pairwise windows
   `max(valid_since[S], valid_since[M])` read from `pooled_by_since` (always an existing bucket —
   the max of two horizon dates is one of them).
4. **Rung 2 (cluster x cluster, prior only)**: DL over the SUBJECT family's contributors
   (leave-S-out), each contributing a count-pooled tally vs the opponent family's contributors
   (leave-O-out, skip Mo == Ms), pairwise-windowed per (Ms, Mo). Gates measure subject-side
   member disagreement — the axis the licensed-imputation probe validated. Singleton subject
   family => rung 2 refuses (nothing to borrow), correct by construction.
5. **Prior admissibility**: a rung anchors the cell only when `pooled_p is not None` AND
   `concentration.passed` AND `heterogeneity.band in {free, labelled}` ("fails its concentration
   or heterogeneity gate is skipped"; `not-computable` is not a pass — an independent prior needs
   a positive verdict, and the label's `I²=` slot must have a number). Strength =
   `PooledCell.prior.strength` (the kernel's evidence-gated [5, 30]).
6. **Display ladder order** (per-cell resolution emitted as data): `measured` (n >= 30) ->
   `imputed` (licensed family fill of the SAME (S,O) question) -> `pooled` (S vs cluster-of-O,
   n_eff >= 30, not refused, opponent's own matches INCLUDED) -> `none` (all refusals named).
   Fineness of the QUESTION orders imputed before pooled — the epic addendum's ladder
   (measured -> family-imputed -> family-range -> ...) already fixed that; the family-range rung
   is carried as the refused ImputedCell + sibling split on the ladder entry for
   -best-call-fallback to render.
7. **Young-era order (the owned decision)**: measured by `scripts/loo_ladder_harness.py` over
   historical disturbances in the real corpus (read-only). The family predictor is the
   subject-side sibling pool (impute-style, leave-subject-out, definers+curated only) — that is
   what addendum #2 rule 5 compares against the anchor. Encoded as a closed frozenset
   `FAMILY_FIRST_KINDS ⊆ {ban, release, unattributed}` in chain.py, with the measured MAEs at the
   definition site; a kind too thin to decide keeps the anchor order and says so. The family-first
   prior uses the SAME default strength (15) as the cross-era anchor it replaces — the harness
   compared values, not strengths, so only the mean changes.
8. **Attribution kind at consumption**: `EraHorizon` gains additive
   `attribution_kind: str | None = None` (from the winning boundary's stored attribution) — the
   only change to `eras/consume.py`; every existing construction is keyword-only and stays valid.
9. **Freshness provenance**: every pooled/imputed cell carries `window_note` ("member windows:
   2026-05-11 x3, full x2; excluded below-floor: X") and `current_regime_share` vs
   `resolve_regime("current")`'s start (n at `max(pair window, regime start)` summed over members
   / pool n). At most one extra scan (the regime-start bucket), opt-in path only.
10. **Members participate only when present on the opponent axis** (they carry resolved horizons
    there); below-floor members are excluded BY NAME in the window_note. Assignees are excluded by
    the kernel (`definer=False` from registry provenance `assigned`); contributors = provenance in
    {derived, curated}. Camps inherit the parent's cluster through `camp_parent` (brief §9).
11. **Consumption-side churn flag: not reconstructible** — the persisted registry holds no
    previous-run diff, so the per-subject churn flag stays a run-side audit concern; the registry
    audit lines here carry window/degraded/full-corpus-exploratory warnings instead. Named gap.
12. **Registry-window audit**: always echo `// superarchetype: registry <id count> clusters,
    window <since>..<until>, derived <date>`; warn when `window_since` is None (full-corpus =
    exploratory, not serving) or predates the current ban-regime start; warn when `degraded`.

## Implementation units (trickiest first: U2 owns the epic's measured decision, U4 is the wiring
with the most ways to silently lie; U1 must land before any mutation so the golden is honest)

**U1 — byte-identity golden (pin BEFORE any mutation).**
`tests/test_matchup_superarchetype_golden.py`: full serialization (every MatchupCell field, sorted
keys; plus subjects/opponents/parents/camp_parent/valid_since/cell_windows/horizon_meta identity
fields) of `build_multi_split_adaptive` over the two-parent hermetic corpus + entity_eras rows,
pinned as sha256 + two exact representative cells (one camp cell with cross-era label, one plain).
Committed green against the untouched builder. Acceptance: test passes on main's code, and keeps
passing through every later unit; new overlay fields assert empty-by-default.

**U2 — the LOO ladder-order harness (owned decision; read-only real corpus).**
`scripts/loo_ladder_harness.py` (stdlib argparse; default DB `data/legacy.duckdb`, read-only
connect; worktree fallback to the parent checkout's path). For every parent entity E in
`entity_eras` with an accepted `stable_since` B and winning-boundary attribution kind K, with a
family in the serving registry: for each opponent O outside E's family with post-era truth
`n >= 20` (E vs O over [B, None)): anchor = `beta_binomial_shrink_to(pre_w, pre_n,
prior_mean=beta_binomial_shrink(marg_pre_w, marg_pre_n))` over [None, B) (the `_cross_era_prior`
construction at parent level); family = definer+curated siblings' pooled rate vs O over
[max(B, sibling stable_since), None) per sibling, pool floor `n >= 40`. Report per-kind (ban /
release / unattributed) cell counts, MAE both ways, win counts; emit the `FAMILY_FIRST_KINDS`
verdict with the thin-kind fallback named. Acceptance: reproducible one-command run; numbers land
in `## Implementation notes`; the verdict is encoded in U3, not asserted.

**U3 — chain kernel (pure, DB-free).**
`src/legacy_engine/analytics/superarchetype/chain.py`:
- `ClusterView` (frozen dataclass: `cluster_of`, `label_of`, `members`, `contributors`,
  `n_clusters`) + `cluster_view(registry) -> ClusterView | None` (None on no clusters);
  `subject_cluster(label, camp_parent, view) -> str | None`.
- `draw_pool_tallies(subject, cluster_id, view, *, pooled_by_since, valid_since, camp_parent,
  camps_of, mirror_n, exclude_opponent=None, subject_cluster_id=None) ->
  tuple[list[MemberTally], str, dict]` — member tallies at pairwise windows, self-mirror injection
  when S is in the cluster, below-floor/zero-tally names, window-mix note + per-window n map.
- `draw_cluster_pair_tallies(subject_base, gs_id, go_id, view, *, ..., exclude_subject,
  exclude_opponent) -> ...` — rung 2's subject-side tallies (row-tally partition sums for split
  parents, non-negativity asserted).
- `rung_prior(...) -> tuple[float, str, float] | None` — rung 1 then rung 2 admissibility per
  decision 5, label per the epic (`superarchetype cell (leave-opponent-out; sa-XXX, m_eff M,
  I²=V)` / `cluster x cluster (leave-S-out, leave-O-out; ...)`).
- `LadderEntry` (frozen: subject, opponent, kind ∈ closed `_VALID_LADDER_KINDS = frozenset(
  {"measured", "pooled", "imputed", "none"})` fail-fast, cluster_id, token, reasons,
  sibling_split) + `resolve_ladder(...)` per decision 6.
- `FAMILY_FIRST_KINDS` + the measured-MAE constants from U2.
Acceptance: unit tests with hand-built dicts cover window selection, LOO exclusion, mirror
injection, assignee/below-floor exclusion, rung fallthrough (gates fail -> rung 2 -> None), label
shapes, ladder order, closed-vocab fail-fast.

**U4 — builder wiring (`matchup.py` + `eras/consume.py`).**
- `build_cell(..., prior_strength: float = SHRINK_STRENGTH)` (additive; passes to
  `beta_binomial_shrink_to(strength=...)`).
- `EraHorizon.attribution_kind: str | None = None`; `era_horizons` populates it from the winning
  boundary's stored attribution kind.
- `build_multi_split_adaptive(..., superarchetypes: "SuperarchetypeRegistry | None" = None)`:
  lazily import chain; when the view is non-None — per-cell rung resolution on the marginal
  branch; young-era family-first override per `FAMILY_FIRST_KINDS` (subject-contributed boundary
  only; falls back to the cross-era anchor, which keeps precedence everywhere else); post-assembly
  `cluster_cells[(S, cluster_id)] -> PooledCell` (display pools, O included, refusals first-class),
  `imputed_cells[(S, O)] -> ImputedCell` (sub-display cells, subject has a family, O outside it;
  licenses computed once per cluster from the era-windowed profile), `ladder[(S, O)] ->
  LadderEntry` for every sub-display (S, O), registry audit lines appended to `audit_preamble`.
- `AdaptiveMultiSplitMatrix` gains default-empty `cluster_cells` / `imputed_cells` / `ladder`
  fields (additive; the one construction site is in this function).
Acceptance: hermetic two-parent corpus + hand-built registry tests prove (a) `superarchetypes=None`
=> cell-for-cell equality with the default build and empty overlay maps; (b) engaged cells carry
the rung `prior_source` labels and changed `p_shrunk` ONLY where the rung engaged; (c) pooled and
imputed cells carry provenance (family, siblings, pool n, license, window mix, regime share,
I² one-sided note, refusal reasons); (d) U1 golden still green; existing multi-split parity suite
untouched and green.

**U5 — consumer seam + audit + spot check.**
`advisory/window.py::build_multi_split_inputs(..., superarchetypes=None)` passthrough (adaptive
mode) + `// superarchetype: layer requires adaptive mode — skipped` line in uniform mode; tests.
Read-only real-corpus spot check (script-free, reported in notes): one thin subject (an Aluren-
family member or young-era entity) — its pooled cell, ladder entries, imputed cells, and the audit
lines, pasted into `## Implementation notes`.

## Test approach

Hermetic only (file-backed or `:memory:` DuckDB; `in_current_regime()` for dates when regime
matters; never the default DB). Pure-kernel tests hand-build `pooled_by_since`/`valid_since`
dicts and registries (`RegistryCluster`/`ClusterMember` constructed directly — no clustering in
tests). Builder tests reuse the two-parent parity corpus (`test_match_results_multi_split`) plus
`write_entity_eras` rows, with a hand-built registry over its parent labels; the imputation-path
test uses a purpose-built corpus with three plain archetypes at generous counts so the license's
column floors are reachable. Byte-identity is enforced twice: the U1 sha-pinned golden and the
existing parity/CLI-golden suites left untouched. Real-corpus runs are read-only validation
reported in notes, never tests.

## Risks (pre-mortem)

- **The golden pins environment-dependent floats.** Mitigated: the corpus is integer-count
  deterministic and all floats flow through the same library calls CI runs; the golden already
  exists in spirit as the parity suite (same fixture). If CI diverges from local, the golden — not
  the feature — is wrong; fix by pinning the serialization, not by loosening equality.
- **The harness finds too few disturbances to decide any kind.** Explicitly a valid outcome: keep
  anchor-first everywhere, encode an empty `FAMILY_FIRST_KINDS`, report the counts. Do not force
  the hypothesis.
- **Rung engagement changes numbers where a consumer pinned them.** The rung only engages when the
  caller passes a registry; no current caller does (the CLI/scripts opt in via
  -best-call-fallback). The U1 golden + parity suite prove the default path.
- **Window drift between member tallies and the cell.** Member tallies deliberately use pairwise
  member windows (era addendum #2), NOT the cell's own `s_ab`; the window-mix note makes the mix
  visible instead of pretending one window.
- **Silent intra-family imputation.** `impute_cell` refuses intra-family targets by construction;
  the ladder test covers an (S, O) pair inside one family.
- **`chain.py` accidentally importing duckdb** (via registry import). Only `TYPE_CHECKING` imports
  of registry types; runtime code takes plain dicts and `MemberTally`s. A test asserts
  `"duckdb" not in sys.modules` after a fresh chain-only import (same discipline as
  `test_no_rounds.py`).

## Implementation notes (2026-08-01, branch impl/superarchetype-chain)

Shipped as designed (Option A), one commit per unit. Deviation from the pre-mortem: the
DB-freeness check became an AST walk over `chain.py`'s import nodes (runtime `duckdb`/`registry`
imports forbidden, `TYPE_CHECKING` exempt) rather than a `sys.modules` probe — importing any
submodule executes the package `__init__`, which legitimately pulls duckdb via `registry`.

**What landed where**

- `analytics/superarchetype/chain.py` (new, DB-free): `ClusterView`/`cluster_view` (contributors =
  provenance `derived`/`curated`; assignees receive), pairwise-window tally drawing
  (`draw_pool_tallies`, `draw_row_tallies`, `draw_family_tallies`, `draw_cluster_pair_tallies` —
  split parents partition-summed over camps), `family_profile`, `rung_prior` (rung 1 LOO by member
  exclusion, rung 2 subject-side DL over count-pooled opponent-family tallies; admissibility =
  `pooled_p` present AND concentration passed AND het band in {free, labelled}),
  `resolve_ladder` + `LadderEntry` (closed kinds `measured|pooled|imputed|none`),
  `registry_audit_lines`, `FAMILY_FIRST_KINDS` (measured; see below).
- `analytics/matchup.py`: `build_cell(..., prior_strength=SHRINK_STRENGTH)` (additive);
  `build_multi_split_adaptive(..., superarchetypes=None)` — rung resolution on the marginal
  branch, cross-era precedence with the (currently empty) family-first exception wired, one
  regime-start bucket scan for freshness shares, post-assembly
  `cluster_cells`/`imputed_cells`/`ladder` maps on `AdaptiveMultiSplitMatrix` (additive
  default-empty fields), registry `//` lines appended to `audit_preamble`.
- `analytics/eras/consume.py`: `EraHorizon.attribution_kind` (additive, from the winning
  boundary's stored attribution; ban/release/unattributed).
- `advisory/window.py`: `build_multi_split_inputs(..., superarchetypes=None)` passthrough
  (adaptive mode); uniform/full + registry emits
  `// superarchetype: layer requires adaptive mode — skipped (uniform window)`.
- `scripts/loo_ladder_harness.py`: the reproducible ladder-order measurement (read-only).

**The LOO harness verdict (the decision this feature owns) — ANCHOR-FIRST everywhere;
`FAMILY_FIRST_KINDS = frozenset()`.** Preregistered floors (truth n>=20, sibling pool n>=40,
>=10 cells/kind to decide), real corpus, serving registry (window 2026-05-11): ban 1 cell,
release 4, unattributed 0 — every kind too thin, anchor kept by rule. Sensitivity at the serving
floors (truth n>=15, pool n>=25 = `_IMPUTE_MIN_POOL`): 14 cells, still <10 per kind, and the
ANCHOR also wins outright — composition (ban+release) MAE 0.1138 (anchor) vs 0.1282 (family),
family 4/10; unattributed 0.1578 vs 0.3119, family 0/4. Family DID beat the marginal (0.1282 vs
0.1359 composition), consistent with the epic's 2026-08-01 probe — but the own-past anchor is the
stronger incumbent for young-era cells on today's corpus. The hypothesis (family-first for
composition-disturbed) is NOT supported; the mechanism stays wired so a future re-measure is a
one-line recalibration. Reproduce: `.venv/bin/python scripts/loo_ladder_harness.py`.

**Byte-identical proof**: sha-pinned full-output golden (`test_matchup_superarchetype_golden.py`,
captured on the untouched builder BEFORE any mutation, commit bfc7f4f) + cell-for-cell equality
tests for `superarchetypes=None` and empty-registry builds + the untouched pre-existing parity
and CLI-golden suites. Full suite after all units: 3507 passed, 1 skipped (pre-existing skip).

**Real-corpus spot check (read-only; measured 2026-08-01 before PR #75; serving registry window
2026-05-11; staged parents; min_row_share=0.001)**:
144 rung-labeled cells and the changed-cell set equals the rung-labeled set exactly; 557 granted
imputations (all from sa-003, the only family clearing the license — 5 evaluable columns, 1
divergent (0.20 <= 0.25), tau_profile 0.269 widening every imputed CI by ±0.13); ladder kinds
none 15956 / imputed 557 / pooled 124. Example: `Ad Nauseam Tendrils [Preordain]` vs Death &
Taxes imputes p=0.358 (pool n=67, 7 sibs, ci 0.12-0.61, regime share 0.39, window mix named); an
Aluren-family assignee (Bant Infect) gets its family pool served (p=0.640, n_eff 4, regime share
0.0 — honestly mutable) and a NAMED intra-family imputation refusal vs Aluren. The audit fires:
the serving registry (2026-05-11) now predates the regime start 2026-06-29 —
`⚠ registry window ... stale taxonomy (window mismatch)` — a real operational finding for the
next `superarchetype run`. At the OLD default `min_row_share=0.02` the layer engages almost
nowhere (16 opponents; every family a comparability desert) — the epic's fillable-cell prize
lives at the serving floor, worth knowing for -best-call-fallback.

**Named narrowings / gaps (deliberate, from the design)**

1. The LCO branch keeps its existing interior anchor (`marginals[base]`); the fully nested
   `LCO' -> superarchetype` form is deferred (second-order on well-fed parent pools). Camp cells
   in windows where the camp's parent is absent fall to the marginal branch and CAN take the rung
   (observed on the real corpus) — consistent with the existing per-window fallback semantics.
2. Consumption-side per-subject churn flag is not reconstructible from the persisted registry
   (no previous-run diff at read time) — run-side audit concern.
3. Rung 2's estimator orientation: DL across subject-family members, each count-pooled across the
   opponent family (leave-S-out/leave-O-out at draw time); gates therefore measure subject-side
   sibling disagreement — the axis the imputation probe validated. Documented at the definition
   site.

**Ruff**: `ruff check src/` (advisory in CI) — changed files carry zero F-class findings; the net
repo delta is +8, all UP037 quoted-annotation style matching `matchup.py`'s existing convention
(325 pre-existing repo-wide).
