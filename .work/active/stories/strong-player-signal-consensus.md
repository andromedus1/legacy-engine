---
id: strong-player-signal-consensus
kind: story
stage: implementing
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
