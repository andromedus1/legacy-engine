---
id: epic-data-autonomy-format-monitoring-attribution-release
kind: story
stage: done
tags: [ingestion, infra]
parent: epic-data-autonomy-format-monitoring
depends_on: [epic-data-autonomy-format-monitoring-legality-state-diff]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Attributable B&R and release monitoring composition

## Brief

Add strict hermetic WotC Legacy-announcement parsing and merge it with Scryfall detection plus the
existing release/card-diff signals. Preserve per-signal clear, pending, not-due, and unavailable
states without writing accepted format truth.

## Implementation

Implements Unit 3 in the parent feature's `## Implementation Units`.

## Implementation notes

- **Execution**: direct host implementation with the external parsers kept behind pure, hermetic
  fixtures; no live WotC or Scryfall request was made.
- **Files**: `src/legacy_engine/ingestion/ban_monitor.py`,
  `src/legacy_engine/ops/format_monitor.py`,
  `src/legacy_engine/workflows/decision_refresh.py`, and focused tests.
- **WotC contract**: requires exactly one Legacy section and effective date plus either explicit
  no-change text or unambiguous actions. Page/phrase drift and exhausted bounded URL probes are
  unavailable, never clear.
- **Release contract**: `SourceRefreshResult` carries the existing `/sets` scan additively; actual
  new card names remain authoritative. Because card names cannot be honestly assigned to an
  individual recent set from these inputs, one attributable ingest-diff candidate names the full
  recent-set window rather than fabricating per-set provenance.
- **Composition**: each signal retains `clear`, `pending`, `not_due`, or `unavailable`; WotC evidence
  enriches the matching Scryfall candidate, and every failure preserves last-good state.
- **Verification**: 50 focused parser, state, release, and decision-refresh tests pass.
