---
source_handle: data-autonomy-scryfall-cards-docs
fetched: 2026-07-31
source_url: https://scryfall.com/docs/api/cards
provenance: source-direct
source_class: api-docs
---

# Scryfall API docs — Card objects (legalities field)

## Summary

The Card object documentation defines the `legalities` field: an object mapping each
play format to one of four values — `legal`, `not_legal`, `restricted`, `banned`. This
is the machine-readable per-card banlist signal: diffing `legalities.legacy` across two
oracle_cards bulk snapshots yields exactly the set of cards whose Legacy legality
changed (ban, unban, or newly-legal printing), which is the proposed detection primitive
for the B&R monitor.

## Key passages

> legalities Object An object describing the legality of this card across play formats. Possible legalities are legal, not_legal, restricted, and banned. — Card object field table

## Structural metadata

HTML page fetched 2026-07-31 (curl, browser UA); text extracted by tag-stripping from
the Card object property table.
