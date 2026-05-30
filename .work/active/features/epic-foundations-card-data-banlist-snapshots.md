---
id: epic-foundations-card-data-banlist-snapshots
kind: feature
stage: drafting
tags: [ingestion]
parent: epic-foundations-card-data
depends_on: [epic-foundations-card-data-package-skeleton]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Ban-List Snapshots & Legality Validation

## Brief

Version-stamped Legacy legality as a blacklist. Model `BanListSnapshot` (a set of banned card names +
per-entry `banned_date` + `ban_reason` + category predicates for conspiracy/ante/stickers/offensive),
seed dated snapshots from WotC B&R announcements (current to the May 18 2026 Undercity Informer ban),
and provide **as-of-date validation**: `is_legal(card, as_of_date)` resolves against the snapshot in
effect on that date, so a 2024 deck that legally ran Psychic Frog validates correctly. Deck-construction
validation too (60+ maindeck, 0–15 sideboard, ≤4 copies unless basic/override).

Legality trusts this blacklist, NOT Scryfall's `legacy` flag (which lags B&R by hours-to-days). Pure
data + validation logic over the `Card`/`Decklist` models. Independent of Scryfall ingestion — depends
only on the model base. Does NOT cover archetype labeling or analytics.

## Epic context
- Parent epic: `epic-foundations-card-data`
- Position in epic: independent capability — parallelizable with `card-model-scryfall`, `card-derivations`, and `duckdb-store` (depends only on the skeleton's model base).

## Inherited design decisions
- **Legality = version-stamped blacklist**, validated as-of-event-date (NOT Scryfall's lagging flag).

## Research briefs
- `docs/briefs/legacy-foundations.md` — the full banned list (dated 2023–2026 changes with reasons), blacklist-vs-whitelist, deck-construction rules, category bans.

## Foundation references
- `docs/ARCHITECTURE.md` — `ingestion/banlist.py`, the `BanListSnapshot` model.
- `docs/SPEC.md` — BanListSnapshot entity; version-stamped-legality NFR.
- `docs/PRINCIPLES.md` — legality is live data; validate against a dated snapshot.
