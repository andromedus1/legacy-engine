---
id: epic-subarchetype-resolution-matchup-cells
kind: feature
stage: drafting
tags: [analytics]
parent: epic-subarchetype-resolution
depends_on: [epic-subarchetype-resolution-discovery]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Variant-conditioned matchup cells

## Brief

Make the matchup matrix variant-aware. Today `analytics/match_results.py` keys on `decks.archetype`
only, so persisted `decks.variant` labels do not split any cell. This feature adds an **optional
variant dimension on the subject side** of a cell — `((archetype, variant), opponent_parent)` — so a
camp's matchups can be resolved separately from its parent's. The opponent stays at parent granularity
(opponent camps are rarely observable from tournament data).

The existing Beta-Binomial shrinkage and speculative(<30)/evolving(30–99)/established(≥100) tiers apply
per cell **unchanged** — splitting the subject shrinks each cell's n, so most split cells land
speculative/evolving and surface **at that tier with the honesty label**, never hidden and never
blended back into the parent. This is the same discipline already used for thin parent cells; no new
honesty machinery.

## Epic context

- Parent epic: `epic-subarchetype-resolution`
- Position in epic: **consumer of `-discovery`** — reads the `decks.variant` labels discovery produces
  (curated + promoted). Parallel with `-card-winrate` after discovery lands.

## Inherited design decisions

From the parent epic's `## Design decisions` (fixed inputs — do not re-ask):
- **Default behavior: opt-in overlay.** Parent-level output stays the default; variant conditioning is
  explicit via a flag (extend the existing `--variant` / `--by-variant` surface). Default `report
  matchups` output must be **byte-identical** to today (gated-additive-augmentation) — existing tests
  stay green untouched.
- Honesty: split cells surface at their own tier, labeled; never auto-split, never blend.

## Research briefs

- `docs/briefs/subarchetype-discovery.md` §7 (Integration → Matchup matrix) — the `(archetype, variant)
  × opponent` key, opponent-stays-parent rationale, and the tier-gate-preservation requirement.

## Foundation references

- `docs/ARCHITECTURE.md` — `analytics/match_results.py` (rounds→archetype join; add optional variant
  carry on the subject), `analytics/matchup.py` (`build_matrix` — add a `variant` subject filter),
  `report matchups` CLI (opt-in flag). Beta-Binomial shrinkage + tier gates are reused as-is.

## Notes for /feature-design

- This feature and `-card-winrate` share a "read the resolved variant for a deck" helper; whichever is
  designed first establishes it (coordinate so it is not duplicated).
- Follow gated-additive-augmentation: the no-flag path must be byte-identical to baseline. Add tests for
  the flag ON path (a known split, e.g. Doomsday Murktide/non-Murktide) proving per-camp cells + correct
  tier labels; hermetic CLI tests pass `--db <tmp>`.
