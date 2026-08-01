---
id: feature-camp-incremental-assignment
kind: feature
stage: review
tags: [analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-28
updated: 2026-07-31
---

# Incremental camp assignment for post-staging decks


Discovery FAIL keeps the frozen staged split (member_keys pinned at the last PASSing
run), so new decks stay camp-unlabeled — 11/12 fresh Cephalid decks had no camp after
the 2026-07-28 refresh because its re-run failed gate-A (stability 0.831). Add an
incremental assignment path for post-staging decks: nearest-camp assignment against the
staged signatures, or membership extension, so a growing corpus doesn't silently
degrade camp coverage between successful discovery runs. Keep provenance honest
(incrementally-assigned decks labeled distinctly from clustered membership).

## Design decisions
<!-- captured 2026-07-31 via feature-design --only-questions; treat as fixed inputs -->
- **Persistence**: persist incremental assignments to the DB alongside staged labels with
  an `assigned_by: incremental` provenance flag — consumers see full coverage, provenance
  is queryable, and the next PASSing discovery run supersedes them.

## Architectural choice
<!-- feature-design, 2026-07-31 -->

Code mapping confirmed: no representation of a camp is currently persisted beyond
`member_keys` (exact `(tournament_id, deck_idx)` cluster membership) and `signature_cards`
(top-5 over-represented card *names*, deltas stripped). The clustering embedding
(`FeatureMatrix.X`, TF-IDF + L2-normalized, further reduced by `reduce_dims` for HDBSCAN)
lives only transiently inside one `discover run` invocation and is discarded. **Persisting
some numeric representation is therefore mandatory** — there is nothing today a fresh deck
could be compared against.

Three options for what to persist and how to compare:

1. **(Chosen) Frozen flex vocabulary + per-camp centroid, raw L2-normalized counts (no
   TF-IDF/SVD).** At `discover run` time, stamp the split's flex-band column list
   (`FeatureMatrix.cards`) onto `DiscoveredSplit`/`DiscoveredSplitRecord` as `flex_cards`,
   and stamp each camp's mean L2-normalized raw-count vector over that vocabulary onto
   `Camp`/`DiscoveredCamp` as `centroid`. A candidate deck is projected into the *same*
   `flex_cards` columns via the identical L2-normalization function, then assigned to the
   camp with highest cosine similarity, gated by an honest minimum-similarity floor.
   Cheap (dot products over ~20-35 dims), deterministic, requires no re-reads of member
   decks at assignment time, and both sides of the comparison go through one shared
   function by construction — trivially consistent. **Trade-off (accepted, documented in
   Risks):** this is *not* bit-identical to the TF-IDF+SVD space HDBSCAN actually
   clustered on — it drops IDF reweighting and the SVD reduction. At flex-band scale
   (~20-35 dims, already small per the subarchetype-discovery brief) this is a reasonable
   simplification; validated by a reconstruction-accuracy test (Testing, Unit 1) that
   checks nearest-centroid recovers each split's OWN member decks' real camp labels at
   high agreement.
2. **Persist a medoid deck-key instead of a synthetic centroid vector.** Store a real
   `(tournament_id, deck_idx)` per camp (the member closest to its own centroid) and
   re-read that one deck's `deck_cards` row at assignment time to build the comparison
   vector on demand. Smaller persisted footprint (a key, not a float list) and reuses the
   existing "reference a real deck by key" idiom (`member_keys`). Rejected: still requires
   computing a centroid internally at discovery time to *pick* the medoid (no compute
   savings), is more sensitive to a single atypical exemplar than an averaged centroid, and
   adds a DB read per candidate deck at assignment time for no accuracy benefit.
3. **Recompute the full TF-IDF+SVD embedding fresh at every `discover apply`, over
   `member_keys` pooled with candidate decks.** Maximum fidelity to "the same
   representation space discovery used." Rejected: expensive (refits `TfidfTransformer`
   and `TruncatedSVD` on every apply, over potentially thousands of member decks), and
   still not truly reproducible without *also* persisting the fitted `idf_` vector and SVD
   `components_` matrix (heavier state than a single mean vector, for a fidelity gain the
   brief itself says matters far less at ~20-35 dims than at wide feature spaces).

Provenance persistence: a **new side table** `variant_incremental_assignments`, not a new
`decks` column. `decks` has exactly 6 columns (`tournament_id, deck_idx, player, result,
archetype, variant`) inserted via one positional `INSERT INTO decks VALUES (?, ?, ?, ?, ?,
?)` call site in `ingestion/store.py`, and the SAME positional-tuple idiom is reproduced in
every hermetic test fixture across the test suite (`tests/test_discover_cli.py`,
`tests/archetype/test_discovered.py`, etc.). Adding a 7th `decks` column would force every
one of those call sites to grow a value — a wide, unrelated blast radius for a feature
that is purely about *provenance of a label*, not the label itself. A side table keyed on
`(tournament_id, deck_idx)` is additive, touches zero existing call sites, and is naturally
rebuildable (drop the table, re-run `discover apply <parent>` — mirrors the
JSON-SSOT-rebuildable-duckdb-table pattern, with `discovered.json` + the current
`decks`/`deck_cards` state as the reconstruction inputs, the same shape `entity_eras`
already uses for a feature-owned derived table).

`decks.variant` itself is read by every downstream consumer (`match_results.py`'s
`effective_label`, `metashare.py`'s `CASE WHEN d.variant IS NOT NULL`, `eras/series.py`,
`generation/consensus.py`'s `card_frequencies`) as an **opaque nullable string** — nothing
branches on how the string got there. Incremental assignment writes `decks.variant` exactly
like `apply_split` already does; every downstream consumer is untouched by construction.

## Implementation Units

### Unit 1: Flex-vector projection + nearest-camp decision (pure, DB-free — trickiest unit)

**File**: `src/legacy_engine/analytics/discovery.py`

```python
def project_flex_vector(counts: dict[str, int], flex_cards: list[str]) -> "np.ndarray":
    """Project raw mainboard counts onto the frozen ``flex_cards`` vocabulary, L2-normalized.

    Missing cards count as 0. Returns an all-zero vector (never raises, never NaN) when the
    deck shares no card with ``flex_cards`` — ``nearest_camp`` treats an all-zero vector as
    "no similarity to anything", never a fabricated match.
    """


def camp_centroid(member_counts: list[dict[str, int]], flex_cards: list[str]) -> list[float]:
    """Mean of L2-normalized per-deck flex vectors for a camp's members, renormalized.

    Uses the SAME ``project_flex_vector`` a candidate deck is projected through — the
    invariant nearest-camp assignment depends on: centroid and candidate always live in
    the identical representation by construction, never two independently-derived spaces.
    Empty ``member_counts`` -> a zero vector (degenerate camp; never assigned to by
    ``nearest_camp`` since cosine similarity against a zero vector is 0.0).
    """


@dataclass(frozen=True)
class NearestCampResult:
    """Outcome of one candidate deck's nearest-camp lookup. ``camp`` is ``None`` when the
    honest-degrade floor isn't cleared — ``reason`` names why, always."""
    camp: str | None
    best_similarity: float
    runner_up: str | None       # second-nearest camp name; diagnostic only, never gates
    reason: str


DEFAULT_MIN_SIMILARITY = 0.35
# Uncalibrated initial default (see Risks) — cosine similarity floor on raw L2-normalized
# flex-band vectors. Unlike Gate C's _TEMPORAL_GAP_DAYS this has no calibration fixture yet;
# CLI-tunable (`discover apply --min-similarity`) until a real-corpus pass calibrates it.


def nearest_camp(
    counts: dict[str, int],
    flex_cards: list[str],
    centroids: dict[str, list[float]],
    *,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> NearestCampResult:
    """Assign ``counts`` to the nearest camp centroid by cosine similarity in the frozen
    flex-band space, or honestly decline below ``min_similarity``.

    ``flex_cards``/``centroids`` empty (pre-incremental-assignment staged record) -> decline
    with a named reason, nothing fabricated. Both vectors are pre-L2-normalized (project_flex_vector
    / camp_centroid), so a plain dot product IS the cosine similarity — no renormalization here.
    """
```

Also extend the existing dataclasses additively (mirrors the Gate C precedent — new
`None`/empty-default fields, every existing hand-built `Camp(...)`/`DiscoveredSplit(...)`
call in `tests/analytics/test_discovery.py` stays green untouched):

```python
@dataclass(frozen=True)
class Camp:
    ...
    centroid: list[float] | None = None   # mean L2-normalized flex vector (see camp_centroid)

@dataclass(frozen=True)
class DiscoveredSplit:
    ...
    flex_cards: list[str] = dataclasses.field(default_factory=list)  # frozen FeatureMatrix.cards
```

Wire into `cluster_and_validate` (discovery.py:526-537, the existing Gate C enrichment
loop) — add centroid computation alongside the existing `median_date`/`pct_current` stamp:

```python
for camp in camps:
    median_date, pct_current = _camp_temporal_stats(decks_by_key, camp.member_keys, current_since)
    member_counts = [decks_by_key[k].counts for k in camp.member_keys]
    centroid = camp_centroid(member_counts, fm.cards)
    enriched_camps.append(dataclasses.replace(
        camp, median_date=median_date, pct_current=pct_current, centroid=centroid,
    ))
```

And stamp `flex_cards=fm.cards` on every `DiscoveredSplit(...)` return site (discovery.py:425
early-return, discovery.py:602 final return) — harmless even on the degenerate/failed paths
(reflects whatever the matrix actually built, never fabricated).

**Implementation Notes**:
- `np` already imported at module top; no new dependency.
- `camp_centroid`/`project_flex_vector` must be added to the module's `__all__` alongside
  `NearestCampResult`/`nearest_camp`/`DEFAULT_MIN_SIMILARITY`.
- This is the trickiest unit: if the reconstruction-accuracy test (Testing, below) shows
  the raw-count cosine space doesn't separate real camps well, revisit Architectural choice
  option 1 before building anything downstream (Units 2-6 all depend on this
  representation being trustworthy).

**Acceptance Criteria**:
- [ ] `project_flex_vector` returns a unit-norm vector when the deck has any overlapping
      flex card, an all-zero vector when it has none, and never raises/NaNs on empty counts.
- [ ] `camp_centroid` of a single-member camp equals that member's own projected vector
      (within floating-point tolerance).
- [ ] `nearest_camp` picks the higher-cosine-similarity camp when centroids clearly differ,
      declines (`camp is None`) when the best similarity is below `min_similarity`, and
      always returns a non-empty `reason`.
- [ ] `nearest_camp` declines honestly (never raises) when `flex_cards`/`centroids` are
      empty.
- [ ] Existing hand-built `Camp(...)` calls in `tests/analytics/test_discovery.py` (lines
      347, 527) and every `DiscoveredSplit(...)` construction remain valid with no changes.

---

### Unit 2: Staged-record schema — `flex_cards` + `centroid`

**File**: `src/legacy_engine/models/variant.py`

```python
class DiscoveredCamp(LegacyEngineModel):
    ...
    centroid: list[float] | None = None
    # Frozen flex-band centroid — mean L2-normalized raw-count vector over this camp's
    # member decks, in the exact representation `nearest_camp` projects candidate decks
    # into (analytics/discovery.py::project_flex_vector / camp_centroid). None on
    # pre-incremental-assignment records — nothing fabricated; incremental assignment
    # honestly declines for that parent until the next `discover run`.


class DiscoveredSplitRecord(LegacyEngineModel):
    ...
    flex_cards: list[str] = Field(default_factory=list)
    # The frozen flex-band vocabulary this split clustered on (FeatureMatrix.cards at
    # discovery time) — the fixed column space nearest-camp assignment projects new decks
    # into. Empty on pre-incremental-assignment records (honest-degrade, see DiscoveredCamp).
```

**Implementation Notes**:
- Both fields are additive with safe defaults — `extra="ignore"` + `None`/`[]` defaults mean
  every one of the 30 real staged splits in `data/variants/discovered.json` (all written
  before this feature) still loads unchanged, exactly like the existing
  `median_date`/`pct_current`/`temporal_mixing` precedent (`test_old_shape_staged_record_
  still_loads_and_lists` in `tests/test_discover_cli.py`).
- No backfill script for the 30 existing real splits in this feature (out of the pinned
  Design decisions' scope) — see Risks.

**Acceptance Criteria**:
- [ ] A `DiscoveredCamp`/`DiscoveredSplitRecord` built with no `centroid`/`flex_cards` kwargs
      validates with `centroid=None`/`flex_cards=[]`.
- [ ] A staged JSON blob shaped like the pre-this-feature real file (no `centroid`/
      `flex_cards` keys at all) still loads via `load_discovered` with no error.

---

### Unit 3: Carry centroid/flex_cards into the staged JSON

**File**: `src/legacy_engine/archetype/discovered.py` (`record_from_split`)

```python
def record_from_split(
    split: DiscoveredSplit,
    *,
    generated_from: str,
    params: dict,
) -> DiscoveredSplitRecord:
    ...
    camps = [
        DiscoveredCamp(
            name=camp.name,
            signature_cards=[...],
            n=camp.n,
            tier=camp.tier,
            member_keys=[tuple(k) for k in camp.member_keys],
            median_date=camp.median_date,
            pct_current=camp.pct_current,
            centroid=camp.centroid,          # NEW
        )
        for camp in split.camps
    ]
    return DiscoveredSplitRecord(
        parent=split.parent,
        generated_from=generated_from,
        params=params,
        camps=camps,
        stability=split.stability,
        temporal_mixing=split.temporal_mixing,
        temporal_note=split.temporal_note,
        flex_cards=split.flex_cards,          # NEW
    )
```

**Acceptance Criteria**:
- [ ] `record_from_split` on a `DiscoveredSplit` with populated `centroid`/`flex_cards`
      produces a `DiscoveredSplitRecord` that round-trips through `save_discovered` ->
      `load_discovered` with the same float values (JSON list serialization, no precision
      loss beyond normal float repr).
- [ ] `record_from_split` on a `DiscoveredSplit` built the old way (no `centroid`/
      `flex_cards` — e.g. hand-built in an existing test) produces `centroid=None`/
      `flex_cards=[]`, matching Unit 2's defaults.

---

### Unit 4: Provenance side table + nearest-camp DB wrapper

**File**: `src/legacy_engine/archetype/discovered.py`

```python
_INCREMENTAL_ASSIGNMENTS_DDL = """
CREATE TABLE IF NOT EXISTS variant_incremental_assignments (
    tournament_id VARCHAR,
    deck_idx INTEGER,
    parent VARCHAR,
    camp VARCHAR,
    assigned_by VARCHAR,     -- always 'incremental' today; named for future extension
    similarity DOUBLE,
    generated_from VARCHAR,  -- the staged split's generation this assignment came from
    assigned_at VARCHAR,     -- ISO date this row was written
    PRIMARY KEY (tournament_id, deck_idx)
)
"""


@dataclass(frozen=True)
class IncrementalAssignmentResult:
    parent: str
    n_assigned: int
    n_declined: int             # candidates considered, below threshold
    n_cleared: int               # stale prior-generation incremental rows cleared first
    per_camp: dict[str, int]     # camp name -> count assigned this run
    degraded: bool               # True: staged split predates flex_cards/centroid support
    note: str | None              # honest-degrade reason when degraded


def assign_incremental(
    con,
    parent: str,
    *,
    discovered_path: Path | str | None = None,
    min_similarity: float = DEFAULT_MIN_SIMILARITY,
) -> IncrementalAssignmentResult:
    """Nearest-camp incremental assignment for decks under ``parent`` NOT covered by the
    staged split's own ``member_keys`` (fresh post-staging decks, and any original noise
    decks) — the honest-coverage complement to ``apply_split``'s exact-membership labeling.

    Supersession: unconditionally clears every existing ``assigned_by='incremental'`` row
    for ``parent`` first (whatever split generation produced them), resetting those decks'
    ``decks.variant`` to NULL UNLESS the CURRENT staged split's ``member_keys`` now claims
    them as real members (in which case ``apply_split``, always called first by the CLI,
    already gave them the correct label). Then reassigns fresh against the CURRENT split.
    Calling this again after a new PASSing ``discover run`` + ``apply_split`` therefore
    naturally supersedes stale incremental labels with no separate bookkeeping.

    Honest-degrade: a staged split with no persisted ``flex_cards``/``centroid`` (a record
    written before this feature) declines entirely — ``degraded=True``, nothing touched,
    nothing fabricated. Re-running ``discover run`` for that parent populates them (Unit 1/2).
    """
```

Body, in order:
1. `con.execute(_INCREMENTAL_ASSIGNMENTS_DDL)` — idempotent, matches `CREATE TABLE IF NOT
   EXISTS` convention; no `ingestion/store.py` change (this table is owned by the discovery
   feature, colocated here — mirrors `analytics/eras/store.py` owning `entity_eras` rather
   than every derived table living in the core ingestion module).
2. `load_discovered(path)`, locate `parent`'s record — fail-fast `ValueError` if absent
   (mirrors `apply_split`'s existing contract).
3. Clear stale rows: read+delete every `variant_incremental_assignments` row for `parent`;
   for any cleared `(tid, idx)` NOT in the current split's pooled `member_keys`, reset
   `UPDATE decks SET variant = NULL WHERE tournament_id=? AND deck_idx=? AND archetype=?`.
4. Degrade check: `if not split.flex_cards or not any(c.centroid for c in split.camps):`
   return `IncrementalAssignmentResult(parent, 0, 0, n_cleared, {}, True, "...")`.
5. Candidate decks: `SELECT tournament_id, deck_idx FROM decks WHERE archetype = ? AND
   variant IS NULL` (member decks are already excluded — step in the CLI order below always
   runs `apply_split` first).
6. Per candidate: read `SELECT name, count FROM deck_cards WHERE tournament_id=? AND
   deck_idx=? AND board='main'` -> `dict`; call `nearest_camp(counts, split.flex_cards,
   {c.name: c.centroid for c in split.camps if c.centroid}, min_similarity=min_similarity)`.
7. On assignment: `UPDATE decks SET variant = ?` + `INSERT INTO
   variant_incremental_assignments VALUES (..., 'incremental', similarity, split.
   generated_from, date.today().isoformat())`; tally `n_assigned`/`per_camp`. On decline:
   tally `n_declined` only (no per-row reason persisted — aggregate counts + the CLI's
   audit line are the honest-degrade surface here, consistent with how other thin/declined
   paths in the codebase report aggregates, not a per-row log).
8. Return `IncrementalAssignmentResult(...)`.

**Implementation Notes**:
- `date` already used elsewhere in this file's neighborhood (cli.py); import
  `from datetime import date` in `archetype/discovered.py`.
- Reuses `load_discovered`/the existing `Path | str | None` + `DISCOVERED_VARIANTS_PATH`
  default-resolution idiom `apply_split` already has (discovered.py:236-239).
- `variant_incremental_assignments` PRIMARY KEY `(tournament_id, deck_idx)` — one row per
  deck, matching `decks`' own PK shape; a re-assignment simply replaces the row (delete
  step in supersession handles this; no separate `INSERT OR REPLACE` needed since the row
  is always deleted-then-reinserted).

**Acceptance Criteria**:
- [ ] Fresh decks under `parent`, unlabeled and NOT in any camp's `member_keys`, that are
      clearly closer to one camp's centroid get `decks.variant` set to that camp and a
      `variant_incremental_assignments` row with `assigned_by='incremental'`.
- [ ] A candidate deck with best similarity below `min_similarity` is left with
      `decks.variant IS NULL` and counted in `n_declined`, not assigned.
- [ ] Re-running `assign_incremental` for a parent whose staged split changed generation
      (different `member_keys`/`centroid`) clears every prior `assigned_by='incremental'`
      row for that parent and reassigns from the new centroids — no orphaned rows
      referencing the old `generated_from`.
- [ ] A staged split with `flex_cards=[]` (pre-this-feature record) returns
      `degraded=True`, touches zero `decks` rows, and raises nothing.
- [ ] `apply_split` (Unit — unchanged) and all of its existing tests remain green, untouched.

---

### Unit 5: `discover apply` CLI wiring

**File**: `src/legacy_engine/cli.py` (`discover_apply`, cli.py:6871-6928)

```python
@discover.command("apply")
@click.option("--archetype", required=True, ...)
@click.option("--db", type=click.Path(exists=True, dir_okay=False), default=None, ...)
@click.option("--discovered-path", type=click.Path(dir_okay=False), default=None, ...)
@click.option(
    "--min-similarity", type=float, default=DEFAULT_MIN_SIMILARITY, show_default=True,
    help="Cosine-similarity floor (raw L2-normalized flex-band vectors) for nearest-camp "
         "incremental assignment; below this a fresh deck stays honestly unlabeled.",
)
@click.option(
    "--no-incremental", is_flag=True, default=False,
    help="Skip nearest-camp incremental assignment for post-staging decks — membership "
         "labeling only (pre-this-feature behavior).",
)
@_verbose
def discover_apply(
    archetype: str, db: str | None, discovered_path: str | None,
    min_similarity: float, no_incremental: bool, verbose: bool,
) -> None:
```

After the existing `apply_split` call + its three echo lines (cli.py:6892-6899 region),
append:

```python
if not no_incremental:
    result = assign_incremental(
        con, archetype, discovered_path=disc_path, min_similarity=min_similarity,
    )
    if result.degraded:
        click.echo(f"// incremental assignment skipped: {result.note}")
    else:
        if result.n_cleared:
            click.echo(
                f"// cleared {result.n_cleared} stale incremental assignment(s) from a "
                "prior staged generation"
            )
        click.echo(
            f"// {result.n_assigned} deck(s) incrementally assigned "
            f"(assigned_by=incremental, min_similarity={min_similarity}); "
            f"{result.n_declined} candidate(s) left unlabeled below threshold"
        )
        for camp_name, n in result.per_camp.items():
            click.echo(f"//   camp {camp_name}: +{n}")
```

**Implementation Notes**:
- Import `assign_incremental`, `IncrementalAssignmentResult`, `DEFAULT_MIN_SIMILARITY` from
  `legacy_engine.archetype.discovered` / `legacy_engine.analytics.discovery` at the top of
  the lazy-import block already used by this command family.
- DB connection pattern unchanged: `con = store.connect(db) if db else store.connect()`,
  `try/finally: con.close()` — `assign_incremental` runs inside the same `try` block,
  after `apply_split`, before `finally`.
- Default is opt-OUT (`--no-incremental` to disable), matching the Design decisions'
  "consumers see full coverage" intent — incremental assignment runs automatically on
  every `discover apply` unless explicitly suppressed.

**Acceptance Criteria**:
- [ ] `discover apply` with no new flags behaves as today for every existing fixture where
      100% of decks are already cluster members (0 candidates -> `"0 deck(s) incrementally
      assigned"` line, purely additive — all existing `in result.output` assertions in
      `tests/test_discover_cli.py::TestDiscoverApply` still pass unmodified).
- [ ] `--no-incremental` suppresses the new pass entirely — no `variant_incremental_
      assignments` row written, no `decks.variant` change beyond what `apply_split` did.
- [ ] The new audit lines are `// `-prefixed, matching the audit-echo-comment-lines
      convention.

## Implementation Order

1. **Unit 1** — flex-vector projection + `nearest_camp` (pure, DB-free) — first: the
   riskiest algorithmic assumption lives here (Risks); everything downstream depends on
   this representation being trustworthy, validated before any schema/DB work proceeds.
2. **Unit 2** — `DiscoveredCamp.centroid` / `DiscoveredSplitRecord.flex_cards` schema —
   depends on Unit 1's shape (`list[float]`/`list[str]`).
3. **Unit 3** — `record_from_split` plumbing — depends on Units 1+2 existing together.
4. **Unit 4** — `variant_incremental_assignments` table + `assign_incremental` DB wrapper —
   depends on Units 1-3 (needs `flex_cards`/`centroid` actually present in a staged record
   to do anything non-degraded).
5. **Unit 5** — CLI wiring — depends on Unit 4's function signature/return type.

No parallel fan-out: units form a strict serial dependency chain (representation ->
schema -> plumbing -> DB wrapper -> CLI), each narrow enough that splitting into child
stories would only add coordination overhead. Single-stride feature — design IS the work.

## Testing

Hermetic throughout — NEVER the default DB. In-memory `store.connect(":memory:")` (mirrors
`tests/archetype/test_discovered.py::_con_with_doomsday_decks`) for unit-level DB tests;
file-backed `tmp_path`-rooted DuckDB + `--db <path>` for every CLI-level test (mirrors
`tests/test_discover_cli.py`'s `_build_discovery_db` family) — no test ever touches
`data/legacy.duckdb` or the real `data/variants/discovered.json`.

### Unit tests: `tests/analytics/test_discovery.py`
- `TestProjectFlexVector`: overlap -> unit-norm vector; no overlap -> all-zero vector;
  empty `flex_cards` -> empty vector, no crash.
- `TestCampCentroid`: single-member camp centroid equals that member's own projected
  vector; multi-member centroid is the renormalized mean; empty member list -> zero vector.
- `TestNearestCamp`: clearly-separated centroids -> correct camp + `runner_up` populated;
  best similarity below `min_similarity` -> `camp is None` with a named `reason`; empty
  `flex_cards`/`centroids` -> honest decline, never raises.
- **Reconstruction-accuracy test (the trickiest-unit validation the pre-mortem calls
  for)**: build the existing two-camp 35+35 fixture pattern (reuse the shape from
  `tests/test_discover_cli.py::_build_discovery_db`), run `cluster_and_validate`, then for
  every member deck of both camps call `nearest_camp` against the split's OWN centroids and
  assert it recovers the deck's actual camp label at >=90% agreement (a sanity floor, not
  the production `min_similarity` gate) — this is the test that would catch "the
  simplified raw-count cosine space doesn't actually separate real camps" before it ships.
- Extend `TestClusterAndValidate*`: assert `Camp.centroid` is populated (non-None, correct
  length = number of flex cards) and `DiscoveredSplit.flex_cards == fm.cards` on a passing
  split; assert both stay `None`/`[]`-shaped appropriately on the noise-only/all-fail paths
  (no fabricated centroid on a degenerate camp).

### Unit tests: `tests/archetype/test_discovered.py`
- `TestRecordFromSplit`: extend to assert `centroid`/`flex_cards` carry through from a
  `DiscoveredSplit` built with those fields populated; a `DiscoveredSplit` built the old
  way (no `centroid`/`flex_cards` args) still produces `centroid=None`/`flex_cards=[]`.
- Round-trip: `save_discovered` -> `load_discovered` preserves `centroid` float values and
  `flex_cards` order.
- Old-shape JSON (hand-written dict, no `centroid`/`flex_cards`/`member_keys` keys) still
  loads via `load_discovered` — mirrors `test_old_shape_staged_record_still_loads_and_lists`.
- `TestAssignIncremental` (new class): extend `_con_with_doomsday_decks()` — or a sibling
  builder — with extra decks under `Doomsday` NOT in any `member_keys`: one whose mainboard
  closely matches camp A's centroid, one matching neither camp (noise-shaped). Stage a
  `DiscoveredSplitRecord` with real `flex_cards`/per-camp `centroid` (hand-built or produced
  via a real `cluster_and_validate` call over the fixture). Assert:
  - the close deck gets `decks.variant` set to camp A's name and a
    `variant_incremental_assignments` row with `assigned_by='incremental'` and a plausible
    `similarity`;
  - the noise-shaped deck stays `decks.variant IS NULL`, counted in `n_declined`;
  - `per_camp` tallies match;
  - a `degraded=True` staged record (`flex_cards=[]`) touches zero decks.
  - **Supersession**: run `assign_incremental` once, then stage a NEW split generation for
    the same parent whose `member_keys`/`centroid` now cover what was previously
    incremental; run `assign_incremental` again; assert the prior `assigned_by='incremental'`
    row is gone (either cleared-and-reassigned-fresh or superseded by a real membership
    label from `apply_split`), never left stale/orphaned.

### CLI tests: `tests/test_discover_cli.py`
- Extend `TestDiscoverApply`'s existing fixture assertions stay green as-is (100%-member
  fixture -> 0 incremental candidates -> additive `"0 deck(s) incrementally assigned"` line
  only, no existing assertion broken).
- New test: extend `_build_discovery_db`-style fixture with a few extra decks inserted
  under the same archetype AFTER the two 35-deck camps (not part of the clustered pool) —
  one close to a camp, one not. `discover run` (stages over the original 70) -> `discover
  apply` -> assert the close extra deck is incrementally assigned to the right camp (both
  via `SELECT variant FROM decks` and via `SELECT * FROM variant_incremental_assignments`),
  the far one stays unlabeled, and the new `// ... deck(s) incrementally assigned` /
  `assigned_by=incremental` audit lines appear.
- `--no-incremental` test: same fixture, flag passed, assert extra decks stay unlabeled and
  no `variant_incremental_assignments` row is written.
- Supersession CLI test: `discover apply` (some decks incrementally assigned) -> re-run
  `discover run` + `discover apply` for the same parent with a fixture shaped so the new
  split's membership now covers those decks -> assert the `// cleared N stale incremental
  assignment(s)...` line appears and the decks carry the real membership label, not a
  stale incremental one.

### Integration point
- `report matchups --split-variant`, `report cards --conditioned --variant`, `generate
  consensus --variant`, and `analytics/eras/series.py`'s per-entity bucketing all read
  `decks.variant` unchanged — no test changes needed there (confirmed via the code-mapping
  pass: every consumer already treats `variant` as an opaque nullable string, NULL-safe).

## Risks

- **Riskiest assumption**: raw L2-normalized flex-band cosine similarity (deliberately
  dropping TF-IDF idf-reweighting and SVD reduction — Architectural choice option 1) is a
  good-enough proxy for "the same representation space discovery used" to make honest,
  low-error nearest-camp decisions on decks HDBSCAN never saw. **Fallback**: the
  reconstruction-accuracy test (Testing, Unit 1) validates it against each split's own
  known members before ship; in production, prefer a conservative `min_similarity` (favor
  false-unlabeled over false-camp-assignment, matching the honest-degrade ethos) and, if
  real-world dogfooding shows misassignment, additively persist the fitted `idf_` vector
  (a `list[float]` aligned to `flex_cards`) for full TF-IDF fidelity without any breaking
  schema change — `centroid`/`flex_cards` are already additive Optional fields.
- **`DEFAULT_MIN_SIMILARITY = 0.35` is uncalibrated** — unlike Gate C's `_TEMPORAL_GAP_DAYS`
  (pinned against two real calibration fixtures), this constant has no corpus-derived
  backing yet, because `centroid`/`flex_cards` don't exist on any of the 30 real staged
  splits until they're regenerated by a fresh `discover run`. **Fallback**: CLI-tunable
  (`--min-similarity`) from day one; flag a follow-up calibration pass (compare nearest-camp
  decisions against a held-out slice of real corpus decks) once real centroids exist.
- **No backfill for the 30 existing real staged splits** in `data/variants/discovered.json`
  — all predate this feature, so `assign_incremental` degrades honestly (`degraded=True`,
  no-op) for every one of them until each parent's `discover run` is re-run and PASSES.
  This is in scope of the existing workflow (re-running `discover run` is already the
  normal refresh cadence) but is a real gap between ship and first benefit. **Fallback**:
  none needed for correctness (honest degrade, not a crash); a one-time backfill script
  re-deriving `flex_cards`/`centroid` for the 30 existing splits from their `member_keys` +
  current `deck_cards` is a plausible fast-follow but is explicitly NOT in this feature's
  pinned Design decisions.
- **Overlapping/shared-staple camps** (3+-camp splits where camps share signature cards)
  could make raw-count cosine less discriminative than the actual TF-IDF+SVD+HDBSCAN split
  achieved, producing closer top-2 similarities than the "real" clustering would tolerate.
  **Fallback**: `NearestCampResult.runner_up` is already captured as a diagnostic; a
  margin-based tightening (decline when top1-top2 gap is too small, not just top1 below an
  absolute floor) is a natural, additive v2 refinement, deliberately deferred to keep this
  feature's scope to a single absolute threshold.
- **`variant_incremental_assignments` unbounded growth**: mitigated by design — every
  `assign_incremental` call clears ALL prior rows for `parent` before reassigning, so the
  table only ever holds the current generation's incremental rows per parent, never
  accumulating stale history.

## Implementation notes
<!-- 2026-07-31 -->

All 5 units landed as designed, in the specified serial order. Files touched:
`src/legacy_engine/analytics/discovery.py`, `src/legacy_engine/models/variant.py`,
`src/legacy_engine/archetype/discovered.py`, `src/legacy_engine/cli.py`, plus
`tests/analytics/test_discovery.py`, `tests/archetype/test_discovered.py`,
`tests/test_discover_cli.py`.

### Reconstruction accuracy — the riskiest assumption, measured

The design's bar was **>=90%** nearest-centroid agreement with a split's own members' real camp
labels, validating that raw L2-normalized flex-band cosine (dropping TF-IDF idf-reweighting and
SVD reduction) is a trustworthy proxy for the space HDBSCAN clustered on.

Measured against the **real corpus** (`data/legacy.duckdb`, read-only; all 30 staged splits in
`data/variants/discovered.json`, pool reproduced from each record's own `params.since`, camps
taken from persisted `member_keys`):

**98.65% overall — 20,844 / 21,130 member decks.** Every split clears the bar individually;
worst three: Lands 92.1%, Jeskai Midrange 92.4%, Grixis Midrange 94.7%. Best: eight splits at
100.0%. Flex-band width ranged 8-50 dimensions.

The assumption holds comfortably — the additive `idf_`-persistence fallback in Risks is NOT
needed. `TestReconstructionAccuracy` in `tests/analytics/test_discovery.py` pins the >=90% floor
hermetically (two-camp fixture and the harder three-camp shared-staples fixture, both 100%),
carrying the real-corpus number in its docstring as the calibration record.

### Deviations from the design (both narrow, behavior-preserving)

- **`--min-similarity` default resolution.** The design specified
  `default=DEFAULT_MIN_SIMILARITY, show_default=True` on the Click option. That requires
  importing `analytics.discovery` at `cli.py` module scope, which costs **~1.0s of numpy import
  on every CLI invocation** (`cli.py` currently has zero top-level `legacy_engine` imports — the
  lazy-import half of the cli-nested-groups pattern). Implemented as `default=None` with in-body
  resolution from `DEFAULT_MIN_SIMILARITY`, `show_default="0.35"`, and
  `test_min_similarity_help_default_matches_the_engine_constant` pinning the displayed value to
  the real constant so it cannot drift. Behavior is identical.
- **Candidate mainboards read in one query, not one per deck.** Design step 6 specified a
  per-candidate `SELECT`. Implemented as a single joined query into `counts_by_key`, then a pure
  decision loop — the objective-search-split shape, materially cheaper on a real parent with
  thousands of unlabeled decks, semantically identical.

### Closed-vocabulary token — made load-bearing rather than ceremonial

`assigned_by` is engine-written, so validating the literal at its own write site would be dead
code. The guard was placed where the token actually crosses a trust boundary instead: reading
prior rows back out of the DB. `assign_incremental` fails fast (naming the offending token and
the sorted allow-set) if `variant_incremental_assignments` holds a row for the parent whose
`assigned_by` is outside `_VALID_ASSIGNED_BY` — refusing to clear or reset state this path did
not write.

### Honest-degrade behavior for the ~30 pre-feature staged splits

A split lacking `flex_cards` or any camp `centroid` returns
`IncrementalAssignmentResult(degraded=True, ...)` with a note naming both the cause and the fix
(`re-run 'discover run --archetype X'`); zero `decks` rows are touched and no side-table row is
written. `discover apply` surfaces it as
`// incremental assignment skipped: <reason>`. Covered at both the DB layer
(`test_record_without_the_frozen_representation_degrades_honestly`) and the CLI layer
(`test_pre_feature_staged_record_degrades_with_a_named_reason`). This is the state every real
staged split is in until its next `discover run`.

### Verification

Full suite: **3055 passed, 1 skipped, 1 xfailed**. New coverage: 25 tests in
`tests/analytics/test_discovery.py` (projection, centroid, nearest-camp, reconstruction floor,
centroid stamping), 15 in `tests/archetype/test_discovered.py` (record plumbing, round-trip,
assignment, both supersession branches, parent-scoping, closed-vocabulary refusal), 8 in
`tests/test_discover_cli.py` (assignment + audit lines, `--no-incremental`, `--min-similarity`,
end-to-end supersession, degrade path). `ruff check src/` adds no new finding *kinds* over
`origin/main`: two new instances, `"np.ndarray"` (UP037) and `date.today()` (DTZ011), each
matching the established convention in the file it lives in.

### Follow-ups this feature deliberately does not do

- `DEFAULT_MIN_SIMILARITY = 0.35` remains uncalibrated. The real-corpus decline rates now
  observable (0-23 declines per split at 0.35) are the input a calibration pass would use.
- No backfill for the 30 existing staged splits — each repopulates on its next `discover run`.
- Margin-based tightening (decline on a thin top1-top2 gap) stays deferred; `runner_up` is
  captured on every `NearestCampResult` as the diagnostic that would drive it.
