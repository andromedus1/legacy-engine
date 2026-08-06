---
id: epic-stable-era-windows-detection-detectors
kind: story
stage: done
tags: [analytics, methodology]
parent: epic-stable-era-windows-detection
depends_on: [epic-stable-era-windows-detection-series]
release_binding: v0.4.0
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Signal detectors S1-S4 (analytics/eras/detect.py)

## Brief
Presence cliff/ramp rules (exact two-proportion tests, trigger card named), composition CPD
(ruptures PELT/KernelCPD cosine + segment-permutation p-values), share-shift detection, win-rate
corroboration. Closed-vocabulary signal enum, deterministic given seed. Trickiest unit — the S2
permutation significance scheme; build it first against the frozen ground-truth fixtures.

## Implementation
Parent feature `epic-stable-era-windows-detection` — Unit 3 (exact signatures + acceptance
criteria there).

## Implementation notes

Built `src/legacy_engine/analytics/eras/detect.py` exactly per the Unit 3 contract: `SIGNAL_TYPES`,
`CandidateBoundary` (closed-vocabulary `__post_init__` fail-fast), `detect_presence`,
`detect_composition`, `detect_share`, `corroborate_winrate`.

**Pinned operating-point constants** (module-level, each with an inline calibration comment):
- `_PELT_PEN = 0.5` (S2, `KernelCPD(kernel="cosine", min_size=3)`) — calibrated against
  `stable_nonevent_series` (silent at every pen down to 0.001; exact period-5 wobble gives the
  cosine cost no sustained variance to split on) and `composition_rebalance_series` (the true
  bucket-18 rebalance survives at pen <= ~1.0, cost gain ~0.88 at the break, and is missed
  entirely at pen >= 2.0). 0.5 sits mid-window with margin both directions.
- `_SHARE_PEN = 0.003` and `_SHARE_MIN_SIZE = 2` (S3, `Pelt(model="l2")`) — calibrated against
  `tron_cliff_series` (fires in the ~[0.001, 0.005] pen window, recovering the 2026-06-15
  boundary) and `stable_nonevent_series` (silent at every pen tested down to 0.0005).

**Sanctioned deviation**: the epic's Unit 3 notes specify `min_size=3` for the S3 PELT call. The
Tron/Candelabra ground-truth fixture falsifies that at the corpus's own recency edge — the ban
cliff (59->20 decks/week) lands in the second-to-last COMPLETE bucket (one bucket before the
necessarily-incomplete trailing week), and `min_size=3` forbids any breakpoint whose right-hand
segment has fewer than 3 points. Verified empirically: with `min_size=3` PELT instead locates the
unrelated release-ramp breakpoint five buckets earlier, missing the epic's own headline
Candelabra validation case by two buckets (outside the ±1-bucket tolerance) at every penalty
tested. Relaxed to `min_size=2` — the minimal change that still floors out singleton-bucket
noise while admitting a real two-bucket-old tail disturbance; other floors (S2's 10-deck bucket
floor, S4's 30-match floor, the ensemble's 30-deck era floor) still guard statistical validity, so
this relaxation isn't carrying the floor alone. Documented in-line in `detect.py` at
`_SHARE_MIN_SIZE`'s definition.

**Tests**: `tests/analytics/eras/test_detect.py` (21 tests) + the frozen fixtures in
`tests/analytics/eras/conftest.py` (Flow State ×3 archetypes, Tron/Candelabra, stable non-event,
composition rebalance, null-candidate generator, stationary-fleet generator for the ensemble
story). All fixtures are literal/deterministic — no DB, no unseeded RNG. Covers: Flow State
adoption on all three archetypes (±1 bucket, trigger card named), Tron share cliff detected while
presence stays silent on Candelabra (its fraction never drops), stable non-event silence across
all three structural detectors, composition-rebalance detection with S1 silence, closed-vocabulary
fail-fast (unknown + all-known signals), determinism (same seed -> identical; different seed ->
same detections, only p-values may drift), the 8-complete-bucket short-series floor, and win-rate
corroboration (both the fires-when-floor-clears and floor-blocks-corroboration cases).

`ruff check src/legacy_engine/analytics/eras/detect.py tests/analytics/eras/` — clean.
