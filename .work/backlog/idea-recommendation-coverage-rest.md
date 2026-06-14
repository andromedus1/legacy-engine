---
id: idea-recommendation-coverage-rest
created: 2026-06-14
tags: [testing]
---

Lower-value test gaps remaining after fix-recommendation-test-coverage (the two highest-value gaps —
overpriced-flag FIRING path + interaction-fact evidence content — are covered in
tests/test_recommendation_coverage.py; suite 1888):
- `tune_deck(collection=)` threading (populated `owned` + byte-identical when None).
- `tune_deck(players=/--strong)` threading + `--players`-beats-`--strong` precedence end-to-end.
- `generate doctor` no-`--archetype` classify branch ("Classified archetype:" echo) + Δ-rendering of a
  known outlier.
- `report subgroup` / `report variants` CLI smoke (diff table + drift warning render).
All test-only; no functionality risk (behaviors verified manually + by adjacent tests).
