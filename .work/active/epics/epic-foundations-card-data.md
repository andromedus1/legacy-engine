---
id: epic-foundations-card-data
kind: epic
stage: done
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

## Design decisions
- **Card representation: typed `Card` Pydantic model** (canonical) — `scryfall.py` resolves raw JSON → Card with derived colors + Legacy tags. Sets the project's model idiom. (vs edh-engine's raw-dict + lazy-resolve.)
- **Card storage: both** — in-memory name index as the primary O(1) resolution path (classifier hot path) + a materialized DuckDB `cards` table for relational joins in analytics.
- **Analytical store: DuckDB** (confirmed) — embedded, column-oriented, rebuildable derived cache over a raw-JSON source of truth; chosen for the matchup-matrix rounds-join + meta-share group-by workload while keeping the "no server, reproducible local files" property.
- **Stack: mirror edh-engine** (hatchling, `src/legacy_engine/`, Click, Pydantic, httpx) + declare duckdb/numpy/scipy/statsmodels/pulp now.
- **Scryfall: extend, don't fork** edh-engine's `scryfall.py`; index the whole oracle pool, resolve on demand.
- **Legality: version-stamped blacklist** validated as-of-event-date (NOT Scryfall's lagging `legacy` flag).

## Decomposition

Split by capability into 5 features. The package skeleton sets the model/CLI/config/confidence patterns
everything inherits; card resolution produces the typed `Card` + in-memory index; derivations and the
DuckDB store both build on the Card model and parallelize; the ban-list is independent (depends only on
the skeleton). Critical path is skeleton → card-model-scryfall → (derivations | store), with the
ban-list running in parallel off the skeleton.

### Child features
- `epic-foundations-card-data-package-skeleton` — package/pyproject/config/CLI skeleton + ConfidenceMetadata + model base (pattern-setting) — depends on: `[]`
- `epic-foundations-card-data-card-model-scryfall` — typed `Card` model + ported Scryfall ingestion (whole-pool index) — depends on: `[epic-foundations-card-data-package-skeleton]`
- `epic-foundations-card-data-card-derivations` — `compute_deck_colors` helper + Legacy card tags — depends on: `[epic-foundations-card-data-card-model-scryfall]`
- `epic-foundations-card-data-duckdb-store` — DuckDB store scaffolding + materialized `cards` table — depends on: `[epic-foundations-card-data-card-model-scryfall]`
- `epic-foundations-card-data-banlist-snapshots` — `BanListSnapshot` blacklist + as-of-date legality validation — depends on: `[epic-foundations-card-data-package-skeleton]`

### Decomposition risks
- `card-model-scryfall` Card-model scope could balloon — constrain to the contract brief's named fields.
- `card-derivations` and `card-model-scryfall` are adjacent (Card + its derived fields); if `card-derivations` proves thin at feature-design it may merge upward.
- `duckdb-store` forward-declares tournament-data tables it doesn't populate — define only `cards` fully now; the tournament-ingestion epic owns the rest.

## Epic review (2026-05-29) — Children complete

All 5 child features at `stage: done`. **Verdict: Approve — epic delivered as briefed.**

Aggregate capability check: the foundations capability works end-to-end — `legacy seed cards`
downloads the Scryfall oracle bulk, builds the whole-pool name index, and materializes the DuckDB
`cards` table; `Card` resolves typed; `compute_deck_colors` + Legacy tags derive correctly;
`legacy seed banlist` reports the version-stamped ban list and `validate_deck` enforces construction
rules. **80 tests green.** Project patterns established and codified (`.agents/skills/patterns/`).

No cross-cutting concerns, no foundation-doc drift, no breaking-change surface (greenfield). Unblocks
the next epic in the chain (`epic-tournament-ingestion`).
