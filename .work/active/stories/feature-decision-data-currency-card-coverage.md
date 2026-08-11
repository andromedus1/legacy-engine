---
id: feature-decision-data-currency-card-coverage
kind: story
stage: implementing
tags: [ingestion, analytics]
parent: feature-decision-data-currency
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Resolve exact card aliases and report card-dimension coverage

## Brief

Stream Scryfall's compressed every-language card artifact into an exact localized-alias index with
collision/provenance data, canonicalize only uniquely earned mappings, recognize oracle-refresh
new-card recoveries, and replace warning noise on the decision-refresh path with a compact typed
coverage report that keeps ambiguous, suspected-truncated, and unresolved gaps visible.

## Implementation

Implement Units 2 and 3 in the parent feature's `## Implementation Units` section. Neither the
current `oracle_cards` mirror, the sparse-language `default_cards` price bulk, nor Scryfall's exact
name endpoint resolves the observed localized spellings. Do not substitute fuzzy matching or mutate
price tables.
