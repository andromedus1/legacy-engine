---
id: fix-ruleset-trailing-comma
kind: story
stage: done
tags: [bug, archetype]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: null
created: 2026-05-30
updated: 2026-06-14
---

# Fix: load_ruleset crashes on trailing commas in upstream rule files

## Brief
Discovered while labeling the real corpus: `label` crashed in `load_ruleset` because 3 hand-maintained
MTGOFormatData files (`Fallbacks/Dredge.json`, `Fallbacks/Stompy.json`, `color_overrides.json`) contain
**trailing commas** — invalid strict JSON. Skipping them would drop real Legacy archetypes (Dredge, Stompy).

## Fix
`archetype/rules.py`: added `_loads_lenient` — strict `json.loads` first, and on a trailing-comma failure,
strip `,` before `]`/`}` and retry (rule-file values are card-name strings, so the regex can't corrupt
content). Wired into all four rule-file reads in `load_ruleset`. Recovers the archetypes rather than
dropping them. Regression test `tests/test_rules_loader.py::test_trailing_comma_tolerated`.

## Outcome
`label` classified all 63,150 decks; only 4.7% unresolved (NULL/Unknown/Conflict) in the last-year slice.
580 tests green.
