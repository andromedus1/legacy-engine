---
id: feature-multi-split-matrix
kind: feature
stage: done
tags: [advisory]
parent: null
depends_on: []
release_binding: v0.4.0
gate_origin: null
created: 2026-07-13
updated: 2026-08-01
---

# Multi-split advisory matrix — one pass across all camp splits

## Completion summary (all three stories at review/done)

- `feature-multi-split-matrix-core-tally` (done, PR #65): `split_variants` seam +
  `camp_parent` provenance in `compute_match_results`; pooling kernel
  (`_pool_opponent_tallies`), `_multi_hierarchy_inputs`, `MultiSplitMatrix` +
  `build_multi_split_matrix` with the uniform parity suite.
- `feature-multi-split-matrix-adaptive-window` (done, PR #70): `build_multi_split_adaptive`
  (one scan per distinct horizon, pooled cross-era priors), `era_horizons(camp_parent=...)`,
  `build_multi_split_inputs` (window.py) + `staged_split_parents` — adaptive parity proven
  field-for-field incl. `cell_windows`/`horizon_meta`/cross-era labels, ~26x on the probe.
- `feature-multi-split-matrix-best-call-onepass` (review, branch `impl/multi-split-onepass`):
  the consumer arc. Best-call page camp sweep = ONE adaptive multi-split pass + one uniform
  multi-split matrix per distinct Nadu-rule fallback date; live-DB old-vs-new diff:
  115 camp rows / 8,855 opponent cells field-for-field identical, arch rows byte-identical;
  camp sweep 326.3s -> 15.5s (~21x; 24.4x matrices-only). Cross-camp P(best) restored via
  one shared-field `rank_decks` MC (fixed seed) over camps + unsplit archetypes on the
  page-used cells, candidacy-gated at the display-suppression coverage threshold; camp
  table gains the labeled column. Docs + knowledge index rolled; hermetic script-level
  parity/Nadu/determinism tests with a mutation-proven diff.

The design's parity guarantee held end-to-end: the one-pass build changed NO existing
number anywhere in the arc.

**Camp-level ranking needs a multi-split matrix.** Ranking all camps (2026-07-13 meta-view
session) required 29 separate `build_advisory_inputs(split_variant=parent)` calls — one split
matrix per parent. Consequences: P(best) is incomparable across per-parent matrices (had to
omit it in the camp view of `decks/best-deck-best-call-ranking.html`), and the sweep costs ~29
matrix builds (~4-5 min). Support `split_variant` accepting multiple/all parents in one matrix
so every camp shares one shared-field MC ranking with a valid cross-camp P(best).

## Design decisions
<!-- --only-questions pass 2026-07-31: no user-facing ambiguities — direction is pinned by
the absorbed member texts, parent-epic decisions, and existing project patterns. Full
feature-design may proceed without an interactive round. -->

Resolved with judgment during the 2026-07-31 full design pass (autopilot delegation; rationale
inline). Cross-model advisory review skipped per orchestrator instruction (non-blocking).

1. **Matrix keying — rectangular, not square: subjects × parent-level opponents.** The
   multi-split matrix's subject axis is *every split parent's camps* (force-included, single-split
   semantics: a split parent's own pooled row is replaced by its camp rows) *plus every unsplit
   archetype* that clears `min_row_share`. The opponent axis is **parent-level labels only** (the
   plain matrix's row-inclusion set). Entities stay plain label strings (`"P [camp]"` per the
   `effective_label` convention), with an explicit `camp_parent: dict[label, parent]` map carried
   alongside — NOT `(archetype, camp|None)` tuple keys, which would fork every cell-key consumer.
   Unsplit archetypes coexist as their own subject rows, which is exactly how the best-call page
   already merges unsplit parents into the camp view.
2. **Camp-vs-own-parent cells are absent (documented), matching per-parent behavior.** In a
   per-parent split matrix the parent label doesn't exist, so `(camp, own_parent)` has no cell and
   the best-call page already emits an unmeasured row for it; the MC rankers impute it as no-data.
   A sibling-pooled `(camp, own_parent)` cell (camp's record vs its sibling camps) was considered
   and **declined for v1**: it omits the own-camp mirror slice of the parent share (biased low/high
   by construction) and would be new methodology inside a batching feature. Logged as a revisit
   candidate for feature-agency-page-methodology.
3. **Shrinkage: the one-pass build changes NO number — it is a pure batching/caching win, and the
   parity test proves it.** Argument: (a) relabeling parent Q's decks only affects pairings that
   touch Q, so a camp-of-P row's tallies vs any opponent are unchanged by other parents' splits;
   (b) every deck of a split parent maps to exactly one camp (`NULL variant → "unlabeled"`), so
   pooling camp-of-Q opponent tallies reproduces the per-parent build's `(camp_P, Q)` tally
   exactly (partition property); (c) marginals are opponent-label-independent, and the parent
   marginal reconstructed as the sum over camp siblings is already asserted exact in
   `_camp_hierarchy_inputs`'s docstring + LCO `>= 0` assertions; (d) the row-inclusion denominator
   `2*(decisive+mirror)` is invariant under relabeling (a cross-camp match moves from mirror to
   decisive but the sum is fixed). Therefore camp cells (wins, n, p_raw, p_shrunk, CI, tier,
   prior_mean, prior_source, cell window) are field-for-field identical to
   `build_[adaptive_]matrix(split_variant=parent)`, and unsplit-subject cells are identical to the
   plain matrix. `_cell_prior` is reused **unchanged** — only its precomputed inputs generalize.
4. **Cell-count economics: store camp×parent cells only; no camp×camp cross-matrix.** Cross-camp
   P(best) comparability requires exactly (i) all candidates in ONE matrix and (ii) one shared
   sampled field — i.e. camp-subject rows vs one parent-level opponent axis fed to `rank_decks`'s
   shared-field MC. Full camp×camp cells are mostly speculative (n<8) and serve no ranking
   consumer; sibling-camp tallies are still used *internally* (LCO priors, parent reconstruction)
   from the maximal camp×camp `MatchResults` tally, which is the single internal representation.
   ~190 subjects × ~95 opponents ≈ 18k cells — no economics problem.
5. **API: new entry points, NOT a `multi_split=True` flag on `build_advisory_inputs`.** The
   return shape genuinely differs (rectangular `MultiSplitMatrix` + camp metadata), and none of
   the ~15 advisory-window-resolution-block call sites want it — a flag that changes the return
   type on the spine violates the pattern's byte-identical-default contract in spirit and forces
   defensive typing on every site. Ship `build_multi_split_matrix` / `build_multi_split_adaptive`
   (matchup.py) + `build_multi_split_inputs` (window.py, same `WindowResolution` mode dispatch so
   it composes with `resolve_advisory_window`). `compute_match_results` gains an additive
   `split_variants` param (opt-in overlay; `None` default byte-identical; existing goldens
   enforce). Zero edits to cli.py or any existing call site.
6. **Perf (probed 2026-07-31, data/legacy.duckdb, 81,161 join rows):** one
   `compute_match_results` scan ≈ 0.22s (0.12s SQL join+fetchall + ~0.10s Python accumulation);
   `build_adaptive_matrix(min_row_share=0.001)` ≈ 8.0s (33 distinct horizons → ~36 scans incl.
   cross-era pre-boundary scans); a split build costs the same as a plain one (7.95s vs 8.01s) —
   label count is irrelevant, scan count × per-scan cost is everything. The 29-30× camp sweep ≈
   30 × (8s adaptive + per-parent fallback `build_matrix` calls) ≈ 4-5 min. One maximal scan
   costs the same as one single-split scan (same rows), so the multi-split sweep ≈ one adaptive
   build (~8-10s) + one uniform multi-split build per distinct ban-fallback date (~0.7s each) ≈
   **~12s, a ~25× reduction**, with pooling over tally dicts (thousands of keys) as noise.
7. **`era_horizons` learns camps via an explicit `camp_parent` map, not prefix parsing.** The
   staged registry contains both `Painter` and `Blue Painter`; prefix-stripping multiple parents
   is fragile in principle. `compute_match_results` records `camp_parent` at relabel time (the
   SSOT — the labeler knows the parent), and it threads through to `era_horizons` as an additive
   param. Existing single-split prefix path (`_parent_label`/`_base_archetype`) is untouched.
8. **Downstream interface (feature-agency-page-methodology):** cheap re-ranking = build the
   matrix once, re-run `rank_decks` (seconds) over `MultiSplitMatrix.ranking_view()` with variant
   gating at the consumer; per-cell precision for the lean view = pooled `MatchupCell`s carry
   n/CI/tier/prior_source unchanged; path-to-grounding reads per-cell n directly.

## Architectural choice

**Chosen: maximal camp×camp tally + opponent-side pooling behind new `build_multi_split_*` entry
points.** One `compute_match_results(split_variants=<all staged parents>)` scan per distinct
window produces the maximal-granularity tally (every split parent's decks camp-labeled on BOTH
sides). The matrix layer then pools the opponent side back to parent level (`(subject,
parent_opponent)` cells), reconstructs parent marginals/LCO reference cells from camp sums, and
feeds the **unchanged** `_cell_prior` chain — so every camp cell is field-for-field identical to
the per-parent `split_variant` build, proven by a parity test, while all camps coexist in one
matrix for a shared-field MC with valid cross-camp P(best). Adaptive windowing reuses the exact
`build_adaptive_matrix` skeleton (one scan per distinct horizon; per-window hierarchy buckets;
lazily-cached cross-era pre-boundary scans), with camp horizons resolved exact → parent →
ban-only via the explicit `camp_parent` map.

**Rejected — Option B: square camp×camp matrix behind `multi_split=True` on
`build_advisory_inputs`/`build_matrix`.** Splitting both sides *as the output* yields a matrix
that is mostly speculative cells (camp×camp n is tiny), does NOT reproduce per-parent numbers
(per-parent cells are camp-vs-pooled-opponent), still forces every consumer to pool, and changes
the spine's return shape behind a flag — the worst fit with the opt-in-analytics-overlay and
advisory-window-resolution-block patterns.

**Rejected — Option C: keep the per-parent API and add a scan cache** (memoize the rounds
join/fetch across the 30 builds). Saves only the SQL half (~0.12s of ~0.22s per scan), still
runs ~30× Python accumulations and 30 hierarchy passes, and — decisively — still produces 30
separate matrices whose P(best) values remain incomparable. Solves neither stated problem.

## Implementation Units

### Unit 1: `split_variants` multi-label seam + `camp_parent` provenance

**File**: `src/legacy_engine/analytics/match_results.py`
**Story**: `feature-multi-split-matrix-core-tally`

```python
@dataclass
class MatchResults:
    ...existing fields...
    mirror_n: dict[str, int] = field(default_factory=dict)
    camp_parent: dict[str, str] = field(default_factory=dict)  # NEW additive: camp label -> parent

def compute_match_results(
    con: duckdb.DuckDBPyConnection, *, provenance: str | None = None,
    since: str | None = None, until: str | None = None,
    split_variant: str | None = None,
    split_variants: Collection[str] | None = None,   # NEW, opt-in; ValueError if both given
) -> MatchResults: ...
```

**Implementation Notes**:
- Normalize internally: `split_set = frozenset((split_variant,)) if split_variant else frozenset(split_variants or ())`;
  raise `ValueError("pass split_variant or split_variants, not both")` when both are non-None.
- Relabel via membership test (`archetype in split_set`), same `f"{archetype} [{variant or 'unlabeled'}]"`
  convention; record `camp_parent[label] = archetype` at relabel time (populated for single-split too —
  additive, no existing consumer reads it). `effective_label` (public single-split fn) untouched.
- The accumulator loop is otherwise byte-identical; the `split_set == frozenset()` path must be the
  literal identity path (opt-in-analytics-overlay).

**Acceptance Criteria**:
- [ ] `compute_match_results(con)` output equals pre-change behavior (existing test_match_results.py +
      report-matchups body goldens stay green, untouched).
- [ ] Singleton equivalence: `compute_match_results(con, split_variants=["Doomsday"])` equals
      `compute_match_results(con, split_variant="Doomsday")` on `matchups`, `archetypes`, `coverage`,
      `mirror_n`; plus `camp_parent == {"Doomsday [Murktide]": "Doomsday", ...}`.
- [ ] Two-parent scan: both parents' decks camp-labeled simultaneously; a cross-parent camp pairing
      tallies as a directed camp×camp cell; a same-camp pairing is a camp-level mirror.
- [ ] `ValueError` when both `split_variant` and `split_variants` are passed.

---

### Unit 2: pooling + multi-parent hierarchy + `MultiSplitMatrix` + uniform builder  *(trickiest kernel)*

**File**: `src/legacy_engine/analytics/matchup.py`
**Story**: `feature-multi-split-matrix-core-tally`

```python
def _pool_opponent_tallies(
    mr: "MatchResults", camp_parent: "Mapping[str, str]",
) -> dict[tuple[str, str], tuple[int, int]]:
    """(subject_label, parent_opponent) -> (wins, n), pooling camp-of-Q opponent labels to Q.
    Pairs where the opponent pools to the subject's own parent are EXCLUDED (decision 2).
    Pure; exact by the camp-partition property."""

def _multi_hierarchy_inputs(
    mr: "MatchResults",
    subjects: list[str],
    opponents: list[str],
    camp_parent: "Mapping[str, str]",
    pooled: dict[tuple[str, str], tuple[int, int]],
) -> tuple[dict[str, float], dict[tuple[str, str], tuple[int, int]], dict[str, str]]:
    """(marginals, parent_cells_lco, camp_of) generalizing _camp_hierarchy_inputs to many parents.
    marginals: subjects + every split parent (reconstructed: sum of camp siblings' wins/losses).
    parent_cells_lco: (camp, parent_opponent) -> (lco_wins, lco_n) = pooled parent totals minus the
    camp's own pooled tally; asserted >= 0 (never clamped). camp_of: subject -> parent-or-self.
    Consumed by the UNCHANGED _cell_prior."""

@dataclass
class MultiSplitMatrix:
    cells: dict[tuple[str, str], MatchupCell]  # (subject, parent_opponent) + (subject, subject) mirrors
    subjects: list[str]        # sorted: all observed camps (force-included) + included unsplit archetypes
    opponents: list[str]       # sorted: plain-matrix row-inclusion set (parent-level labels)
    camp_parent: dict[str, str]
    parents: list[str]         # split parents actually observed in the corpus
    provenance: str | None
    total_matches: int         # decisive count at CAMP granularity (documented; differs from plain)
    caveat: str

    def ranking_view(self) -> MatchupMatrix:
        """Get-based MatchupMatrix view for the shared-field MC rankers (rank_decks /
        positioning_score, which only use .cells.get + field iteration). NOT square:
        archetypes = sorted(subjects | opponents). Never feed to square-matrix consumers
        (best_deck_vs_best_call, matrix printers)."""

def build_multi_split_matrix(
    con, *, parents: "Collection[str]", provenance: str | None = None,
    min_row_share: float = 0.02, since: str | None = None, until: str | None = None,
) -> MultiSplitMatrix: ...
```

**Implementation Notes**:
- One `compute_match_results(..., split_variants=parents)` scan; subjects/opponents inclusion per
  decision 1 (denominator `2*(decisive+mirror)` is relabel-invariant, so inclusion matches the
  plain matrix exactly; parents included as opponents iff their reconstructed record clears the floor).
- Every `(subject, opponent)` ordered pair gets a cell (n=0 emitted for unobserved) EXCEPT
  `opponent == camp_parent[subject]` (absent, decision 2). `(s, s)` mirror cells from `mr.mirror_n`
  for every subject (camps included; camp labels are not opponents, that's fine — cells is a dict).
- Priors: `_cell_prior(subject, opponent, ...)` verbatim over `_multi_hierarchy_inputs` outputs —
  same `"marginal"` / `"parent cell (leave-camp-out)"` prior_source labels.
- Parents absent from the corpus are dropped gracefully (no camps observed → no rows; mirrors the
  single-split no-op precedent).

**Acceptance Criteria**:
- [ ] **Parity (uniform, camp rows)**: on a hermetic 2-parent fixture, for each parent P, every
      `(camp_of_P, opponent)` cell equals `build_matrix(con, split_variant=P, ...)`'s cell
      field-for-field (wins, n, p_raw, p_shrunk, ci_low, ci_high, tier, display, prior_mean,
      prior_source), for every opponent in the shared key set; camp mirror cells equal too.
- [ ] **Parity (uniform, unsplit rows)**: every `(unsplit_subject, parent_opponent)` cell equals the
      plain `build_matrix(con)` cell field-for-field.
- [ ] `(camp, own_parent)` key absent from `cells`.
- [ ] Singleton degenerate case: `build_multi_split_matrix(parents=[P])` camp cells == the
      `split_variant=P` build's camp cells over the shared key set.
- [ ] `ranking_view()` returns a `MatchupMatrix` whose `.cells` is the same dict and that
      `rank_decks` consumes without error on the fixture.

---

### Unit 3: adaptive multi-split builder (era windows + cross-era priors, pooled)  *(trickiest unit — highest unknowns)*

**Files**: `src/legacy_engine/analytics/matchup.py`, `src/legacy_engine/analytics/eras/consume.py`
**Story**: `feature-multi-split-matrix-adaptive-window`

```python
# eras/consume.py — additive param; prefix path untouched
def era_horizons(
    con, archetypes: list[str], *, provenance: str | None = None,
    split_variant: str | None = None,
    camp_parent: "Mapping[str, str] | None" = None,   # NEW: explicit camp->parent (wins over prefix)
    affect_threshold: float = 0.25,
) -> tuple[dict[str, EraHorizon], tuple[str, ...]]: ...

# matchup.py
@dataclass
class AdaptiveMultiSplitMatrix:
    multi: MultiSplitMatrix
    valid_since: dict[str, str | None]                 # subjects + opponents
    cell_windows: dict[tuple[str, str], str | None]    # window actually used per emitted cell
    horizon_meta: "dict[str, EraHorizon]" = field(default_factory=dict)
    audit_preamble: tuple[str, ...] = ()

def build_multi_split_adaptive(
    con, *, parents: "Collection[str]", provenance: str | None = None,
    min_row_share: float = 0.02, affect_threshold: float = 0.25,
    horizons: dict[str, str | None] | None = None,     # testing/pinning hook, as in build_adaptive_matrix
) -> AdaptiveMultiSplitMatrix: ...
```

**Implementation Notes**:
- Mirror `build_adaptive_matrix`'s skeleton exactly: full maximal scan → inclusion → horizons for
  subjects ∪ opponents (camps resolve exact `entity_eras` row → parent row → ban-only via
  `camp_parent`; opponent side uses the PARENT-level horizon, matching per-parent builds) → one
  maximal scan per distinct `valid_since` → per-window `_pool_opponent_tallies` +
  `_multi_hierarchy_inputs` buckets → cells at `s_ab = max(valid_since[subj], valid_since[opp])` →
  cross-era prior override for thin (n<100) era-sourced cells via pooled pre-boundary scans
  (`pre_mr_cache`/`pre_hierarchy_cache` keyed by boundary date, one extra scan per distinct
  boundary). `_era_sourced_boundary` logic verbatim.
- Distinct-horizon count grows only by camps with their own era rows (most inherit parents);
  measured plain baseline is 33 — expect ≈33-40 scans, ~8-10s total.

**Acceptance Criteria**:
- [ ] **Parity (adaptive, camp rows)**: on a hermetic fixture with `entity_eras` rows (exact camp
      row + parent-inherited camp + ban-only entity, covering all three horizon sources), every
      camp cell equals `build_adaptive_matrix(con, split_variant=P)`'s cell field-for-field AND
      `cell_windows[(camp, opp)]` matches; `horizon_meta[camp].source/since` match.
- [ ] **Parity (adaptive, unsplit rows)**: unsplit-subject cells equal plain
      `build_adaptive_matrix(con)` cells vs parent-level opponents, incl. cross-era-prior cells
      (`prior_source` label `"pre-disturbance value (window < ...)"` identical).
- [ ] Explicit `horizons=` override bypasses `era_horizons` and pins windows (deterministic test hook).
- [ ] `era_horizons(camp_parent=...)` resolves a camp with no own row to its parent's horizon
      without prefix parsing; existing `split_variant` prefix behavior untouched (existing
      tests/analytics/eras/test_consume.py green).

---

### Unit 4: window.py entry point + registry helper

**Files**: `src/legacy_engine/advisory/window.py`, `src/legacy_engine/archetype/discovered.py`
**Story**: `feature-multi-split-matrix-adaptive-window`

```python
# archetype/discovered.py
def staged_split_parents(path: "Path | str | None" = None) -> list[str]:
    """Sorted unique parents of status=='candidate' splits in the discovery registry
    (DISCOVERED_VARIANTS_PATH default); [] when the registry is missing/empty."""

# advisory/window.py
@dataclass(frozen=True)
class MultiSplitAdvisoryInputs:
    multi: object                  # analytics.matchup.MultiSplitMatrix
    adaptive: object | None        # AdaptiveMultiSplitMatrix when win.mode == "adaptive", else None
    field_since: str | None
    field_until: str | None
    audit: tuple[str, ...]

def build_multi_split_inputs(
    con: duckdb.DuckDBPyConnection, win: WindowResolution, *,
    parents: "Collection[str]", provenance: str | None = None, min_row_share: float = 0.02,
) -> MultiSplitAdvisoryInputs: ...
```

**Implementation Notes**:
- Same mode dispatch as `build_advisory_inputs`: adaptive → `build_multi_split_adaptive` +
  `resolve_field_era` + `_adaptive_audit(horizon_meta, audit_preamble)` + field line + one
  `// multi-split: N parents, M camp rows` line; uniform/full → `build_multi_split_matrix` over
  `win.since/until`. Lazy imports inside the function (module-load convention).
- `build_advisory_inputs` and all ~15 spine call sites: **zero edits** (enforced by the
  byte-identical acceptance below).

**Acceptance Criteria**:
- [ ] Adaptive-mode inputs carry audit lines naming disturbed entities + the field line + the
      multi-split line; uniform/full modes return the windowed matrix with empty-or-window audit,
      matching `build_advisory_inputs` conventions.
- [ ] `git diff` for this feature contains no hunk in `cli.py` and no change to
      `build_advisory_inputs`; existing freshness-stripped CLI body goldens pass untouched.
- [ ] `staged_split_parents()` returns the registry parents sorted (30 on the live registry);
      [] on a missing file.

---

### Unit 5: best-call page one-pass migration + cross-camp P(best)

**Files**: `scripts/refresh_best_call_ranking.py`, `scripts/best_call_ranking_template.html`
**Story**: `feature-multi-split-matrix-best-call-onepass`

**Implementation Notes**:
- Replace the per-parent camp loop (30 × (`build_adaptive_matrix(split_variant=p)` + per-date
  fallback `build_matrix(split_variant=p)`)) with: parents = `staged_split_parents()`; ONE
  `build_multi_split_adaptive(con, parents=parents, min_row_share=...)`; fallback windows = the
  SAME per-pair `max(subj_ban, opp_ban)` Nadu-rule dates, but built once per distinct date as
  `build_multi_split_matrix(parents=parents, since=d)` serving all parents (camp labels inherit
  the parent's ban date exactly as today).
- `make_cells` unchanged in logic — camp rows now read from the one multi-split cell dict; the
  `(camp, own_parent)` pair stays the unmeasured-row path it already handles.
- **Cross-camp shared-field ranking (the restored number):** `rank_decks(msm.ranking_view(),
  build_custom_field(parent_shares, counts=parent_window_counts), candidates=[*camp_labels,
  *unsplit_field_archetypes], seed=<fixed>)` — one shared Dirichlet field draw across ALL camps →
  per-row `p_best` + `s_quantile` (+ `data_coverage`) added to the camp blob rows; template gains
  a P(best) column in the camp table with the coverage caveat (suppress display below the
  existing `_PBEST_SUPPRESS_COVERAGE` convention; label full-field S per `coverage_caveated`).
- Docs rolled forward in the same stride: `docs/analysis/best-call-ranking.md` (one-pass method +
  P(best) column + new timing), `docs/ARCHITECTURE.md` matchup.py/window.py rows (multi-split
  entry points). Then `/knowledge-index` regeneration.

**Acceptance Criteria**:
- [ ] One-off live-DB verification during implementation: old-path vs new-path camp cell dicts are
      identical (`p`, `raw`, `n`, `window`, `tier`, `measured` per opponent) for every camp row —
      logged in the story body, not a committed test (hermetic tests carry the guarantee).
- [ ] Camp sweep wall-time drops from ~4-5 min to under ~30s on the live DB (timing echoed by the
      script).
- [ ] Camp table shows P(best) + risk-quantile from ONE shared-field MC (fixed seed, reproducible),
      coverage-suppressed per the existing honesty gates; archetype-level view byte-unchanged.
- [ ] Runbook + ARCHITECTURE updated; `// multi-split` provenance line in the page's audit header.

## Implementation Order

1. **Unit 1** (`split_variants` seam) — thin substrate everything depends on; ~30 lines.
2. **Unit 2** (pooling + multi hierarchy + uniform builder + the parity-test scaffold) — the
   trickiest *kernel* (pooling exactness, LCO reconstruction) lands here with its uniform parity
   test; if pooling parity fails here, the architecture is re-examined before any adaptive work.
3. **Unit 3** (adaptive multi-split) — the trickiest *unit* overall (windows × hierarchy ×
   cross-era interactions); sequenced as early as its substrate allows, reusing Unit 2's proven
   kernel + fixture.
4. **Unit 4** (window.py entry point + registry helper) — thin composition layer.
5. **Unit 5** (best-call page migration + P(best) + docs) — consumer last, validating the whole
   arc against the live DB.

## Testing

Hermetic only — NEVER the default DB (`--db`/`:memory:` per the file-backed-cli-test-db-builder
pattern; existing conventions in `tests/test_matchup_split_variant.py` /
`tests/test_matchup_hierarchy.py`: `store.connect(":memory:")` + `parse_cache_item` + direct
`UPDATE decks SET archetype/variant`).

### Unit tests: `tests/test_match_results_multi_split.py`
- singleton equivalence vs `split_variant`; two-parent simultaneous relabel; camp_parent contents;
  ValueError on both params; `split_variants=None` identity (existing suite untouched is the
  primary gate).

### Unit tests: `tests/test_matchup_multi_split.py`
- **The parity test (headline)** — fixture: 2 split parents (2 camps + unlabeled residue each),
  3 plain archetypes, matches spanning two windows, cross-parent camp pairings, same-parent
  cross-camp pairings, camp mirrors. Assertions per Units 2-3 acceptance: camp rows vs
  `build_[adaptive_]matrix(split_variant=P)` per parent; unsplit rows vs the plain builds;
  `cell_windows`/`prior_source`/mirror parity; `(camp, own_parent)` absence.
- Pure-kernel tests: `_pool_opponent_tallies` exactness on hand-built `MatchResults` (no DB);
  `_multi_hierarchy_inputs` LCO = pooled-parent-minus-camp with the ≥0 assertion firing on a
  corrupted non-partition input.
- Adaptive horizon-source coverage: exact camp era row / parent-inherited / ban-only fallback;
  explicit `horizons=` pinning; cross-era prior parity on a thin post-boundary camp cell.

### Unit tests: `tests/test_advisory_window_multi_split.py`
- `build_multi_split_inputs` mode dispatch (adaptive/uniform/full) + audit lines;
  `ranking_view()` + `rank_decks` end-to-end on the fixture: P(best) sums to ~1 across candidates,
  camps and unsplit archetypes ranked in one call, deterministic under seed.
- `staged_split_parents` on a tmp registry file + missing-file default.

### Integration seams
- Byte-identical default: full existing suite green untouched (goldens included) — the
  opt-in-analytics-overlay enforcement.
- `rank_decks`/`positioning_score` over `ranking_view()` — verify no use of `.archetypes`
  squareness (covered by the end-to-end test above).
- Unit 5's live-DB old-vs-new blob diff is a one-off implementation verification (documented in
  the story), not a committed test.

## Risks

- **Pooling-exactness assumption (riskiest)**: the whole parity claim rests on camp labels
  partitioning a split parent's decks (NULL → "unlabeled") and on scan determinism across the
  maximal and per-parent scans (dup-CTE `ANY_VALUE` rows are dropped pre-use, so no
  nondeterminism is expected). — **Fallback**: the parity test catches any violation
  field-for-field before anything ships; if a genuine mismatch surfaces, keep the per-parent path
  as the shipped truth and demote multi-split to ranking-only until reconciled.
- **Camp-vs-own-parent imputation hole**: cross-camp P(best) imputes each camp's cell vs its own
  parent's field share (no cell by design), slightly distorting camps of large parents. —
  **Fallback**: `data_coverage` already counts the hole and the page's coverage suppression
  applies; the sibling-pooled-cell alternative is logged (decision 2) for
  feature-agency-page-methodology to promote if the distortion matters in practice.
- **`MultiSplitMatrix` misuse by square-matrix consumers**: someone feeds `ranking_view()` to
  `best_deck_vs_best_call` or a printer that iterates `archetypes × archetypes`. — **Fallback**:
  own dataclass (not a `MatchupMatrix` subclass), loud docstrings on `ranking_view()`; printers
  keep requiring square matrices.
- **Distinct-horizon growth**: camps with their own era rows add scan windows (plain baseline 33).
  — **Fallback**: bounded by distinct `entity_eras` dates; if the build creeps past ~15s, dedupe
  scan windows by date once (they already share `mr_by_since`), or drop camp-exact horizons to
  parent-inherited behind a flag.
- **Script-migration drift (Nadu rule)**: the fallback-window set must stay per-pair
  `max(subj_ban, opp_ban)`; a subtle regression here re-opens the banned-era inflation hole. —
  **Fallback**: the one-off old-vs-new blob diff in Unit 5 acceptance is exactly this check;
  the runbook documents the invariant.
