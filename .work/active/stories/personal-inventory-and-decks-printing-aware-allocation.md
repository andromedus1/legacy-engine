---
id: personal-inventory-and-decks-printing-aware-allocation
kind: story
stage: drafting
tags: [data-model, foundation, hold-for-review]
parent: feature-personal-inventory-and-decks
depends_on: [feature-personal-inventory-and-decks]
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

> **Held for human review** alongside the parent feature. Design-only until then.

# Printing/condition-aware allocation (the $33-vs-$2 Dismember refinement)

## Scope
Promote `printing` and `condition` from **recordable** (parent feature: optional fields, default
`None`, name-level allocation baseline) to **fully allocation-aware**: track which exact physical copy
(`name` + `printing` + `condition` + `foil`) is free vs allocated to which deck, and let a deck version
pin specific printings. Adds the value hooks the later acquisition advisor needs.

## Design notes
- Builds on the parent's identity tuple for a physical-copy bucket: `(name, printing, condition, foil)`.
- `allocation.buildability` / `free_binder` / `contention` gain a printing-aware mode (gated on
  printings being present in both the inventory entry and the deck card ref); name-only remains the
  fallback (gated-additive-augmentation — name-only path byte-identical to parent behavior).
- Optional `DeckCardRef.printing` pins a version's card to a specific printing for value/allocation.
- Out of scope here (and in the parent): a price feed. This story makes printing *allocation-aware*;
  valuation lands with the acquisition advisor that consumes it.

## Acceptance criteria
- Allocation distinguishes copies by `(name, printing, condition, foil)` when printings are present;
  falls back to name-level when absent, with no behavior change vs the parent for printing-less data.
- Contention reports surface printing-specific overlaps ("both decks claim the foil mh3:62 copy").
- Tests: pure-layer tables over mixed printing-present / printing-absent inventories.

## Hold
Design complete at parent; this child is held for human review before implementation. Stage stays
`drafting`.
