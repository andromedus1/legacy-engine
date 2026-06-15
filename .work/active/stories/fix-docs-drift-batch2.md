---
id: fix-docs-drift-batch2
kind: story
stage: implementing
tags: [documentation]
parent: null
depends_on: []
release_binding: null
gate_origin: docs
created: 2026-06-14
updated: 2026-06-14
---

# Foundation-doc drift: batch 2 (PRs #8-#11) (gate-docs, 3 High + Medium)
- **ARCHITECTURE.md** CLI diagram + Conventions: add the 7th advise leaf `advise field`; add the `--provenance online|paper` advisory flag (now on all advise leaves + report matchups/meta); add `report affectedness` to the report leaf list; note the `positioning.py` opt-in `--list-granular` S_granular overlay; note the `data/hosers/legacy.json` catalog data file + loader in the sideboard.py row. Bump `updated:`.
- **SPEC.md**: add [Built] capability bullets — provenance-filtered advisory, standalone field-read, list-granular positioning, `ramp` vulnerability coverage, considering/bubble pool, report head-to-head (`matchups --a/--b`), `report affectedness`, `report trends --movers`.
- **README.md**: `--provenance` is on advise leaves too (not just report); add examples for `advise field`, `--list-granular`, `report affectedness|matchups --a/--b|trends --movers`; refresh the test-count.
- Then run `/knowledge-index` to regen (foundation `updated:` dates predate this batch's surfaces).
