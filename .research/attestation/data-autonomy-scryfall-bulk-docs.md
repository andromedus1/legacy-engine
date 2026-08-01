---
source_handle: data-autonomy-scryfall-bulk-docs
fetched: 2026-07-31
source_url: https://scryfall.com/docs/api/bulk-data
provenance: source-direct
source_class: api-docs
---

# Scryfall API docs — Bulk Data Files

## Summary

Official documentation for Scryfall's bulk exports. Bulk files are daily exports,
collected once every 12-24 hours, and are now distributed as gzipped JSONL archives
(`.jsonl.gz`) whose URLs change timestamp each day and must be discovered
programmatically via the `/bulk-data` API. Prices inside bulk card objects are declared
"dangerously stale after 24 hours" and unfit for storefront use; gameplay data (names,
oracle text) changes much less often — weekly or post-release downloads suffice if only
gameplay data is needed. These cadence facts bound how fast a bulk-diff-based B&R
detector can possibly react (one bulk cycle) and set the polling budget for the
scheduled refresh.

## Key passages

> Scryfall provides daily exports of our card data in bulk files. — intro

> URLs for files change their timestamp each day, and can be fetched programmatically. — intro

> Each bulk file is a gzipped JSONL (JSON Lines) archive: You will specifically download a jsonl.gz archive and need to decompress or stream it on disk. — format note

> Please note: Card objects in bulk data include price information, but prices should be considered dangerously stale after 24 hours. — price caveat

> Updates to gameplay data (such as card names, Oracle text, mana costs, etc) are much less frequent. If you only need gameplay information, downloading card data once per week or right after set releases would most likely be sufficient. — cadence guidance

> Bulk data is only collected once every 12-24 hours — collection cadence

## Structural metadata

HTML page fetched 2026-07-31 (curl, browser UA — the docs site 403s generic fetchers);
text extracted by tag-stripping. Page sections: intro, JSONL format, per-file listing,
tags files, cadence note.
