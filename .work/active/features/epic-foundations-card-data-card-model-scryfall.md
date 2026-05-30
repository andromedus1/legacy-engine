---
id: epic-foundations-card-data-card-model-scryfall
kind: feature
stage: review
tags: [ingestion]
parent: epic-foundations-card-data
depends_on: [epic-foundations-card-data-package-skeleton]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Card Model & Scryfall Ingestion

## Brief

The typed `Card` Pydantic model and the Scryfall ingestion that produces it. Port edh-engine's
`ingestion/scryfall.py` (~214 lines — verified to contain `download_bulk_data`, `load_card_index`,
`_batch_lookup`, `normalize_name`, `resolve_card_pool`) and adapt it for Legacy: download the
`oracle_cards` bulk, index the **whole** oracle pool by name + each split/DFC/adventure face name
(O(1) name→card, the classifier's hot path), with the `/cards/collection` batch fallback. Resolve raw
Scryfall JSON into the canonical `Card` model.

The `Card` model carries identity (name, mana_cost, cmc, type_line, layout, card_faces), the raw color
inputs the classifier needs (`colors`, `produced_mana`), and `legalities.legacy` — but legality is
authoritatively validated against the ban-list blacklist (sibling feature), not this field. Derived
Legacy fields (deck-color helper, is_free_spell, staple_role, mana-base tags) are layered in the
`card-derivations` sibling. Does NOT include the DuckDB cards table (that's `duckdb-store`) or the
ban-list.

## Epic context
- Parent epic: `epic-foundations-card-data`
- Position in epic: produces the `Card` model + in-memory name index that `card-derivations`, `duckdb-store`, and (later) the archetype classifier all consume.

## Inherited design decisions
- **Card model = typed Pydantic** (canonical representation; resolve raw JSON → Card).
- **Card storage = both** — this feature owns the in-memory name index (primary resolution path); the DuckDB `cards` table is materialized by the `duckdb-store` sibling.
- **Scryfall ADR = extend, don't fork** edh-engine's scryfall.py; index the whole pool, resolve on demand (no fixed `card_pool.json` subset).

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md` — the exact fields, the whole-pool indexing, split/DFC/adventure face handling, oracle_cards bulk, batch fallback, the Card model shape.
- `docs/briefs/legacy-foundations.md` — the deck-as-data card model.

## Foundation references
- `docs/ARCHITECTURE.md` — `ingestion/scryfall.py`, `models/Card`.
- edh-engine port source: `/Users/<user>/dev/edh-engine/src/edh_engine/ingestion/scryfall.py`.

## Decomposition risks
- **Card model scope creep** — model only the fields the contract brief names (identity, colors, produced_mana, type_line, layout, card_faces, legalities), not all of Scryfall. Resist over-modeling.

## Architectural choice (autopilot, judgment)
Keep the in-memory index as **raw Scryfall dicts** (fast whole-pool load + face keys, ported from
edh-engine's `load_card_index`) and **resolve to a typed `Card` on demand** via `Card.from_scryfall`.
Resolving ~30k cards to Pydantic eagerly is wasteful when a run touches a few hundred; the hot path is
name→dict O(1), and a typed `Card` is materialized only where needed (classifier, store). Satisfies the
epic's "index whole pool, resolve on demand" + dual-storage decisions. (Eager-Card-index rejected on
load cost; dicts-everywhere rejected — the epic locked a typed Card.)

## Implementation Units

### Unit 1: `Card` model — `src/legacy_engine/models/card.py`
Typed Pydantic `Card(LegacyEngineModel)` with: `name`, `mana_cost`, `cmc`, `type_line`, `colors`
(Scryfall `colors`), `produced_mana`, `oracle_text`, `layout`, `card_faces` (raw, for split/DFC),
`legalities` (raw; NOT authoritative — see banlist). `is_land` property (`"Land" in type_line`);
`from_scryfall(raw)` = `model_validate` (extra="ignore" drops unmodeled keys). Re-export from `models/__init__.py`.
**Acceptance**: round-trips a real Scryfall dict; `is_land` true for a dual-land type line; split card keeps `card_faces`; unmodeled keys dropped.

### Unit 2: Scryfall ingestion — `src/legacy_engine/ingestion/scryfall.py`
Port edh-engine's `ScryfallClient` (bulk download + name index + `/cards/collection` batch fallback +
`normalize_name`), adapted: index the **whole** oracle pool (name + each ` // ` face), drop the
Moxfield-metadata filtering (no Moxfield), add `get_card(name) -> Card | None` resolving via
`Card.from_scryfall`. Replace the `seed cards` CLI stub with a lazy import calling `download_bulk_data`
+ index build.
**Acceptance**: `load_card_index` indexes a fixture by name AND face; `get_card("Fire")` resolves a "Fire // Ice"; `normalize_name` fixes curly apostrophes; `download_bulk_data` is HTTP-mocked (no network).

## Testing
- `tests/test_card.py` — `from_scryfall` mapping, `is_land`, split-card faces, extra-key drop (TestCard).
- `tests/test_scryfall.py` — `load_card_index` from a small fixture (name+face keys); `get_card` → `Card`; `normalize_name`; monkeypatch `_fetch_bulk_metadata` + client GET so `download_bulk_data` does no network. Deterministic.

## Implementation notes
- **Files created**: `src/legacy_engine/models/card.py` (Card), `src/legacy_engine/ingestion/scryfall.py` (ScryfallClient, ported+adapted); updated `models/__init__.py` (export Card) and `cli.py` (`seed cards` → real lazy-imported impl).
- **Tests added**: `tests/test_card.py`, `tests/test_scryfall.py` — full suite **45 passing in 0.09s**, deterministic, no network.
- **Discrepancies from design**: none material. Followed the established patterns (Card subclasses `LegacyEngineModel`; scryfall paths via config; CLI stub replaced per cli-nested-groups pattern).
- **Test debt fixed in-session**: `test_cli` still listed `seed cards` as a not-implemented stub — stale after wiring it; removed that parametrize entry (which had been triggering a real ~170MB Scryfall download in the suite). Its real behavior is covered by mocked `test_scryfall`.
- **Adjacent issues parked**: none.
