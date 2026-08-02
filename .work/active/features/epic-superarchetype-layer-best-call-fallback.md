---
id: epic-superarchetype-layer-best-call-fallback
kind: feature
stage: review
tags: [advisory, analytics, docs]
parent: epic-superarchetype-layer
depends_on: [epic-superarchetype-layer-chain, feature-multi-split-matrix]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-01
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

## Design (feature-design pass, 2026-08-01)

Everything rendered here EXISTS on `AdaptiveMultiSplitMatrix` (PR #74): `ladder[(subject,
opponent)] -> LadderEntry` (closed kinds `measured -> imputed -> pooled -> none`, every finer
refusal named, `sibling_split` for range rendering), `imputed_cells[(subject, opponent)] ->
ImputedCell` (license + veto + tau-widened CI + freshness), `cluster_cells[(subject, cluster_id)]
-> PooledCell` (refusals first-class: `m_eff`, I² band + `one_sided_note`, `member_split`,
exclusions, `window_note`, `current_regime_share`). This feature is consumption and rendering only.

### Decision 1 — ladder/agency isolation (the explicit decision this design owns)

**Superarchetype content renders ONLY in the row-expansion ledger, carried in an additive per-cell
`sa` key on page-unmeasured cells. The pre-existing cell fields (`p/raw/n/ci_low/ci_high/window/
tier/measured`) and every row-level field are never touched.** Every downstream reader — `row_stats`
(adj / floor / agency / coverage / grounded), `blowouts()`, `out_used -> rank_matrix -> P(best) /
s_cov`, the template's measured-cell census, the strata assignment — computes from bit-identical
inputs, so the no-leak claim is structural, not behavioral: the metrics cannot change because their
inputs cannot.

This consciously supersedes the Brief's pre-addendum sentence "the `adj` field-WR aggregate (which
superarchetype cells DO feed)": addendum #1 locked *"labeled lean, never a grounded row input"*,
and `adj` is an input to `agency = min(adj, floor)` — feeding `adj` would enter the agency
computation silently, exactly what the locked ladder forbids. Consequences, both documented on the
page: (a) **no new stratum** — the Brief's "fallback-only rows get their own labeled stratum"
existed to quarantine metric contamination that no longer occurs; row strata inputs are unchanged,
so `grounded` stays measured-only by construction; (b) the page's promise is *"fewer blank cells
and honest leans"* in the expanded ledger, never improved headline coverage.

Leak surfaces enumerated (each guarded by the Unit-1 anti-leak test):
- `row_stats` `n1` (`n>=1 and p is not None`) -> `adj`: thin cells already feed adj — `sa` never
  writes `p`/`n`;
- `_floor_eligible` -> `floor`: measured-gated, fields untouched;
- `out_used` (populated for every cell with a `use`, thin included) -> the shared-field MC: the
  cell OBJECT is never replaced;
- `blowouts()` / `measCells` in the template: keyed on `c.measured`, untouched;
- strata: `r.grounded` / `r.recent_4wk`, untouched.

### Decision 2 — page-gate vs engine-gate split

Rung 1 ("measured cell clears its gate") is the PAGE's existing selection — era cell at
`n >= ground_n` (8), else ban-scoped fallback at `n >= ground_n` — byte-identical, chips included.
The `sa` payload is consulted only for page-unmeasured cells (`measured: false`). The fallback
content itself was resolved by the builder at the ENGINE's display gate (pooled `n_eff >= 30`;
imputed pool `n >= 25` + earned license + per-cell veto): borrowed family evidence clears a
*stricter* bar than a deck's own measured cells, which is the right asymmetry and is stated in the
definitional card. Engine ladder entries exist exactly for multi-split cells with `n < 30`, a
superset of the page-unmeasured cells (parity makes the two `n`s identical for shared subjects),
so no page-unmeasured cell can miss its entry where the pair exists in the multi-split matrix.

Subjects: `msa.ladder` covers camps + unsplit archetypes (the multi-split subject set). Archetype
rows that are split parents have no ladder key — their fallback lives on their camp rows, where the
finer truth is. Documented in the runbook, guarded by `.get()`.

### Decision 3 — page floor: keep `--min-row-share 0.001` (no change)

The script's default is ALREADY 0.001 (the page-level row floor was lowered when the page grew its
long tail); 0.02 is `build_multi_split_adaptive`'s own parameter default, which the page has always
overridden. The registry rides the SAME one-pass build the page already runs, so the chain engages
at the page's existing floor — exactly where the thin rows live (Cradle Control, Aluren, the
31-of-35 archetypes with zero n>=30 cells all sit below 0.02 involvement). Deliberate pick: 0.001,
zero floor churn, justified by the epic's own coverage evidence.

### Decision 4 — registry source + audit surface

`main()` reads `read_superarchetype_members(con)` from the SAME `--db` connection (the DuckDB
derived cache is the registry module's documented consumption seam; `superarchetype run` rebuilds
it in the refresh cycle right before this page). Absent tables -> `None` -> the build's
byte-identical off path (hermetic tmp-DB tests stay green untouched). `--no-superarchetypes`
opts out for baseline/audit regeneration. The builder-emitted `// superarchetype:` lines (including
the stale-taxonomy warning, which fires today, correctly) are filtered from `msa.audit_preamble`
by their own prefix and appended to `meta.audit`, plus one script-computed ladder-census line.
Era-degrade preamble lines are NOT newly surfaced (out of scope; would break off-path identity).

### Decision 5 — intra-family labeling scope

v1 labels family relationships only on superarchetype-SOURCED content (the pooled cell's
`intra-family share` chip, `intra` flags on split members). Measured cells stay byte-identical per
rung 1's acceptance bar — the Aluren-vs-Show-and-Tell worked example reads through the family
chips and splits in the same expansion, not through decoration of the measured cell.

### Options considered

- **A (chosen): expansion-only additive `sa` payload.** Structural no-leak proof; measured content
  byte-identical layer-on vs layer-off; smallest diff against the co-editor feature.
- **B: feed adj+coverage + new labeled stratum (epic design decision 6 as written).** Rejected:
  violates the locked display-ladder addendum ("never a grounded row input") and the arc directive
  (imputed/pooled must not enter `agency = min(adj, floor)`), and changes headline numbers for
  nearly every thin row — fails the byte-identity acceptance bar.
- **C: shadow columns (`adj†`/`coverage†`) computed with leans.** Rejected: row-aggregate lean
  views belong to `feature-agency-page-methodology` (same script/template co-editor); shipping a
  second aggregate vocabulary here double-implements the exact overlap the epic warns about.

### Units (trickiest first)

**Unit 1 — script: registry consumption + anti-leak `sa` overlay.**
`scripts/refresh_best_call_ranking.py`:
- `compute_blob(..., superarchetypes: SuperarchetypeRegistry | None = None)`; pass to the ONE
  `build_multi_split_adaptive(..., superarchetypes=...)` call (no second build);
- `_split_json(split) -> list[dict]` (`a/w/n/p/tier/intra` per member, r4 floats);
- `_sa_payload(subj, opp, msa, label_of) -> dict | None`: kind `imputed` (p, ci, pool_n, k,
  family label+id, cur, window_note, license reason, tau, split, reasons), kind `pooled`
  (p, ci, n_eff, tier, m_eff, i2, i2_band, intra_share, cur, window_note, notes = served-with
  labels from `provenance[1:]`, split, reasons), kind `none` -> `range` (split from
  `sibling_split` else the pooled cell's `member_split`, source `siblings|members`, family, the
  matching named refusal line, cur/window_note from the same source, reasons) or `None` when no
  split exists (cell renders exactly as today);
- attach loop after rows are built: unmeasured cells only, arch + camp rows, census counts;
- `meta.audit` += builder `// superarchetype` lines + census line;
- `main()`: `--no-superarchetypes` flag; `read_superarchetype_members(con)`.
Acceptance: (a) anti-leak test — blob(layer-on) vs blob(layer-off) on a hermetic corpus: `meta`
equal except the appended audit lines; every row equal on all non-`cells` keys; measured cells
identical dicts; unmeasured cells identical except an optional added `sa` key; (b) non-vacuity —
the fixture produces at least one `imputed`, one `pooled`, and one `range` payload; (c) the
stale-taxonomy warning line lands in `meta.audit` when the registry window predates the current
regime start; (d) absent registry -> blob equal to the pre-change script's output (existing parity
+ determinism tests stay green untouched); (e) hermetic file-DB `main()` e2e: registry written via
`rebuild_superarchetype_members` -> page contains the chips; `--no-superarchetypes` -> byte-equal
to the registry-absent page.

**Unit 2 — template: fallback rendering + copy discipline.**
`scripts/best_call_ranking_template.html`:
- ledger renderer: `!c.measured && c.sa` renders the fallback line per kind; the measured branch
  and the plain unmeasured branch are character-identical to today;
- chips: `imputed from <family> (k sibs, pool n=N)`; `pooled vs <family> (n_eff N, <tier>)` +
  `intra-family NN%` when share > 0; range lines show `family range lo–hi% across k <source>
  (pool n=N)` with NO point estimate + the named refusal chip (`dominated by <member>`, the I²
  band/spread guard text, local veto, comparability desert);
- freshness: `cur < 0.5` -> amber `◦mostly pre-regime (NN% current)` marker (mirrors the row-level
  `◦not current` convention); cur + window mix always in the title tooltip;
- title tooltips carry the full reasons chain, window note, license/gate detail, and the I²
  one-sidedness caveat;
- a conditional key line (only when the row has fallback content) stating the ladder and the
  isolation rule ("leans never enter agency, adj, floor, coverage, or strata") + the I² caveat;
- definitional card: one new `<li>` (hidden unless the blob carries fallback content) with the
  ladder, the "fewer blank cells and honest leans — never grounded coverage" promise, the
  stricter-gate-for-borrowed-evidence note, and the full one-sidedness caveat;
- CSS: `.cells .sa` dashed-left-border treatment, muted text kept (a lean is quieter than a
  measurement).
Acceptance: e2e render test asserts chips + caveat text + key line present with a registry and
absent without; measured-cell render path untouched (asserted via the Unit-1 blob identity + the
e2e `--no-superarchetypes` byte-equality).

**Unit 3 — docs roll-forward.** `docs/analysis/best-call-ranking.md`: `superarchetype run` joins
the refresh cycle before the page; the ladder + chip vocabulary; the isolation decision (leans are
ledger-only); the `--no-superarchetypes` knob; frontmatter decisions updated. Feature file carries
`## Implementation notes` with the real-corpus validation numbers.

**Unit 4 — real-corpus validation (read-only).** Regenerate layer-on (serving registry from the
real DB) and layer-off; diff per the anti-leak contract; report: whether sac-001 earns its license
(gate numbers either way), ladder-kind counts across the page, 3-5 concrete examples with chips,
wall-time delta, the stale-taxonomy warning line as rendered.

### Pre-mortem

- **sac-001 fails its license on serving windows** -> that is a FINDING for quality review; report
  `cols_evaluated` / `sig_divergent_cols` / `tau_profile` and the named reason; never weaken gates.
- **Ladder empty at page pairs** (multi-split inclusion mismatch vs the archetype matrix) ->
  `.get()` guards everywhere; real-corpus census proves non-vacuity or reports honestly.
- **Audit-line prefix drift** (`// superarchetype`) -> pinned by test.
- **Blob bloat from splits** -> splits are contributor-sized (<=7 members per family); census line
  makes growth visible; no caps needed in v1.
- **Template regression on measured rendering** -> the measured branch is not edited; enforcement
  is the blob-level identity plus the `--no-superarchetypes` byte-equality e2e.
- **Performance** (license profiles + imputation attempts per sub-display cell on the real corpus)
  -> measured in Unit 4; the build stays ONE pass either way.
- **Co-editor collision** (`feature-agency-page-methodology`) -> additive `sa` key + one new
  renderer branch + one `<li>` keeps the merge surface minimal; no shared lines rewritten.

## Implementation notes

Implemented in four commit-sized units (publication commit for the final unit is blocked only by
the managed sandbox's read-only `.git/worktrees` metadata):

1. Registry consumption and the additive, ledger-only `sa` overlay in
   `scripts/refresh_best_call_ranking.py`, including `--no-superarchetypes`, audit census, and
   hermetic on/off identity coverage.
2. The imputed / pooled / family-range renderer, chips, freshness muting, conditional key, and
   definitional-card honesty copy in `scripts/best_call_ranking_template.html`.
3. The refresh-cycle and methodology roll-forward in `docs/analysis/best-call-ranking.md`.
4. Typed renderer hardening + real-corpus validation. Payload semantics now serialize typed
   `Concentration.passed/label`, `Heterogeneity.band/note/reason/one_sided_note`,
   `PooledCell.refused_reason`, `ImputedCell.reason`, and current-regime fields directly; renderer
   truth never comes from `PooledCell.provenance` or parsed `prior_source` prose.

### Implementation discovery and bounded deviation

The first real-corpus on/off diff caught six camp cells whose pre-existing `p` moved from `0.5000`
to `0.5007` because passing the registry to `build_multi_split_adaptive` also activates the
engine's family prior rungs. Row headlines happened not to move on this corpus, but the cell drift
violated Decision 1's structural anti-leak contract. The abandoned WIP tried to detect those rungs
by parsing `prior_source` prefixes and then alter floor eligibility; that was removed because the
string is not a typed semantic contract and the behavior contradicted the design.

Smallest one-pass repair: `build_multi_split_adaptive(..., apply_superarchetype_priors=False)` is
now a typed overlay-only consumer seam. It still computes `cluster_cells`, `imputed_cells`,
`ladder`, and audit lines from the registry in the same pass, while leaving `multi.cells` on the
baseline hierarchy. The best-call page uses that seam. Builder-level and script-level tests are
non-vacuous: overlay maps/chips engage, including two real camp rows, while every base cell stays
identical.

### Real-corpus validation (2026-08-01)

Database: `/Users/<user>/dev/legacy-engine/data/legacy.duckdb`; page defaults
(`field_since=2026-06-29`, `ground_n=8`, `min_row_share=0.001`), 94 archetype rows + 115 camp rows
against 77 field opponents (16,016 page cells total).

- Layer-on artifact: `/private/tmp/legacy-best-call-validation-af7ada/layer-on.html`, SHA-256
  `c3dd4a77ea4c4037cc34125c9311313bf07abad1fe65d154a171e0f710b246d5`, wall time 26.49s.
- Layer-off artifact: `/private/tmp/legacy-best-call-validation-af7ada/layer-off.html`, SHA-256
  `7bc93c3020ade6099ecd4f316465c59955ae974b9e643727cb3275eb723206eb`, wall time 26.12s.
  Observed layer cost: +0.37s (+1.4%).
- Structural diff: PASS after the overlay-only seam. `meta` is identical after removing the
  appended `// superarchetype` lines; every row's non-cell fields are identical; every measured
  cell is identical; every unmeasured cell is identical after removing only its optional `sa`
  key. Zero mismatches across all 16,016 cells.
- Page display census: 2,230 measured; 438 imputed leans; 95 pooled leans; 9,442 family-range
  displays; 3,811 still blank (no renderable split). Engine sub-display ladder census from the
  same build: 573 imputed, 126 pooled, 15,938 none; measured cells are intentionally absent from
  `ladder`.
- `sac-001` (`White creature`: Death & Taxes, Energy, Orzhov Midrange, Orzhov Scam) license:
  **granted**, 6 evaluable columns, 0 significantly divergent, significant fraction 0.00 <= 0.25,
  `tau_profile=0.03388150959308456`; 736 attempted cells yielded 16 imputed points. The other
  granted family `sa-003` yielded 557, for the previously reported 573 licensed imputations across
  the two families.
- Stale taxonomy warning surfaced exactly:
  `// superarchetype: ⚠ registry window 2026-05-11 predates the current regime start 2026-06-29 — stale taxonomy (window mismatch)`.

Representative rendered ledger cells (all are explicitly family **leans**, never grounded rows):

- Black Midrange vs Mystic Forge Combo: 63.33%, 95% CI 32.05–92.18, chip `imputed from
  <sa-003 label> (7 sibs, pool n=30)`, 96.67% current-regime evidence.
- Black Midrange vs Energy: 40.51%, 95% CI 16.90–64.99, chip `imputed from <sa-003 label>
  (7 sibs, pool n=79)` plus amber `◦mostly pre-regime (43% current)`.
- Dimir Midrange vs Dimir Death's Shadow: 51.43%, 95% CI 37.98–64.67, chip `pooled vs
  <sa-003 label> (n_eff 48.0, evolving)` plus `intra-family 100%`; typed gates are
  `m_eff=3.75`, `I²=0.00 (free)`, with the one-sidedness note in the tooltip.
- Cephalid breakfast [Stoneforge Mystic] vs Energy: no point estimate; `White creature` family
  range 0–100% across Death & Taxes (0/3) and Energy (1/1), refusal chip `pooled cell below the
  engine display gate (n_eff 2 < 30)`, plus `◦mostly pre-regime (0% current)`.

Scoped verification after the final seam: `109 passed` across
`tests/test_matchup_superarchetype.py`, `tests/test_refresh_best_call_ranking.py`, and
`tests/test_matchup_multi_split.py`.

Full verification: `PYTHONPATH=. .venv/bin/pytest -q` -> **3,519 passed, 1 skipped in 104.29s**.
(`.venv/bin/pytest -q` without the explicit repo-root path is not a valid invocation in this
isolated checkout because an installed top-level `tests` package shadows the repo's namespace at
collection time.)
