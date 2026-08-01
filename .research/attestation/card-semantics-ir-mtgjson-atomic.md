---
source_handle: card-semantics-ir-mtgjson-atomic
fetched: 2026-07-31
source_url: https://mtgjson.com/data-models/card/card-atomic/
provenance: source-direct
source_class: standard
---

# MTGJSON data model — Card (Atomic)

## Summary

MTGJSON's Card (Atomic) model is the per-oracle-identity card record (one entry per functional
card, not per printing). Fields relevant to a semantics IR: `keywords` ("A list of keywords
found on the card"), `types` / `subtypes` / `supertypes` (the parsed decomposition of the type
line — MTGJSON pre-splits what Scryfall ships as a single `type_line` string), and `text` (the
rules text). MTGJSON offers no functional/semantic classification beyond keywords and type
decomposition — there is no removal/counterspell/tutor-style tagging in the data model. Its
value to the IR is (a) the pre-parsed type decomposition and (b) the companion Keywords.json
enumeration (attested separately) that provides the closed keyword vocabulary as data.

## Key passages

> keywords — "A list of keywords found on the card." — § Card (Atomic) field docs

> types — "A list of all card types of the card, including Un-sets and gameplay variants."
> — § Card (Atomic) field docs

> subtypes — "A list of card subtypes found after em-dash." — § Card (Atomic) field docs

> supertypes — "A list of card supertypes found before em-dash." — § Card (Atomic) field docs

> text — "The rules text of the card." — § Card (Atomic) field docs

## Structural metadata

Data-model documentation page from mtgjson.com (v5 documentation). Card (Atomic) is one of
several card models (Card (Set), Card (Deck), ...); atomic keys are card names, values are
arrays of face objects.
