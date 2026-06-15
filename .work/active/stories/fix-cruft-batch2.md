---
id: fix-cruft-batch2
kind: story
stage: implementing
tags: [cleanup]
parent: null
depends_on: []
release_binding: null
gate_origin: cruft
created: 2026-06-14
updated: 2026-06-14
---

# Cruft sweep: batch 2 (gate-cruft, 1 High + Medium/Low)
- **High** `advisory/sideboard.py:733` — `_empirical_sideboard_pool` is dead in prod (recommend_sideboard ~2104-2119 inlines the identical `card_frequencies(board=side)` + adoption logic; the function survives only via tests). Collapse the inline block to call it (extend it to also return modal_count), OR delete it + its tests.
- **Medium** `sideboard.py:1889` — `_considering_label`: `w = model.element_weight.get(...)` assigned, never read; delete. `:1885-1892` — its docstring/comment claim a `"tag (Archetype N%)"` format but the code emits `"{tag} ({arch})"` (no %); fix the comment.
- **Low** `sideboard.py:1665-1667` stale "post_board must sum to 60 / planning skipped" comment (no such skip); `report.py:97-121` over-complex 3-token `_load_field` parse (a single `rsplit(None,1)` suffices); `cli.py:135` `_print_head_to_head` reverse-direction line prints a shrunk rate with no low-n caveat (the primary cell has one).
