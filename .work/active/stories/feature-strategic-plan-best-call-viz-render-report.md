---
id: feature-strategic-plan-best-call-viz-render-report
kind: story
stage: done
tags: [analytics, viz, ui]
parent: feature-strategic-plan-best-call-viz
depends_on: [feature-strategic-plan-best-call-viz-data-contract]
release_binding: null
gate_origin: null
created: 2026-08-02
updated: 2026-08-02
---

# Strategic-plan table, portrait, and generated report

## Brief

Render the approved sortable/filterable peer table with accessible row expansion, reusable plan
portrait, and exact opponent-plan ledger in Best Deck / Best Call; remove both superseded figures and
verify the regenerated production document.

## Implementation

Implement Units 4–5 from the parent feature's `## Implementation Units` section.

## Implementation notes

- Execution capability: high; generated-data UI semantics, accessibility, and removal of superseded visual surfaces required integrated verification.
- Review weight: standard (caller/default).
- Files changed: `scripts/best_call_ranking_template.html`, `tests/test_refresh_best_call_ranking.py`, `docs/analysis/best-call-ranking.md`, generated `decks/best-deck-best-call-ranking.html`, and generated knowledge indexes.
- Tests added/removed: replaced obsolete visible-family-payload assertions with strategic-plan isolation/payload and end-to-end disclosure/removal assertions; retained superarchetype ledger-fallback tests.
- Simplification: removed the visible taxonomy hierarchy, strategy-family agency heatmap, camps × parent-opponents map, and their dedicated renderer/CSS paths; retained only composition-family ledger fallback evidence.
- Discrepancies from design: no browser automation is installed in the repository, so responsive and keyboard contracts were verified structurally through the generated HTML/JavaScript and semantic DOM assertions rather than automated screenshots.
- Adjacent issues parked: none.
- Verification: focused strategy/report suite — 38 passed; full suite — 3,543 passed with one existing UMAP warning; embedded JavaScript parsed with Node; no placeholder remained; generated report contained the plan controls/disclosure and none of the removed renderer identifiers; `git diff --check` clean; knowledge-index lint 0 errors (6 pre-existing warnings).
