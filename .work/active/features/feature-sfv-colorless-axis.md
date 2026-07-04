---
id: feature-sfv-colorless-axis
kind: feature
stage: implementing
tags: [advisory]
parent: epic-scorer-flexibility-valuation
depends_on: [feature-sfv-attachments]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Colorless/trigger vulnerability axis — close the Consign acceptance criterion

## Brief

Promoted from backlog during the epic's completion review because **Consign to Memory is named in
the epic's acceptance oracle** ("FoN / Consign move from winners-only into overlap") and remains
winners-only at **95.7%** adoption in 258 Boulder-relevant top-finisher boards. Mechanism
(confirmed): Consign's catalog `attacks = {combo, storm-reliant}` is a strict subset of Force of
Negation's, so under correct submodular marginal-gain FoN dominates and Consign's marginal is ~0 —
tag-subset dominance, not a solver bug. Winners run BOTH because Consign answers an axis FoN cannot.

**Oracle (DB-verified 2026-07-03):** `{U}`, "Replicate {1}" + **"Counter target triggered ability or
colorless spell."** Colorless spells and TRIGGERED ABILITIES only — not a general counterspell.
Premier vs Saga chapter triggers (Black Saga Storm / Blue Artifacts), storm-count triggers, Chalice
triggers, Eldrazi/colorless spells; replicate {1} scales to multiple triggers in one turn.

## Design (inline — story-sized)

Add a mechanics-derived vulnerability axis so trigger/colorless-answering cards attach to the
archetypes whose plan runs through colorless spells or key triggered abilities:

- **`colorless-reliant`** in `whattoplay.py`'s `VulnerabilityTag` vocabulary: derived in
  `_vulnerability_from_composition` from colorless-nonland-spell density (a card with empty
  `colors` and a castable spell type) ≥ a named threshold constant (pick by inspecting real
  archetypes: Eldrazi, Blue Artifacts/Affinity, Saga Storm should fire; Dimir/Izzet should not —
  verify against the corpus and document the threshold choice). Judgment call allowed on whether a
  separate `trigger-reliant` axis is derivable purely from composition (Saga density etc.) — if it
  isn't cleanly mechanics-derivable, ship `colorless-reliant` only and note why.
- **Catalog:** add the new tag to Consign's `attacks` (keeping `combo, storm-reliant`). Check
  whether other catalog cards genuinely attack the axis (e.g. Stifle-likes if present; do NOT
  stretch cards that don't).
- **Pure mechanics** — no empirical prior; the 95.7% signal motivates the investigation, the tag
  derivation must stand on composition alone.

## Acceptance

Field-scoped `advise backtest` (Dimir Tempo + Boulder): **Consign moves winners-only → overlap**
(recommended by the engine) with FoN still in overlap and the suite green (2546 floor + new tests).
