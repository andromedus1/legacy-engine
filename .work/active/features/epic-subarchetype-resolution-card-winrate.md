---
id: epic-subarchetype-resolution-card-winrate
kind: feature
stage: implementing
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

## Design decisions

Resolved with judgment under autopilot:
- **Conditioning mechanism**: `compute_card_winrates(..., deck_archetype: str | None = None,
  deck_variant: str | None = None)` — the attribution loop is untouched; only the deck→cards map
  (query b) filters to decks matching the archetype (and camp when given). Default `None/None` is
  byte-identical (gated-additive).
- **CLI surface**: `report cards --archetype X --conditioned [--variant NAME]` — opt-in flag; the
  default `report cards` path is unchanged. Conditioned mode prints BOTH numbers per card
  (marginal + archetype-conditioned) and emits the honest-degrade line
  `// sign conflict: <card> marginal <±x> vs within-<X> <±y> — archetype-specific keep/cut calls
  must not use the marginal alone` whenever the two lifts disagree in sign. Both magnitudes always
  shown; nothing auto-corrected (divergence-as-diagnostic).
- **Sign-conflict helper**: pure `conflict_cards(marginal: list[CardValue], conditioned:
  list[CardValue]) -> list[tuple[str, float, float]]` in `analytics/card_value.py` — unit-testable
  without DB.
- **Subgroup win%**: `SubgroupSplit` gains optional fields (`wins_with/n_matches_with/
  wins_without/n_matches_without`, default `None`) + `subgroup_compositions(..., with_winrates:
  bool = False)`; `report subgroup` prints per-camp win% + match-n + tier when computed, with the
  thin-sample note. Default off → existing output byte-identical, existing tests untouched.
- **Variant source**: `decks.variant` (labeler-populated; display-label contract per
  fix-variant-resolution-display-key). Reuses the matchup-cells plumbing conventions; no new
  label rewriting needed here (deck-side filter, not cell relabeling).

## Implementation Units

1. `compute_card_winrates(..., deck_archetype=None, deck_variant=None)` — filter the deck-map query
   by archetype/variant (`analytics/match_results.py`). Byte-identical default.
2. `conflict_cards(...)` pure helper (`analytics/card_value.py`).
3. `report cards --conditioned [--variant]` + honest-degrade sign-conflict lines + audit-echo
   provenance (`cli.py`); `--conditioned` without `--archetype` → ClickException.
4. `subgroup_compositions(..., with_winrates=False)` + optional SubgroupSplit fields + per-camp
   win% in `report subgroup` output (`analytics/subgroup.py`, `cli.py`).
5. Tests (hermetic, `--db <tmp>`): (a) default `report cards` + `report subgroup` byte-identical
   goldens; (b) the Bauble-shaped scenario — a card in one strong + one weak archetype where the
   marginal lift is negative but the within-archetype lift is positive → conditioned mode shows
   both and the sign-conflict line fires; (c) `--variant` narrows the denominator; (d) subgroup
   win% correctness + thin note.

## Testing
Pure tests for `conflict_cards`; hermetic CLI/DB tests per Unit 5. Goldens are the load-bearing
gated-additive proof.

## Risks
- **Subgroup win% join cost** — bounded: restricted to one archetype's decks; reuses the
  cardinality-safe CTE pattern.
- **Camp-conditioned cells will often be speculative** — expected; tier labels + thin notes carry
  the honesty (surface-labeled, never hidden).
