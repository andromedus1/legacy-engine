---
source_handle: data-autonomy-scryfall-rate-limits
fetched: 2026-07-31
source_url: https://scryfall.com/docs/api/rate-limits
provenance: source-direct
source_class: api-docs
---

# Scryfall API docs — Rate Limits

## Summary

Scryfall's hard rate limits: search-family endpoints 2/second, most other API methods
10/second, and — decisive for the scheduled-refresh design — the bulk-file origin
`*.scryfall.io` has **no** rate limits. Excessive requests earn HTTP 429. So a daily
launchd job that hits `/bulk-data` once and `/sets` once, then downloads from
`data.scryfall.io`, is far inside the budget.

## Key passages

> The Scryfall API ( api.scryfall.com ) has the following hard rate limits: /cards/search — 2/second (500ms) … All other methods — 10/second (100ms) — limits table

> The direct file origins located at *.scryfall.io do not have rate limits. — bulk origin

> Submitting excessive requests to API server may result in an HTTP 429 Too Many Requests status code. — enforcement

## Structural metadata

HTML page fetched 2026-07-31 (curl, browser UA); text extracted by tag-stripping.
Related requirement on the API overview page (`/docs/api`): all requests must send
accurate `User-Agent` and `Accept` headers.
