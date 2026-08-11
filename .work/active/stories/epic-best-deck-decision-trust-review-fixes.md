---
id: epic-best-deck-decision-trust-review-fixes
kind: story
stage: implementing
tags: [analytics, advisory, honesty, testing, players, privacy, docs]
parent: epic-best-deck-decision-trust
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Close aggregate best-deck decision-trust findings

Implement the receiver-confirmed cross-feature findings from the epic's one standard aggregate
review, then execute the real-corpus future-only benchmark without retrospective tuning.

## Acceptance criteria

- [ ] Retrospective origin snapshots reclassify training decks through pinned parent rules (or fail
      exact stored/replayed parity), and stored-label mutation cannot change frozen predictions.
- [ ] One shared production recommendation function owns grounded/current/Agency ordering; page and
      benchmark parity holds when a stale grounded deck has higher Agency than a current one.
- [ ] Player fit-summary counts below the privacy floor serialize/render as suppressed nulls while
      sufficient aggregate counts remain available.
- [ ] Benchmark frozen methodology evidence computes the true uniform strict-common-era diagnostic
      or emits a named unavailable reason; it never relabels adaptive sources as strict-common.
- [ ] Page and runbook display benchmark validation state and artifact identity, with honest defaults
      for not-run/not-evaluable/descriptive/predictive-claim-supported.
- [ ] The preregistered benchmark is executed against the current repository corpus after fixes;
      artifacts are local/immutable, their ids and claim status are recorded in durable story/epic
      evidence, and no estimator/threshold is changed in response to outcomes.
- [ ] Cross-feature focused tests and the full repository suite are green; knowledge/docs checks pass.

## Review closure contract

This story is the named fix set for a `standard`-weight epic review. Green verification and honest
empirical execution return the epic directly to `done`; do not run a second independent review pass.
