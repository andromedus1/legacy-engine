---
id: fix-variant-resolution-display-key
kind: story
stage: done
tags: [archetype, bug]
parent: epic-subarchetype-resolution-matchup-cells
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Fix: variant resolution keyed on base_archetype silently NULLs color-prefixed archetypes

## Brief
Found dogfooding the split-variant matchup flag end-to-end: `decks.variant` was NULL for every
Dimir Tempo deck despite shipped Bauble/non-Bauble registry rules. Root cause: the labeler called
`resolve_variant(result.base_archetype, ...)` (internal rule name, e.g. "Delver") while registry
parents are written against the display label ("Dimir Tempo"). Only Smallpox populated — its
base == display. The existing labeler test masked the bug by using a base-name parent in its
fixture, diverging from the shipped registry's convention.

## Fix
`labeler.py` resolves against `result.archetype` (display); `models/variant.py` contract docstring
corrected (parent = display label — base names span sibling archetypes and would smear rules);
test fixture aligned to the corrected contract with an explanatory comment. Display keying is the
only correct choice: all registry consumers (`report meta --by-variant`, `generate consensus
--variant`, the new `--split-variant`) filter by `decks.archetype`.
