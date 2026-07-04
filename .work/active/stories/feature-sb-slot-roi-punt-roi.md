---
id: feature-sb-slot-roi-punt-roi
kind: story
stage: review
tags: [advisory]
parent: feature-sb-slot-roi-punt
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Slot-ROI table + punt detection + render

## Brief

Additive decision-support layer: per-matchup slot-ROI (`marginal equity gain × field share`),
punt detection (max realistic dedication still <50%, or better ROI elsewhere), rendered in
`advise sideboard`. Does NOT change which cards are picked — it advises slot allocation.

## Implementation

Covers parent feature **Units D1 + D2 + D3** — see `feature-sb-slot-roi-punt` § Implementation
Units for `MatchupROI`, `_slot_roi_table`, punt rules, render block, and acceptance criteria.
Files: `src/legacy_engine/advisory/sideboard.py` + `src/legacy_engine/cli.py`; tests in
`tests/test_sideboard.py` + a CLI render test with a tmp `--db`.

## Implementation notes (as-built)

**Files changed:**
- `src/legacy_engine/advisory/sideboard.py` — `MatchupROI` dataclass, `_matchup_max_equity_gain`,
  `_slot_roi_table` (D1+D2), `SideboardPackage.slot_roi` additive field, `recommend_sideboard`
  Step 4b wiring (D3 data side).
- `src/legacy_engine/cli.py` — `advise sideboard`'s `// slot-ROI (...)` render block (D3 CLI side).
- `tests/test_sideboard.py` — `TestMatchupMaxEquityGain`, `TestSlotROITable`,
  `TestMatchupROIDataclass`, `TestSlotROIRecommendSideboardIntegration` (22 new tests).
- `tests/test_cli.py` — `TestSlotROIPuntRender` (2 new tests, tmp `--db`).

**ROI/punt math (D1+D2):**
- `base_equity` = matchup cell `p_shrunk` vs the deck's own archetype, sourced via
  `lookup_head_to_head` on a freshly-built `build_adaptive_matrix(con)`. Honest-degrade: when
  the cell is absent OR its tier is `speculative` (n<30), `base_equity` is forced flat to `0.5`
  (not the beta-shrunk estimate, which can still read e.g. ~0.58 off a 3-0 record) —
  deliberately more conservative than the shrinkage prior alone, per the parent feature's
  explicit honesty requirement.
- `max_equity_gain` **reuses the coverage model's own concave shaping** rather than a fresh
  curve (the parent feature's #1 risk mitigation): for the opponent's best-covered
  `(archetype, tag)` element, `element_weight / field_share` recovers the per-copy equity swing
  the solver itself would realize (weight already bakes in the Unit B3 impact multiplier for
  that specific opponent). That per-copy value is then shaped across `_MAX_DEDICATED_SLOTS`
  (=4, matching `_U_REDUNDANCY_DEFAULT`'s length) copies using the SAME `_u_redundancy` curve
  Unit B4 uses for the solver's own per-card-copy diminishing returns — so a dedicated-swing
  hoser (0.20) and a soft one (0.10) don't get the same ceiling. Capped at
  `_MAX_REALISTIC_EQUITY_GAIN = 0.35` (mirrors `_EMPIRICAL_SWING_CAP`'s role elsewhere as a
  sanity bound) so a single strong signal can't imply an unrealistic swing.
- `roi_per_slot` = first-slot marginal gain (`_u_redundancy(1) == 1.0` always, so this equals
  the recovered per-copy equity) × `field_share` — the expected-match-win unit the table ranks
  by, descending.
- Punt (a): `not crosses_half` (`base_equity + max_equity_gain < 0.5`) → reason "max dedication
  still <50%".
- Punt (b), reallocation: only evaluated when (a) doesn't already fire. A matchup is flagged
  when its `roi_per_slot` falls below `_REALLOCATION_MARGIN` (0.5) of the best OTHER matchup's
  `roi_per_slot` **among matchups that themselves cross_half** (a genuinely investable
  alternative, not just a higher raw number) → reason "better ROI elsewhere".
- **Judgment call**: the spec's "beat the ROI of the next-best slot" phrasing, read literally,
  would flag every matchup except the single top-ranked one — not useful decision support (real
  boards legitimately hedge across several worthwhile matchups). I required a MEANINGFUL gap
  (half the best alternative's ROI) before recommending reallocation, and restricted the
  "alternative" set to matchups that themselves clear 50% (otherwise "the better ROI elsewhere"
  could itself be an equally-doomed matchup, which isn't a real alternative).
- **HARD RULE**: `confidence == "speculative"` short-circuits both (a) and (b) — `punt` stays
  `False` and `punt_reason` stays `""`. Verified this is load-bearing (not vacuous) with
  `test_never_punts_speculative_tier_despite_dwarfed_roi`, which constructs a speculative row
  whose `roi_per_slot` genuinely is dwarfed by a `crosses_half` alternative and confirms the
  guard, not a coincidental non-trigger, prevents the punt.
- **Judgment call**: added a `_MIN_FIELD_SHARE_FOR_ROI = 0.01` floor (mirroring the existing 1%
  noise-floor precedent in `recommend_sideboard`'s swing-override scan) after manually running
  `advise sideboard` against the real corpus (`data/legacy.duckdb`, Doomsday Tempo deck) during
  verification and finding the field has a long tail of ~300+ near-zero-share archetypes,
  producing an unusable 346-row block. With the floor, the same run renders ~26 meaningful rows
  and — as a real-world sanity check — correctly surfaces Dimir Tempo (established tier, no
  catalog coverage, 47%→47% equity) as a `[PUNT — max dedication still <50%]`, matching this
  project's own known-hard-matchup notes for that archetype.
- Mirror matches (`opponent == deck_archetype`) are excluded — no "hose yourself" question.

**Card selection unchanged (confirmed):** `slot_roi` is computed in `recommend_sideboard`
immediately after the coverage model is built (Step 4b) but strictly BEFORE the ILP/greedy
solve runs (Step 5) — architecturally it cannot feed back into `final_cards` since the solver
never reads it. `test_slot_roi_layer_does_not_change_card_selection` reinforces this with a
monkeypatched `_slot_roi_table` returning deliberately adversarial values (a fake punted,
negative-ROI row) and asserts `pkg.cards`/`covered_weight`/`solver_used` are byte-identical to
the un-monkeypatched run, while confirming `pkg.slot_roi` itself did change (so the comparison
isn't vacuous).

**Wiring:** `recommend_sideboard` gates the whole layer on `archetype is not None` (need a "my
side" to look up cells for) and wraps `build_adaptive_matrix(con)` + `_slot_roi_table(...)` in a
try/except, degrading to `slot_roi=()` on any failure — an honest "not computed", never a
fabricated table. Verified `build_adaptive_matrix` does not raise even on a fully rounds-less
in-memory corpus (returns `archetypes=[]`), so in practice every archetype-gated call gets a
(possibly all-speculative) table rather than an empty one; the empty-tuple path is exercised by
the CLI's monkeypatched "no slot-ROI block" render test instead of relying on a specific corpus
shape to genuinely gate it off.

**Render (D3, `advise sideboard`):** a `// slot-ROI (decision support — expected match-win per
dedicated slot):` block, one `// vs <opponent> (<share>%): <base>% → <ceiling>% equity
ROI/slot=<value> [confidence=<tier>]` line per row (ranked desc), with a trailing
`[PUNT — <reason>]` marker when punted. Confirmed via a real end-to-end run against
`data/legacy.duckdb`.

**Verification:** `.venv/bin/python -m pytest -q` → 2457 passed (2433 existing + 24 new: 22 in
`test_sideboard.py`, 2 in `test_cli.py`). No test gaming; no escape hatch needed — the parent
feature's spec mapped cleanly onto the existing coverage-model/matchup-matrix primitives.
