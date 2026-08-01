---
id: idea-adj-field-wr-recompute-divergence
created: 2026-07-31
tags: [analytics, honesty, agency-page]
---

An independent hand-rolled recompute of Cradle Control's matchup cells disagrees with the
best-call page's cells by ~4 points on the same field weighting. Worth reconciling — either
the ad-hoc SQL is wrong or the page's per-cell window selection is biased favorably.

**Page (from the 2026-07-31 screenshot), field-weighted over the 12 measured top-field
opponents (64.4 share-points):**
- shrunk cells → **54.4** (reproduces the page's published ADJ FIELD WR 54.3 ✓ — formula confirmed:
  field-weighted mean of shrunk cells, measured opponents only)
- the page's own RAW cells → **53.8** (so shrinkage contributes only ~+0.6 here, NOT the driver)

**Independent recompute** (bare `Cradle Control` label, rounds table, match-win parsing
`split_part(result,'-',1) > split_part(result,'-',2)`), same 12 opponents, same share weights:
- since 2024-12-16 → **49.0%**
- 2026 YTD → **50.0%**

**Per-cell disagreements (mine vs page raw):** Death & Taxes 41.5% n=41 vs 60.0% n=50 (page FC);
Energy 40.0% n=25 vs 52.6% n=19; Azorius Midrange 58.8% n=17 vs 68.8% n=16; Dimir Tempo 38.9%
n=108 vs 45.6% n=92; Show and Tell 47.6% n=84 vs 30.0% n=10 (page used the narrow `era` window
here). Note the pattern: my n is often LARGER while my WR is LOWER — consistent with either
(a) the page's per-cell window selection excluding stretches where Cradle did badly, or (b) a
double-count/mismatch in the ad-hoc join, or (c) different match-counting (draws/byes/dedupe).

Cells that agree closely: Izzet Delver 61.4 n=88 vs 62.5 n=88; Lands 60.6 n=33 vs 60.6 n=33;
TES 45.5 n=11 vs 45.5 n=11 — so the methods agree exactly where windows coincide, which points
at window selection rather than the counting primitive.

**Why it matters:** ADJ FIELD WR is a headline column users sort by. If per-cell maximal windows
can systematically favor a deck's historical good stretches, the column needs either a
recency-decay term or a companion "same-window recompute" honesty check. Pairs with
[[idea-verdict-stability-column]] (rank stability across estimators) and
[[feature-ranking-honesty-guards]].

**Reproduce:** scratchpad script pattern is in the 2026-07-31 session; rebuild by computing
per-opponent cells for `Cradle Control` at windows {full, 2024-12-16, 2026-01-01, 2026-05-11}
and field-weighting by current-regime share.
