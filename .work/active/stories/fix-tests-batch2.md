---
id: fix-tests-batch2
kind: story
stage: drafting
tags: [testing]
parent: null
depends_on: []
release_binding: null
gate_origin: tests
created: 2026-06-14
updated: 2026-06-14
---

# Test-coverage gaps: batch 2 (gate-tests, Medium/Low)
- **Medium** empirical-sideboard-swings POSITIVE data-informed path untested: no test drives `recommend_sideboard` Step 3e with a rounds corpus that yields swing overrides and flips `swing_data_informed=True` / `swing_overrides_count>0` / `heuristic_note`→`_DATA_INFORMED_NOTE` ("presence-correlational"). Add a hermetic seeded-corpus test (use --db / :memory:).
- **Low** bigmana-ramp-tag: no e2e test that a ramp-heavy field yields a ramp hoser (Harbinger/Damping Sphere) in `recommend_sideboard`'s chosen 15 / considering pool. Add one.
(Hermeticity audited CLEAN for this batch — keep new CLI/DB tests seeding their own --db.)
