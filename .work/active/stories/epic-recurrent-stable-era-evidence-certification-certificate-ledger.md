---
id: epic-recurrent-stable-era-evidence-certification-certificate-ledger
kind: story
stage: implementing
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-certification
depends_on: [epic-recurrent-stable-era-evidence-certification-family-equivalence]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Immutable certificate run and exact-id ledger

## Brief

Implement Unit 4 from the parent feature: compose the exact discovery/partition/guard/equivalence
pipeline, persist immutable versioned certificates and explicit no-candidate entities, and expose
canonical exact-id reads as the only downstream handoff.

## Implementation

See `epic-recurrent-stable-era-evidence-certification` Unit 4 and its exact interfaces,
implementation notes, and acceptance criteria. Only certificates with final status `certified` may
become historical interval inputs; this story does not implement matchup consumption.

Review weight remains `standard` at the parent feature boundary.

## Acceptance

- Every admitted/refused/abstained interval and every no-candidate entity round-trips with complete
  partition, semantic, support, context, equivalence, configuration, and hash evidence.
- Exact retries are idempotent, divergent collisions fail, and no latest/substitute read exists.
- Rejected/inconclusive/camp/gap evidence cannot be consumed as a certified historical component.

## Tests

Run focused run/store integration tests, all certification/discovery/era tests, Ruff on touched
files, and compileall as specified by the parent feature.
