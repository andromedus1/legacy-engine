---
id: feature-player-effect-diagnostic-review-fixes
kind: story
stage: done
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

- [x] Training/validation rows outside the frozen action universe are deterministically excluded
      with named counts; real-corpus freeze/run no longer raises missing-base-probability errors.
- [x] Benchmark protocol and identity-snapshot hashes are verified before inner selection, freeze,
      and evaluation; mutation is rejected even when held-out schedules appear unchanged.
- [x] Player and familiarity identifiability constraints are part of fitting, with frequency-weighted
      zero familiarity effects and predictions consistent with the selected penalized objective.
- [x] Fold status reuses the benchmark common-case matches/events/dates/actions/field-mass support
      verdict; cold-start and venue strata have declared proportionate minimums before promotion use.
- [x] Accessibility retains ambiguous match-side denominator mass, recomputes repeat/familiarity
      eligibility per venue, and privacy-suppressed cells expose no exact identity counts.
- [x] Inner origins are distinct, chronological, before the outer cutoff, row-date safe, and bound to
      base prediction identity.
- [x] Event bootstrap preserves replacement multiplicity; neutral-regret comparison is paired by
      event block rather than subtracting marginal intervals.
- [x] Any supported measured calibration, cold-start, venue, or neutral-regret harm produces `stop`;
      unsupported evidence remains named not-evaluable/diagnostic-only.
- [x] Hermetic and representative real-corpus-path regressions cover all review probes; focused and
      full repository verification are green.

## Review closure contract

This story is the named fix set for a `standard`-weight review. Green implementation verification
returns the parent feature directly to `done`; do not run a second independent review pass.

## Implementation notes

- Reconciled every outer/inner training and validation row against its own frozen base grid, with
  cutoff-safe named exclusion ledgers. A representative hermetic DuckDB fixture retains a historical
  parent outside the current grid and proves the freeze records—not crashes on—that row.
- Bound the loaded benchmark protocol, full/grid inner base identities, identity mode/digest,
  schedule, and outer base bytes at the relevant selection/freeze/evaluation boundaries.
- Moved frequency-weighted player and per-player familiarity centering into the penalized objective;
  serialized coefficients and predictions now use that exact fitted parameterization.
- Reused the benchmark common-match/event/date/action/field-mass verdict and added explicit
  match/event/date floors for every cold-start and venue claim stratum.
- Retained ambiguous sides in identity denominators, recomputed repeat/familiarity within each
  venue, and suppressed all below-floor identity counts in structured and Markdown output.
- Preserved bootstrap block replacement multiplicity, replaced marginal-interval regret subtraction
  with paired event-block differences, and made supported calibration/cold/venue/regret harm a
  terminal `stop`; missing support remains non-promotional without optimistic null filling.
- Tests: 18 focused player tests and 107 affected player/benchmark/ranking tests passed. Owned Ruff,
  compile, diff, and knowledge-index checks are recorded at closure; full-suite evidence is recorded
  on the parent after this checkpoint commit.
- Documentation: the Best Call methodology and architecture entries now state the repaired
  exclusion, centering, binding, support, privacy, paired-uncertainty, and adverse-evidence contracts.
- Production ranking, Agency, P(best), and the ten-estimator registry remain unchanged.
- Adjacent issues parked: none.
