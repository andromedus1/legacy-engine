---
id: feature-agency-page-methodology-review-fixes
kind: story
stage: done
tags: [analytics, advisory, honesty, bug, tests, docs, accessibility]
parent: feature-agency-page-methodology
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Close agency-methodology review findings

Implement the receiver-confirmed findings from the feature's one standard review pass without
changing the pinned methodology or gated authority.

## Acceptance criteria

- [ ] On initial load, `_interactiveN` and P(best) display/sort semantics match the generated
      `ground_n`; changing the control still marks generated-gate evidence stale.
- [ ] Canonical grounding, grounding-path planning, and browser replay share one documented
      deterministic top-k ordering for equal field shares.
- [ ] Archetype and camp detail diagnostics have keyboard-operable disclosure controls with
      `aria-expanded` and `aria-controls` state kept in sync.
- [ ] The runbook gives the posterior soft-min equation and exact seed, draw count, temperature,
      precision scale, and unresolved-prior strength used for replay.
- [ ] Executed JS/behavioral and Python regressions cover the default state, tie case, and disclosure
      state; focused and full repository suites are green.

## Review closure contract

This story is the named fix set for a `standard`-weight review. Green implementation verification
returns the parent feature directly to `done`; do not run a second independent review pass.

## Implementation notes

- Initialized each generated archetype, camp, and plan row's interactive gate marker from
  `meta.ground_n` before first render. This preserves the serialized gated score and P(best) on load;
  subsequent gate changes still mark generated diagnostics stale and suppress stale P(best).
- Canonical projection, path planning, and browser replay now break equal field-share top-k ties by
  stable opponent identifier ascending. The runbook records the shared rule.
- Archetype and camp diagnostics now use focusable button disclosures with `aria-expanded` and
  `aria-controls` synchronized whenever the detail row opens or closes.
- The runbook now owns the exact posterior soft-min equation and the replay constants: 20,000 draws,
  seed 730021, temperature 0.05, precision scale 30, Jeffreys 0.5, and unresolved-prior strength 2.
- Added a Python regression for equal-share canonical/path agreement and an executed Node regression
  against the tracked template JavaScript covering initial P(best)/sorting, browser tie ordering,
  disclosure state, and post-change staleness. No tests were removed or weakened.
- Simplification: initial load sets only the interaction marker; it does not duplicate the generated
  calculation or introduce a second P(best) implementation. Gated authority, candidacy, evidence
  strata, posterior math, and all estimator thresholds remain unchanged.
- Design deviations and adjacent production bugs: none.
- Verification: focused measurement/report suite — 67 passed; full repository suite — 3,670 passed,
  1 skipped in 193.65s; canonical knowledge-index workflow — 0 errors and 11 existing warnings.
