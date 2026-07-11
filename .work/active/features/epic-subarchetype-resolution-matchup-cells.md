---
id: epic-subarchetype-resolution-matchup-cells
kind: feature
stage: implementing
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

## Design decisions

Resolved with judgment under autopilot:
- **Mechanism = opt-in label-split of ONE target archetype** (`split_variant: str | None` on
  `compute_match_results` / `build_matrix`; `report matchups --split-variant <ARCHETYPE>`). When set,
  any deck whose `archetype == split_variant` gets the effective label `"<arch> [<variant>]"`
  (from `decks.variant`; NULL → `"<arch> [unlabeled]"` — residue stays visible, per the epic).
  Everything downstream (marginals, cells, Beta-Binomial shrinkage, tiers, display gates) is reused
  UNCHANGED — camp rows simply replace the parent row in the flagged run.
- **Deviation from the brief's subject-side-only key, logged**: the brief's rationale (opponent camp
  unobservable) does not bind this corpus — rounds join both players' decklists, so the camp label is
  known on both sides. The label-split subsumes subject-side conditioning (its cells are a projection)
  and is strictly simpler: no new cell-key type, no parallel code path. Default (no flag) remains
  byte-identical (gated-additive-augmentation).
- **Row inclusion**: camp rows of the split archetype are force-included regardless of
  `min_row_share` (they are the point of the query); all other rows keep the normal floor. Honesty is
  carried by the per-cell tier labels, not by hiding rows.
- **Variant source**: `decks.variant` as persisted by the labeler (curated registry today; promoted
  discovery splits once `discover promote` + `label` re-run). No on-the-fly variant resolution here.
- **Shared helper for the sibling feature**: `effective_label(archetype, variant, split_variant)` —
  a tiny pure function in `match_results.py`; `-card-winrate` reuses it.

## Implementation Units

1. **`effective_label`** (pure, `analytics/match_results.py`):
   `def effective_label(archetype: str | None, variant: str | None, split_variant: str | None) -> str | None`
   — returns `archetype` unless `split_variant` matches, else `f"{archetype} [{variant or 'unlabeled'}]"`.
2. **`compute_match_results(..., split_variant: str | None = None)`**: `_JOIN_SQL` additionally
   selects `d1.variant, d2.variant`; both sides' labels pass through `effective_label` before
   tallying. `None` path byte-identical (SQL may select the extra columns unconditionally — Python
   ignores them when unsplit — provided the no-flag output objects are unchanged).
3. **`build_matrix(..., split_variant: str | None = None)`** and
   **`build_adaptive_matrix(..., split_variant=...)`** passthrough; row inclusion force-includes
   labels starting with `f"{split_variant} ["`. `valid_since`/affectedness lookups for camp labels
   fall back to the parent archetype's horizon (strip the ` [camp]` suffix).
4. **CLI**: `report matchups --split-variant <ARCHETYPE>` (+ head-to-head `--a/--b` accept camp
   labels); audit-echo `// split-variant: <arch> (camps from decks.variant; unlabeled residue shown)`.
5. **Tests** (hermetic, `--db <tmp>`): build a tmp DB with two labeled camps in one archetype +
   rounds; assert (a) no-flag output byte-identical to pre-change (golden), (b) flagged run shows camp
   rows with correct n/tier/shrinkage and the parent row absent, (c) unlabeled residue row appears,
   (d) force-include works below the floor, (e) adaptive fallback uses the parent horizon.

## Testing
Unit tests for `effective_label` (pure); hermetic CLI + builder tests per Unit 5. The byte-identical
golden check is the load-bearing test (gated-additive contract).

## Risks
- **Adaptive-matrix horizon for camp labels** — mitigated by the strip-suffix fallback (Unit 3);
  tested.
- **Sub-2% camp rows flooding the full matrix print** — only the split archetype is force-included;
  bounded by its own camp count.
