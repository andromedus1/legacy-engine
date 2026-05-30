---
id: epic-foundations-card-data-banlist-snapshots
kind: feature
stage: done
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

## Implementation notes
- **Files created**: `src/legacy_engine/models/banlist.py` (`BanListSnapshot` + copy-limit/basic-land/override constants), `src/legacy_engine/ingestion/banlist.py` (`BASELINE_BANS`, dated `BAN_EVENTS` 2022–2026, `banlist_as_of`, `current_banlist`, `validate_deck`); wired `seed banlist` CLI.
- **Tests added**: `tests/test_banlist.py` — as-of-date legality + deck-construction validation. Full suite **80 passing in 0.27s**.
- **Discrepancies from design**: none material.
- **Bug caught during implementation**: `Entomb` was initially in both `BASELINE_BANS` and `BAN_EVENTS` — removed from baseline so as-of-date legality is correct (it must only be banned from 2025-11-10).
- **Test debt fixed in-session**: removed `seed banlist` from `test_cli`'s not-implemented list (now wired); fixed two `test_banlist` fixtures that were themselves illegal decks (24 copies of Daze) — the validator correctly rejected them.
- **Adjacent issues parked**: none.

## Review (2026-05-29)
**Verdict**: Approve. **Blockers/Important**: none.
**Nits**: `BASELINE_BANS` is seeded from the brief and is extensive but not guaranteed exhaustive of every historical ban; `BAN_EVENTS` is the authoritative dated layer and is current to 2026-05-18. The Underworld Breach Legacy date is approximate (flagged in the brief) — `2025-02-01` placeholder. Category bans (conspiracy/ante/stickers/offensive) are listed but predicate-matching is left to the caller (no card-type data needed yet).
**Notes**: as-of-date legality verified across four date windows; `validate_deck` covers size, 4-of (with basic/override exemptions), and ban checks. Legality is the version-stamped blacklist, NOT Scryfall's flag (PRINCIPLES #5). 80 tests green.
