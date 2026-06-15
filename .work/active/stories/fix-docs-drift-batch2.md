---
id: fix-docs-drift-batch2
kind: story
stage: done
tags: [documentation]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: docs
created: 2026-06-14
updated: 2026-06-14
---

# Foundation-doc drift: batch 2 (PRs #8-#11) (gate-docs, 3 High + Medium)
- **ARCHITECTURE.md** CLI diagram + Conventions: add the 7th advise leaf `advise field`; add the `--provenance online|paper` advisory flag (now on all advise leaves + report matchups/meta); add `report affectedness` to the report leaf list; note the `positioning.py` opt-in `--list-granular` S_granular overlay; note the `data/hosers/legacy.json` catalog data file + loader in the sideboard.py row. Bump `updated:`.
- **SPEC.md**: add [Built] capability bullets — provenance-filtered advisory, standalone field-read, list-granular positioning, `ramp` vulnerability coverage, considering/bubble pool, report head-to-head (`matchups --a/--b`), `report affectedness`, `report trends --movers`.
- **README.md**: `--provenance` is on advise leaves too (not just report); add examples for `advise field`, `--list-granular`, `report affectedness|matchups --a/--b|trends --movers`; refresh the test-count.
- Then run `/knowledge-index` to regen (foundation `updated:` dates predate this batch's surfaces).

## Resolution
- **ARCHITECTURE.md**: Added `advise field` to CLI diagram (box + Conventions list); added `report affectedness` to report leaf list; added Cross-cutting flags notes for `--provenance online|paper` (all advise leaves + report matchups/meta), `--list-granular`, `report affectedness`, and `report trends --movers`; noted `data/hosers/legacy.json` in the sideboard.py row; added Conventions bullets explaining each new surface. Bumped `updated: 2026-06-14`.
- **SPEC.md**: Added [Built] bullets for ban-affectedness report, trends movers digest, list-granular positioning overlay, considering/bubble pool, ramp vulnerability, standalone field read (`advise field`), provenance-filtered advisory, head-to-head matchup lookup. Bumped `updated: 2026-06-14`.
- **README.md**: Updated the `--provenance` note to cover all advise leaves; added `advise field` + `--list-granular` + `report affectedness` + `report matchups --a/--b` + `report trends --movers` examples; added status-table rows for the new capabilities; refreshed test count to 2199.
- **Knowledge index**: regenerated via `python scripts/gen_knowledge_index.py` — 20 docs, 0 errors (4 pre-existing orphan warnings unchanged).
