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

## Session handoff — 2026-08-01 FINAL WRAP

Resume on branch `fix/deep-review-followups`. The completed work is split into committed units:

- `1a26452` closes the already-merged best-call fallback substrate item (PR #76).
- `a2b86a1` implements this story's Unit 1 provenance-honesty fix and tests it.

The next unit is finding 3, the matchup-plan land-resolution failure. Start at
`src/legacy_engine/advisory/sideboard.py` in `_resolve_land_names` and `_plan_matchups`; the main
caller resolves land names once near the matchup-plan build. Today a cards-table/query failure
returns an empty set and silently makes lands eligible cuts. Preserve the compatibility wrapper if
useful, but carry an explicit resolution failure into `_plan_matchups`. The safe behavior is a
named degraded plan with no swaps—not an unsafe plan built from an empty exemption set. Inspect the
closed `plan_status` vocabulary before adding or reusing a status. Existing focused coverage starts
near `tests/test_sideboard.py`'s `test_resolve_land_names_degrades_on_missing_table` and land-never-
sided-out tests.

After that, finish findings 4 and 5 in small committed units: replace the golden float self-
comparison with an independent expected/canonical check; broaden `n_eff` monotonicity beyond one
fixed `logit_mean`; execute the family-first override branch; and establish timestamped real-corpus
snapshot wording. The dilution/provenance gap from finding 4 is already covered by Unit 1.

For finding 2, do not naively rebuild the registry from the thin 2026-06-29 window. Record the
serving decision and advance `epic-superarchetype-layer-era-core-pools`, consistent with the merged
methodology research in PR #77. The failed preview means the three-level page remains blocked: first
implement and run the offline representation benchmark, select a validated method, generate a new
preview, and obtain user approval. `story-readme-repo-currency` remains last.

Operational constraints for resume:

- All GitHub operations must authenticate as `andromedus1`; verify with an explicit per-command
  token before any PR or merge. The canonical remote is
  `https://github.com/andromedus1/legacy-engine.git`.
- Keep commit-per-unit. Merge substrate-carrying branches; never rebase them.
- Render superarchetype verdicts from typed fields, never provenance prose.
- Run the full suite before moving this story to review. If GitHub reports no checks, re-push so CI
  actually fires. Use 12-significant-figure float canonicalization for any new goldens.
- `.claude/scratch/` is unrelated untracked user material and must remain untouched and uncommitted.
