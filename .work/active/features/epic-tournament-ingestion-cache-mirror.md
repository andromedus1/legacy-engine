---
id: epic-tournament-ingestion-cache-mirror
kind: feature
stage: done
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

## Architectural choice (autopilot, judgment)
Add to `ingestion/cache.py`: `mirror_cache(repo, dest, runner=subprocess.run)` — `git clone` if `dest`
absent else `git pull`; the `runner` is injected so tests assert the branch without invoking git.
`discover_legacy_events(cache_dir)` walks `Tournaments/<Source>/<Y>/<M>/<D>/*.json`, loads each, keeps
those with `Tournament.Formats == "Legacy"`, yielding `(path, source)` (source = the dir under
`Tournaments/`). `ingest_cache(con, cache_dir)` parses + `load_tournament`s each discovered event,
returns the count. `seed cache` CLI = `mirror_cache()` → `ingest_cache(connect(), CACHE_DIR)`. Tests
drive discovery/ingest from a fixture dir; the live clone is never run in tests.

## Implementation Units
### Unit 1: `ingestion/cache.py` additions
`mirror_cache(repo=FBETTEGA_CACHE_REPO, dest=CACHE_DIR, runner=subprocess.run)`,
`discover_legacy_events(cache_dir) -> list[tuple[Path, str]]`, `ingest_cache(con, cache_dir) -> int`.
### Unit 2: wire `seed cache` CLI (mirror → ingest)
**Acceptance**: `discover_legacy_events` finds Legacy events under the Tournaments tree and skips non-Legacy + non-json; `ingest_cache` loads N tournaments into DuckDB; `mirror_cache` calls `git clone` when dest absent and `git pull` when present (via injected runner, no real git); `seed cache` reports tournaments ingested.

## Testing
- `tests/test_cache_mirror.py` — build a fixture `Tournaments/MTGO/2026/05/24/*.json` (a Legacy Challenge) + `Tournaments/MTGmelee/...` (Legacy paper) + a non-Legacy file (filtered out); assert discovery, `ingest_cache` row counts in in-memory DuckDB, and `mirror_cache` clone-vs-pull branch with a fake runner. No network/git.

## Implementation notes
- **Files changed**: `src/legacy_engine/ingestion/cache.py` (+`mirror_cache` with injected runner, `discover_legacy_events`, `ingest_cache`); wired `seed cache` CLI (mirror → ingest).
- **Tests added**: `tests/test_cache_mirror.py` — full suite **105 passing in 0.38s**. No network/git (runner injected; discovery/ingest from a fixture tree).
- **Discrepancies from design**: none.
- **Test debt fixed in-session**: removed `seed cache` from `test_cli`'s not-implemented list (now wired); fixed a discover test that asserted the wrong sort order (uppercase `O` < lowercase `m`) → switched to a set comparison.
- **Adjacent issues parked**: none.

## Review (2026-05-29)
**Verdict**: Approve. **Blockers/Important**: none.
**Nits**: `mirror_cache` uses `--depth 1` (shallow) — fine for a mirror we only ever pull HEAD of; if historical backfill is needed later, drop the depth. `ingest_cache` re-reads each file's JSON after discovery already parsed it — negligible at this scale, could pass the loaded dict through if profiling ever flags it.
**Notes**: The mirror is the decouple boundary (analytics reads the local mirror + DuckDB, never live upstream); git is isolated behind an injected runner so tests never clone. End-to-end `seed cache` = mirror → discover → parse → load. 105 tests green. Last feature of the epic.
