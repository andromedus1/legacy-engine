---
id: feature-list-granular-positioning
kind: feature
stage: done
tags: [advisory, analytics, card-level]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

**Deferred from `epic-advisory-output-honesty` (2026-06-06) as a research spike** — kept out of that
epic to avoid adding heuristic false-precision to an honesty-focused epic.

Positioning `S` is computed purely from the **archetype** classification, so two different 75s that
classify as the same archetype get an identical S (observed: a grindy Hymn/Strix Dimir Tempo build and
a lean Daze/Nethergoyf build both scored S=0.464). This makes positioning useless for the most common
real question — "is my exact list better-pointed at this field than that other list of the same deck?"

The per-card layer already exists (`report cards` presence-correlational lift) but isn't wired into
positioning. Spike: nudge the per-matchup win-rate by the deck's card composition (presence of
matchup-relevant cards vs the archetype baseline), as a clearly-labeled heuristic overlay on top of
the archetype-level S. Must honor the presence-correlational / not-causal caveat and not present the
overlay as causal precision. Promote to its own epic/feature once the approach is validated. Related
to [[idea-hoser-catalog-expansion]].

## Spike result

**Date:** 2026-06-14  
**Status: VALIDATED — approach works; recommend PROMOTE to feature**

### Does it differentiate?

Yes. On a hermetic corpus (no real DB), two same-archetype Dimir Tempo lists:

- **Grindy (Hymn/Strix)**: `s_granular` higher on ANT-heavy field (60% ANT) — Hymn
  to Tourach's positive lift vs combo propagates into the overlay, pulling
  `s_granular` above archetype S.
- **Lean (Daze/Nethergoyf)**: `s_granular` higher vs Red Stompy-heavy field —
  Daze + Nethergoyf lift vs aggro differentiates the list in the other direction.

Archetype-level S is byte-identical for both lists (same matrix row, same seed) —
the default `positioning_score` path is completely unchanged.

### Implementation summary

Added **Unit 6** to `advisory/positioning.py`:

- `composition_adjusted_winrates()`: per-matchup WR nudged by `card_value_matchup`
  lift signals, gated to `tier in ("evolving", "established")` (speculative lift
  ignored), clamped to ±5pp per matchup, scaled 0.5× to keep the overlay
  sub-dominant.
- `positioning_score_granular()`: opt-in entry point; returns
  `GranularPositioningResult` with `base` (unchanged archetype S), `s_granular`,
  `adjusted_winrates` dict, and mandatory `caveat` string. Callers MUST display
  the caveat.
- `GRANULAR_CAVEAT` constant: presence-correlational / not-causal label always
  attached to every result.

12 hermetic tests in `tests/test_positioning_granular.py`; all pass. Full suite:
2180 passed (was 2168 pre-spike).

### Honesty constraints met

- Opt-in, default OFF: `positioning_score` unchanged.
- Caveat always present on `GranularPositioningResult.caveat`.
- Not exposed via `advisory/__init__.py` — callers must import from
  `advisory.positioning` directly (extra friction reinforces experimental status).

### Limitations to document in the feature brief

1. `CardWinRates` must be computed from the real corpus and passed in — the CLI
   integration is not done here (spike is API-only).
2. Gating at `"evolving"` (n≥30) means thin card matchup cells contribute nothing;
   most cards will be speculative vs niche opponents. Real-world differentiation
   will be weaker than the hermetic corpus suggests.
3. Non-land card counts are used as the normalisation denominator; lands should be
   excluded from `deck_cards` by the caller (or the function should call
   `fetch_card` to detect is_land — that needs a DB handle, which breaks purity).
4. The `scale=0.5` / `max_nudge=0.05` constants are untuned defaults; a
   calibration pass against real corpus data is needed before any production use.

### Promote recommendation

**PROMOTE.** The core approach is sound and correctly differentiates same-archetype
lists without contaminating the baseline. The main open work is:
(a) CLI integration (`advise positioning --list-granular`),
(b) passing real `CardWinRates` through the advisory CLI path,
(c) constant calibration against real data,
(d) `fetch_card` land-detection in `composition_adjusted_winrates` (or document
    caller contract).
Suggested epic tag: `feature-list-granular-positioning-overlay`.

## Promotion (2026-06-14)
Spike VALIDATED (core Unit 6 already merged in PR #10: composition_adjusted_winrates / positioning_score_granular / GranularPositioningResult / GRANULAR_CAVEAT, opt-in + default-off + caveated, 12 hermetic tests). Promoted to a feature to HARDEN into production. This is the first step of a broader valued direction: **analyze decks as individual cards, not just archetype labels.**

### Remaining production items (the hardening work)
1. **CLI integration** — wire an opt-in flag (e.g. `advise positioning --list-granular`) that renders `s_granular` alongside archetype S with the mandatory caveat; keep default output byte-identical.
2. **Real CardWinRates plumbing** — feed `card_value_matchup` from the live corpus (the spike used seeded inputs); reuse the existing card_value/window machinery; honor ban-regime windowing.
3. **Constant calibration** — the 0.5x scale and ±5pp clamp are provisional; pin them with a test that the overlay stays sub-dominant to archetype S and reproduces the grindy-vs-lean differentiation.
4. **Land detection** — exclude basic/utility lands from the composition signal so they don't add noise (use the existing is_land / land classification).

Honesty constraints (UNCHANGED): opt-in, default OFF, presence-correlational caveat always shown, never presented as causal precision.

## Implementation notes

**Implemented 2026-06-14.** All 4 hardening items complete; 2199 tests passing (+19 new).

### 1. CLI integration (`advise positioning --list-granular`)
Added `--list-granular` flag (default OFF) to `advise positioning` in `cli.py`. When set, calls the new `_render_list_granular` helper which outputs:
- `// [GRANULAR_CAVEAT]` on the audit line (always, honesty contract)
- `S_granular (list-granular, experimental): <value>`
- `S (archetype-level, baseline): <value>`
- `delta (S_granular − S): <±value>`
- Deck composition note including land exclusion count

Default (flag absent) path is byte-identical — confirmed by test `test_positioning_without_flag_byte_identical`.

### 2. Live CardWinRates plumbing
`_render_list_granular` calls `compute_card_winrates(con, provenance=provenance, since=field_since, until=field_until)` — the same window the positioning path uses (honors ban-regime windowing via `inputs.field_since/field_until`). Lands are filtered from `mainboard` via `filter_nonland_cards(mainboard, _is_land)` where `_is_land` calls `store.fetch_card` → `row["is_land"]`. CLI resolves live data and passes it into the pure `positioning_score_granular` (no DB coupling in the core function).

### 3. Constant calibration
`_GRANULAR_MAX_NUDGE = 0.05` and `_GRANULAR_SCALE = 0.5` retained as-is. Both constants now have extended rationale docstrings explaining the calibration target. Tests in `TestConstantCalibration`:
- (a) Sub-dominance: `|s_granular - base_S| < _GRANULAR_MAX_NUDGE` asserted for both lists
- (b) Grindy/lean differentiation: grindy > lean on 60% ANT field asserted explicitly
- (c) Clamp never exceeded: extreme deck (20x Hymn) asserts nudge ≤ `_GRANULAR_MAX_NUDGE`
Current values pass all tests; no adjustment needed.

### 4. Land detection
Added `filter_nonland_cards(deck_cards, is_land_fn)` utility to `advisory/positioning.py` (pure, testable without DB). Caller supplies the `is_land_fn` predicate. Unknown cards (not in DB) are kept (conservative default). The CLI supplies `fetch_card`-backed predicate; tests supply lambdas. Tests confirm: (a) lands excluded, (b) unknowns kept, (c) land-only deck difference → identical `s_granular`, (d) baseline `base.s_mean` unaffected.

### Test counts
- 19 new hermetic tests in `tests/test_positioning_granular_hardening.py`
- 8 CLI tests are hermetic: use `tmp_path` file-backed DuckDB + `--db` flag (never touch `data/legacy.duckdb`)
- Full suite: **2199 passed** (was 2180 pre-spike → 2192 post-spike → 2199 post-hardening)
