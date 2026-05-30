---
id: epic-tournament-ingestion-cache-mirror
kind: feature
stage: drafting
tags: [ingestion]
parent: epic-tournament-ingestion
depends_on: [epic-tournament-ingestion-cache-parser, epic-tournament-ingestion-duckdb-tables]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Cache Mirror + `seed cache` Wiring

## Brief
Mirror the fbettega `MTG_decklistcache` repo locally (git clone, then `git pull` for incremental
refresh) and discover the Legacy tournament-file paths within it (walk `Tournaments/<Source>/<Y>/<M>/<D>/`,
filter to `Formats == "Legacy"`). Wire the `seed cache` CLI to run the full mirror → parse → load
pipeline. The mirror layer is the decouple boundary: analytics reads only the local mirror + DuckDB,
never the live upstream. The git operations live behind a thin function so tests can drive
discovery/load against a fixture directory without cloning.

## Epic context
- Parent epic: `epic-tournament-ingestion`. The integration feature — ties parser + duckdb-tables into `seed cache`.

## Inherited design decisions
- Mirror-and-decouple: consume the cache JSON from a local mirror (not mtgo.com); swap-able behind the ingestion boundary.
- git clone/pull + day-folder discovery; provenance from source dir.

## Research briefs
- `docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md` — repo layout, cadence, consumption strategy, Legacy event discovery.
- `docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md` — mirror-and-decouple resilience, staleness.

## Foundation references
- `docs/ARCHITECTURE.md` — `ingestion/cache.py` mirror; `config.CACHE_DIR`, `config.FBETTEGA_CACHE_REPO`; the `seed cache` CLI command.
