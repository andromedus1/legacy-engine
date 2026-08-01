---
source_handle: data-autonomy-mtgjson-allprices
fetched: 2026-07-31
source_url: https://mtgjson.com/downloads/all-files/
provenance: source-direct
source_class: api-docs
---

# MTGJSON docs — AllPrices / AllPricesToday file descriptions

## Summary

MTGJSON ships two price files: AllPrices (90 days of history for all cards, keyed by
card uuid) and AllPricesToday (current-day prices only). AllPricesToday is the
right-sized daily pull for a price-refresh job; AllPrices provides backfill/history if
the engine ever wants price trends.

## Key passages

> File containing all prices of cards in various formats organized by a card's `uuid` property for the past 90 days. — AllPrices description

> File containing all prices, for the current day, of cards in various formats organized by a card's `uuid` property. — AllPricesToday description

## Structural metadata

MTGJSON downloads/all-files page, fetched 2026-07-31 via WebFetch. Update cadence is
not stated on this page (see data-autonomy-mtgjson-faq for build times).
