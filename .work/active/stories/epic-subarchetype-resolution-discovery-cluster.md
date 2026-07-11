---
id: epic-subarchetype-resolution-discovery-cluster
kind: story
stage: review
tags: [analytics, archetype]
parent: epic-subarchetype-resolution-discovery
depends_on: [epic-subarchetype-resolution-discovery-repr]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Discovery: HDBSCAN clustering + two-gate validation + naming

## Brief
Units 3-4 — the trickiest core. `cluster_and_validate` (HDBSCAN on the reduced embedding; Gate A
bootstrap co-membership stability ≥0.9 + silhouette diagnostic; Gate B both-camp evolving tier +
signature divergence via reused `subgroup.diff_compositions`, ≥2 cards |Δ|≥0.75; double-dipping guard;
auto-naming) and the thin DB wrapper `discover_subarchetypes(con, archetype, …)`.

## Implementation
Parent feature `## Implementation Units` → Unit 3 (cluster_and_validate, `DiscoveredSplit`/`Camp`) +
Unit 4 (DB wrapper), in `src/legacy_engine/analytics/discovery.py`. Tests (no DB for Unit 3): clean
2-camp split passes; blob → FAIL "single cluster"; 300/12 → FAIL "below evolving floor"; determinism.
Unit 4 hermetic with a seeded two-camp pool.

## Implementation notes

- Landed `Camp`, `DiscoveredSplit`, `cluster_and_validate` (Unit 3), and `discover_subarchetypes`
  (Unit 4) in `src/legacy_engine/analytics/discovery.py`. `parent` is threaded through via
  `dataclasses.replace(split, parent=archetype)` in the DB wrapper — `cluster_and_validate` itself
  has no notion of the archetype label (matches the exact Unit 3 signature, which doesn't take a
  `parent` argument), so the pure core always constructs `DiscoveredSplit(parent="", ...)` and
  the wrapper stamps it afterward.
- **Naming**: for exactly 2 camps, the single most-divergent flex-band card (top `|Δ|` from one
  `diff_compositions` call between the two camps) decides the pairing — whichever camp has the
  positive delta gets `<card>`, the other gets `non-<card>` (mirrors the shipped
  Bauble/non-Bauble convention). For 3+ camps, each camp is named by its own top *positive*-delta
  card vs. the pooled rest (falls back to `camp-{idx}` if a camp has no positive-delta card at
  all — a documented, not-yet-observed edge case). `Camp.signature_cards` stores the *full*
  `diff_compositions` output (not just a top-N slice) since Gate B's divergence count needs the
  complete list, not a display-truncated one; the CLI (`-cli` story) truncates for display.
- **Gate A** (`_bootstrap_stability`): resamples rows with replacement `n_boot` times, re-clusters
  each resample with the same `min_cluster_size`, and averages pairwise co-membership agreement
  against the base labeling restricted to pairs non-noise in *both* labelings. Vectorized via
  numpy broadcasting (`O(n^2)` per resample) — trivial at corpus scale (≤2500 decks) per the
  parent feature's Risks section.
- **Gate B** (`_gate_b_domain`): pulled out as a standalone, directly-testable pure function
  taking `list[Camp]` — see the next bullet for why that was necessary, not just a style choice.
- **Design finding — HDBSCAN's `min_cluster_size` floor makes one of the four spec'd Unit-3
  acceptance scenarios only reachable by testing a sub-piece directly, not the full pipeline.**
  `min_cluster_size = max(30, round(0.10*n))` (the design decision, verbatim) has a hard floor of
  30 — HDBSCAN *by construction* can never emit a non-noise cluster smaller than that. So a
  literal "300/12 split -> Gate B fails on the 12-camp for being below the evolving floor" can
  never happen by running the actual clusterer (HDBSCAN would simply mark those 12 points as
  noise, giving a *different* honest reason: "single cluster" or "no clusters found", not "camp
  below evolving floor"). Resolution: extracted `_gate_b_domain(camps, ...)` as an independently
  callable pure function (same spirit as `_greedy_tune` in the objective-search-split pattern) and
  tested the below-floor scenario directly against it with hand-built `Camp` objects
  (`TestGateBDomainDirect`). This is a strictly stronger test than trying to force the scenario
  through HDBSCAN — it exercises Gate B's exact threshold logic without depending on clustering
  internals cooperating. Not escalated as a design flaw (the validation logic is correct and now
  more thoroughly covered), but flagged per the "note deviations" instruction since the acceptance
  criterion's literal wording implied an end-to-end test.
- **`allow_single_cluster=True`** on both HDBSCAN calls (base + bootstrap). Discovered empirically:
  HDBSCAN's default (`allow_single_cluster=False`) *refuses* to ever emit one all-encompassing
  cluster — a genuinely homogeneous parent (no real split) comes back 100% noise instead of "1
  cluster". That's a strictly less legible honest-degrade signal than "single cluster, no
  separable structure," and scenario (b) in the spec explicitly wants the latter wording.
  Verified this doesn't blur genuine splits: the two-well-separated-camps fixture still resolves
  to exactly 2 clusters with the flag on (`TestClusterAndValidateCleanSplit`), so Gate B's own
  `>=2 camps` check — not HDBSCAN's refusal — is what rejects the homogeneous case.
- Also added `copy=True` explicitly to both HDBSCAN calls to silence a scikit-learn 1.9
  `FutureWarning` about the `copy` default changing in 1.10 (harmless now, but keeps test output
  clean and avoids a silent behavior change on a future sklearn upgrade).
- Tests appended to `tests/analytics/test_discovery.py` (all pure, no DB, for Unit 3; in-memory
  DuckDB via `store.connect(":memory:")` for Unit 4 — no file-backed DB needed since Unit 4 has no
  CLI surface yet, that lands in `-cli`). 34 tests total in the file (17 from `-repr` + 17 new).
  Full suite (`pytest tests/ -q`) green: 2640 passed, 1 xfailed (pre-existing, unrelated).

## Orchestrator fix (post-wave verification, 2026-07-11)

Ground-truth dogfood (Doomsday, the brief's validated 292/878 split) initially returned
single-cluster + 47% noise. Root cause: `min_samples` silently inherited
`min_cluster_size` (117 at n=1170 — hyper-conservative density per the hdbscan docs) and
`allow_single_cluster=True` introduced a root-cluster bias. Fix: decoupled `min_samples`
(default 10, exposed as `--min-samples`, mirrored into the Gate-A bootstrap so stability
stresses the same clusterer) and reverted to sklearn's `allow_single_cluster=False` (both
k<2 outcomes report an honest "no separable structure" reason). Blob acceptance test
updated to assert the honest-FAIL essence rather than the single-cluster mechanism.
Post-fix dogfood: PASS — rediscovers the Tempo camp (n=239: Tamiyo +3.21, Wasteland
+2.07, Murktide +1.48) and Turbo camp (n=417: Personal Tutor +3.05), plus a third
established Flow State camp (n=172) the manual split had pooled; stability 0.980.
