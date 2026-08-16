---
id: epic-recurrent-stable-era-evidence-certification-partition-contract
kind: story
stage: implementing
tags: [analytics, testing]
parent: epic-recurrent-stable-era-evidence-certification
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Deterministic event partition and certification corpus

## Brief

Implement Unit 1 from the parent feature: repair the discovery handoff so nomination uses only a
deterministic whole-event discovery partition, construct the disjoint certification corpus, bind
both roles into immutable manifests, and reject any legacy/full-corpus or digest-mismatched run
before certification.

## Implementation

See `epic-recurrent-stable-era-evidence-certification` Unit 1 and its exact interfaces,
implementation notes, and acceptance criteria. This story owns the cross-item discovery-manifest
correction required for valid certification; it does not implement statistical gates.

Review weight remains `standard` at the parent feature boundary.

## Acceptance

- Event roles are atomic, disjoint, exhaustive, cutoff-safe, and deterministic.
- Discovery candidates cannot depend on certification-role facts, outcome relations, or future rows.
- Only an exact partition-marked discovery run can open the certification boundary.

## Tests

Run focused partition/source/discovery-run tests, the existing discovery suite, Ruff on touched
files, and compileall as specified by the parent feature.
