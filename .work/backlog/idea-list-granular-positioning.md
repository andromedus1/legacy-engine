---
id: idea-list-granular-positioning
created: 2026-06-06
tags: [advisory, analytics, spike]
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
