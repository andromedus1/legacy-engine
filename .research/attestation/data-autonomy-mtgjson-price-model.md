---
source_handle: data-autonomy-mtgjson-price-model
fetched: 2026-07-31
source_url: https://mtgjson.com/data-models/price/price-list/
provenance: source-direct
source_class: api-docs
---

# MTGJSON docs — Price List data model

## Summary

MTGJSON's price data model. Its provider set includes **cardkingdom** (alongside
cardhoarder, cardmarket, cardsphere, tcgplayer, manapool), and each provider entry
carries optional `buylist` and `retail` price-point maps plus a required `currency`
string — i.e., MTGJSON already aggregates Card Kingdom retail AND buylist prices (and
TCGplayer's) keyed by MTGJSON card uuid. This makes MTGJSON the sanctioned-aggregator
alternative to hitting Card Kingdom's endpoint directly.

## Key passages

> cardhoarder, cardkingdom, cardmarket, cardsphere, tcgplayer, manapool — provider list

> "buylist" for "selling cards to this provider" … "retail" for "buying cards from this provider" — property semantics (both optional)

> buylist?: PricePoints; currency: string; retail?: PricePoints; — TypeScript model

## Structural metadata

MTGJSON documentation page (data-models/price/price-list), fetched 2026-07-31 via
WebFetch; quotes are the field/provider enumerations from the model table.
