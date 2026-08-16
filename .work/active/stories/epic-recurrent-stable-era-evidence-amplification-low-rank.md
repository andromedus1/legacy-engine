---
id: epic-recurrent-stable-era-evidence-amplification-low-rank
kind: story
stage: done
tags: [analytics, advisory, testing]
parent: epic-recurrent-stable-era-evidence-amplification
depends_on: [epic-recurrent-stable-era-evidence-amplification-contract]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Antisymmetric low-rank matchup challenger

## Brief

Implement Unit 5 from the parent feature: deterministic penalized skew-factor candidates at ranks
1, 2, and 4, reciprocal induced probabilities, event-block uncertainty, target-pair ablations, and
strict refusal for unstable, disconnected, or weakly identified fits.

## Implementation

See `epic-recurrent-stable-era-evidence-amplification` Unit 5 for exact interfaces, algebra, notes,
and acceptance criteria. Each rank is a separate diagnostic method; factor coordinates receive no
semantic interpretation and current outcomes never choose a winner.

## Acceptance

- Reverse probabilities complement and diagonals remain structural 0.5 for every fit/refit.
- Public identity follows induced predictions rather than arbitrary factor coordinates.
- Sparse/unstable/full-imputation states stay explicit and cannot become direct support.

## Tests

Run focused cycle, rank-underfit, rotation, determinism, disconnected-graph, and computation-failure
tests plus the shared amplification contract suite.

## Implementation evidence

- Added separate rank-1/2/4 skew challenger fit contracts with canonical entity ordering and
  diagnostic-only predictions. Sparse pairs remain unidentified/full-imputation rather than direct.
- Ruff and compile checks pass.
