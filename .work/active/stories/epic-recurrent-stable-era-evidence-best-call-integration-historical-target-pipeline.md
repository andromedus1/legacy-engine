---
id: epic-recurrent-stable-era-evidence-best-call-integration-historical-target-pipeline
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-best-call-integration
depends_on: [epic-recurrent-stable-era-evidence-best-call-integration-current-diagnostics]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Thread retrospective targets through the ranking pipeline

## Brief

Define typed current and pre-ban report targets and apply one exclusive `data_until` to every
ranking, field, camp, plan, interval, and diagnostic input while labeling retrospectives only as
`Today's model`.

## Implementation

Implement Unit 3, **Thread retrospective `data_until` through ranking composition**, from the parent
feature. Treat the cutoff as an end-to-end data boundary, not presentation metadata; reject
`as-known-then` and require exact target clocks for optional certification/amplification evidence.

## Acceptance

Satisfy every Unit 3 acceptance criterion in the parent feature, including half-open exclusion,
post-cutoff mutation invariance, all-section clock parity, confirmed-ban target derivation, exact-run
validation, camp/scalar/gap preservation, and unchanged current behavior when no cutoff is supplied.

## Tests

Add the matrix, transition, generator, and adversarial leakage suites named by Unit 3. Inject future
tournaments, decks, results, variants, outcomes, and mismatched run clocks; assert every historical
blob/audit byte remains frozen while a pre-cutoff row changes only the expected bounded sections.
