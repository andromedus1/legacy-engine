---
id: story-deep-review-followups
kind: story
stage: review
tags: [analytics, cleanup]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-01
updated: 2026-08-02
---

# Deep-review follow-ups (2026-08-01, 7-feature post-merge review)

## Brief

Findings batch from `docs/reviews/2026-08-01-shipped-features-deep-review.md` (all verdicts
APPROVE or APPROVE-WITH-FOLLOWUPS; the golden re-pin was fully exonerated — the reviewer
reconstructed the original full-precision canonicalization and reproduced the pre-mutation sha
exactly). File:line refs verified at review time.

1. **aggregate.py provenance honesty (HIGH — blocks nothing but lies today):** refused pooled
   cells carry a `served with concentration label:` provenance string (aggregate.py:866-870);
   served not-computable cells carry no heterogeneity label in provenance (aggregate.py:790-792).
   Renderers were warned to read typed fields; fix the strings so provenance matches the verdict.
2. **Registry window decision (HIGHEST VALUE):** the serving registry (2026-05-11) predates the
   regime start (2026-06-29); the stale-taxonomy warning fires on every build. Naive re-run at
   --since 2026-06-29 thins definers drastically (~1900 decks) — decide the serving window with
   eyes open, or accelerate epic-superarchetype-layer-era-core-pools (the principled fix).
   Re-check the license/imputation landscape after any regeneration.
3. **matchup-plan-flex silent degrade (sideboard.py:2659-2661):** a `_resolve_land_names` DB
   failure resurrects the land-cut bug at log.debug with no plan-note trace — the feature's own
   headline defect returning invisibly. Needs a named degrade note on the plan.
4. **Vacuous/weak tests:** golden readable-diff self-compares float fields
   (test_matchup_superarchetype_golden.py:111-117); n_eff monotonicity tested at fixed logit_mean
   only (test_aggregate.py:198-207); dilution fixtures mask the missing not-computable provenance
   label (test_aggregate.py:522-543); family-first override branch has zero execution coverage
   (matchup.py:1244-1257 — only the frozenset() assert).
5. **Note hygiene:** chain's "557 imputations, all sa-003" rotted within hours (573 across
   sa-003 + sac-001 after PR #75) — timestamp real-corpus snapshots in implementation notes as a
   convention.

## Implementation progress

### Unit 1 — aggregate provenance honesty

Fixed the typed-verdict/provenance mismatch before any further renderer work. A heterogeneity-
refused cell now says `refused with concentration label:` when concentration also fails; it never
claims that label was served. A served `not-computable` heterogeneity cell now carries
`served with heterogeneity label: <typed reason>` instead of omitting the verdict from provenance.
Regression coverage pins both directions against the typed `Heterogeneity.band` and
`Concentration.passed` fields. Verification: `99 passed` in
`tests/analytics/superarchetype/test_aggregate.py`.

### Unit 2 — fail-safe land resolution

Added a checked land-type lookup while preserving `_resolve_land_names` as the compatibility
wrapper. Both the direct planner path and `recommend_sideboard` now carry lookup failure into
`_plan_matchups`, which returns a named `land-resolution-failed` degraded plan with no swaps for
every opponent. The missing-table regression proves a land can never become eligible merely
because the `cards` lookup failed. Two pre-existing pure planner fixtures now inject their known
empty land set explicitly instead of accidentally depending on a missing table.

### Unit 3 — review-test integrity and snapshot hygiene

- Replaced the golden representative cell's self-compared floats with independent exact expected
  values while retaining the full-output hash.
- Replaced the fixed-`logit_mean` partial-derivative `n_eff` test with a joint-estimator sequence
  over observed member tallies whose fitted heterogeneity rises as effective sample falls.
- Added a real builder test that enables `FAMILY_FIRST_KINDS` for a stored young release era and
  proves the family-current imputation branch sets the prior and source label.
- Timestamped and config-stamped the chain feature's original real-corpus spot check so its 557
  imputation count is explicitly historical rather than a timeless assertion.

### Integrated verification and bounded review

- Focused sideboard verification: 7 passed.
- Superarchetype golden/aggregation/chain verification: 122 passed.
- Full suite: 3,522 passed, 1 warning (UMAP's existing seeded `n_jobs` warning).
- `git diff --check`: clean.

Bounded inline review found no remaining correctness blocker in this story's changed surfaces.
The serving-registry decision remains intentionally outside this cleanup story and continues in
`epic-superarchetype-layer-era-core-pools`; the three-level page remains gated on that output.

## Next capability step

Do not naively rebuild the registry from the thin 2026-06-29 global window. Advance
`epic-superarchetype-layer-era-core-pools` through design and its offline representation benchmark,
then select a validated serving method, generate a new preview, and obtain user approval before the
three-level page uses superarchetype output as a headline ranking.
