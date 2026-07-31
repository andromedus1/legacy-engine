---
id: feature-camp-incremental-assignment
kind: feature
stage: drafting
tags: [analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-28
updated: 2026-07-31
---

# Incremental camp assignment for post-staging decks


Discovery FAIL keeps the frozen staged split (member_keys pinned at the last PASSing
run), so new decks stay camp-unlabeled — 11/12 fresh Cephalid decks had no camp after
the 2026-07-28 refresh because its re-run failed gate-A (stability 0.831). Add an
incremental assignment path for post-staging decks: nearest-camp assignment against the
staged signatures, or membership extension, so a growing corpus doesn't silently
degrade camp coverage between successful discovery runs. Keep provenance honest
(incrementally-assigned decks labeled distinctly from clustered membership).

## Design decisions
<!-- captured 2026-07-31 via feature-design --only-questions; treat as fixed inputs -->
- **Persistence**: persist incremental assignments to the DB alongside staged labels with
  an `assigned_by: incremental` provenance flag — consumers see full coverage, provenance
  is queryable, and the next PASSing discovery run supersedes them.
