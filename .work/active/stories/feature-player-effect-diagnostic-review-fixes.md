---
id: feature-player-effect-diagnostic-review-fixes
kind: story
stage: implementing
tags: [analytics, players, experimental, honesty, bug, tests, privacy]
parent: feature-player-effect-diagnostic
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Close player-effect diagnostic review findings

Implement the receiver-confirmed findings from the feature's one standard review pass. Production
ranking remains unchanged and the diagnostic cannot exceed candidate-for-promotion-study.

## Acceptance criteria

- [ ] Training/validation rows outside the frozen action universe are deterministically excluded
      with named counts; real-corpus freeze/run no longer raises missing-base-probability errors.
- [ ] Benchmark protocol and identity-snapshot hashes are verified before inner selection, freeze,
      and evaluation; mutation is rejected even when held-out schedules appear unchanged.
- [ ] Player and familiarity identifiability constraints are part of fitting, with frequency-weighted
      zero familiarity effects and predictions consistent with the selected penalized objective.
- [ ] Fold status reuses the benchmark common-case matches/events/dates/actions/field-mass support
      verdict; cold-start and venue strata have declared proportionate minimums before promotion use.
- [ ] Accessibility retains ambiguous match-side denominator mass, recomputes repeat/familiarity
      eligibility per venue, and privacy-suppressed cells expose no exact identity counts.
- [ ] Inner origins are distinct, chronological, before the outer cutoff, row-date safe, and bound to
      base prediction identity.
- [ ] Event bootstrap preserves replacement multiplicity; neutral-regret comparison is paired by
      event block rather than subtracting marginal intervals.
- [ ] Any supported measured calibration, cold-start, venue, or neutral-regret harm produces `stop`;
      unsupported evidence remains named not-evaluable/diagnostic-only.
- [ ] Hermetic and representative real-corpus-path regressions cover all review probes; focused and
      full repository verification are green.

## Review closure contract

This story is the named fix set for a `standard`-weight review. Green implementation verification
returns the parent feature directly to `done`; do not run a second independent review pass.
