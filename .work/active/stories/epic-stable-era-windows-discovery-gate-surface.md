---
id: epic-stable-era-windows-discovery-gate-surface
kind: story
stage: review
tags: [analytics, archetype]
parent: epic-stable-era-windows-discovery-gate
depends_on: [epic-stable-era-windows-discovery-gate-core]
release_binding: null
gate_origin: null
created: 2026-07-12
updated: 2026-07-12
---

# Era-default discovery window + report/staging surfacing

## Brief
Unit 2: discover run defaults to the parent's era window (--all-pool escape), camp lines carry median date/%current/Gate C warning, staged records persist the fields additively.

## Implementation
Parent feature `epic-stable-era-windows-discovery-gate` — exact contracts + acceptance criteria there.

## Implementation notes

**`src/legacy_engine/cli.py` — `discover run`**
- New `--all-pool` flag (default off). Window resolution precedence, inside the existing
  `con`/`try`/`finally` block (moved up so `entity_era_window` can query `entity_eras` before
  `discover_subarchetypes` runs):
  1. explicit `--since` wins outright (even over a simultaneous `--all-pool`) — no dedicated
     echo beyond the existing `// window: ...` report line.
  2. `--all-pool` -> `effective_since = None` (full corpus) + `// pool window: full corpus
     (--all-pool)`.
  3. neither given -> `entity_era_window(con, archetype)` supplies `effective_since` +
     `// pool window: since <date or 'full corpus'> (<label>)` (byte-identical ban-regime
     fallback when the archetype has no `entity_eras` row, per `entity_era_window`'s own
     contract).
- `effective_since` threads everywhere `since` used to: the `discover_subarchetypes` query, the
  new `current_since` kwarg (pct_current's reference date — the era window's own since, by
  design, even under `--all-pool`), the report's `// window:` line, and the staged record's
  `params["since"]`.
- **Behavior change, intentional**: `discover run`'s default pool is no longer the full corpus.
  Existing hermetic CLI tests whose fixtures predate the live ban regime now need `--all-pool`
  to keep testing full-pool discovery mechanics (the era-default window logic gets its own
  dedicated tests instead) — updated per-call in `test_discover_cli.py`, documented in the
  module's opening docstring.
- `_print_discovery_report` camp lines gain a trailing `_format_camp_temporal` fragment:
  `  median <YYYY-MM-DD> · <NN>% current`, omitting `% current` when `pct_current` is `None`
  and omitting the whole fragment when `median_date` is `None`. A `// ⚠ temporal mixing:
  <temporal_note>` line prints right after the camp lines when `split.temporal_mixing`.
  `discover list` renders the identical fragments + warning per staged split/camp.

**`src/legacy_engine/models/variant.py`**
- `DiscoveredCamp` gains `median_date: str | None = None`, `pct_current: float | None = None`.
  `DiscoveredSplitRecord` gains `temporal_mixing: bool = False`, `temporal_note: str | None =
  None`. All four additive with defaults; `extra="ignore"` + defaults together mean an OLD
  staged JSON record (missing these keys entirely) loads unchanged — verified directly with a
  hand-written old-shape record in `test_discover_cli.py`.

**`src/legacy_engine/archetype/discovered.py`**
- `record_from_split` copies `camp.median_date`/`camp.pct_current` per camp and
  `split.temporal_mixing`/`split.temporal_note` onto the record — no other staging/promotion
  logic touched (`promote_split`/`apply_split` are unaware of Gate C fields, by design; Gate C
  is a discovery-time diagnostic, not a promotion gate).

**Tests**
- `tests/test_discover_cli.py`: `TestDiscoverRunEraDefault` (4) — no-era-data ban-regime
  fallback excludes a stale fixture and reports FAIL honestly; `--all-pool` restores the full
  pool and stages; explicit `--since` overrides both the era-default and a simultaneous
  `--all-pool`; a seeded `entity_eras` `stable_since` row is honored and echoed. Plus 10
  existing `discover run` invocations updated to pass `--all-pool` (documented in the module
  docstring) so they keep testing pipeline mechanics rather than the (now era-aware) default.
- `TestDiscoverGateCSurfacing` (4) — a two-generation fixture (`_build_two_generation_db`,
  same calibration shape as Unit 1's analytics fixture) surfaces the warning line + per-camp
  `median <date>` in both `discover run` and `discover list`; the staged JSON persists
  `temporal_mixing`/`temporal_note`/`median_date` on disk; a hand-written pre-epic-shape staged
  record still loads and lists with no Gate C fields rendered (no crash, nothing fabricated).
- `tests/archetype/test_discovered.py`: 2 new `TestRecordFromSplit` cases — Gate C fields carry
  through `record_from_split`, and the pre-epic call shape (no Gate C fields on the analytics
  `DiscoveredSplit`/`Camp`) still produces a valid record with the new fields defaulting to
  `None`/`False`.

**Full suite**: `2928 passed, 1 xfailed` (prior baseline after Unit 1 was `2918 passed, 1
xfailed`; the 10 new tests above account for the delta exactly).

**Ruff**: `ruff check` on `models/variant.py`, `archetype/discovered.py`, and both test files is
clean. `cli.py` shows 17 pre-existing `F821` findings (forward-referenced string type
annotations ruff can't resolve, e.g. `"DiscoveredSplit"`) — confirmed byte-identical in count
before/after this story's diff (only line numbers shift); not introduced by this change, not
fixed by it either (out of scope).

**Deviations**: none from the parent feature's Unit 2 contract.
