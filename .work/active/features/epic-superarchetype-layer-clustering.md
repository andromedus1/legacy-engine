---
id: epic-superarchetype-layer-clustering
kind: feature
stage: review
tags: [analytics, archetype]
parent: epic-superarchetype-layer
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Superarchetype taxonomy — cluster archetypes into strategy families, derived + curated

## Brief

Delivers the **taxonomy itself**: the offline pass that turns the corpus's ~183 archetype labels
into a small set of named strategy clusters, plus the registry that every downstream consumer reads.
The method is pinned by the brief and is not open for re-invention: per-archetype **core set**
(maindeck cards at >=50% inclusion in that archetype's in-window decks) **minus format staples**
(cards core to >=30% of the cluster-defining archetypes); **Jaccard dissimilarity** on the stripped
cores; **average-linkage agglomerative** clustering on the precomputed dissimilarity (every
archetype gets a cluster — no noise class, which is the decisive reason HDBSCAN is rejected here:
an archetype called noise gets no superarchetype at all, and it will be a thin unusual archetype,
i.e. exactly the row this epic exists to cover); cut at the deepest height where every retained
branch clears a **multiscale-bootstrap AU p-value > 0.95** computed by resampling the **card feature
vocabulary**, cross-checked against co-membership stability > 0.9. Archetypes with **>=30 decks and
>=8 core cards** may **define** a cluster (~30 archetypes, 83.7% of the field); everything else with
>=5 core cards is **assigned** by nearest centroid and never defines one (~182 archetypes, 98.3% of
the field, zero unassignable). Camps inherit their parent's cluster.

The hard-removal of format staples is the load-bearing step, not an optimization: with the 14
measured staples left in, average-linkage returns a single cluster containing 16 of 34 archetypes
("plays blue"), and TF-IDF down-weighting is *not* sufficient (IDF-weighted cosine still fuses 14 of
30). With them removed the same algorithm recovers the epic's motivating `Aluren` + `Show and Tell`
branch without being told to. The feature also owns the **curated override layer** — the brief
enumerates the derived clustering's known-wrong assignments (Doomsday landing with the fair Dimir
decks, Cephalid Breakfast with the fair Azorius decks, Grixis Reanimator with TES, Red Stompy with
Show and Tell), every one a residual shell/color artifact — so curated entries win by key, derived
fills the gaps, and each override records the derived assignment it replaced so the divergence stays
auditable. Era handling is settled by measurement: co-membership agreement across windows spanning
both the Flow State step and the Candelabra ban is 0.957, so cluster **identity** stays stable across
refreshes while **membership** is recomputed per window and churn is surfaced as a diagnostic.

**Not covered here.** No match-outcome data enters this feature at all — the clustering input is
decklist composition (`deck_cards`) and nothing else. That separation is architectural, not
incidental: it is what keeps the taxonomy clear of the double-dipping trap the camp layer had to
work around, and it means the cut height can never be tuned against the coverage it unlocks. Pooling
member cells, `n_eff`, the concentration/heterogeneity gates, the shrinkage rung, and anything that
renders a win rate belong to the three sibling features.

## Epic context

- Parent epic: `epic-superarchetype-layer`
- Position in epic: **foundation feature** — produces the cluster identity/membership types and the
  registry that `-aggregation`, `-chain`, and `-best-call-fallback` all consume. Nothing else in the
  epic can be validated on real data until this lands.

## Inherited design decisions

From the epic's `## Strategic decisions` (locked at scope) and `## Design decisions` (locked at
epic-design). Treat as fixed inputs — do not re-ask:

- **Data-driven clustering with a curated override layer** (hybrid-derived-curated-registry): curated
  wins by key, derived fills gaps, the overridden derived assignment is recorded.
- **Registry split mirrors the existing precedent exactly**: curated JSON ships inside the package
  (`PACKAGE_DATA_DIR/superarchetypes/legacy.json`, path constant in `config.py`, fail-fast
  path-taking loader per curated-json-resource-loader); the derived half is written under `DATA_DIR`
  by the offline pass, like `DISCOVERED_VARIANTS_PATH`.
- **Offline pass, never a hot-path clustering.** Matrix builders READ the registry; they never
  cluster inline. The registry records the window it was derived over, and a mismatch against the
  window a consumer is using is a loud `//` audit line, never a silent stale taxonomy.
- **Cluster identity persists across refreshes by max-overlap matching** against the previous
  registry; unmatched clusters get a new id; the id→member mapping change is reported in the run's
  audit. Curated entries own both id and display name and win outright.
- **Composition evidence only for the cut.** The cut height is chosen from AU p-values over card
  features and co-membership stability. Coverage of the matchup matrix is *never* an input to any
  clustering parameter (coverage is monotone in coarseness and would select K=1).
- **Two sourcing caveats the brief flags on itself, to be discharged during design, not ignored:**
  (a) the **feature-axis** bootstrap (resampling the card vocabulary rather than the archetypes) is
  the brief's own design decision, not something its pvclust attestation states — confirm it
  against pvclust's documentation before implementing, and record the answer; (b) pvclust's AU rule
  is stated for a *single* cluster, so applying it across a whole dendrogram is a further extension
  — record explicitly that no multiplicity correction is applied across branches.
- **No era-partitioned taxonomy.** Recompute membership on the window the consumer sources over;
  keep cluster identity stable; surface churn (expected baseline ~0.96 window-over-window
  agreement) as a diagnostic.
- **Honest degrade with a name** for every refusal: an archetype below the assignee floor, a branch
  failing AU, an empty/missing registry — each surfaces a labeled reason, never a silent drop.

## Research briefs

- `docs/briefs/superarchetype-aggregation.md` — **primary**. §2 (what transfers from the camp layer
  and what does not — HDBSCAN and TF-IDF explicitly do NOT), §3.1 representation + the measured
  14-card staple list, §3.2 Jaccard + the cophenetic-correlation tripwire caveat, §3.3 average
  linkage, §3.4 cut selection + the measured K/coverage table (use it as a sanity band, K≈6-12, not
  as an objective), §3.5 definer/assignee floors + why the curated layer is required, §9 era
  scoping, §10 implementation notes (reuse discovery's shape; `scipy.cluster.hierarchy`; AU
  bootstrap as a numpy loop; no new heavyweight dependency).
- `docs/briefs/subarchetype-discovery.md` — the same problem one level down; the source of the
  pipeline shape (`build feature matrix → reduce → cluster → validate → name`) and the
  objective-search-split discipline, but explicitly NOT of the algorithm choices.
- `docs/briefs/change-point-detection.md` — §1 ground truths (Flow State step, Candelabra ban) that
  bound the era-stability measurement.

## Foundation references

- `docs/VISION.md` — the three-level-taxonomy decision (superarchetype → parent archetype → camp).
- `docs/SPEC.md` — the `Superarchetype` domain entity and the superarchetype capability bullet.
- `docs/ARCHITECTURE.md` — `analytics/superarchetype/` module rows; the CLI conventions block.
- `.agents/skills/patterns/` — `objective-search-split` (pure core + thin DB wrapper),
  `hybrid-derived-curated-registry`, `curated-json-resource-loader`,
  `json-ssot-rebuildable-duckdb-table`, `honest-degrade-marker`, `audit-echo-comment-lines`,
  `cli-nested-groups`, `closed-vocabulary-fail-fast-token`, `pytest-factory-fixtures`.
- Code to read before designing: `src/legacy_engine/analytics/discovery.py` (the pipeline shape that
  transfers), `src/legacy_engine/archetype/discovered.py` (registry staging/promotion/apply),
  `src/legacy_engine/analytics/eras/` (the closest package-shaped precedent: detect / store /
  consume), `src/legacy_engine/config.py` (path constants).

## Design

<!-- Written 2026-07-31 during the feature-design pass (autopilot delegation). Ambiguities were
resolved with judgment and the rationale is inline. Cross-model peer review skipped per the
orchestrator's instruction. No child stories: the four units share one module pair and one type
graph, and unit 2's output is unit 3's input in the same call — splitting them would cost more in
seam-writing than it buys. -->

### Architectural options weighed

**Option A — one flat module `analytics/superarchetype.py`.** Everything (cores, staples, distance,
AU, assignment, curated merge, JSON, DuckDB, churn) in one file, following `discovery.py`'s
single-file precedent. Rejected: `discovery.py` is 828 lines and stops at "return a result object" —
it persists nothing. This feature owns two persistence surfaces (derived JSON SSOT + rebuildable
DuckDB table) and a curated resource loader, which `eras/` already demonstrates wants its own module.
A flat file would also put curated-file I/O in the same import graph as the pure numeric core, so the
"pure core takes card data only" property would rest on discipline rather than on structure.

**Option B (chosen) — the epic's locked two-module package: `cluster.py` + `registry.py`.**
`cluster.py` is the objective-search-split shape verbatim from `discovery.py`: a pure DB-free core
plus one thin read-only DB wrapper at the bottom whose single query names exactly two corpus tables,
`decks` and `deck_cards` (plus `tournaments` for the date window). `registry.py` owns every byte that
leaves the process: the curated loader, the merge, the derived JSON SSOT, the rebuildable DuckDB
cache, cluster-identity persistence, and the churn diagnostic. The dependency edge runs
`registry.py -> cluster.py` and never back, so the pure core cannot reach a file or a table at all.

**Option C — a four-module package mirroring `eras/` (`compose.py` / `cluster.py` / `store.py` /
`run.py`).** Rejected as premature: `eras/` earned four modules because it has three genuinely
independent detectors plus an ensemble. Here the pipeline is one linear chain, and the epic already
fixed the module names that `ARCHITECTURE.md` publishes. Splitting further would invent seams the
sibling features (`aggregate.py`, `consume.py`) will not use.

**Decision: Option B.** The offline-pass orchestration (`run_superarchetypes`) lives at the bottom of
`registry.py` rather than in a third `run.py`, because it is 95% persistence: it calls one pure
function and then does identity-matching, merging, churn, and two writes.

### The no-`rounds` property — how it is enforced, not merely promised

Three independent layers, because this is the epic's sharpest methodological hazard:

1. **Type-structural.** The only input to the pure core is `ArchetypeDeck(archetype, key, cards)`.
   No type in `cluster.py` has a wins/losses/result field, so a coverage objective is not
   *expressible* against the core's inputs, let alone optimisable.
2. **Query-structural.** `cluster.py` contains exactly one corpus `con.execute(...)`, and it is the
   only corpus read in the whole package. `registry.py`'s statements touch only its own
   `superarchetype_members` table.
3. **Mechanically tested.** `tests/analytics/superarchetype/test_no_rounds.py` runs both a source
   tripwire (scan `cluster.py` + `registry.py` for the tokens `rounds`, `match_results`, `wins`,
   `losses`, `winrate` — fail if any appears in executable source) and a runtime SQL spy: a proxy
   connection that records every statement text passed to `execute`/`executemany` and asserts no
   recorded statement mentions `rounds` or `match_results`, driven by a real end-to-end
   `run_superarchetypes` call against a tmp DuckDB that *does* contain a populated `rounds` table.
   The spy is the load-bearing one — it proves the property at runtime, not just in the source.

### Units

Ordered trickiest-first, which is also dependency order for the two hard ones.

---

#### Unit 1 — AU multiscale bootstrap + cut selection (`cluster.py`) — TRICKIEST

The only genuinely novel numerics in the feature, and the one place the brief flags its own port as
unverified. Everything else is assembly.

```python
_AU_SCALES: tuple[float, ...] = (0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4)
_AU_MIN: float = 0.95          # calibration choice, not a sourced constant
_AU_MIN_BP: float = 0.30       # calibration choice, not a sourced constant
_DEFAULT_N_BOOT: int = 200     # calibration choice, not a sourced constant

@dataclass(frozen=True)
class BranchSupport:
    node: int
    members: tuple[str, ...]
    height: float
    bp: tuple[float, ...]          # BP per scale, in _AU_SCALES order
    bp_at_unit_scale: float
    au: float
    v: float | None                # signed-distance / curvature fit; None when unfittable
    d: float | None

def au_pvalues(
    M: "np.ndarray",               # (n_archetypes, n_cards) binary stripped-core indicator
    labels: list[str],
    *,
    seed: int = 0,
    n_boot: int = _DEFAULT_N_BOOT,
    scales: tuple[float, ...] = _AU_SCALES,
) -> dict[int, BranchSupport]: ...

def select_supported_clusters(
    Z: "np.ndarray",
    labels: list[str],
    support: dict[int, BranchSupport],
    *,
    au_min: float = _AU_MIN,
    min_bp: float = _AU_MIN_BP,
) -> tuple[list[list[str]], list[str], list[str]]:
    """-> (clusters, singleton_labels, reasons)"""
```

**Method, pinned.** For each scale `r`, draw `n_boot` resamples of the **card feature vocabulary**
with replacement at size `round(r * n_cards)`, express the resample as a per-card multiplicity weight
vector, recompute the **weighted** Jaccard dissimilarity
`1 - sum(w * min(a,b)) / sum(w * max(a,b))` (the exact generalisation of set Jaccard under column
multiplicity — a card drawn twice counts twice), re-run average linkage, and score `BP(r)` as the
fraction of replicates in which the base node's exact leaf set appears as a node of the bootstrap
dendrogram. Then fit Shimodaira's multiscale model `psi(r) = v/sqrt(r) + d*sqrt(r)` where
`psi(r) = -Phi^-1(BP(r))`, by weighted least squares with pvclust's BP-variance weights
`n_boot * phi(psi)^2 / (p(1-p))`, and report `AU = 1 - Phi(d - v)`.

**Sourcing caveats discharged here, per the epic's instruction.**
(a) *The feature-axis port.* pvclust resamples the **rows** of the input data matrix — the axis that
is *not* being clustered (pvclust clusters columns). Our objects are archetypes and our features are
cards, so resampling the card vocabulary IS pvclust's own axis, not a departure: the brief's flagged
"port" turns out to be the faithful reading, and the only real adaptation is that our per-column
statistic is a set-Jaccard rather than a correlation. Recorded as confirmed.
(b) *Whole-dendrogram application.* pvclust states the AU rule for a single cluster; we apply it to
every branch and **no multiplicity correction is applied across branches**. Recorded explicitly, in
the module docstring and in `superarchetype explain`'s output, because it means the count of
supported branches is optimistic in the usual multiple-comparisons direction.
(c) *The `>0.95` comparison is strict* (`au > au_min`), per the citation audit's correction.

**`_AU_MIN_BP` — a guard the brief does not specify, added on measured evidence.** AU is a
*bias-corrected extrapolation* of BP. Measured on the real corpus (see `## Implementation notes`),
near-root branches show BP ~ 0.02-0.15 that is essentially **flat across all ten scales**; with no
scale signal the fit returns `d ~ 0` and AU collapses to `Phi(v)`, handing 0.93-0.97 to branches
observed in under a tenth of replicates. That is extrapolation without evidence, and it is precisely
the direction that would silently manufacture a mega-cluster. The guard states the minimum claim
plainly: *a branch must also have been observed as a branch in at least 30% of same-size resamples.*
Named constant, comment at the definition site marking it a calibration choice, CLI-overridable.

**Cut rule — `pvpick` semantics, not a single height.** The brief's phrase "the deepest height where
each retained branch clears AU > 0.95" cannot be read as one horizontal cut: measured on the corpus,
the single-height reading is dominated by the weakest branch at that height and returns either K=25
(cut below the first unsupported merge) or K=1 (the root, which is trivially supported in every
replicate). Both are outside the brief's own K~6-12 sanity band, so the single-height reading is not
what the brief intended. Implemented instead as pvclust's `pvpick`: descend from the root, retain the
**largest** eligible node on each path, recurse into the children of any node that is not eligible.
**The root is excluded from candidacy** — "all thirty archetypes are one cluster" is not a claim, and
it has BP = 1.0 by construction. Leaves reached without being covered become **singleton clusters
with the named reason `au-unsupported singleton`** — never dropped, because every archetype must get
a superarchetype.

**Acceptance criteria.**
- Determinism: two `au_pvalues` calls with the same `(M, labels, seed, n_boot, scales)` return
  bitwise-identical `au`/`bp` values, and the value does not depend on scale iteration order (each
  replicate's RNG is derived from `(seed, scale_index, replicate_index)`, never a shared stream).
- A synthetic matrix with two cleanly disjoint card blocks yields `au > 0.95` on the two block nodes.
- A synthetic matrix of pure noise yields no node clearing both `au_min` and `min_bp`, and
  `select_supported_clusters` returns every label as a singleton with the named reason.
- `select_supported_clusters` never returns the root as a cluster when `n_labels >= 2`.
- Every label appears exactly once across `clusters + singletons` (partition invariant).

---

#### Unit 2 — representation: cores, definers, staples, distance (`cluster.py`)

```python
_CORE_INCLUSION: float = 0.50       # calibration choice
_STAPLE_DEFINER_FRACTION: float = 0.30
_DEFINER_MIN_DECKS: int = 30
_DEFINER_MIN_CORE_CARDS: int = 8
_ASSIGNEE_MIN_CORE_CARDS: int = 5

@dataclass(frozen=True)
class ArchetypeDeck:
    archetype: str
    key: tuple[str, int]
    cards: frozenset[str]           # maindeck names only; no counts, no outcomes

@dataclass(frozen=True)
class ArchetypeComposition:
    archetype: str
    n_decks: int
    core: frozenset[str]
    stripped_core: frozenset[str]
    is_definer: bool
    tier: ConfidenceLevel

def build_compositions(decks, *, core_inclusion=_CORE_INCLUSION, ...
) -> tuple[dict[str, ArchetypeComposition], tuple[str, ...]]:
    """-> (compositions keyed by archetype, the derived format-staple tuple)"""

def jaccard_dissimilarity(a: frozenset[str], b: frozenset[str]) -> float
def weighted_jaccard_matrix(M: "np.ndarray", weights: "np.ndarray") -> "np.ndarray"
```

Ordering is fixed and non-circular: raw cores for every archetype -> definers by
`n_decks >= 30 AND len(core) >= 8` -> staples as cards core to `>= 30%` of **definers** -> strip
staples from every archetype's core. Copy counts are deliberately discarded at the query boundary
(`cards` is a `frozenset`) — the brief's §3.1 finding is that superarchetype splits are
package-level, and dropping counts makes the abundance confound structurally impossible rather than
merely unused. Empty union -> dissimilarity `1.0` (two archetypes with nothing left after stripping
are maximally dissimilar, never `0/0`).

**Acceptance criteria.** Reproduces the brief's measured corpus figures within rounding: 30 definers
at 83.8% field share, the exact 14-card staple list, cophenetic correlation 0.916 for
Jaccard/average. Hand-built fixtures cover: an archetype at exactly 50% inclusion (included — the
threshold is `>=`), a definer at exactly 30 decks / exactly 8 core cards (included), a definer whose
stripped core is empty (excluded from the matrix with a named reason, not a zero row).

---

#### Unit 3 — pure pipeline + assignment + stability (`cluster.py`)

```python
_STABILITY_MIN: float = 0.90        # calibration choice
_VALID_PROVENANCE = frozenset({"derived", "assigned", "curated"})

@dataclass(frozen=True)
class ClusterMember:
    archetype: str
    provenance: str                 # closed vocabulary; __post_init__ fails fast
    n_decks: int
    note: str | None = None

@dataclass(frozen=True)
class DerivedCluster:
    key: str                        # deterministic content key over the sorted definer members
    label: str                      # auto-name: the definers, sorted, " + "-joined
    members: tuple[ClusterMember, ...]
    au: float | None                # None for an au-unsupported singleton
    height: float | None

@dataclass(frozen=True)
class ClusterSolution:
    clusters: tuple[DerivedCluster, ...]
    staples: tuple[str, ...]
    definers: tuple[str, ...]
    unassigned: tuple[tuple[str, str], ...]     # (archetype, named reason)
    stability: float
    cophenetic: float
    reasons: tuple[str, ...]        # every gate outcome, verbatim
    degraded: bool
    seed: int
    n_boot: int

def cluster_archetypes(decks, *, seed=0, n_boot=200, au_min=_AU_MIN, ...) -> ClusterSolution
```

**Assignment of the long tail — a deliberate, logged deviation from the brief's wording.** The brief
says "nearest cluster centroid over the staple-stripped cores". A literal mean-vector centroid is
metric-inconsistent with Jaccard (Jaccard is not an inner-product space, and the brief itself warns
against feeding non-metric dissimilarities to metric-assuming methods). Implemented instead as
**average Jaccard dissimilarity to the cluster's definer members** — which is exactly average
linkage's own criterion, so an assignee is placed by the same rule that formed the cluster it joins.
Ties break on `(distance, cluster.key)` for determinism. An assignee with `< 5` core cards, or with
an empty stripped core, is **unassigned with a named reason** and appears in
`ClusterSolution.unassigned` — it never gets a fabricated home.

**Stability cross-check.** Resample the card vocabulary at `r = 1.0`, recluster, cut to the same K
with `fcluster(criterion="maxclust")`, and average pairwise co-membership agreement against the base
partition over definers. Reported on every run and compared against `_STABILITY_MIN`; it is a
**diagnostic that annotates**, never a gate that empties the taxonomy — the AU rule already refuses
unsupported branches, and failing the taxonomy twice for the same evidence would leave the epic with
nothing to serve.

**Honest-degrade paths, each with a named reason in `reasons` and `degraded=True`:** no definers at
all; every definer's stripped core empty; no branch clearing the AU cut (every definer a singleton).

---

#### Unit 4 — registry: curated merge, persistence, identity, churn (`registry.py`)

```python
# config.py additions
SUPERARCHETYPES_DIR = PACKAGE_DATA_DIR / "superarchetypes"
SUPERARCHETYPES_REGISTRY_PATH = SUPERARCHETYPES_DIR / "legacy.json"   # curated SSOT
DERIVED_SUPERARCHETYPES_PATH = DATA_DIR / "superarchetypes" / "derived.json"  # derived SSOT

def load_curated_superarchetypes(path: Path | str) -> dict[str, CuratedCluster]
def _load_default_curated() -> dict[str, CuratedCluster]     # degrades to {} on any error
CURATED_SUPERARCHETYPES = _load_default_curated()            # bound once at import

def merge_curated(solution, curated, *, window, ...) -> SuperarchetypeRegistry
def match_identities(new, previous) -> tuple[SuperarchetypeRegistry, tuple[str, ...]]
def membership_churn(new, previous) -> ChurnReport

def write_derived_registry(registry, path) -> None
def read_derived_registry(path) -> SuperarchetypeRegistry | None
def init_superarchetype_schema(con) -> None
def rebuild_superarchetype_members(con, registry) -> None
def read_superarchetype_members(con) -> SuperarchetypeRegistry | None
def run_superarchetypes(con, *, since, until, seed=0, n_boot=200, ...) -> RunResult
```

- **curated-json-resource-loader**: `load_curated_superarchetypes` is standalone, path-taking, never
  imports config, and raises `ValueError` naming the offending path and cluster/archetype key on a
  missing id/label, a duplicate archetype across clusters, or a bad provenance token.
  `_load_default_curated` resolves the config path and degrades to `{}` on any error, so an absent
  or mis-edited curated file no-ops instead of crashing import.
- **hybrid-derived-curated-registry**: `merge_curated` — a curated cluster wins the id and label
  outright; a curated member assignment wins by archetype key, is stamped `provenance="curated"`,
  and **records the derived cluster it replaced** in `ClusterMember.note`, so every override is
  auditable rather than invisible.
- **json-ssot-rebuildable-duckdb-table**: `DERIVED_SUPERARCHETYPES_PATH` is the SSOT;
  `superarchetype_members` is a derived cache rebuilt DROP -> schema -> INSERT on every run. Read
  degrades to `None` on `duckdb.CatalogException` only; every other DB error stays loud.
- **Identity across refreshes** (epic decision 5): `match_identities` maps each new cluster to the
  previous cluster with maximal member overlap, greedily by descending overlap, one-to-one; an
  unmatched new cluster mints `sa-<nnn>` past the previous max. Curated ids are never remapped.
- **Churn** (brief §9): `ChurnReport` carries co-membership agreement over the archetypes present in
  both refreshes, the per-archetype moves, and the arrivals/departures. `run` prints it as `//`
  lines with the measured ~0.96 baseline named, so a materially lower figure reads as an alarm.

---

#### Unit 5 — CLI (`cli.py`, `superarchetype` group)

`superarchetype run|list|explain`, following cli-nested-groups exactly: `@main.group()`, each leaf
calls `_setup_logging(verbose)` first, `--db` path option, `con.close()` in a `finally`, all
provenance on `// `-prefixed lines (audit-echo-comment-lines).

- `run [--db] [--since] [--until] [--au-min] [--min-bp] [--n-boot] [--seed] [--dry-run]` — the
  offline pass. Echoes window, definer/assignee counts and field share, the staple list, K, per
  cluster its AU and members, stability vs `_STABILITY_MIN`, the churn report, the identity remap,
  and every honest-degrade reason. `--dry-run` computes and prints without writing either surface.
- `list [--db] [--cluster ID]` — clusters and members with `derived`/`assigned`/`curated`
  provenance; `(no superarchetype registry — run `superarchetype run` first)` when absent.
- `explain ARCHETYPE [--db]` — one archetype's assignment: its cluster, its provenance, shared vs
  disjoint stripped-core cards against each cluster-mate, the branch AU, the no-multiplicity-
  correction caveat, and the derived assignment any curated override replaced.

The derivation window is recorded on the registry, and `list`/`explain` echo it so a consumer can
see which window the taxonomy was derived over (epic decision 3 — no hot-path clustering, no silent
staleness).

### Test approach

`tests/analytics/superarchetype/` (`test_cluster.py`, `test_registry.py`, `test_no_rounds.py`) plus
`tests/test_cli_superarchetype.py`. Factory fixtures returning `_make_X(**kwargs)` closures in a
package `conftest.py`; `TestX` classes; every CLI test builds a file-backed tmp DuckDB via
`_build_superarchetype_db(tmp_path) -> str` and passes `--db <that path>` — never the default DB.
The pure core is tested entirely on hand-built `ArchetypeDeck` lists with no DuckDB at all. One
determinism test pins a full `ClusterSolution` round-trip at a fixed seed. Real-corpus figures are
recorded in `## Implementation notes`, not asserted in tests — the corpus moves weekly.

### Pre-mortem

1. **AU extrapolates a mega-cluster into existence.** The exact failure the staple strip exists to
   prevent, arriving through the back door. Caught in prototyping; mitigated by `_AU_MIN_BP` and by
   excluding the root from candidacy. Residual risk: a *mid-tree* branch with moderate BP and a
   flat curve. Surfaced by printing BP-at-unit-scale beside AU in `explain`.
2. **The taxonomy comes out too conservative to help.** Measured: it does — only a handful of
   branches clear the cut, leaving most definers as singletons. This is the honest reading of the
   evidence and is why the curated layer is not optional. Mitigated by making every threshold a
   named, CLI-overridable calibration constant and by having `run` print the full AU profile, so
   recalibration is evidence-driven and one flag wide.
3. **Bootstrap cost explodes.** 10 scales x 200 replicates x an O(m^2 * n_cards) distance rebuild.
   Measured at ~4-7s for 30 definers x 256 cards; acceptable for an offline pass, and the CLI
   exposes `--n-boot`.
4. **Cluster identity churns anyway** because max-overlap matching is greedy and a two-way split can
   hand the id to the wrong half. Mitigated by reporting the remap loudly and by letting curated
   entries own ids outright — the fix for a wrong id is a curated entry, not an algorithm change.
5. **Someone later "improves" coverage by tuning the cut.** The whole point of the no-`rounds`
   enforcement. If a future change adds a `rounds` read to this package, `test_no_rounds.py` fails.

## Implementation notes

Delivered 2026-07-31. Files: `src/legacy_engine/analytics/superarchetype/{__init__,cluster,registry}.py`,
`src/legacy_engine/data/superarchetypes/legacy.json` (curated SSOT, ships empty),
two `config.py` path constants, the `superarchetype run|list|explain` group in `cli.py`,
`tests/analytics/superarchetype/{conftest,test_cluster,test_registry,test_no_rounds}.py`,
`tests/test_cli_superarchetype.py`. `docs/SPEC.md` and `docs/ARCHITECTURE.md` rolled forward where
the shipped cut rule differs from what epic-design anticipated (see "Cut selection" below).

### Real-corpus validation

Run read-only against a **copy** of `data/legacy.duckdb` (the real corpus file was never opened for
write) over the brief's own window `[2026-05-11, 2026-07-30]`, seed 0, `n_boot=200`.

**1. Aluren + Show and Tell — YES, recovered unprompted.** Cluster `sa-001`,
**AU = 0.972, BP@1.0 = 0.92**, the strongest-supported non-trivial branch after the Izzet and
Tron pairs. The brief's motivating case reproduces exactly, with no curated entry and nothing in the
pipeline that knows the pair exists. Five long-tail archetypes (`Creative combo`, `High Tide`,
`Hypergenesis`, `Bant Infect`, `5c Cascade Rhinos`) assign into the same family, which reads
correctly as "cheat something enormous into play".

**2. Clusters at the AU cut: K = 20** over 30 definers — **5 AU-supported multi-definer branches**
plus **15 `au-unsupported singleton`s**. The five supported branches, with their measured support:

| Branch | AU | BP@1.0 |
|---|---|---|
| Izzet Delver + Izzet Midrange | 0.996 | 0.99 |
| Mystic Forge Combo + Tron | 0.993 | 0.98 |
| Azorius Midrange + Azorius Stoneblade | 0.974 | 0.94 |
| **Aluren + Show and Tell** | **0.972** | **0.92** |
| Dimir Delver + Dimir Midrange + Dimir Tempo + Doomsday + Grixis Midrange + Grixis Reanimator + TES | 0.959 | 0.39 |

**3. Definers vs assignees and field coverage.** 183 archetype labels over 5,226 in-window decks.
**30 definers covering 83.8%** of the field (the brief measured 83.7%); **152 assignees**, so
**182 archetypes and 98.5% of the field are placed** (the brief measured 182 / 98.3%). Exactly
**one** archetype is unassigned — the literal label `Unknown`, at 2 core cards, refused by the
assignee floor with a named reason. The derived 14-card staple list matches the brief's verbatim:
Brainstorm, Daze, Flooded Strand, Flow State, Force of Will, Island, Lotus Petal, Misty Rainforest,
Polluted Delta, Ponder, Scalding Tarn, Thoughtseize, Underground Sea, Wasteland. Co-membership
stability **0.944** (>= 0.90); cophenetic correlation **0.916**, matching the brief exactly.

**4. The "plays blue" mega-cluster IS reproducible with hard staple removal disabled.** At the
brief's own height cut of 0.93, staples left in fuse **14 of 30 definers** into one cluster —
Aluren, Azorius Midrange, Azorius Stoneblade, Cephalid breakfast, Dimir Delver, Dimir Midrange,
Dimir Tempo, Doomsday, Grixis Midrange, Izzet Delver, Izzet Midrange, Jeskai Midrange, Show and
Tell, White Beanstalk. The brief's central justification is confirmed, and its "14 of 30" figure is
exact. Through the full shipped pipeline (AU cut applied) with staples left in it is worse still:
**K = 2, with 24 of 30 definers in one cluster.** With hard removal the largest cluster at the same
height cut is **7**. Note also that cophenetic correlation *rewards* the wrong answer — 0.945
without stripping vs 0.916 with — which is why the module treats it as a change tripwire only,
never an arbiter.

### Cut selection — the one place the shipped rule differs from the brief's wording

The brief says "the deepest height where each retained branch clears AU > 0.95". Measured, the
single-horizontal-cut reading does not work on this corpus: it is dominated by the weakest branch at
that height and returns **K = 25** (cut just below the first unsupported merge) or **K = 1** (the
root, which every bootstrap replicate reproduces by construction). Both sit outside the brief's own
K≈6-12 sanity band. Shipped instead as pvclust's `pvpick` semantics — descend from the root, retain
the largest eligible branch on each path, root excluded from candidacy — which is what "every
retained branch clears AU" means operationally, since retained branches need not share a height.

A second, larger discovery: **AU alone is not safe here.** Near-root branches show BP ≈ 0.02-0.15
that is essentially *flat across all ten scales*; with no scale signal the multiscale fit returns
curvature `d ≈ 0` and AU collapses to `Phi(v)`, handing 0.93-0.97 to branches observed in under a
tenth of resamples. Left unguarded that reassembles the mega-cluster the staple strip exists to
prevent — the failure arriving through the back door. Shipped guard: `_AU_MIN_BP = 0.30`, a raw
bootstrap-probability floor at scale 1.0 required in addition to the AU cut. A related fix inside
the fit itself: below `_MIN_FIT_POINTS = 3` usable scales the two-parameter model is an
interpolation dressed as an extrapolation (it scored AU 0.70 for a branch present in ~99% of every
resample), so the branch falls back to its mean BP.

Both are named module-level constants with the rationale at the definition site and both are CLI
flags, per the epic's provenance discipline.

### The honest read on the taxonomy's shape

**The derived layer is markedly more conservative than the brief's K≈8 operating point.** Only 5
branches clear the cut; 15 of 30 definers stay singletons. That is the evidence, not a bug: the
branches AU refuses are *precisely* the ones the brief itself flagged as chassis-driven artifacts
(Cephalid breakfast with the fair Azorius decks at AU 0.72, Red Stompy with Show and Tell at 0.79,
Grixis Reanimator with TES at 0.88, Golgari Landfall + Smallpox at 0.63). AU declining to assert
those is the method working. Red Stompy in particular is a singleton here rather than mis-fused into
the combo family, which is strictly better than the derived result the brief reports.

The consequence for the epic is real and should reach `-aggregation` planning: the pooling benefit
from the *derived* layer alone is narrower than the brief's coverage table projects, because that
table was computed at a fixed K=8 height cut rather than at the AU cut. Two levers exist and both
are one line: lower `--au-min` / `--min-bp`, or add curated clusters. The shipped curated registry
is deliberately empty so the derived behaviour is observable before anyone leans on overrides. One
known override candidate is already visible: `sa-007` pools Doomsday and TES with the fair Dimir
decks at BP 0.39, which is the weakest supported branch and the least defensible family in the run.

### The no-`rounds` property

Enforced three ways and tested (`tests/analytics/superarchetype/test_no_rounds.py`, 8 tests):
a **runtime SQL spy** proxy connection records every statement executed during a full
`run_superarchetypes` pass against a tmp DuckDB carrying a *populated* `rounds` table and asserts
none names `rounds`/`match_results`; a **source tripwire** scans both modules' executable source
(comments, docstrings and — the bug this caught — Python 3.12+ f-string parts stripped via
`tokenize`) for outcome tokens; and a **type check** asserts `ArchetypeDeck` carries exactly
`{archetype, key, cards}` and that no dataclass in the package exposes an outcome field. Each
enforcement has a companion test proving it would actually fire.

Deliberate related deviation: the `superarchetype` CLI group does **not** use
`resolve_advisory_window` (advisory-window-resolution-block), because that block's thin-regime
degrade counts `rounds` — the taxonomy must not be a function of match outcomes at any point,
including its window choice. Documented at the group definition.

### Verification

Full suite **3281 passed, 1 skipped** (89 of them new). `ruff check` on the new package and
`config.py`: **clean**. `cli.py` is a pure 259-line insertion at its pre-existing finding count
(ruff's `--fix` initially rewrote 39 unrelated pre-existing lines there; that churn was reverted and
the block re-applied). Determinism is pinned by unit tests and confirmed on the real corpus: two
seeded runs return an identical `ClusterSolution`, and two CLI `--dry-run` invocations produce
byte-identical output.
