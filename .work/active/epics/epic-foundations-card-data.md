---
id: epic-foundations-card-data
kind: epic
stage: drafting
tags: [ingestion]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Foundations & Card Data

## Brief

The base layer everything else builds on: the shared Pydantic data models, project config/CLI
skeleton, the extended Scryfall card-data ingestion (indexing the whole Legacy oracle pool), the
DuckDB analytical-store scaffolding, and dated ban-list snapshots for version-stamped legality.

This epic delivers a queryable card dimension and the storage substrate — `Card` resolution by name
(including split/DFC/adventure faces), the deck-color helper (`lands.produced_mana ∩ nonlands.colors`,
NOT `color_identity`), the `BanListSnapshot` blacklist with `banned_date`/`ban_reason`, and a DuckDB
database that the rest of the system reads. It does NOT cover tournament data (that's
`epic-tournament-ingestion`) or any archetype/analytics logic.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md` — the Scryfall fields the system keys on; ADR: extend edh-engine's `scryfall.py`, index the whole oracle pool; the Card model + colors-of-deck helper.
- `docs/briefs/legacy-foundations.md` — deck-as-data card model, `staple_role`/`is_free_spell` tags, the ban-list (current to May 18 2026) + blacklist validation.
- `docs/briefs/ingestion-archetype-contracts/parent.md` — the synthesized data-layer build plan.

## Foundation references
- `docs/ARCHITECTURE.md` — `models/`, `ingestion/scryfall.py`, `ingestion/store.py` (DuckDB), `ingestion/banlist.py`; the storage decision (raw JSON source-of-truth + rebuildable DuckDB).
- `docs/SPEC.md` — Card, BanListSnapshot entities; reproducibility + version-stamped-legality NFRs.
- `docs/PRINCIPLES.md` — legality is live data; sibling-consistent, divergence-justified.

## Anticipated child features
- Pydantic models package (`Card`, `BanListSnapshot`, `ConfidenceMetadata`, shared base types)
- CLI + config skeleton (Click nested groups; `config.py` paths/URLs/pinned-SHAs)
- Extended Scryfall ingestion (oracle bulk + whole-pool name index + face-name keys + batch fallback)
- Deck-color helper + Legacy card tags (`is_free_spell`, `staple_role`, mana-base tags)
- DuckDB store scaffolding (schema, load helpers, rebuildable-from-raw guarantee)
- Ban-list snapshots (dated blacklist + as-of-date validation)
