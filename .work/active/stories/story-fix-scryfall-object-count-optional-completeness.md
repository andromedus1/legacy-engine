---
id: story-fix-scryfall-object-count-optional-completeness
kind: story
stage: review
tags: [bug, ingestion]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Accept live Scryfall completeness metadata without weakening truncation safety

## Symptom

Installed smoke-refresh attempt `7ea5d98a34344a60916f1603e2985542` failed at `sources` with
`Scryfall bulk metadata is missing positive object_count`.

## Root cause

The review correction assumed Scryfall's current bulk listing declared an `object_count`. The live
`/bulk-data` records for both `oracle_cards` and `default_cards` instead declare a positive
`compressed_size` alongside `jsonl_download_uri`; they do not include an object count. The new
guard therefore rejected the authoritative contract before downloading anything.

## Fix approach

For current gzipped JSONL, require positive provider-declared `compressed_size`, compare it exactly
with the raw downloaded gzip bytes, then fully decompress and validate every nonblank row before
atomic replacement. Retain exact `object_count` validation only when that legacy metadata field is
actually present. This uses provider provenance rather than guessed row thresholds and still rejects
truncated or structurally invalid candidates.

## Regression test

`tests/test_scryfall.py::test_download_bulk_data_accepts_live_jsonl_download_uri` uses captured
live-shaped metadata (`jsonl_download_uri`, `updated_at`, `compressed_size`, no `object_count`) and
currently fails with the reported exception. Complementary truncation coverage will assert a byte
count mismatch preserves the prior mirror and metadata.

## Implementation notes

Execution capability: direct focused repair. The failure is isolated to one ingestion contract and
one test module; no cross-subsystem design or independent reviewer is warranted.

Changed `src/legacy_engine/ingestion/scryfall.py` and `tests/test_scryfall.py`. Current JSONL
downloads require at least one positive provider completeness declaration, compare raw gzip bytes
against `compressed_size` when present, fully parse every row, optionally enforce `object_count`,
then atomically publish. Legacy arrays still require `object_count`. Local metadata retains both
provider declarations for auditability.

Regression-first evidence: the captured live-shaped oracle test failed with the reported missing
`object_count` exception before the fix and passes afterward. A new truncation test supplies a
one-byte-short payload and proves the prior raw mirror and metadata remain byte-for-byte intact;
another guard proves metadata with neither completeness field is rejected.

Confirmation so far: changed-file Ruff is clean; the focused Scryfall/price/monitor/refresh slice is
`124 passed`; a read-only live `/bulk-data` metadata check resolves `oracle_cards` to
`(24502828, None)` and `default_cards` to `(77463009, None)` through the corrected helper. No bulk
download, scheduler run, database mutation, provider-state mutation, or adjacent issue was bundled.
