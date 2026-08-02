---
id: story-deep-review-followups
kind: story
stage: implementing
tags: [analytics, cleanup]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-01
updated: 2026-08-01
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
