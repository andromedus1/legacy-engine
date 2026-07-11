---
source_handle: mtgo-archetype-parser
fetched: 2026-07-11
source_url: https://github.com/Badaro/MTGOArchetypeParser
provenance: source-direct
---

## Summary

Badaró's MTGOArchetypeParser — the de facto production standard for archetype tagging across the
MTGO tournament-data ecosystem (and the parser legacy-engine's own archetype layer reimplements). It
is a rules-based engine: archetypes (and their sub-variants) are hand-authored card-presence
conditions, NOT discovered by clustering. This is the baseline/contrast for the discovery epic — the
dominant approach solves subarchetype splitting via curated boolean rules, which is exactly the
human-authoring the epic wants to reduce dependence on.

## Key passages

- Rules-based: "Rules-based engine to detect archetypes from MTGO decklists." (README tagline,
  confirmed verbatim; the parser's Variant mechanism — a variant matches only after the parent
  archetype's rules match — is documented in the companion MTGOFormatData repo and is the direct
  curated analogue of the discovered `decks.variant` split, but was not confirmed verbatim on the
  fetched README page.)
