---
id: feature-decision-data-currency
kind: feature
stage: drafting
tags: [ingestion, infra, analytics]
parent: epic-best-deck-decision-trust
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Decision-data currency — reproducible runtime, card coverage, and refresh cycle

## Brief

Keep the evidence behind the ranking current and make gaps visible. Align the supported local
Python environment with CI, normalize recoverable localized card names to English, distinguish
localized/new-set/unrecoverable card-dimension misses, emit a compact coverage summary, and provide
one repeatable refresh cycle for tournament data, labels, discoveries, eras, and ranking output
with B&R/new-release awareness.

This feature absorbs the focused scope of `idea-local-ci-python-drift` and
`bug-card-dimension-localized-and-new-card-gaps`, plus the scheduled refresh/format-monitoring
member of `epic-data-autonomy`. It explicitly excludes the upstream tournament hot spare,
Card Kingdom pricing, and unrelated catalog enrichment.

## Strategic decisions

- Raw provider data remains the source of truth; DuckDB remains rebuildable.
- Exact localized aliases may normalize automatically with provenance; ambiguous/truncated names
  remain unresolved and counted rather than guessed.
- Refresh automation is local and repeatable; no cloud service or protected-branch push is part of
  this feature.

## Simplification opportunity

Replace the multi-command operator runbook with one composition command while retaining the
individual commands as testable primitives. Consolidate warning spam into one coverage result plus
drill-down detail.
