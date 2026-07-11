---
id: epic-subarchetype-resolution-discovery-repr
kind: story
stage: review
tags: [analytics, archetype]
parent: epic-subarchetype-resolution-discovery
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Discovery: flex-band representation + reduction

## Brief
Units 1-2 of the discovery engine (see parent feature body). The DB-free flex-band feature-matrix
builder (`DeckVector`/`FeatureMatrix`, TF-IDF over `[flex_lo, flex_hi]` counts, L2-normalized, sorted
row order) and the injectable `reduce_dims` (TruncatedSVD default seeded; UMAP opt-in). Add
`scikit-learn` + `umap-learn` to `pyproject.toml`.

## Implementation
Parent feature `## Implementation Units` → Unit 1 (build_feature_matrix) + Unit 2 (reduce_dims), in
`src/legacy_engine/analytics/discovery.py`. Tests: `tests/analytics/test_discovery.py` — flex-band
selection, L2 norms, deterministic SVD shape/values (no DB).

## Implementation notes

- Landed `src/legacy_engine/analytics/discovery.py` with `DeckVector`, `FeatureMatrix`,
  `build_feature_matrix` (Unit 1), and `reduce_dims` (Unit 2). Module docstring pins the whole
  engine's shape (Units 1-4 land here across this story + `-cluster`).
- `build_feature_matrix`: per-card inclusion computed over the sorted-by-key deck pool; flex band
  = `[flex_lo, flex_hi]` inclusive; `<2` flex cards degrades to a fully empty `FeatureMatrix`
  (`keys=[]`, `cards=[]`, `X` shape `(0,0)`) — the caller (Unit 3/6) emits the honest "no
  separable structure" message rather than crashing on a degenerate matrix.
  `TfidfTransformer(norm="l2")` from scikit-learn produces the L2-normalized TF-IDF cells.
- `reduce_dims`: `TruncatedSVD(random_state=seed)` default; `umap` lazy-imported only when
  `method="umap"` is requested (verified with a monkeypatched `builtins.__import__` guard test
  that the `svd` path never imports `umap`). Pass-through when `n_features <= n_components`.
- **Deviation/clarification**: the spec's `min(n_components, n_features-1)` cap inside the SVD
  branch is a defensive no-op once you also honor the pass-through guard — entering the SVD
  branch already implies `n_features > n_components`, hence `n_features-1 >= n_components`
  always, so the min collapses to `n_components`. Kept the `min()` verbatim per spec (harmless,
  self-documenting), but the acceptance criterion "shape `(n, min(k, n_features-1))`" is
  equivalent to `(n, k)` in every reachable case — documented in the test docstring rather than
  silently "fixed" or removed.
- Dependencies: added `scikit-learn>=1.3` to core `dependencies` and `umap-learn` under
  `[project.optional-dependencies].discovery` in `pyproject.toml`. Both installed in `.venv` via
  `uv pip install --python .venv/bin/python ...` (the venv ships no `pip` module; `uv pip` is the
  working installer path in this environment). `umap-learn` installed cleanly (no numba build
  failure encountered here) — its smoke test still uses `pytest.importorskip("umap")` per the
  risk mitigation, so CI stays green even if a future environment can't build it.
- Tests: `tests/analytics/test_discovery.py`, 17 tests, all pure (no DB). Full suite
  (`pytest tests/ -q`) green: 2623 passed, 1 xfailed (pre-existing, unrelated).
