---
id: fix-tests-batch2
kind: story
stage: done
tags: [testing]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: tests
created: 2026-06-14
updated: 2026-06-15
---

# Test-coverage gaps: batch 2 (gate-tests, Medium/Low)
- **Medium** empirical-sideboard-swings POSITIVE data-informed path untested: no test drives `recommend_sideboard` Step 3e with a rounds corpus that yields swing overrides and flips `swing_data_informed=True` / `swing_overrides_count>0` / `heuristic_note`→`_DATA_INFORMED_NOTE` ("presence-correlational"). Add a hermetic seeded-corpus test (use --db / :memory:).
- **Low** bigmana-ramp-tag: no e2e test that a ramp-heavy field yields a ramp hoser (Harbinger/Damping Sphere) in `recommend_sideboard`'s chosen 15 / considering pool. Add one.
(Hermeticity audited CLEAN for this batch — keep new CLI/DB tests seeding their own --db.)

## Resolution (2026-06-15)
Both added to `tests/test_sideboard.py`, hermetic `:memory:`:
- **Medium** `TestEmpiricalSideboardSwings::test_package_swing_data_informed_true_with_correlated_tech`
  — a current-regime contrast corpus (Control-with-Surgical beats Combo; Control-without loses) gives
  the side tech a positive presence-correlational lift; with a low-curated-swing catalog the empirical
  proxy wins, flipping `swing_data_informed=True`, `swing_overrides_count>=1`, and the note to the
  presence-correlational data-informed note. Dated 2026-05-19+ so the default adaptive window (current
  ban regime) scans it. Discovered the positive path only fires in adaptive mode (no explicit
  since/until) AND on in-regime data — both prior integration tests passed explicit windows, which is
  exactly why this path was uncovered.
- **Low** `TestRecommendSideboard::test_ramp_heavy_field_yields_ramp_hoser` — a BigMana archetype
  running ≥4 diagnostic big-mana lands (Cloudpost/Eldrazi Temple, loaded into the cards table so
  `vulnerability_tags` counts them) earns the `ramp` tag; Damping Sphere (colorless ramp hoser) lands
  in the chosen 15.
