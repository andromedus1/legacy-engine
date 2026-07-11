---
id: epic-subarchetype-resolution-card-winrate
kind: feature
stage: drafting
tags: [analytics, honesty]
parent: epic-subarchetype-resolution
depends_on: [epic-subarchetype-resolution-discovery]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Archetype/variant-conditioned card win-rate

## Brief

Fix the cross-archetype contamination in per-card win-rate and make it variant-aware. Today
`compute_card_winrates` pools a card's results across every archetype that plays it — which made
Mishra's Bauble read as a −0.040 "cut" for Dimir Tempo while the within-archetype subgroup showed
Goyf+Bauble was the *best* cell (59.7%, n=159). This feature (1) restricts the W/L denominator to the
archetype's (or camp's) own decks, (2) emits an **honest-degrade sign-conflict warning** when a card's
marginal (cross-archetype) lift disagrees in sign with its within-archetype/within-camp win-rate, and
(3) surfaces the subgroup win% directly in `report subgroup` (it currently shows only copy-count
deltas — the W/L split that actually decides a keep/cut had to be computed by hand).

## Epic context

- Parent epic: `epic-subarchetype-resolution`
- Position in epic: **consumer of `-discovery`** — the variant-conditioned mode reads discovery's
  `decks.variant` labels. Parallel with `-matchup-cells` after discovery lands. The archetype-conditioned
  mode + sign-conflict warning are usable independently of variants (they only need the parent label),
  but variant-conditioning is the reason this sits under the epic.

## Inherited design decisions

From the parent epic's `## Design decisions` (fixed inputs — do not re-ask):
- **Default behavior: opt-in overlay.** The existing marginal `report cards` output stays the default;
  the archetype/variant-conditioned denominator and the sign-conflict warning are additive
  (gated-additive-augmentation — baseline path byte-identical).
- Honesty: the sign-conflict warning is a labeled honest-degrade marker, not a silent correction; both
  numbers (marginal + conditioned) are shown, the human decides.

## Research briefs

- `docs/briefs/subarchetype-discovery.md` §7 (Integration → Per-card win-rate) — restrict-denominator,
  sign-conflict honest-degrade warning, surface subgroup win% in `report subgroup`.
- Motivating case: the Dimir Tempo Bauble keep/cut contamination (see epic body).

## Foundation references

- `docs/ARCHITECTURE.md` — `analytics/match_results.py::compute_card_winrates` (per-card W/L; add an
  archetype/variant-scoped denominator), `analytics/card_value.py` / `report cards` (marginal lift +
  the new sign-conflict warning), `analytics/subgroup.py` / `report subgroup` (surface subgroup win%).

## Notes for /feature-design

- Shares the "read the resolved variant for a deck" helper with `-matchup-cells`; do not duplicate.
- The honest-degrade sign-conflict marker follows the project's honest-degrade pattern (named reason,
  both magnitudes shown). Add tests proving: (a) archetype-scoped denominator differs from marginal on
  the Bauble case; (b) sign-conflict warning fires when signs disagree; (c) baseline marginal output
  unchanged. Hermetic CLI tests pass `--db <tmp>`.
