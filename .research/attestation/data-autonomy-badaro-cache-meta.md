---
source_handle: data-autonomy-badaro-cache-meta
fetched: 2026-07-31
source_url: https://api.github.com/repos/Badaro/MTGODecklistCache
provenance: source-direct
source_class: api-response
---

# GitHub API — Badaro/MTGODecklistCache (the predecessor cache) metadata

## Summary

Metadata for the original C# tournament cache that the fbettega pipeline succeeded.
It is archived and last pushed 2025-06-10 — the "upstream has already died once"
precedent. Fetched alongside (same session): `Badaro/MTGODecklistCache.Tools` (the C#
scraper) reports `"archived":true,"pushed_at":"2025-09-24T15:55:28Z"`, and
`Badaro/MTGOFormatData` (the archetype rules legacy-engine vendors) reports
`"archived":false,"pushed_at":"2026-07-21T07:31:56Z"` — the rules repo is still
actively maintained even though Badaro's cache+scraper are dead.

## Key passages

> {"archived":true,"description":"Cache in JSON format of tournaments posted on MTGO, Manatraders, Melee and Topdeck Websites","license":null,"pushed_at":"2025-06-10T17:14:13Z"} — repo metadata

> {"archived":true,"description":"Tools used to update MTGODecklistCache.","pushed_at":"2025-09-24T15:55:28Z"} — GET /repos/Badaro/MTGODecklistCache.Tools

> {"archived":false,"description":"Format and card data for use with MTGOArchetypeParserData","license":null,"pushed_at":"2026-07-21T07:31:56Z"} — GET /repos/Badaro/MTGOFormatData

## Structural metadata

GitHub REST v3 `GET /repos/{owner}/{repo}` for the three Badaro repos, jq-projected;
fetched 2026-07-31 via authenticated `gh api`.
