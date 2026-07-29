---
id: idea-camp-incremental-assignment
created: 2026-07-28
tags: [discovery]
---

Discovery FAIL keeps the frozen staged split (member_keys pinned at the last PASSing
run), so new decks stay camp-unlabeled — 11/12 fresh Cephalid decks had no camp after
the 2026-07-28 refresh because its re-run failed gate-A (stability 0.831). Add an
incremental assignment path for post-staging decks: nearest-camp assignment against the
staged signatures, or membership extension, so a growing corpus doesn't silently
degrade camp coverage between successful discovery runs. Keep provenance honest
(incrementally-assigned decks labeled distinctly from clustered membership).
