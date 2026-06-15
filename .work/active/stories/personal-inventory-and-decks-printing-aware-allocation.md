---
id: personal-inventory-and-decks-printing-aware-allocation
kind: story
stage: done
tags: [data-model, foundation, hold-for-review]
parent: feature-personal-inventory-and-decks
depends_on: [feature-personal-inventory-and-decks]
release_binding: v0.1.0
gate_origin: null
created: 2026-06-13
updated: 2026-06-14
---

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

## Implementation notes

**New primitive**: `PhysicalKey(name, printing, condition, foil)` — a `NamedTuple` in `collection/allocation.py`. All four fields match `InventoryEntry`'s identity tuple. Usable as a dict key.

**New builder helpers** (pure, no I/O):
- `inventory_to_physical(entries)` — `list[InventoryEntry]` → `dict[PhysicalKey, int]`
- `deck_to_physical(cards)` — `list[DeckCardRef]` → `dict[PhysicalKey, int]` (printing-pinned refs carry the pin; unpinned refs get `printing=None`)

**New printing-aware allocation functions** (gated-additive):
- `free_binder_physical(owned, allocated)` — `PhysicalKey`-keyed dicts → free counts per physical copy
- `contention_physical(per_deck_physical, owned)` → `list[ContentionEntry]` where each entry has `physical_key` set

**`ContentionEntry` extended**: added `physical_key: PhysicalKey | None = None` field (defaults to `None`). Entries produced by the original name-level `contention()` have `physical_key=None`; entries from `contention_physical()` always have it set.

**Name-level functions unchanged**: `buildability`, `free_binder`, `contention`, `aggregate_owned` are byte-identical to the parent feature's baseline (gated-additive — no behaviour change when printing absent).

**Tests**: `tests/test_printing_aware_allocation.py` — 34 pure-layer tests:
- `PhysicalKey` identity/equality
- `inventory_to_physical`/`deck_to_physical` builders (including aggregation, foil separation, condition separation)
- `free_binder_physical`: only matching printing reduced; over-committed floors at 0
- `contention_physical`: same-printing contested; different-printing not crossed; foil/non-foil tracked independently; sorted by shortfall
- Mixed presence: printing-absent entries get `None` key; no cross-printing bleed
- Regression: all name-level functions produce identical results; `contention()` sets `physical_key=None`
