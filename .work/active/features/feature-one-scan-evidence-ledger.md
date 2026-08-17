---
id: feature-one-scan-evidence-ledger
kind: feature
stage: drafting
created: 2026-08-16
updated: 2026-08-16
tags: [analytics, perf]
parent: null
depends_on: []
release_binding: null
gate_origin: null
---

# Build interval evidence from one physical match scan

## Brief

The live localized-evidence refresh spends minutes in `build_selected_outcome_ledger` because it
calls `resolve_match_records` once per subject/opponent pair and each call re-runs the full
rounds/decks/tournaments join. Replace the N-pair full-corpus rescans with one physical resolver scan
and in-memory canonical pair grouping, preserving byte-for-byte selected-ledger semantics, reverse
orientation derivation, half-open interval gaps, and atomic last-good report publication.

## Simplification opportunity

Delete the pair loop's repeated SQL resolution path. Resolve each physical match once, canonicalize
its orientation once, group it by pair once, and keep the existing pure interval selector as the
only admission authority.
