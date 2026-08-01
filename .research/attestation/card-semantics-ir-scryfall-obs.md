---
source_handle: card-semantics-ir-scryfall-obs
fetched: 2026-07-31
source_url: https://api.scryfall.com/cards/named?exact=Force%20of%20Negation
provenance: source-direct
source_class: standard
---

# Scryfall API live observations — `keywords` coverage on Legacy staples

## Summary

Direct queries against the live Scryfall REST API (2026-07-31) to measure what the `keywords`
array does and does not capture for the card classes legacy-engine's advisory layer cares
about. Result: `keywords` faithfully carries CR keyword abilities — Murktide Regent returns
`["Flying", "Delve"]` — but returns an empty array for cards whose analytically important
behavior is expressed through non-keyword templated prose: Force of Negation (pitch
alternative cost, `keywords: []`) and Leyline of the Void (opening-hand replacement +
graveyard replacement, `keywords: []`). So Scryfall `keywords` is free, reliable seed data
for the keyword-mechanic slice (delve/flash/ward/storm...) and structurally silent on
alternative-cost, opening-hand, color-conditional, and scope templates — those must come from
oracle-text analysis.

## Key passages

> "name": "Force of Negation", "keywords": [], "oracle_text": "If it's not your turn, you may
> exile a blue card from your hand rather than pay this spell's mana cost.\nCounter target
> noncreature spell. If that spell is countered this way, exile it instead of putting it into
> its owner's graveyard." — GET /cards/named?exact=Force of Negation

> "name": "Murktide Regent", "keywords": ["Flying", "Delve"]
> — GET /cards/named?exact=Murktide Regent

> "name": "Leyline of the Void", "keywords": [], oracle_text begins: "If this card is in your
> opening hand, you may begin the game with it on the battlefield.\nIf a card would be put
> into an opponent's graveyard..." — GET /cards/named?exact=Leyline of the Void

## Structural metadata

Three GET requests to `https://api.scryfall.com/cards/named?exact=<name>` with a descriptive
User-Agent and `Accept: application/json`, per Scryfall API usage guidance. JSON card objects;
values quoted verbatim from the responses.
