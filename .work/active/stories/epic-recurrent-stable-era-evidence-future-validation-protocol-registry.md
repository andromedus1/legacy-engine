---
id: epic-recurrent-stable-era-evidence-future-validation-protocol-registry
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-future-validation
depends_on: [epic-recurrent-stable-era-evidence-amplification]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Freeze the recurrent-validation protocol and estimator registry

## Brief

Add the separately versioned, closed-schema recurrent-evidence benchmark protocol, exact estimator
registry, support/margin configuration, and immutable identity rules without changing the shipped v1
benchmark protocol, registry, hashes, or artifacts.

## Implementation

Implement Unit 1, **Append-only protocol, estimator registry, and artifact identity**, from the
parent feature. Preserve all legacy artifact goldens and reject any result-driven or mutable
promotion field at the protocol boundary.

## Acceptance

Satisfy every Unit 1 acceptance criterion in the parent feature, including the complete derived
registry, closed-schema/hash checks, and byte-identical historical benchmark artifacts.

## Tests

Implement `tests/advisory/test_recurrent_validation_protocol.py` with registry/order, invalid
protocol, immutable hash, registration-time, fold-boundary, and shipped-v1 golden cases.
