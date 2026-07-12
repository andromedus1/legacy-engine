---
id: epic-stable-era-windows-consumption-matrix
kind: story
stage: review
tags: [analytics, advisory]
parent: epic-stable-era-windows-consumption
depends_on: [epic-stable-era-windows-consumption-adapter]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Adaptive matrix horizon injection + window/audit swap

## Brief
Units 2+3: build_adaptive_matrix horizon injection with byte-identical empty-eras fallback; build_advisory_inputs field era + trigger-carrying _adaptive_audit + alarm lines.

## Implementation
Parent feature `epic-stable-era-windows-consumption` — exact contracts + acceptance criteria there.

### Implementation notes (2026-07-11)

**Unit 2 — `src/legacy_engine/analytics/matchup.py`:**

- `build_adaptive_matrix` gains `horizons: dict[str, str | None] | None = None`. When `None`
  (the new default), horizons resolve via `analytics.eras.consume.era_horizons` (era-aware,
  honest-degrading to the pre-epic `archetype_valid_since`-only computation for any entity with no
  `entity_eras` row). When supplied explicitly, `horizons` is used verbatim as `valid_since`,
  bypassing `era_horizons` entirely — this is the hook the byte-identical-fallback test uses to
  pin the exact pre-epic behavior.
- `AdaptiveMatrix` gains two new fields, both defaulted so existing direct-construction call
  sites (`tests/test_sideboard.py`'s `AdaptiveMatrix(matrix=..., valid_since={}, cell_windows={})`)
  stay valid untouched: `horizon_meta: dict[str, EraHorizon] = {}` (the full per-entity
  source/trigger/alarm metadata) and `audit_preamble: tuple[str, ...] = ()` (the whole-path
  no-era-data degrade line, when `era_horizons` detected it).
- `valid_since`/`cell_windows` computation is otherwise UNCHANGED — same `max(a, b)` cell-window
  assembly, same one-scan-per-distinct-horizon cost model.

**Unit 3 — `src/legacy_engine/advisory/window.py`:**

- `_adaptive_audit` now takes `(horizon_meta, audit_preamble=())` instead of `valid_since`.
  Format: entities with a detected disturbance (`source in {"era","era-parent"}` and `since is
  not None`) are named individually with their trigger in parens (e.g. `"Doomsday since
  2026-04-20 (release: Flow State adoption)"`); `ban-only`-sourced entities are counted, not
  named (`"N entities ban-only"`); the line always ends `"; all others full-corpus"`. One `// ⚠`
  line per alarm-flagged entity is appended after — alarms never truncate the summary, only add
  lines. `audit_preamble` (the whole-path no-era-data line) is prepended verbatim when present.
- `build_advisory_inputs`'s adaptive branch now sources the field window from
  `analytics.eras.consume.resolve_field_era` (replacing the old `resolve_regime("current")`
  call) and appends one `"// field: since <date> (<label>)"` audit line. `field_until` stays
  `None` (the current-regime bookend is always open-ended, matching the pre-epic behavior).

### Tests

- `tests/test_adaptive_regime.py::TestEraAwareDefaultFallback` (3 new): the byte-identical
  fallback proof — `build_adaptive_matrix(horizons=archetype_valid_since(...))` (old path,
  explicit) vs `build_adaptive_matrix()` (new default path, on a connection with NO
  `entity_eras` table) produce identical `valid_since`, `cell_windows`, `matrix.cells`,
  `matrix.archetypes`, `matrix.total_matches`; plus explicit-horizons bypass and a seeded-era
  resolution test proving the default path genuinely reads the store.
- `tests/test_advisory_window.py::TestAdaptiveAudit` (5 new) + `TestBuildAdvisoryInputsFieldEra`
  (2 new): audit format (no-disturbance / named-with-trigger / ban-only-counted /
  alarm-appends-without-truncating / preamble-prepended-verbatim), and `build_advisory_inputs`
  wiring `resolve_field_era` in adaptive mode while leaving uniform mode's field window
  unchanged (shares `win.since`/`win.until`, empty audit).

### Verification

- `.venv/bin/python -m pytest -q tests/test_adaptive_regime.py tests/test_advisory_window.py
  tests/test_matchup.py tests/test_matchup_split_variant.py tests/test_sideboard.py` → all green
  (67 tests across the touched files).
- Full suite (`.venv/bin/python -m pytest -q`) → 2905 passed, 1 xfailed (baseline 2881 + 14 Unit 1
  tests + 10 Unit 2/3 tests).
- `ruff check` on `matchup.py`, `window.py`, and both touched test files → clean.
- Golden re-pin check (Unit 5 preview): `tests/test_conditioned_card_winrate.py` and
  `tests/test_matchup_split_variant.py` (the only two `GOLDEN`-pinned files in the suite) both
  invoke their pinned commands with `--all-time` or an explicit `--since`, so neither ever
  reaches the adaptive branch this story touches — both passed UNCHANGED, byte-for-byte, no
  re-pin needed. Confirmed by inspection of both golden tests' CLI invocations, not just by the
  full suite staying green.

### Deviations from the parent doc

- `_adaptive_audit`'s ban-only wording groups ban-only entities into a count
  (`"N entities ban-only"`) rather than naming each one's date — matches the parent doc's own
  example line ("... ; 3 entities ban-only; all others full-corpus") exactly.
- `resolve_field_era` is NOT passed `provenance` from the `_load_field`/matrix provenance basis
  in a per-basis way beyond a single pass-through — see `consume.py`'s own docstring note: the
  field-era boundary is treated as a single global gate, not per-provenance-basis, per the epic's
  "One global window (analysis-gates convention)" design decision.
