---
id: epic-stable-era-windows-consumption-adapter
kind: story
stage: done
tags: [analytics]
parent: epic-stable-era-windows-consumption
depends_on: []
release_binding: v0.4.0
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Era-horizon adapter + field era resolver

## Brief
Unit 1: analytics/eras/consume.py — per-label horizon resolution (era → parent → ban-only), audit preamble, alarm surfacing, resolve_field_era max rule with thin degrade.

## Implementation
Parent feature `epic-stable-era-windows-consumption` — exact contracts + acceptance criteria there.

### Implementation notes (2026-07-11)

New file `src/legacy_engine/analytics/eras/consume.py`:

- `EraHorizon` frozen dataclass: `since` / `source` (`"era"` | `"era-parent"` | `"ban-only"`) /
  `trigger` / `alarm`.
- `era_horizons(con, archetypes, *, provenance=None, split_variant=None, affect_threshold=0.25)` —
  exact `entity_eras` row → parent row (camp labels via a locally duplicated `_parent_label`,
  same shape as `matchup._base_archetype`; duplicated rather than imported to avoid an
  `eras -> matchup -> eras` import cycle, since Unit 2 imports `era_horizons` from here) → ban-only
  fallback via `archetype_valid_since`. Returns `(horizons, audit_preamble)`; `audit_preamble` is
  the one-line whole-path degrade (`"// eras: no era data — ban-only horizons; run `eras run`"`)
  ONLY when `entity_eras` is missing/empty entirely — an entity individually absent from an
  otherwise-populated table degrades silently to ban-only for just that label (correct: the table
  isn't "absent", just incomplete for that entity).
- `_winning_boundary_trigger` — finds the accepted, non-floor-rejected boundary matching
  `stable_since` and surfaces its attribution `detail` as the trigger string.
- `resolve_field_era(con, *, provenance=None, min_share=0.02)` — `max(current ban-regime start,
  latest accepted boundary among PARENT entities [`parent == entity`, camps excluded] with
  full-corpus deck share >= min_share)`; self-heals to the ban-regime start + labeled banner when
  the resulting `[field_since, now)` window has fewer than 500 decks (`_FIELD_THIN_DECKS_FLOOR`,
  decks-based since field share is a metashare concept, not `window.py`'s rounds-based thinness
  proxy). Also degrades (without the thin-window wording) when there's no era data, no deck data,
  or no candidate boundary later than the ban-regime start.

### Tests

`tests/analytics/eras/test_consume.py` — 14 tests, hermetic `:memory:` DuckDB, `write_entity_eras`
+ hand-built `EntityEras`/`EraBoundary`/`Attribution` fixtures (mirrors `test_store.py`'s factory
idiom) plus real decks loaded via `ingestion.store`/`parse_cache_item` for `resolve_field_era`'s
deck-count queries:

- `TestEraHorizonsResolutionOrder` (7): exact entry (date + None/full-history), camp→parent
  fallback, camp's own entry winning over parent, entity individually absent from a populated
  table (no audit line), whole table absent (audit line present), alarm surfaced only when fired,
  and the ban-only branch genuinely re-derives `archetype_valid_since` (not just `None`).
- `TestResolveFieldEra` (7): no era data, high-share entity widens the field window, below-floor
  entity ignored, camp rows excluded from the share gate, thin resulting window degrades with a
  banner, and a boundary earlier than the ban-regime start never moves the window backward.

### Verification

- `.venv/bin/python -m pytest -q tests/analytics/eras/test_consume.py` → 14 passed.
- `ruff check` on both files → clean.
- Full suite (`.venv/bin/python -m pytest -q`) → 2881 passed, 1 xfailed (unchanged baseline;
  `consume.py` is new and unused by any other module yet, so zero risk of regression this story).

### Deviations from the parent doc

None. `era_horizons`/`resolve_field_era` signatures match the Unit 1 contract exactly.
