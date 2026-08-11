---
id: feature-decision-data-currency-refresh-cycle
kind: story
stage: implementing
tags: [ingestion, infra, analytics]
parent: feature-decision-data-currency
depends_on:
  - feature-decision-data-currency-runtime-alignment
  - feature-decision-data-currency-card-coverage
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Compose the decision-data refresh cycle

## Brief

Provide one typed, repository-local refresh composition for tournament/rules/cards refresh, card
coverage reconciliation, labeling, all staged camp applications, era detection, and final ranking
generation. Surface release scans, the registered B&R ledger, era alarms, step failures, and the
ranking output without shell orchestration, cloud state, commits, or pushes.

## Implementation

Implement Unit 4 in the parent feature's `## Implementation Units` section after both dependency
stories complete. Preserve the existing individual CLI/script surfaces and make the tracked ranking
writer the final step only.
