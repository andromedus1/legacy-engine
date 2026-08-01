---
id: epic-superarchetype-layer-clustering
kind: feature
stage: drafting
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
