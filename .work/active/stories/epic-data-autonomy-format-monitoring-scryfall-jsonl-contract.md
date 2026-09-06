---
id: epic-data-autonomy-format-monitoring-scryfall-jsonl-contract
kind: story
stage: done
tags: [ingestion, infra]
parent: epic-data-autonomy-format-monitoring
depends_on: [epic-data-autonomy-local-refresh-operations]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Repair Scryfall gzipped JSONL bulk ingestion

## Brief

Repair the upstream bulk contract that gates scheduled refresh and legality monitoring. Stream and
validate the current `jsonl_download_uri` payload atomically for oracle and price data while keeping
legacy cached JSON arrays readable.

## Implementation

Implements Unit 1 in the parent feature's `## Implementation Units`: shared URI selection, streamed
gzip JSONL validation, last-good preservation, and recorded-contract regression tests.

## Implementation notes

- **Execution**: direct host implementation because all worker slots were occupied; the change is a
  focused external-contract repair with deterministic fixtures.
- **Root cause**: the production oracle and prices paths indexed the removed `download_uri` key and
  assumed JSON arrays, while live Scryfall metadata now provides `jsonl_download_uri` pointing to
  gzipped JSON Lines.
- **Files**: `src/legacy_engine/ingestion/scryfall.py`, `tests/test_scryfall.py`.
- **Fix**: prefer the current metadata key, stream/decompress and validate JSONL into an atomic
  normalized mirror, retain legacy array readers, and publish metadata only after validation.
- **Regression evidence**: the new live-contract test failed with the original `KeyError`; focused
  Scryfall, alias, and price tests pass after the repair. Corrupt candidates preserve both the
  last-good mirror and metadata.
- **Adjacent issues**: none discovered.
