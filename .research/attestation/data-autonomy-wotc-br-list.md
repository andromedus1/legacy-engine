---
source_handle: data-autonomy-wotc-br-list
fetched: 2026-07-31
source_url: https://magic.wizards.com/en/banned-restricted-list
provenance: source-direct
source_class: reference-page
---

# WotC — standing Banned & Restricted list page

## Summary

The standing all-formats banned/restricted list ("Banned & Restricted | Magic: The
Gathering"). It is a Nuxt-rendered page, but the format sections and the card names are
present in the served HTML — a grep for "Candelabra of Tawnos" in the raw fetched HTML
hits twice — so the page is scrapeable without JavaScript execution. The Legacy section
opens with a fixed heading ("Legacy Banned Cards / The following cards are banned in
legacy tournaments:") followed by category-ban prose (Conspiracy-type cards, ante
cards, offensive cards) and then the card list. Viable as a slower-moving cross-check
for the B&R monitor, though the announcement page + Scryfall legalities diff are the
sharper signals.

## Key passages

> Legacy Banned Cards The following cards are banned in legacy tournaments: 25 cards with the Card Type "Conspiracy." … 9 cards that reference "playing for ante." … Cards whose art, text, name, or combination thereof that are racially or culturally offensive are banned in all formats. — Legacy section opening (tag-stripped text)

> grep -c "Candelabra of Tawnos" on the raw served HTML returns 2 — server-rendered card list check, 2026-07-31

## Structural metadata

HTML fetched 2026-07-31 (curl, browser UA; HTTP 200, no redirect). Nuxt app shell with
server-rendered content sections.
