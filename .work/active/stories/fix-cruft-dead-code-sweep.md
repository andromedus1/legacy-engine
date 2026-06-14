---
id: fix-cruft-dead-code-sweep
kind: story
stage: implementing
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

