---
id: epic-recurrent-stable-era-evidence-interval-selection
kind: story
stage: implementing
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-interval-consumption
depends_on: [epic-recurrent-stable-era-evidence-interval-algebra]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Exact pair selection and gap-proof match provenance

## Brief

Implement Unit 2 from the parent feature: one resolved-match ledger, deterministic match ids, exact
subject/opponent interval intersection, gap-preserving row selection, and the legacy aggregate API as
an adapter over the shared selection seam.

## Implementation

See `epic-recurrent-stable-era-evidence-interval-consumption` Unit 2 for exact interfaces, notes, and
acceptance criteria. Preserve existing join cardinality, ambiguity, bye/draw, mirror, split-label,
source, and directed-symmetry behavior while retaining both sides' component/certificate provenance.

## Acceptance

- A row enters only an exact pair atom before exclusive `data_until`; one-sided history and gaps are
  excluded.
- Stable match/component ids survive ordering and pooling without duplication.
- One-component scalar aggregation remains field-for-field compatible with the current API.

## Tests

Run focused match-record/selection tests, existing match-results/era tests, Ruff on touched files,
and compileall as specified by the parent feature.
