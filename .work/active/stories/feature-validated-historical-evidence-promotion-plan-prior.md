---
id: feature-validated-historical-evidence-promotion-plan-prior
kind: story
stage: done
tags: [analytics, advisory]
parent: feature-validated-historical-evidence-promotion
depends_on: [feature-deck-rankings]
release_binding: null
created: 2026-09-05
updated: 2026-09-05
---

# Test opponent-plan borrowing for sparse matchup floors

## Design refinement
Prior-strength scaling alone cannot change a zero-observation matchup's mean. Add one fixed challenger that uses actual opponent-specific clean historical evidence, before opening any confirmation outcomes. This is the fourth fixed model comparison, not a tuned response to confirmation results. Grounding: existing clean interval corpus and strategic-family-ladder target exclusion; curated analytics.strategy_plan primary assignments.

## Implementation
Host owns advisory/plan_borrowing.py and its tests, independent of the worker's projection/evaluator files. `build_plan_borrowing_priors(corpus: IntervalEvidenceCorpus, primary_plans: Mapping[str,str], target_pairs: Iterable[tuple[str,str]], *, strength_cap: float=15.0) -> dict[tuple[str,str], PlanBorrowingPrior]`. One pass indexes directed totals from unique physical nonmirror observations by subject/plan and subject/opponent; subtract all target-pair observations from the donor group. For nonempty donors set mean=(wins+1)/(n+2), strength=min(15,n); omit no-donor/unmapped targets so original fitted prior stays exact. Preserve donor counts/events/opponents and bind selection to the corpus/primary mapping. Do not add direct match observations or a new display gate.

The parent evaluator will test this challenger on identical frozen cases alongside scales1,.5,2; target direct W/n never changes. Only positive development evidence justifies a candidate choice before confirmation. Production remains the baseline until the comparison supports a change. Prior-only floors remain uncertain; borrowing from a broad plan is not proof of an exact matchup. Donor pairs retain their own clean eligibility and this is an explicit transfer assumption, not universal interval compatibility. Conditional intervals omit fitted-prior and cross-cell uncertainty.

## Verification
Target outcome changes leave donor prior unchanged; reverse physical orientation has the right outcome; duplicate IDs and future outcomes fail; n0 cells can change mean from informative donors; no-donor/unmapped targets preserve fallback; no main/secondary plan double counting; deterministic output and capped strength. Child closes directly on green tests, and integrated feature receives one independent review.

## Implementation and verification
Implemented the pure clean-corpus donor index and bounded prior with corpus/plan-selection binding, distinct donor event/opponent counts, and historical-origin counts. Six focused tests pass: target exclusion, reverse orientation, prior-only estimate, cap, no-donor fallback, unrelated plans, duplicate physical IDs, and cutoff isolation. Child checkpoint is complete; parent integration and comparative evaluation remain the feature boundary.
