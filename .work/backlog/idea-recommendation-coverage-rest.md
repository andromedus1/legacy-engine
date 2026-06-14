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

## Resolution

Resolved 2026-06-14. 32 tests added in `tests/test_recommendation_coverage_rest.py`
(31 pass, 1 xfailed). Suite: 1944 passed, 1 xfailed (was 1913 passed).

Real bug exposed (fix-cli-log-undefined): `generate tune` and `generate consensus` call
`log.info(...)` in the `--players`+`--strong` precedence branch (cli.py lines 3187, 3499)
but `log = logging.getLogger(__name__)` is missing at module level. Causes `NameError`
when both flags are combined. Test `test_cli_players_wins_over_strong` is xfailed (strict=False)
and documents the fix: add `log = logging.getLogger(__name__)` after imports in cli.py.
Assertion NOT weakened — will auto-green when the fix lands.
