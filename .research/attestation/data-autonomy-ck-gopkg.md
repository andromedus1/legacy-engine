---
source_handle: data-autonomy-ck-gopkg
fetched: 2026-07-31
source_url: https://pkg.go.dev/github.com/mtgban/go-cardkingdom
provenance: source-direct
source_class: library-docs
---

# go-cardkingdom (mtgban) — Card Kingdom API client documentation

## Summary

Documentation of an established third-party client for Card Kingdom's price API
(mtgban is the price-aggregation project behind mtgban.com). Confirms the two
endpoints (singles at /api/v2/pricelist, sealed at /api/sealed_pricelist), that the
client always sends an identifying User-Agent, and pins the field semantics observed in
the live fetch: PriceRetail = what CK charges buyers, PriceBuy = buylist offer with 0
meaning "not purchasing", QtyBuying = additional copies CK will buy, ScryfallID = the
cross-reference key (empty for sealed). Corroborates that third-party consumption of
this endpoint is established practice.

## Key passages

> PricelistURL = "https://api.cardkingdom.com/api/v2/pricelist" — constant

> SealedListURL = "https://api.cardkingdom.com/api/sealed_pricelist" — constant

> UserAgent is the HTTP User-Agent header sent with every request. — constant doc

> PriceBuy (float64): Current buylist price Card Kingdom will pay, in USD (0 = not purchasing) — field doc

> ScryfallID (string): Scryfall UUID for cross-referencing with Scryfall API (empty for sealed products) — field doc

## Structural metadata

pkg.go.dev rendered package documentation, fetched 2026-07-31 via WebFetch; constants
and field docs quoted from the package's exported symbols.
