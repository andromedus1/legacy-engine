---
id: epic-stable-era-windows-era-ledger-store
kind: story
stage: review
tags: [analytics, ingestion]
parent: epic-stable-era-windows-era-ledger
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# BAN_EVENTS curated-JSON migration + entity_eras store

## Brief
Units A+B of the parent feature: banlist events JSON loader (module API unchanged, append path for the confirm loop) and the rebuildable entity_eras DuckDB store with stable_since_map() as the consumption entry point.

## Implementation
Parent feature `epic-stable-era-windows-era-ledger` — exact contracts + acceptance criteria there.

## Implementation notes

**Unit A — `ingestion/banlist.py` + `data/banlist/events.json`**
- `events.json` carries the 12 `BAN_EVENTS` entries verbatim (dates/cards/reasons), including
  the non-ASCII "Troll of Khazad-dûm" (`ensure_ascii=False` on write; verified round-trip).
- `load_ban_events(path)` — fail-fast citing path/index/key on bad root shape, bad date, missing
  card/reason, or a duplicate `(date, card)` pair; always returns sorted by `(date, card)`.
- `append_ban_event(date, card, reason, *, path)` — the confirm-loop write path; rejects a
  duplicate `(date, card)`; creates the file (+ parent dirs) if absent; keeps it sorted.
- `_load_default_ban_events()` binds `BAN_EVENTS` at import from `config.BAN_EVENTS_PATH`.
  **Deliberate deviation** from the curated-json-resource-loader pattern's usual
  degrade-to-empty-on-error convention: an empty `BAN_EVENTS` would silently un-ban every dated
  card (a legality regression), so this loader lets a broken/missing shipped file fail loudly at
  import instead — documented in the module docstring.
- Config: `BAN_EVENTS_DIR`/`BAN_EVENTS_PATH` added to `config.py` (package-data convention,
  matching `HOSERS_REGISTRY_PATH`). No `pyproject.toml`/MANIFEST change needed — hatchling's
  default wheel build already ships everything under `src/legacy_engine` (verified: the existing
  `data/hosers|variants|players` JSON already ship this way with no explicit include/exclude).
- Module API unchanged: `BAN_EVENTS`, `BASELINE_BANS`, `banlist_as_of`, `current_banlist`,
  `validate_deck` all still importable exactly as before; every existing consumer
  (`analytics/trends.py::regime_windows`, `analytics/affectedness.py`) imports `BAN_EVENTS`
  unchanged.

**Unit B — `analytics/eras/store.py`**
- `init_eras_schema(con)` — idempotent `CREATE TABLE IF NOT EXISTS entity_eras`.
- `write_entity_eras(con, eras, attributions, alarms, *, run_meta)` — DROP → schema → INSERT,
  always a full replace (never upsert): `derive_eras`'s BH-FDR is fleet-wide, so a partial
  recompute would corrupt every other entity's `bh_accepted` verdict.
- `read_entity_eras(con) -> dict[str, StoredEntityEras]` — full typed round-trip
  (`StoredEntityEras` → `StoredBoundary` → `StoredAttribution`/`StoredSignal`), boundaries
  serialized as a JSON column, attribution + alarm as first-class columns.
- `stable_since_map(con) -> dict[str, str | None]` — the consumption seam; a lightweight direct
  query (no JSON deserialization) since `-consumption`'s adaptive-matrix horizon function only
  needs the date.
- `run_meta` threads `post_boundary_decks: dict[entity, int]` (the `eras list` confidence-tier
  sample size) and `parent: dict[entity, str]` (since `ensemble.EntityEras` itself carries no
  `parent` field — that lives on `series.EntitySeries`) — both computed by `-run`'s `run_eras`.
- `Attribution`/`AlarmFlag` (owned by the `-run` story, not yet implemented at this story's
  layer) are consumed duck-typed via `TYPE_CHECKING`-only imports (`from __future__ import
  annotations` defers all annotation evaluation) — `store.py` has no runtime dependency on
  `attribution.py`/`run.py`. Unit B's own tests use local doubles carrying the same
  `kind`/`card`/`detail` and `p_change`/`note` shape.

**Tests**: `tests/test_banlist.py` (+15: `TestLoadBanEvents`, `TestAppendBanEvent`),
`tests/analytics/eras/test_store.py` (11 new: schema idempotence, full round-trip incl. nested
signals/attribution, alarm fields, camp `parent` threading, rebuild-replaces-stale-entity,
`stable_since_map` matching ensemble output + honest-empty on a missing table).

**Verification**: scoped (`-k "banlist or affectedness or trends or regime"`) green before and
after (142 passed both times — proves zero behavior change for existing BAN_EVENTS consumers);
full suite 2836 passed, 1 xfailed (baseline 2813 + 1 xfail + 23 net new tests); `ruff check` clean
on all changed/new files.

**Deviations**: none from the pinned Unit A/B contracts. The `_load_default_ban_events`
fail-loud-on-error choice is a documented, deliberate deviation from the general curated-loader
convention (see above), not from this story's own AC.
