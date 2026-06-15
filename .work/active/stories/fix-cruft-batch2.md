---
id: fix-cruft-batch2
kind: story
stage: done
tags: [cleanup]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: cruft
created: 2026-06-14
updated: 2026-06-14
---

# Cruft sweep: batch 2 (gate-cruft, 1 High + Medium/Low)
- **High** `advisory/sideboard.py:733` — `_empirical_sideboard_pool` is dead in prod (recommend_sideboard ~2104-2119 inlines the identical `card_frequencies(board=side)` + adoption logic; the function survives only via tests). Collapse the inline block to call it (extend it to also return modal_count), OR delete it + its tests.
- **Medium** `sideboard.py:1889` — `_considering_label`: `w = model.element_weight.get(...)` assigned, never read; delete. `:1885-1892` — its docstring/comment claim a `"tag (Archetype N%)"` format but the code emits `"{tag} ({arch})"` (no %); fix the comment.
- **Low** `sideboard.py:1665-1667` stale "post_board must sum to 60 / planning skipped" comment (no such skip); `report.py:97-121` over-complex 3-token `_load_field` parse (a single `rsplit(None,1)` suffices); `cli.py:135` `_print_head_to_head` reverse-direction line prints a shrunk rate with no low-n caveat (the primary cell has one).

## Resolution
- **High** Extended `_empirical_sideboard_pool` to return `tuple[frozenset[str], dict[str, int]] | None` (pool + freq_map). Collapsed the 15-line inline block in `recommend_sideboard` (lines 2104-2119) to a 3-line call. Updated tests to unpack the tuple and assert on both pool and freq_map.
- **Medium** Deleted dead `w = model.element_weight.get(e, 0.0)` assignment in `_considering_label` loop body. Fixed docstring: `"tag (Archetype N%)"` → `"tag (Archetype)"` to match emitted format.
- **Low** Trimmed stale "post_board must sum to 60 / planning skipped" comment to a simple "Tally swaps" header. Simplified `_load_field` 3-token parse: replaced split-reconstruct-rsplit with `split(None,1)` + `rsplit(None,1)` on the remainder — all tests green. Added `[speculative — n=X < DISPLAY_GATE_N]` caveat to the reverse-direction line in `_print_head_to_head`.
- Suite: 2199 passed.
