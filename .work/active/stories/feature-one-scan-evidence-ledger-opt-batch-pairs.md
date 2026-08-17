---
id: feature-one-scan-evidence-ledger-opt-batch-pairs
kind: story
stage: implementing
tags: [analytics, perf, testing]
parent: feature-one-scan-evidence-ledger
depends_on: []
release_binding: null
gate_origin: perf-design
created: 2026-08-16
updated: 2026-08-16
---

# Batch canonical pair selection over one resolved-match scan

## Brief

Replace the selected-outcome ledger's per-pair full-corpus resolver loop with one unfiltered
physical-match resolution, exact canonical pair grouping, and a derived selected-row pair index.
Preserve the reference ledger rows/digest, interval gaps, physical identities, and reverse-derived
orientation exactly while reducing resolver calls to one per ledger build.

## Verification contract

- Exact row and digest parity against the retained per-pair reference algorithm on parent and
  multi-split fixtures.
- Resolver call count is exactly one for any non-empty pair set.
- Live parent+camp interval benchmark and full ranking complete under the feature target.
