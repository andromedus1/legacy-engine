---
id: idea-one-scan-evidence-ledger
created: 2026-08-16
updated: 2026-08-16
tags: [analytics, perf]
---

The live localized-evidence refresh spends minutes in `build_selected_outcome_ledger` because it
calls `resolve_match_records` once per subject/opponent pair and each call re-runs the full
rounds/decks/tournaments join. Replace the N-pair full-corpus rescans with one physical resolver scan
and in-memory canonical pair grouping, preserving byte-for-byte selected-ledger semantics, reverse
orientation derivation, half-open interval gaps, and atomic last-good report publication.
