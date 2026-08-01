---
id: story-cleanup-nits-batch
kind: story
stage: done
tags: [analytics, cleanup]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-08-01
---

# Cleanup-nits batch — four small low-risk polish items

## Brief

Batch of four independently-verified small findings, drained in one story: (1) discovery
deep-review nits (incl. `_bootstrap_stability` diagonal in the pair mask — fix is
`np.fill_diagonal(pair_mask, False)` + re-check threshold); (2) docstring historical-prose
nit in advisory/sideboard.py (rolling-foundation: present behavior only); (3) gate-cruft
v0.3.0 Low note (belt-and-braces except around documented never-raises `backtest_board` in
advisory/sweep.py:326); (4) gate-tests v0.2.0 three Low coverage gaps. Full member texts
below. NOTE: item (1) changes emitted numbers slightly (bias fix) — not tagged [refactor].

## Member findings (absorbed from backlog)

---

### idea-discovery-review-nits


Three MINOR notes from the deep review of the discovery engine (PR #36, APPROVE) — polish, not
defects:
1. `_bootstrap_stability` pair mask includes the matrix diagonal (self-pairs always agree) →
   slight uniform upward bias; exact fix `np.fill_diagonal(pair_mask, False)` + re-check the
   0.90 threshold still passes the Doomsday ground truth.
2. Stability excludes pairs that dissolve to noise under resampling (spec-conformant, but heavy
   noise-dissolution isn't penalized — consider a reported noise-dissolution-rate diagnostic).
3. Report vs staged record order signature cards differently in rare negative-Δ-in-top-5 cases
   (cli.py slices then filters; discovered.py filters then caps) — unify.

---

### idea-docstring-historical-prose-nit


# Docstring "removed by feature-X" historical prose (rolling-foundation nit)

gate-cruft v0.2.0, Low confidence. `src/legacy_engine/advisory/sideboard.py:1646`: the
element-weights docstring says "draw-prob deflation removed by feature-sfv-weights" — historical
prose + internal feature slug in code. Reword to present behavior only (draw_prob intentionally
excluded via `score_without_draw_prob()`); git is the audit trail. Optional/low priority.

---

### gate-cruft-low-v030


Low-confidence cruft note from the v0.3.0 gate (awareness, keep-leaning): advisory/sweep.py:326
wraps `backtest_board` (documented never-raises) in a belt-and-braces except that converts a
hypothetical failure into per-entry skipped_reason + warning. Textbook "except around can't-throw"
shape, BUT consistent with the honest-degrade batch posture (one archetype must not abort the
sweep). Recommendation: keep; revisit only if the never-raises contract is ever formalized.

---

### gate-tests-low-findings-v020


# gate-tests v0.2.0 — three Low findings (complementary coverage)

1. **Identical-configs CI-overlap half untested** (`epic-sb-config-evaluation-config-comparator`
   Unit 2 AC): extend `test_identical_configs_p_half` to assert `ev_a_base_ci`/`ev_b_base_ci`
   overlap (identical under shared draws). `tests/advisory/test_compare.py::TestMonteCarlo`.
2. **"Byte-identical when off" gating contracts asserted via single sentinels** (`gating` +
   `hedge-allocator`): compare the full SideboardPackage (off) against a captured baseline instead
   of `natural_budget_count is None` / `insurance_cards == frozenset()`. Mitigation: the whole
   pre-existing suite runs the off path — real gated-additive evidence — hence Low.
3. **Stale `graveyard-reliant` synthetic fixtures** in test_collection_aware_engine.py (4),
   test_generation_tuning.py (5), test_interaction_facts.py prose — vacuous w.r.t. the vocab
   migration; rename the synthetic labels (cheap hygiene, no new tests).

## Implementation notes

**Item 1 — `_bootstrap_stability` diagonal bug** (`analytics/discovery.py:528`, right after
`pair_mask = mask[:, None] & mask[None, :]`): applied the exact fix,
`np.fill_diagonal(pair_mask, False)`. Self-pairs (`i == j`) always "agree" (a label always
equals itself in both the base and bootstrap labeling), so including the diagonal biases
the mean upward by exactly `(1 - true_off_diagonal_agreement) / n` per resample — verified
arithmetically with a standalone 10-point hand-built example (5/5 split, one point flipped
in the resampled run): WITH diagonal → 0.820000, WITHOUT → 0.800000 (Δ = +0.02, matches the
closed-form `(1-p)/n = 0.2/10 = 0.02` exactly).

Re-measured the shipped ground-truth fixtures BEFORE and AFTER the fix:
- `tests/analytics/test_discovery.py::_two_camp_decks()` (n=70, seed=0, n_boot=30):
  **before = 1.0, after = 1.0** (unchanged).
- `TestDiscoverSubarchetypesDB::test_discover_subarchetypes_finds_the_split` — the Doomsday
  ground truth (35/35 synthetic split via the hermetic in-memory DB, seed=0, n_boot=20):
  **before = 1.0, after = 1.0** (unchanged), `split.passed` stays `True`, still clears the
  0.90 gate with room to spare.

No regression: these fixtures are perfectly separable (every bootstrap resample recovers
the identical 2-cluster partition), so their true off-diagonal agreement was already 1.0 —
there was nothing for the diagonal to inflate. The bug's effect is real but only shows up
when the underlying split is imperfectly stable (off-diagonal agreement < 1.0); confirmed
this is a real, non-vacuous code change via the standalone arithmetic example above, not
via the (unaffected) shipped fixtures. Full `tests/analytics/test_discovery.py` suite
(67 passed, 1 skipped) stays green.

**Item 2 — docstring historical prose** (`advisory/sideboard.py`, `_build_coverage_model`'s
"Impact-modulated element weights" section, found at line ~1827 on current main — the story
cited line 1646 from an older revision): reworded "removed by feature-sfv-weights" /
"the exact bug feature-sfv-weights fixes" framing to present-tense — `draw_prob` is
described as *intentionally excluded* via `score_without_draw_prob()` (to avoid
double-counting the draw dimension, which is exclusively Unit B4's per-copy taper job),
not narrated as a fix to a past bug. No behavior change (docstring only).

**Item 3 — sweep.py belt-and-braces except**: re-verified on current main.
`backtest_board`'s docstring claims "Honest-degrade: never raises," but its body (lines
402/414/415: `_qualifying_top_finisher_decks`, `_observed_sideboard_frequency`,
`_observed_copy_distribution`) is NOT wrapped in try/except — only the internal
`recommend_sideboard` call is (lines 419-434). So the "never raises" contract is
documented intent, not a mechanically-enforced guarantee for every code path; a genuine DB
read failure in one of those three unwrapped helpers WOULD propagate up through
`backtest_board`. `run_sweep`'s except around `backtest_board` (sweep.py:428) is therefore
not pure superstition-over-can't-throw — it is real defense for a real (if narrow) failure
mode, and matches the honest-degrade batch posture (one archetype's DB hiccup must not
abort the whole sweep). **Decision: KEEP, unchanged.** No code touched for this item.

**Item 4 — gate-tests coverage gaps**:
- (a) `tests/advisory/test_compare.py::TestMonteCarlo::test_identical_configs_p_half`:
  added `assert r.ev_a_base_ci == r.ev_b_base_ci`. Since both configs share the archetype
  "TempoA", `_mc_base`'s `row_cache` reuses ONE draw array for both, so the base CIs are not
  merely overlapping but element-wise identical — verified the CI is non-degenerate
  (`(0.478, 0.521)`, width ≈4.3%, not a trivial constant) before asserting equality, so the
  new assertion is a real check, not a vacuous tautology.
- (b) Strengthened two single-sentinel "byte-identical when off" assertions to full
  `SideboardPackage` equality against a captured baseline (the pre-feature call with the
  kwarg omitted entirely, not just set to its default value):
  `TestGating.test_smart_off_is_baseline` (`tests/test_sideboard.py`) now asserts
  `pkg == baseline` (baseline = `self._pkg()`, no `smart` kwarg) in addition to the original
  `natural_budget_count is None`; `TestHedgeAllocator.test_recommend_sideboard_hedge_off_no_insurance`
  now asserts `pkg == baseline` (baseline = the same call with `hedge` omitted) in addition
  to the original `insurance_cards == frozenset()`. Both pass (`recommend_sideboard` is
  deterministic — closed-form Beta/Dirichlet math, no unseeded RNG).
- (c) Renamed stale `graveyard-reliant` synthetic labels to `graveyard-recursion` (the real,
  current HOSER_CATALOG tag for the same conceptual cards, e.g. Surgical Extraction) in
  `tests/test_collection_aware_engine.py` (4 occurrences), `tests/test_generation_tuning.py`
  (5 occurrences), `tests/test_interaction_facts.py` (3 prose occurrences). Pure rename, no
  new tests, no behavior change — confirmed `grep -rn "graveyard-reliant" tests/ src/` finds
  zero remaining test hits (one pre-existing historical-prose comment in
  `advisory/whattoplay.py:748` was left untouched — out of this item's stated file scope).
