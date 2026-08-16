---
id: epic-recurrent-stable-era-evidence-certification-guards-support
kind: story
stage: implementing
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-certification
depends_on: [epic-recurrent-stable-era-evidence-certification-partition-contract]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Ordered semantic, support, concentration, and context guards

## Brief

Implement Unit 2 from the parent feature: materialize exact candidate/reference samples from the
held-out corpus and evaluate confirmed affectedness/contracts, pending truth, event/time support,
concentration, simulated power, and context overlap as typed pass/reject/abstain evidence.

## Implementation

See `epic-recurrent-stable-era-evidence-certification` Unit 2 and its exact interfaces,
implementation notes, and acceptance criteria. Preserve guard order and suppress unsupported
magnitudes; pending monitor evidence is never promoted into a confirmed fact.

Review weight remains `standard` at the parent feature boundary.

## Acceptance

- Confirmed semantic incompatibility rejects; unresolved truth and weak support abstain with named
  evidence; unaffected entities are never blanket-reset.
- Raw duplicates cannot buy effective support, and context weighting remains diagnostic only.
- Camps and outcomes remain structurally absent.

## Tests

Run focused guard/support/context tests plus the partition/discovery suite, Ruff on touched files,
and compileall as specified by the parent feature.
