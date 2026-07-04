---
id: gate-tests-low-findings-v020
created: 2026-07-04
tags: [testing]
---

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
