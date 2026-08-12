---
id: epic-data-autonomy-format-monitoring-scryfall-jsonl-contract
kind: story
stage: implementing
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
