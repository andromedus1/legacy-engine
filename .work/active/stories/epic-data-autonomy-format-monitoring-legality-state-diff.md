---
id: epic-data-autonomy-format-monitoring-legality-state-diff
kind: story
stage: done
tags: [ingestion, infra]
parent: epic-data-autonomy-format-monitoring
depends_on: [epic-data-autonomy-format-monitoring-scryfall-jsonl-contract]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Durable legality observation and candidate state

## Brief

Build the typed, atomically persisted last-good legality baseline and pure candidate transition
logic, including stable identities, evidence-hash acknowledgement, confirmed retirement, and loud
unsupported reversal handling.

## Implementation

Implements Unit 2 in the parent feature's `## Implementation Units`.

## Implementation notes

- **Execution**: direct host implementation, kept isolated in a new pure state module while the
  sibling local-refresh feature completed review in shared operations files.
- **Files**: `src/legacy_engine/ops/format_monitor.py`, `src/legacy_engine/config.py`,
  `tests/test_format_monitor.py`.
- **Behavior**: validates the closed Legacy legality vocabulary and oracle identities, establishes
  a first-run baseline without historical guesses, detects stable transitions, preserves exact
  evidence acknowledgements, reopens on material evidence, retires operator-confirmed bans, and
  leaves unsupported reversals visibly pending.
- **Authority**: the module neither imports nor calls `append_ban_event`; its atomically written file
  is recoverable operational state, separate from curated format truth.
- **Verification**: 12 focused monitor/config tests pass, including corrupt/incomplete snapshot and
  failed atomic-replace preservation.
