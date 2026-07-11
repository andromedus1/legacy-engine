---
id: epic-subarchetype-resolution-discovery
kind: feature
stage: implementing
tags: [analytics, archetype]
parent: epic-subarchetype-resolution
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Subarchetype discovery engine

## Brief

The research-gated core of the epic: a data-driven engine that discovers play-pattern subarchetypes
*within* a single parent archetype at corpus scale, validates them statistically, auto-names them from
signature cards, and stages the survivors as **candidate** variant splits for human promotion. It
delivers a `discover` CLI surface (report candidate splits for an archetype, with per-camp stats) and a
`promote` step that moves a confirmed split into the curated `data/variants/legacy.json`. It does NOT
change any existing analytics output — that is the two consumer features. It does NOT silently rewrite
the curated taxonomy — discovery only ever produces candidates in a staging registry.

Method is fully pinned by the attested brief `docs/briefs/subarchetype-discovery.md`: build the
per-parent feature matrix over the **flex band** (drop the ubiquitous core and rare tail by inclusion
thresholds), TF-IDF/count representation, reduce (TruncatedSVD/UMAP), cluster with **HDBSCAN**
(self-determines k, labels outlier brews as noise) on the reduced embedding, then gate each split
through BOTH a statistical gate (resampling stability >0.9 / prediction strength >0.8; internal indices
secondary) AND the domain gate the engine already trusts (both camps reach evolving tier n≥30; large
signature-card inclusion/copy divergence). Guard against the double-dipping trap (no naive significance
test on the clustered data). Auto-name from top signature cards.

## Epic context

- Parent epic: `epic-subarchetype-resolution`
- Position in epic: **foundation feature** — both consumer features (`-matchup-cells`, `-card-winrate`)
  depend on the `decks.variant` labels this engine produces (discovery-first, per the epic decision).

## Inherited design decisions

From the parent epic's `## Design decisions` (fixed inputs — do not re-ask):
- **Deps**: scikit-learn **+ umap-learn** (sklearn ships HDBSCAN ≥1.3, TruncatedSVD, TF-IDF, silhouette;
  umap-learn adds the UMAP reduction — accept the numba build weight). Add to `pyproject.toml`.
- **Human-confirm hook**: `discover` → **staging registry** → `promote`. Candidates land in a staging
  registry (status: candidate) that analytics can read as labeled-speculative; `promote` moves a
  confirmed split into curated `data/variants/legacy.json`. Never auto-rewrite the curated taxonomy.
- Honesty: candidate splits and their camps carry sample-tier labels; nothing thin is hidden.

## Research briefs

- `docs/briefs/subarchetype-discovery.md` (attested) — the method SSOT: §2 representation, §3 distance,
  §4 algorithm (HDBSCAN primary), §5 two-gate validation + double-dipping guard, §6 auto-naming, §8
  implementation notes (build on `subgroup.py`, `variants.py`, `decks.variant`; runs offline as a
  labeling pass sibling to `label`).

## Foundation references

- `docs/ARCHITECTURE.md` — `archetype/` subsystem (`variants.py` curated registry; the discovery
  engine is its data-driven front-end) and `analytics/subgroup.py` (`report subgroup` — the existing
  single-axis discovery front-end this generalizes; already computes signature-card divergence).
- `data/variants/legacy.json` — the curated registry (promotion target); `decks.variant` — persistence.

## Notes for /feature-design

- Split into child stories if it exceeds one implement pass: candidate seams are (a) feature-matrix +
  representation + reduction, (b) HDBSCAN + validation gates, (c) auto-naming + staging registry +
  `discover`/`promote` CLI. Keep the pure clustering/validation logic DB-free and unit-testable with
  hand-built inputs (objective-search-split pattern).
- Reuse `subgroup.py`'s divergence computation for Gate B. New CLI leaves follow the nested-group +
  fail-loud-stub pattern; audit-echo `// ...` provenance lines for the discovery report.
- Hermetic CLI tests pass `--db <tmp>`, never the default DB.

## Design decisions

Resolved with judgment under autopilot (brief + epic decisions pin the rest):
- **Module placement**: pure logic in `analytics/discovery.py` (DB-free: matrix build from
  hand-supplied deck-card rows → reduce → cluster → validate → name; objective-search-split pattern),
  with a thin DB-reading wrapper. Staging-registry model in `models/variant.py`; loader + promotion in
  `archetype/discovered.py` (sibling of `variants.py`). CLI in a new top-level `discover` group.
- **Reduction default = TruncatedSVD** (`random_state=seed`, deterministic, no numba); **UMAP opt-in**
  via `--reducer umap`. Rationale: reproducible tests + no CI numba flakiness; UMAP is installed (epic
  dep) but not the default. Honors "both deps" while defaulting to the safe/deterministic one.
- **Representation** = TF-IDF over flex-band **counts**, L2-normalized; cosine on the reduced embedding.
  Flex band = per-parent inclusion in `[flex_lo, flex_hi]` (default `[0.10, 0.95]`), configurable.
- **Clustering** = `sklearn.cluster.HDBSCAN` (ships in sklearn ≥1.3 — no separate `hdbscan` pkg),
  `min_cluster_size = max(30, round(0.10*n))` (ties the smallest camp to the evolving floor), noise = -1.
- **Validation** = Gate A (statistical): bootstrap **co-membership stability** over `B=50` resamples,
  threshold **0.9**; silhouette reported as a secondary diagnostic only (HDBSCAN is non-convex, so it
  does not gate). Gate B (domain): both camps `n≥30` AND signature divergence via the reused
  `subgroup.diff_compositions` — require **≥2 flex cards with |Δ|≥0.75 copies**. Double-dipping guard:
  stability is the *only* significance-style test and it is resampling-based; **no naive t-test/chi-square
  on the clustered data** (explicit, per brief §5).
- **Auto-naming** follows the existing registry convention (`Bauble`/`non-Bauble`): name each camp by
  its top over-represented signature card; the 2-camp case names `<card>` / `non-<card>`.
- **Determinism**: sort decks by `(tournament_id, deck_idx)` before matrix build; seed every RNG
  (`--seed`, default 0). HDBSCAN is deterministic given fixed input order.
- **Staging**: `data/variants/discovered.json` (derived side, DATA_DIR) — `DiscoveredSplit` records
  with `status: candidate`; `discover promote` converts a camp set into `VariantRule` entries appended
  to the curated package `src/legacy_engine/data/variants/legacy.json` (+ `defaults` for the complement).

## Architectural choice

Options weighed: **(A)** one monolithic `discover()` doing DB→matrix→cluster→validate→write; **(B)** a
DB-free pure core (`analytics/discovery.py`) fed a plain deck-card structure + injected reducer/clusterer,
with a thin DB wrapper and a separate registry/promotion module; **(C)** fold discovery into
`subgroup.py`. Chose **(B)** — it mirrors the project's objective-search-split pattern (heavy DB read
once → plain dict → pure, unit-testable loop), keeps scikit-learn/umap confined to the pure core so the
clustering/validation is testable with hand-built matrices and no DB, and keeps the curated-registry
concern (`archetype/discovered.py`) separate from the compute. (C) was rejected: `subgroup.py` is a
single-axis diff, not a clustering engine; discovery *reuses* its `diff_compositions` for Gate B but is
a distinct capability.

## Implementation Units

### Unit 1 — Flex-band feature matrix (pure)
**File**: `src/legacy_engine/analytics/discovery.py` · **Story**: `-repr`
```python
@dataclass(frozen=True)
class DeckVector:
    key: tuple[str, int]              # (tournament_id, deck_idx), for stable ordering
    counts: dict[str, int]            # mainboard card -> copies

@dataclass(frozen=True)
class FeatureMatrix:
    keys: list[tuple[str, int]]       # row order (sorted)
    cards: list[str]                  # flex-band column order
    X: "np.ndarray"                   # shape (n_decks, n_flex), TF-IDF, L2-normalized

def build_feature_matrix(decks: list[DeckVector], *, flex_lo: float = 0.10,
                         flex_hi: float = 0.95) -> FeatureMatrix: ...
```
**Notes**: compute per-card inclusion over `decks`; keep cards with `flex_lo ≤ incl ≤ flex_hi`; build
count matrix in sorted key order; `TfidfTransformer(norm="l2")`. Degrade: if <2 flex cards, return an
empty matrix (caller emits "no separable structure").
**Acceptance**: given hand-built decks with 1 ubiquitous + 1 rare + 2 flex cards, columns == the 2 flex
cards; rows in sorted key order; L2 row norms ≈ 1.

### Unit 2 — Reducer (pure, injectable)
**File**: `src/legacy_engine/analytics/discovery.py` · **Story**: `-repr`
```python
def reduce_dims(X, *, method: str = "svd", n_components: int = 10, seed: int = 0): ...
```
**Notes**: `svd` → `TruncatedSVD(n_components=min(n_components, n_features-1), random_state=seed)`;
`umap` → `umap.UMAP(n_components=n_components, random_state=seed)`. `n_components` auto-capped below
n_features. If `n_features ≤ n_components`, pass through (no reduction).
**Acceptance**: `svd` output shape `(n, min(k, n_features-1))`; identical across two runs (deterministic).

### Unit 3 — Cluster + validate + name (pure — the trickiest unit)
**File**: `src/legacy_engine/analytics/discovery.py` · **Story**: `-cluster`
```python
@dataclass(frozen=True)
class Camp:
    name: str
    member_keys: list[tuple[str, int]]
    signature_cards: list[tuple[str, float]]   # (card, delta) top divergent, desc
    n: int
    tier: ConfidenceLevel

@dataclass(frozen=True)
class DiscoveredSplit:
    parent: str
    camps: list[Camp]
    n_noise: int
    stability: float           # mean bootstrap co-membership agreement
    silhouette: float | None   # secondary diagnostic
    passed: bool               # Gate A AND Gate B
    reasons: list[str]         # why passed / failed (honest-degrade labels)

def cluster_and_validate(fm: FeatureMatrix, decks: list[DeckVector], *,
                         reducer=reduce_dims, seed: int = 0, n_boot: int = 50,
                         stability_min: float = 0.90, min_delta: float = 0.75,
                         min_sig_cards: int = 2) -> DiscoveredSplit: ...
```
**Notes**: reduce → `HDBSCAN(min_cluster_size=max(30, round(0.10*n))).fit`; drop noise(-1). Gate A:
resample rows with replacement `n_boot` times, re-cluster, average pairwise co-membership agreement vs
the base labeling (only over non-noise pairs); `stability ≥ stability_min`. Gate B: every camp
`tier != speculative` (n≥30) AND `sum(1 for c,d in sig if abs(d) ≥ min_delta) ≥ min_sig_cards`, where
`sig` comes from `subgroup.diff_compositions` run per camp vs the rest. Naming: top |delta| card per
camp; 2-camp → `<card>` / `non-<card>`. **No p-value test on clustered data** (guard). `reasons`
records each gate outcome verbatim for the honest-degrade report.
**Acceptance**: (a) two hand-built well-separated camps (distinct flex signatures, n≥30 each) →
`passed=True`, 2 camps, correct names; (b) one blob → 1 cluster, `passed=False`, reason "single cluster";
(c) a 300/12 split → `passed=False`, reason "camp below evolving floor"; (d) deterministic across runs.

### Unit 4 — DB wrapper
**File**: `src/legacy_engine/analytics/discovery.py` · **Story**: `-cluster`
```python
def discover_subarchetypes(con, archetype: str, *, since: str | None = None,
                           **params) -> DiscoveredSplit: ...
```
**Notes**: query mainboard deck-card rows for the parent's in-window pool → `list[DeckVector]` → call
the pure pipeline. Read-only.

### Unit 5 — Staging registry model + loader/promotion
**Files**: `src/legacy_engine/models/variant.py` (models), `src/legacy_engine/archetype/discovered.py`
(loader/promotion) · **Story**: `-cli`
```python
class DiscoveredCamp(LegacyEngineModel):
    name: str; signature_cards: list[str]; n: int; tier: str
class DiscoveredSplitRecord(LegacyEngineModel):
    parent: str; generated_from: str; params: dict; camps: list[DiscoveredCamp]
    stability: float; status: str = "candidate"
class DiscoveredRegistry(LegacyEngineModel):
    version: str; splits: list[DiscoveredSplitRecord] = []

def load_discovered(path) -> DiscoveredRegistry            # curated-json-resource-loader pattern
def stage_split(reg, split) -> DiscoveredRegistry          # upsert by parent
def promote_split(parent, camp_name, discovered_path, registry_path) -> None
    # convert the chosen split's camps -> VariantRule entries appended to legacy.json + defaults
```
**Notes**: `DISCOVERED_VARIANTS_PATH = DATA_DIR/"variants"/"discovered.json"` (new `config.py` const).
Promotion builds `InMainboard` conditions from each camp's top signature card, mirroring existing
registry entries; complement → `defaults[parent]`. Fail-fast on unknown parent / already-promoted.

### Unit 6 — `discover` CLI group
**File**: `src/legacy_engine/cli.py` · **Story**: `-cli`
```
discover run --archetype X [--since] [--reducer svd|umap] [--seed] [--db]   # compute + stage + report
discover list                                                               # show staged candidates
discover promote --archetype X --variant NAME                               # curate into legacy.json
```
**Notes**: nested-group + fail-loud-stub pattern; `_setup_logging(verbose)` first; audit-echo `// ...`
provenance lines (window, params, stability, per-camp n+tier, gate reasons, PASS/FAIL). `run` prints the
honest-degrade report even on FAIL (never silently drops a rejected split).

## Implementation Order
1. Unit 1 (matrix) — foundation, everything hangs on the flex-band representation.
2. Unit 2 (reducer) — injected into Unit 3.
3. Unit 3 (cluster+validate+name) — the trickiest; validates feasibility of the whole feature.
4. Unit 4 (DB wrapper) — thin, once the pure core is proven.
5. Unit 5 (staging/promotion) — depends on the DiscoveredSplit shape from Unit 3.
6. Unit 6 (CLI) — wires it together.

## Testing
- **Unit 1-3 (pure, no DB)** `tests/analytics/test_discovery.py`: hand-built `DeckVector` lists —
  flex-band selection, deterministic reduction, the four Unit-3 acceptance scenarios (clean split /
  blob / lopsided / determinism). This is the bulk of the coverage; no DB needed.
- **Unit 4** hermetic: `_build_discovery_db(tmp_path)` with a seeded two-camp Doomsday-like pool.
- **Unit 5** `tests/archetype/test_discovered.py`: load/stage/promote round-trip; promotion appends
  valid `VariantRule`s + sets defaults; fail-fast paths.
- **Unit 6** hermetic CLI: `discover run --db <tmp>` (never default DB) → staged file + report;
  `promote` → legacy.json entry; FAIL split still prints the honest report.

## Risks
- **umap-learn/numba in CI** — mitigated: SVD is the default and UMAP is opt-in, so CI green does not
  depend on numba; a UMAP smoke test is `skipif` when import fails.
- **Bootstrap stability cost** — `n_boot=50` re-clusters per discovery; parents are ≤~2500 decks over
  ≤~35 dims, so this is seconds, offline. Fallback: expose `--n-boot`, allow lowering.
- **HDBSCAN finds >2 camps** — design handles k≥2 (name each by top signature); Gate B applies per camp,
  so a spurious 3rd thin camp fails the tier check and the split is reported FAIL with the reason.
