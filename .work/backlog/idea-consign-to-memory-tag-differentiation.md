---
id: idea-consign-to-memory-tag-differentiation
created: 2026-07-03
tags: [advisory, sideboard]
---

Consign to Memory stays `winners-only` (95.7% observed) in the Dimir Tempo vs Boulder-field
`advise backtest` even after `feature-sfv-breadth-objective`'s true submodular marginal-gain
aggregation was confirmed/hardened.

**Root cause (verified, not hand-waved):** Consign to Memory's catalog `attacks={combo,
storm-reliant}` is a STRICT SUBSET of Force of Negation's `attacks={combo, storm-reliant,
noncreature-reliant}` (`data/hosers/legacy.json`), both `swing=dedicated`. Under ANY correct
monotone-submodular coverage objective, a card whose coverage is a strict subset of an
already-picked card's coverage can never out-rank it — this is mathematically inherent, not a
breadth-aggregation defect. (Audited as part of `feature-sfv-breadth-objective`: the objective
already sums marginal gain across every element a card covers; `docs/briefs/scorer-flexibility-
valuation.md`'s D1 diagnosis turned out, on code audit, to already be correctly implemented in
the greedy/ILP/hedge/considering-pool paths.)

The real gap is attachment-tag granularity (`feature-sfv-attachments`' domain, already shipped):
Consign to Memory and Force of Negation are mechanically distinct in real play (Consign counters
ANY spell including creatures, plus activated/triggered abilities and land drops; FoN only
counters noncreature spells) but the current tag ontology can't distinguish them, so Consign is
invisible to the solver as long as FoN is in the board.

**Suggested direction:** a future catalog-touching feature should add a tag Consign covers that
FoN does not (e.g. a distinguishing "creature-reliant-combo" or "activated-ability-reliant" or
"land-based-combo" axis FoN structurally can't hit) so the two stop being modeled as pure
subset/superset.

**Explicitly out of scope for `feature-sfv-breadth-objective`** (confined to
`advisory/sideboard.py`'s aggregation logic, not the hoser catalog's tag semantics). Do NOT fix
by gaming the objective (e.g. an artificial "distinct-card diversity bonus") — that would violate
the epic's pure-mechanics guardrail.
