---
id: fix-tuner-core-protection
kind: story
stage: review
tags: [generation, quality]
parent: null
depends_on: []
release_binding: null
gate_origin: tests
created: 2026-06-13
updated: 2026-06-13
---

# Tuner over-cuts high-inclusion core cards

## Finding (gate-tests, High)
`generation/tuning.py` field-tuner protects cards only via the ≥65%-inclusion lock in `partition_flex`.
A card that is the field MODE but sits below 65% inclusion (e.g. Nethergoyf at 3 copies, ~50-64%) is
classified flex and can be cut to 0 on ANY positive lift — there is no minimum-lift threshold and no
inclusion-weighted cut penalty. Test-drive: `advise refresh` cut all 3 Nethergoyf for Marsh Flats on
epsilon presence-correlational lift, then the same report's outlier check flagged the result as
off-consensus. Self-contradictory output.

## Fix
Decide + encode the intended policy: add a minimum-lift-to-cut gate (don't swap on sub-threshold lift)
and/or an inclusion-weighted penalty so high-mode cards resist cuts. Encode as a failing-then-passing
test: a mode-3 flex card at ~0.6 inclusion vs a pool card exceeding it by epsilon → tuner does NOT cut
the core card to 0. Supersedes part of idea-test-drive-findings #2.

## Implementation notes

### Policy chosen: dual gate (flat noise floor + inclusion-weighted cut resistance)

Both protections are applied together. A swap is only accepted when the gain exceeds:

    required_gain = max(_MIN_SWAP_GAIN, cut_inclusion_pct * _INCLUSION_CUT_RESISTANCE)

**Constants** (named, in `src/legacy_engine/generation/tuning.py`):
- `_MIN_SWAP_GAIN = 0.02` — flat noise floor; screens epsilon-level lift differences across all
  flex cards regardless of inclusion. Per-card field-weighted values are presence-correlational
  signals the codebase itself disclaims as "indicative not precise" — a 0.001 gain is noise.
- `_INCLUSION_CUT_RESISTANCE = 0.08` — per-unit-inclusion multiplier; a card at 60% archetype
  inclusion requires a gain ≥ max(0.02, 0.60 × 0.08) = 0.048 to be cut.

**Calibration rationale**: a gain of 0.02–0.05 is at the noise floor of field-share-weighted
presence-correlational lift. A real, clearly-better swap on an n≥30 evolving-tier corpus produces
gains well above 0.10 (Brainstorm vs Combo with 100% field share yields ~0.33 lift). The thresholds
block epsilon-driven gutting while leaving real edges entirely unblocked.

### Changes

**`src/legacy_engine/generation/tuning.py`**
- Added `_MIN_SWAP_GAIN` and `_INCLUSION_CUT_RESISTANCE` named module constants with detailed
  docstrings explaining the policy rationale.
- `_greedy_tune` gains `inclusion_pcts`, `min_swap_gain`, and `inclusion_cut_resistance` optional
  kwargs (all default-valued → backward-compatible; existing callers and tests unaffected).
- The gain check `if gain <= 0.0` is replaced with the dual-gate check.
- `tune_deck` calls `card_frequencies` once after `partition_flex` to build `_inclusion_pcts` dict,
  then threads it into `_greedy_tune`. This is a lightweight SQL query (same as partition_flex's
  internal call) — not the heavy winrates scan.

### Tests

**New (4 tests, all failing-then-passing)** in `tests/test_generation_tuning.py::TestGreedyTune`:
- `test_epsilon_gain_does_not_cut_high_inclusion_flex_card` — THE core-protection AC: flex card at
  0.60 inclusion vs pool card with gain=0.001 → swap is BLOCKED, card stays at 3 copies.
- `test_large_gain_still_cuts_high_inclusion_flex_card` — no-over-freeze guard: flex card at 0.60
  inclusion vs pool card with gain=0.25 → swap PROCEEDS (0.25 >> 0.048 required).
- `test_flat_noise_floor_blocks_epsilon_on_zero_inclusion_card` — the flat floor applies even to
  cards with 0% inclusion (user-injected cards); gain=0.001 < 0.02 → blocked.
- `test_inclusion_pcts_none_uses_flat_floor_only` — backward-compat path: `inclusion_pcts=None`,
  gain just above `_MIN_SWAP_GAIN` → swap proceeds.

**Existing tests**: No tests were updated. All 4 existing swap tests use gains well above the new
floor (0.4, 0.2, 0.5, 0.4) — they continue to pass without modification. The behavior they test
(large, clearly-real swaps) is exactly what the policy preserves.

**Suite**: 1869 passed (was 1865 + 4 new tests).
