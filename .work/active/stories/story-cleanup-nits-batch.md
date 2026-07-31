---
id: story-cleanup-nits-batch
kind: story
stage: implementing
tags: [analytics, cleanup]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-31
updated: 2026-07-31
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
