---
source_handle: data-autonomy-scryfall-bulk-api
fetched: 2026-07-31
source_url: https://api.scryfall.com/bulk-data
provenance: source-direct
source_class: api-response
---

# Scryfall live API — GET /bulk-data listing (2026-07-31)

## Summary

The live bulk-data listing as of 2026-07-31. Load-bearing observation: every
`bulk_data` object (all seven types, including `oracle_cards` and `default_cards`)
carries **only** `jsonl_download_uri` — the plain-JSON `download_uri` field is gone.
legacy-engine's `ingestion/scryfall.py` reads `meta["download_uri"]`
(`_validate_scryfall_uri(meta["download_uri"])`, line 107), so the engine's bulk
download path is latently broken against the current API and will KeyError on its next
cold run. `updated_at` timestamps confirm daily refresh (all types stamped 2026-07-31
~21:00 UTC at a 2026-07-31 ~23:00 UTC fetch). `oracle_cards` compressed size ~24.4 MB,
`default_cards` ~77.2 MB. A copy of the listing is saved at
`.research/reference/data-autonomy-upstream/scryfall-bulk-listing-2026-07-31.json`.

## Key passages

> "type": "oracle_cards", "updated_at": "2026-07-31T21:03:00.228+00:00", … "jsonl_download_uri": "https://data.scryfall.io/oracle-cards/oracle-cards-20260731210300.jsonl.gz", "compressed_size": 24396732 — oracle_cards entry

> "type": "default_cards", … "jsonl_download_uri": "https://data.scryfall.io/default-cards/default-cards-20260731211028.jsonl.gz", "compressed_size": 77176423 — default_cards entry

> Field check across all seven entries: URI-bearing keys are exactly `uri` and `jsonl_download_uri`; no entry has `download_uri`. — key inventory (oracle_cards, unique_artwork, default_cards, all_cards, rulings, art_tags, oracle_tags)

## Structural metadata

Live JSON responses: `GET /bulk-data` (list) and `GET /bulk-data/oracle_cards` (single
object), fetched 2026-07-31 with a descriptive User-Agent. Saved copy in the reference
corpus (path above).
