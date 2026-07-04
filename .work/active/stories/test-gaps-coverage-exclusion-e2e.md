---
id: test-gaps-coverage-exclusion-e2e
kind: story
stage: done
tags: [testing, discovery]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: null
created: 2026-06-01
updated: 2026-06-15
---

`report gaps` / `compute_archetype_gaps` exclude thin-matchup-data archetypes via
`rank_decks(min_coverage=…) → low_coverage → excluded_low_coverage`. That gate is tested at the
unit level (`_assemble_gaps` with an injected `low_coverage` set) and verified-by-construction at
the seam, but there is no end-to-end test that drives a *real* thin-coverage archetype out through
`rank_decks` (the corpus seam test runs with `min_coverage=0.0`, disabling the gate). Add a
3-archetype corpus (one archetype with decks but no decisive rounds → data_coverage≈0, small share
so it doesn't tank others' coverage) and assert it lands in `excluded_low_coverage` and not in
`gaps`. Closes the deep-review nit on `epic-gap-discovery-archetype-gaps`.

## Resolution (2026-06-15)
Already covered: `tests/test_gaps.py::TestThinCoverageExclusion` is exactly the requested test —
a hermetic 3-archetype `:memory:` corpus (Control / Combo at n=100 decisive vs ThinArch with 0
decisive rounds → data_coverage=0, ~small share). `test_thin_archetype_excluded_from_gaps` drives
ThinArch out through `rank_decks` at `min_coverage=0.5` (asserts it's in `excluded_low_coverage`,
not in `gaps`); `test_thin_archetype_included_when_gate_disabled` pins the gate-off behavior. Added
after this idea was filed. Verified green; no new code needed.
