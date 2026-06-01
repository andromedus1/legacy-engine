---
id: idea-gaps-e2e-coverage-exclusion-test
created: 2026-06-01
tags: [testing, discovery]
---

`report gaps` / `compute_archetype_gaps` exclude thin-matchup-data archetypes via
`rank_decks(min_coverage=…) → low_coverage → excluded_low_coverage`. That gate is tested at the
unit level (`_assemble_gaps` with an injected `low_coverage` set) and verified-by-construction at
the seam, but there is no end-to-end test that drives a *real* thin-coverage archetype out through
`rank_decks` (the corpus seam test runs with `min_coverage=0.0`, disabling the gate). Add a
3-archetype corpus (one archetype with decks but no decisive rounds → data_coverage≈0, small share
so it doesn't tank others' coverage) and assert it lands in `excluded_low_coverage` and not in
`gaps`. Closes the deep-review nit on `epic-gap-discovery-archetype-gaps`.
