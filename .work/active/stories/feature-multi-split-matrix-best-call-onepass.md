---
id: feature-multi-split-matrix-best-call-onepass
kind: story
stage: implementing
tags: [advisory]
parent: feature-multi-split-matrix
depends_on: [feature-multi-split-matrix-adaptive-window]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
---

# Best-call page one-pass migration + cross-camp P(best)

## Brief

Migrate `scripts/refresh_best_call_ranking.py`'s camp sweep from ~30 per-parent split builds
(~4-5 min) to one `build_multi_split_adaptive` + one `build_multi_split_matrix` per distinct
Nadu-rule fallback date (~12s), keeping `make_cells` logic and the per-pair
`max(subj_ban, opp_ban)` fallback-window invariant byte-identical (one-off live-DB old-vs-new
camp-cell diff logged here as verification). Then restore the omitted number: ONE shared-field
`rank_decks` over `ranking_view()` with candidates = all camp labels + unsplit field archetypes
and a parent-level Dirichlet field (fixed seed) -> per-row `p_best` + `s_quantile` +
`data_coverage` in the camp blob, with a P(best) column in the template gated by the existing
coverage-suppression conventions. Roll docs forward: `docs/analysis/best-call-ranking.md`
runbook + `docs/ARCHITECTURE.md` matchup/window rows, then `/knowledge-index`.

## Implementation

Parent feature `feature-multi-split-matrix` — Unit 5 of `## Implementation Units` (exact
notes and acceptance criteria there). Files: `scripts/refresh_best_call_ranking.py`,
`scripts/best_call_ranking_template.html`, the two docs. Engine guarantees come from the
sibling stories' hermetic parity tests; this story's live-DB diff is a one-off implementation
verification, not a committed test.
