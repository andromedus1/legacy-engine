---
id: fix-cruft-dead-code-sweep
kind: story
stage: done
tags: [cleanup]
parent: null
depends_on: []
release_binding: null
gate_origin: cruft
created: 2026-06-13
updated: 2026-06-13
---

# Dead-code / stale-comment sweep (gate-cruft)

High:
- `advisory/acquire.py:331-354` — dead per-printing `for...pass` loop (real logic is in the orchestrator
  642-675); delete the block.
- `advisory/acquire.py:356-358` — phantom `owned_prices` injection comment describing a seam that doesn't
  exist; delete.
Medium:
- `interaction_facts.py:209-217` — `_classify_affects` if/else adds `"symmetric"` in BOTH branches (the
  condition is computed and discarded); collapse to one unconditional add (verify intended behavior).
- `advisory/acquire.py:63-65` — unused `_GRAVEYARD_TAG/_COMBO_TAG/_MANABASE_TAG` constants; delete.
- `ingestion/releases.py:23` — unused `_SCRYFALL_SETS_PATH` (fetch_sets hardcodes inline); delete or use.
Low: stale comments in primer.py:412 ("always shown"), primer.py:350-366 (unused params),
card_distribution.py:226 (docstring overstates predicate), sideboard.py:1330-1341 (unreachable invariant
warning). Fix or remove.

## Resolution

All items resolved. Changes:
- `advisory/acquire.py`: deleted dead per-printing `for...pass` loop (was ~331-354), phantom `owned_prices`
  comment (was ~356-358), and unused `_GRAVEYARD_TAG/_COMBO_TAG/_MANABASE_TAG` constants (~63-65).
- `interaction_facts.py`: collapsed the `_classify_affects` if/else that added `"symmetric"` in both
  branches into a single unconditional `scopes_found.add("symmetric")`. The `_RE_STATIC_RESTRICTION`
  check was genuinely unused (both branches produced identical output). Behavior preserved.
- `ingestion/releases.py`: deleted unused `_SCRYFALL_SETS_PATH` constant; `fetch_sets` hardcodes
  the `/sets` path inline.
- `advisory/primer.py`: fixed stale "always shown" comment (now "shown when not degraded"); dropped
  unused `sideboard` and `note` params from `_prose_no_swap_needed` and its call site.
- `generation/card_distribution.py`: corrected docstring that overstated `is_outlier` predicate with
  a redundant `(name in dists)` clause already guaranteed by earlier code.
- `advisory/sideboard.py`: downgraded the unreachable swap-loop invariant `log.warning` (which fired
  only on an impossible mismatch by construction) to a plain comment.
Full suite: 1869 passed.

