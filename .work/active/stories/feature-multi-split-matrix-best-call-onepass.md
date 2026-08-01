---
id: feature-multi-split-matrix-best-call-onepass
kind: story
stage: review
tags: [advisory]
parent: feature-multi-split-matrix
depends_on: [feature-multi-split-matrix-adaptive-window]
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-01
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

## Implementation notes

Branch `impl/multi-split-onepass`. Camp sweep migrated to ONE
`build_multi_split_adaptive(parents=staged_split_parents())` + one
`build_multi_split_matrix(parents=..., since=d)` per distinct per-pair
`max(parent_ban, opp_ban)` Nadu-rule date (6 windows on the live corpus, serving all 30
parents). `make_cells`/`row_stats` logic unchanged; camp rows read the multi-split cell
dict; `(camp, own_parent)` stays the unmeasured-row path.

**Live-DB old-vs-new camp-cell diff (the Unit 5 acceptance verification)** — both paths
run against the same DB snapshot (corpus through 2026-07-30, field since 2026-06-29,
defaults ground_n=8/top_k=8/cover_min=0.8/min_row_share=0.001): all 115 camp rows
**field-for-field identical** across 1,955 row fields and 8,855 opponent cells (`p`,
`raw`, `ci_low`, `ci_high`, `n`, `window`, `tier`, `measured` per cell, plus
adj/floor/agency/coverage/grounded/since/horizon/shares/_idx per row); the 94 archetype
rows byte-identical; meta differs only in the additive `rank` + `audit` keys.

**Wall-clock (same snapshot, same machine)** — old per-parent path: 337.0s total, camp
sweep 326.3s. One-pass path: 26.3s total; camp sweep 15.5s = 13.4s matrices + 2.0s
shared-field ranking. Sweep speedup ~21x (24.4x on the matrices-only portion, matching
the design's ~25x); acceptance "under ~30s" met. The script echoes each phase's time.

**Cross-camp P(best) (the restored number)** — one `rank_decks` MC, seed `RANK_SEED`
(20260731), 20k draws, parent-level Dirichlet field from the window counts; candidates =
all camp labels + unsplit field archetypes. Camp rows carry additive
`p_best`/`s_q`/`s_cov`/`s_caveated`; the camp table gains the P(best) column (Q25 chip,
S* below 85% coverage, n/a + coverage for gated rows); `meta.rank` + two `// multi-split`
/ `// cross-camp P(best)` audit-header lines carry provenance. Current-corpus top rows:
Dimir Tempo [Barrowgoyf] 0.274, Doomsday [unlabeled] 0.226, Energy [Sand Scout] 0.208,
Blue Artifacts [Thoughtseize] 0.128 (26/115 camp rows ranked, 34/163 candidates).

**Two design-judgment deviations from the Unit 5 sketch (empirical findings, logged):**
1. *Ranking basis*: the literal `msm.ranking_view()` (era-windowed adaptive cells) puts
   114/115 camps at data_coverage ≈ 0 (camp era cells are n<30 nearly everywhere) — the
   whole column suppresses and one zero-coverage camp degenerates to p_best=1.0. The MC
   instead ranks on the PAGE-USED cells (the ledger's own era-preferred, ban-scoped
   fallback selection, captured via `make_cells(out_used=...)`) — same shared-field
   comparability, same Nadu windows the page already stands on.
2. *Candidacy gate*: with zero-coverage candidates included, 100% of the P(best) mass
   lands on suppressed rows (imputation-noise argmax; suppressing display does not remove
   them from the shared budget). Candidacy is now gated at `_PBEST_SUPPRESS_COVERAGE`
   (the same 5% threshold that gates display); excluded rows carry `p_best=None` with
   `s_cov` as the visible reason.

**Hermetic tests** (`tests/test_refresh_best_call_ranking.py`, 11 tests, ~2s): the
retired per-parent path reconstructed verbatim in-test and diffed field-for-field against
`compute_blob` over 3 parametrizations on a two-parent fixture extended with a pre-ban
rounds-bearing Painter/Entomb tournament + a camp-exact era row (all three window sources
— era / BA / FC — in actual use); the Nadu-rule cell pinned numerically
((Painter [Grindstone], Control) = BA 2025-11-10 n=15, never FC n=30); candidacy/caveat
gate semantics; shared p_best budget <= 1; whole-blob determinism under the fixed seed;
`main()` end-to-end render against a tmp file DB. **Non-vacuity proven** by a
symbol-anchored mutation (`subj_ban=p_ban -> subj_ban=None` in the camp `make_cells`
call): all 3 parity parametrizations + the Nadu pin fail (window flips BA->FC, n 15->30),
then reverted to green.

Docs rolled: `docs/analysis/best-call-ranking.md` (one-pass method, P(best) column,
timing), `docs/ARCHITECTURE.md` window.py row (`build_multi_split_inputs`; the matchup.py
row was rolled by the sibling stories), knowledge index regenerated.
