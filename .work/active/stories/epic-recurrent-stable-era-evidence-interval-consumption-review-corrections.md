---
id: epic-recurrent-stable-era-evidence-interval-consumption-review-corrections
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-interval-consumption
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Integrate and correct exact interval consumption

## Scope

Replace the reviewed dead/parallel interval definitions with the single exercised eligibility and
evidence authority promised by the parent feature.

## Acceptance criteria

- Production parent and multi-split matrix paths consume exact interval selection, preserve excluded
  gaps, thread clocks/split variants, and return populated typed evidence when certificates exist.
- Resolved match records select only the requested directed pair, normalize player orientation and
  outcomes, and use stable outcome-independent identities.
- Pair/subject/opponent component ids describe actual interval components and remain constant for
  all matches within one component; concentration operates on those components.
- Open-start normalization cannot borrow provenance from later finite intervals.
- The exact certificate result governs the required current reference component; authority,
  duplicate, interval/id, and promoted-profile constraints are validated with explicit abstention.
- Current, expanded, and added views aggregate their own selected rows and form an exact match-id
  partition with view-local hierarchy/prior inputs and no observation/prior overlap.
- Disjoint scalar projection refuses with typed reason; new boundary APIs are exported.
- New adversarial unit/integration tests cover pair orientation/unrelated exclusion, gaps, clocks,
  current certificate identity, component concentration, W-L-n reconstruction, parent/camp/
  multi-split parity, hierarchy locality, no-double-count priors, and production call sites.
- Relevant/full tests, Ruff, compileall, and a representative interval matrix run pass; `uv.lock`
  remains excluded.

## Review origin

Created from the single standard independent review of the parent feature on 2026-08-16. After this
named fix set is green, the parent closes administratively without another independent pass.
