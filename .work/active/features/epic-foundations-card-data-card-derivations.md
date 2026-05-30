---
id: epic-foundations-card-data-card-derivations
kind: feature
stage: drafting
tags: [ingestion]
parent: epic-foundations-card-data
depends_on: [epic-foundations-card-data-card-model-scryfall]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Card Derivations: Deck-Color Helper & Legacy Tags

## Brief

The Legacy-semantic enrichment layered onto resolved cards. Two capabilities: (1) the **deck-color
helper** `compute_deck_colors(decklist) → colors` implementing MTGOArchetypeParser's `GetColors` —
a color is in the deck iff it appears in BOTH a land (`produced_mana`, minus C) AND a nonland
(`colors`); NOT `color_identity`. This is the helper the archetype classifier's color-prefix step
consumes. (2) **Legacy card tags** derived from Scryfall fields: `is_free_spell` (oracle-text
alt-cost patterns), mana-base tags (`is_original_dual`, `is_fetchland`, `is_fast_mana_land`,
`is_denial_land`, etc. from type_line / produced_mana / oracle_text), and `staple_role` from a
curated name→role table seeded by the foundations brief's staples table.

These are pure functions / derived fields over the `Card` model — the analytically valuable
Legacy-specific signals. Does NOT include archetype classification itself (that's the archetype epic);
this only provides the color + tag inputs it will need.

## Epic context
- Parent epic: `epic-foundations-card-data`
- Position in epic: consumer of `card-model-scryfall`; parallelizable with `duckdb-store`. The `compute_deck_colors` helper is a hard dependency of the later archetype classifier.

## Inherited design decisions
- **Card model = typed Pydantic** — tags are derived fields/methods on Card; the color helper operates over a list of Cards.
- Color = lands.produced_mana ∩ nonlands.colors (NOT color_identity) — the single most important derivation correctness point.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md` — GetColors intersection method, the field mapping, is_free_spell / mana-base / staple_role derivation recipes.
- `docs/briefs/legacy-foundations.md` — the staples table (seed for staple_role), is_free_spell definition, mana-base classification tags.

## Foundation references
- `docs/ARCHITECTURE.md` — `archetype/colors.py` (the color helper lives at the card layer per the contract brief), the Legacy card tags on the Card model.
