---
source_handle: data-autonomy-ck-pricelist
fetched: 2026-07-31
source_url: https://api.cardkingdom.com/api/v2/pricelist
provenance: source-direct
source_class: api-response
---

# Card Kingdom live pricelist API — GET /api/v2/pricelist (2026-07-31)

## Summary

Direct fetch of Card Kingdom's public pricelist endpoint, no authentication, plain GET
with a descriptive User-Agent. Returned a 66,775,641-byte JSON document with two top
keys, `meta` (created_at timestamp + base_url) and `data`: 149,977 product rows. Each
row carries `sku`, **`scryfall_id`** (direct join key to the engine's card layer),
`name`, `edition`, `is_foil`, `price_retail`, `qty_retail`, `price_buy` (buylist),
`qty_buying`, and per-condition buy prices/quantities (NM/EX/VG/G). Spot check on the
dogfooding pain card: Lion's Eye Diamond (Mirage) shows retail $949.99 / NM buylist
$535.00 — confirming the CK-vs-Scryfall divergence that motivated the idea. The
`meta.created_at` of 2026-07-31 14:10 on a same-day fetch indicates the list is
regenerated at least daily. A trimmed sample (meta, row schema, LED rows) is saved at
`.research/reference/data-autonomy-upstream/ck-pricelist-sample-2026-07-31.json`.

## Key passages

> "meta": {"created_at": "2026-07-31 14:10:35", "base_url": "https://www.cardkingdom.com/"} — response meta

> data row count: 149,977; response size: 66,775,641 bytes — measured on the 2026-07-31 fetch

> {"id": 10000, "sku": "4ED-117", "scryfall_id": "a363bc91-8278-448e-9d5c-564e4b51eb62", "url": "mtg/4th-edition/abomination", "name": "Abomination", "variation": "", "edition": "4th Edition", "is_foil": "false", "price_retail": "0.35", "qty_retail": 16, "price_buy": "0.01", "qty_buying": 10, "condition_values": {"nm_price": "0.35", …}} — first data row (schema example)

> Lion's Eye Diamond (Mirage, sku MIR-307, scryfall_id 63bacc32-d6ba-420c-9b49-299c08e5fb39): "price_retail": "949.99", "qty_retail": 20, "price_buy": "535.00", "qty_buying": 22 — spot check

## Structural metadata

Live JSON fetched 2026-07-31 with `curl -A "legacy-engine-research/0.1"`; no API key or
login required; single request, ~67 MB. No usage-policy text is embedded in the
response. Sample preserved in the reference corpus (path above).
