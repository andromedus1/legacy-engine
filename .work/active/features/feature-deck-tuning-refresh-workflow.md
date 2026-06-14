---
id: feature-deck-tuning-refresh-workflow
kind: feature
stage: done
tags: [advisory, generation, workflow]
parent: null
depends_on: [feature-regime-windowing-consistency, feature-three-venue-meta-frame, feature-archetype-empirical-recommendations, feature-card-count-outlier-advisor]
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

Build a **deck-tuning refresh workflow**: one command/run that pulls current data and emits a
ready-to-play tuning package for attacking the current meta. For a given archetype it should produce:

1. **Recommended maindeck** (field-tuned, current-regime-aware).
2. **Recommended sideboard** (15, field-tuned).
3. **A concise plain-speak primer** explaining how the sideboard attacks each meaningful opponent —
   in readable prose, not a stat dump — **including the exact OUT/IN swaps** for each matchup.

Crucially, produce this main+sideboard+primer **for each meaningful split of the data.** Today the
splits we've identified are **online vs paper**; the future target is **online / paper / local
(Boulder, CO) / big tournament**. The workflow should iterate the same recipe per split and label
each output by venue.

Constraints / context (from the 2026-06-13 dogfood session that motivated this):
- Must be **ban-regime-correct** by default (current regime field + adaptive matchup windows) — see
  [[idea-ban-regime-everywhere]]. Loudly state the window + thinness.
- The per-split fields are exactly the three-venue frame in [[idea-three-venue-meta-frame]]; local
  and big-tournament splits depend on `epic-local-meta-support` geo + event-tier dimensions, so the
  workflow ships online/paper first and expands as those land.
- The plain-speak primer is the new deliverable beyond what exists: `advise sideboard` already emits
  OUT/IN plans, but they're terse, presence-correlational, and per-card-noisy in thin regimes. This
  wants a synthesized, human-readable "here's how you beat X, and here's what comes in/out" writeup.
- Manual workflow done by hand this session: build per-venue `--field` files from `report meta`,
  run `advise`/`generate tune`/`advise sideboard` per field, then map recommendations to the
  player's actual collection and write the primer. Automating + collection-awareness is the ask.
- Could be a natural first consumer of the [[idea-web-interface]] surface (per-venue tuning pages).

## Design

### CLI Command: `advise refresh`

Placed in the `advise` group (not `generate`) because the primary output is advisory prose —
the primer — not a raw deck list. `generate tune` remains the list-generation primitive;
`advise refresh` orchestrates it + renders a ready-to-read package. Consistent with `advise report`,
`advise sideboard`, `advise whattoplay` in the same group.

Usage:
```
legacy-engine advise refresh --deck shell.txt --archetype "Dimir Tempo"
legacy-engine advise refresh --deck shell.txt --venues online,paper
```

Inherits `--since/--until/--regime/--all-time` window opts. Default: adaptive per-opponent
ban-aware (same as `generate tune`).

### Orchestration (`advisory/refresh.py`)

**Per-venue loop** over `DEFAULT_VENUES` (online + paper), extensible to local/regional when
`epic-local-meta-support` lands:

1. `build_global_field(con, provenance=venue.provenance)` — each venue gets its own meta-share
   distribution. Empty-corpus venues are marked `data_absent=True` (kept, not silently dropped —
   absence is information per the three-venue-frame honesty contract).
2. `tune_deck(con, archetype, maindeck, sideboard_in, field=field, ...)` — reuses the full
   tuning pipeline: greedy per-card-value maindeck tuning + `recommend_sideboard` for the 15 +
   `matchup_plans` OUT/IN data. Adaptive windows active by default.
3. `build_deck_doctor_report` (per board) for card-count-outlier deltas — surfaced as annotations
   on the package header, not blocking.
4. `generate_primer(...)` — pure assembly of the human-readable primer from `matchup_plans`.
5. Returns `RefreshResult` with one `VenueTuningPackage` per venue.

### Package Assembly (`VenueTuningPackage`)

Each package carries:
- `maindeck` (60): the tuned deck from `tune_deck.maindeck`
- `sideboard` (≤15): `tune_deck.sideboard`
- `primer`: `SideboardPrimer` from `generate_primer`
- `tuned_deck`: raw `TunedDeck` (swaps, value delta, positioning_s, fell_back flag, etc.)
- `outlier_deltas`: `CardCountDelta` list (is_outlier=True only)
- `window_label`: echoes the adaptive/regime window for transparency

### Plain-Speak Primer (`advisory/primer.py`)

**Pure function** (`generate_primer`) — objective-search-split: heavy DB work is done upstream
(matchup_plans from tune_deck); primer generator only does text assembly.

Takes: archetype, sideboard, matchup_plans, venue_label, window_label, optional field_shares.
Returns: `SideboardPrimer` with one `MatchupBlurb` per opponent.

**Blurb tiers** (honesty contract):
- `degraded=True` or `n_basis=0`: labeled `"reasoning-based"` — explicit "no per-card data
  cleared the confidence gate; this guidance is reasoning-based, not data-derived." Sideboard
  composition is described structurally (graveyard hate, combo hate, etc.) without fake numbers.
- `tier="speculative"` (n < 30): labeled `"speculative"` — data present but thin; swap details
  withheld as unreliable; player told to rely on 15 composition.
- `tier in ("evolving", "established")` with swaps: labeled with tier — describes WHY cards
  come out ("below-baseline performance in this matchup") and WHY they come in ("positive lift"),
  with the presence-correlational disclaimer. ALWAYS includes exact OUT and IN.
- Gate cleared but no swaps: honest note that the maindeck is already well-configured for this
  opponent; no swaps surfaced.

**Ordering**: blurbs ordered by `field_shares` desc (most relevant opponent first), tie-break alpha.

**Global disclaimer**: every primer carries the presence-correlational disclaimer verbatim.

### Gated-Additive Compliance

- Empty matchup_plans → primer assembles with a "no per-matchup data" fallback message.
- No-signal fallback (thin corpus, `fell_back=True`) → `tune_deck` returns consensus maindeck
  unchanged; primer has no data blurbs; package is still valid and labeled.
- Empty venue corpus → `data_absent=True`, package renders "(no data for this venue)".
- Existing tests are byte-identical (no existing function signatures changed).

## Implementation notes

**Files created:**
- `src/legacy_engine/advisory/primer.py` — pure primer generator (289 lines)
- `src/legacy_engine/advisory/refresh.py` — orchestration + rendering (310 lines)

**Files modified:**
- `src/legacy_engine/cli.py` — added `advise refresh` command (~110 lines appended before `identify` group)

**Tests created:**
- `tests/test_refresh_workflow.py` — 17 tests (all new)

**Test counts:** 1548 total (was 1531; +17 new, 0 changed).

**Key deviations / notes:**
- `build_deck_doctor_report` takes `(con, user_main, user_side, archetype, ...)` positional
  ordering (con first, maindeck second, sideboard third) — this is the actual signature per the
  implementation; the refresh orchestrator calls it twice (once per board) as designed.
- The integration tests in `TestRunRefresh` use an in-memory corpus without a `cards` table,
  so the 60-card legality invariant is only tested on the `fell_back=True` path (maindeck unchanged).
  A real-corpus integration test would require seeded card data; the pure-function primer tests
  provide the bulk of coverage.
- Collection-aware filtering is OUT OF SCOPE per the feature spec (the collection-aware feature
  is held). The non-collection version ships here.
- Ruff auto-fixed 4 unused-import warnings in `primer.py` and `refresh.py` post-implementation.
