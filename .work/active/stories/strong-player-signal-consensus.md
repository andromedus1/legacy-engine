---
id: strong-player-signal-consensus
kind: story
stage: review
tags: [generation]
parent: feature-strong-player-signal
depends_on: [strong-player-signal-identity, strong-player-signal-strength]
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

# Player-filtered consensus / tune — regime-safe, gated-additive

Wire the strong-player set into `generate consensus` / `generate tune` as an optional player filter.
See parent `feature-strong-player-signal` § Design (Decision 3).

**Hard-filter for v1** (weighting deferred): restricting the consensus deck pool to a player set is
the minimal auditable change — one extra predicate in the existing `deck_pool` CTE. **Gated-additive
pattern**: `players is None` → byte-identical to today. **Regime-safe**: the filter applies *on top
of* the existing window; default stays the latest ban-regime; thin strong+windowed pools
**degrade honestly with a banner**, never silently widen the window (honors
[[idea-ban-regime-everywhere]] — a strong player's prior-regime list is still stale).

## Units
- U1 — `consensus.card_frequencies(con, archetype, *, ..., players=None, alias_map=None)`: thread an
  optional player set into the `deck_pool` CTE (`AND lower(trim(d.player)) IN (resolved handles)`);
  `None` → no predicate → byte-identical SQL. Resolve `players` through `player_aliases` / `resolve_player`.
- U2 — `consensus.build_consensus` + `tuning.tune_deck` accept `players` / `alias_map`, pass through to
  `card_frequencies` / the consensus seed; thin-pool honest-degrade (low `sample_n` + speculative tier
  + banner; do NOT widen the window).
- U3 — CLI `generate consensus|tune` gain `--players "h1,h2"` and `--strong` (+ `--min-events/--min-tier/
  --min-win-rate`). `--strong` computes `strong_player_set` for the archetype+window. `--players` +
  `--strong` together → `--players` wins (log a note).

## Tests (additions to consensus/tuning test modules + a regime fixture)
- `build_consensus(..., players=None)` **byte-identical** to current output (the gated-additive invariant).
- `players={strong}` narrows the pool, changes modal counts on a hand-built corpus where a strong
  player runs a distinct flex card.
- Thin strong+windowed pool → low `sample_n` + speculative tier + banner; window NOT widened.
- Regime-safety: `--strong` default window == latest regime; a player's prior-regime list does not
  leak into the current-regime consensus (fixture: one player strong across two regimes, different lists).

## AC
- No `--players`/`--strong` → existing behaviour unchanged (byte-identical).
- Player filter composes with the existing window/provenance flags; default window stays latest regime.
- Thin pools degrade honestly; `--all-time` is the only window-widening escape, and only when explicit.

## Implementation notes

### Files changed
- `src/legacy_engine/generation/consensus.py` — added `_resolve_player_handles()` helper;
  threaded `players: set[str] | None` and `alias_map: dict | None` through `card_frequencies`
  and `build_consensus`.  Gated-additive: `players=None` path emits identical SQL to baseline
  (no predicate added).  Thin-pool honest-degrade: when `players` is set and `sample_n <
  _THIN_SAMPLE_FLOOR` (30), a `⚠ THIN PLAYER-FILTERED POOL` banner is appended to
  `legality_errors`; window is never widened.

- `src/legacy_engine/generation/tuning.py` — threaded `players`/`alias_map` through
  `partition_flex`, `candidate_pool`, and `tune_deck` (additive kwargs; all default `None`).

- `src/legacy_engine/cli.py` — added new `identify` group with three leaves:
  - `identify suggest` → `suggest_aliases` (heuristic, writes nothing)
  - `identify strong` → `compute_player_records` + `is_strong` tabular output
  - `identify track <player>` → `player_archetype_history` per-regime table
  Added `--players`, `--strong`, `--min-events`, `--min-tier`, `--min-win-rate` to
  `generate consensus` and `generate tune`.  When `--players` + `--strong` are both
  supplied, `--players` wins (explicit beats derived; logged).

### Test file created
- `tests/analytics/players/test_consensus_players.py` — 34 new tests across 6 classes:
  `TestGatedAdditiveInvariant`, `TestPlayerFilterNarrowsPool`, `TestThinPoolHonestDegrade`,
  `TestRegimeSafety`, `TestAliasResolutionInFilter`, `TestIdentifyCLI`.

### Deviations from spec
- None.  All three spec ACs satisfied.  Thin-pool banner goes into `legality_errors` (the
  existing audit-trail field on `GeneratedDeck`) rather than a separate field — keeps the
  data model minimal and the CLI rendering consistent.  The banner is clearly prefixed with
  `⚠ THIN PLAYER-FILTERED POOL` so callers can distinguish it from actual legality failures.

### Test count
- Before: 1458.  After: 1492.  All 1492 pass.
