---
id: epic-subarchetype-resolution-matchup-cells
kind: feature
stage: review
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

## Implementation notes

All 5 units landed as designed; no deviations from this document.

- **Unit 1** — `effective_label(archetype, variant, split_variant)` in `match_results.py`: identity
  unless `archetype == split_variant`, in which case `f"{archetype} [{variant or 'unlabeled'}]"`.
  Exported from `legacy_engine.analytics`.
- **Unit 2** — `compute_match_results(..., split_variant=None)`. `_JOIN_SQL` now selects
  `d1.variant`/`d2.variant` unconditionally (the shared `uniq_decks` CTE gained
  `ANY_VALUE(variant) AS variant`, used only by `_JOIN_SQL` — `_CARD_WINRATES_SQL`'s query is
  untouched by the extra CTE column). Both sides' labels pass through `effective_label` right after
  unpacking each row, before the bye/ambiguous/mirror/decisive branching — so mirror-detection,
  marginals, and directed cells all key on the post-split label. `split_variant=None` makes
  `effective_label` the identity, so every downstream value is unchanged.
- **Unit 3** — `build_matrix(..., split_variant=None)` and `build_adaptive_matrix(...,
  split_variant=None)` pass `split_variant` straight through to `compute_match_results`, and both
  add `_force_prefix = f"{split_variant} ["` to the row-inclusion predicate (`... or
  arch.startswith(_force_prefix)`) so camp rows bypass `min_row_share`. For the adaptive horizon, a
  new pure helper `_base_archetype(label, split_variant)` strips a matching camp label back to the
  parent archetype before calling `archetype_valid_since` (which only knows plain
  `decks.archetype` values), then the resulting `valid_since` is broadcast back to every camp of
  that parent. `split_variant=None` makes `_base_archetype` the identity, so `build_adaptive_matrix`'s
  no-flag path is byte-identical (verified: the `archetype_valid_since` call site now runs over
  `sorted({_base_archetype(a, None) for a in included})`, which reduces to `included` itself since
  it was already a sorted, deduplicated list).
- **Unit 4** — `report matchups --split-variant <ARCHETYPE>` (threaded through
  `advisory.window.build_advisory_inputs`, which every other `build_advisory_inputs` call site
  leaves at its new `split_variant=None` default). Prints `// split-variant: <arch> (camps from
  decks.variant; unlabeled residue shown)` once per invocation, right after the data-freshness
  echo, only when the flag is passed. `--a`/`--b` (head-to-head) needed no code change — camp
  labels are just archetype strings once they're in `matrix.archetypes`, and `lookup_head_to_head`
  already does a plain dict lookup.
- **Unit 5** — new test file `tests/test_matchup_split_variant.py` (24 tests, existing test files
  untouched). One shared single-tournament corpus (`_build_camp_corpus`, rounds repeated against 4
  deck rows — same technique as `test_matchup.py`'s `_LARGE` fixture) gives three Doomsday camps
  (Murktide n=32/evolving, Painter n=1/below the 2% floor, NULL-variant "unlabeled" n=3) vs a
  Control opponent, covering (a) the golden no-flag/byte-identical check — asserted both at the
  `build_matrix` level and at the CLI text level (no bracketed label or audit line leaks in without
  the flag, even though `decks.variant` is populated in the DB) — (b) parent-row-absent/camp-rows
  correct n+tier, (c) the unlabeled residue row, and (d) force-include below `min_row_share` (plus a
  negative case: an unrelated non-split fringe archetype pair stays excluded — force-include is
  scoped to the split archetype only). (e) reuses `test_adaptive_regime.py`'s Entomb-ban two-regime
  pattern with the Doomsday archetype relabeled to carry a variant, confirming the camp inherits the
  parent's `valid_since` and its windowed cell is a strict post-ban subset of the full-corpus cell.

No product bugs were found. Full suite: 2691 passed, 1 xfailed (pre-existing, unrelated) — no
regressions.
