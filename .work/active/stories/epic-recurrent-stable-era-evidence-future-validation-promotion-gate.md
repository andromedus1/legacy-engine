---
id: epic-recurrent-stable-era-evidence-future-validation-promotion-gate
kind: story
stage: implementing
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-future-validation
depends_on:
  - epic-recurrent-stable-era-evidence-future-validation-common-case-scoring
  - epic-recurrent-stable-era-evidence-future-validation-decision-regret
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Aggregate evidence without granting promotion authority

## Brief

Apply the preregistered simultaneous useful-coverage and non-degradation conjunction, emit exhaustive
promotable/negative/inconclusive/support-censored/invalid assessments, persist an immutable evidence
bundle, and allow only an inert operator-review proposal for an exact promotable candidate.

## Implementation

Implement Unit 5, **Aggregate status, immutable evidence bundle, and operator-only proposal**, from
the parent feature. No CLI or API may select a current-corpus winner, mutate active configuration, or
promote automatically.

## Acceptance

Satisfy every Unit 5 acceptance criterion in the parent feature, including simultaneous useful-
coverage/non-degradation clauses, all five statuses, deterministic immutable bundles, v1
compatibility, and operator-only inert proposals.

## Tests

Implement the promotion, store, and CLI suites named by Unit 5 with boundary cases for every status,
multiplicity, current-corpus winner attacks, artifact collisions, and absence of any config mutation.
