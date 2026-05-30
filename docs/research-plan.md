---
name: research-plan-legacy-engine
description: Read to know what research must run before /architecture, and what's deferred per-pillar. The routing plan for /research, /deep-research, and /brief invocations.
type: research-plan
kind: planning
summary: |
  Research routing plan for legacy-engine. Two grounding briefs are already done (legacy-foundations,
  legacy-metagame). One load-bearing /research remains before /architecture: the fbettega-cache +
  MTGOFormatData data contracts (the ingestion + archetype-parser layer). Advisory statistics is a
  smaller /research; Scryfall is reuse-from-edh-engine (no research). Goldfish and generation research
  are deferred to their pillars.
decisions:
  - "Two grounding briefs are DONE (legacy-foundations, legacy-metagame) — they cover rules, mulligan, constraints, meta, archetypes, data sources, and how-to-attack."
  - "One load-bearing /research before /architecture: the fbettega cache JSON schema + MTGOFormatData rule schema + parser port strategy (the ingestion + archetype-parser data contracts)."
  - "Advisory statistics is a focused /research (win-rate CI method, sample-size gating, sideboard set-cover formulation) — can run before or alongside /architecture."
  - "Scryfall card-data ingestion needs NO research — port edh-engine's scryfall.py directly."
  - "Goldfish-pillar research (mana-solver port, straight-London mulligan adaptation, clock calibration) is deferred to the Deck Mechanics pillar; rules grounding already exists in legacy-foundations."
created: 2026-05-29
updated: 2026-05-29
related:
  - {slug: docs/ARCHITECTURE.md, relationship: depends-on}
  - {slug: docs/briefs/legacy-foundations.md, relationship: depends-on}
  - {slug: docs/briefs/legacy-metagame.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/parent.md, relationship: depends-on}
---

# Research Plan: legacy-engine

## Already grounded (done)
- ✅ **[brief] legacy-foundations** — rules/turn structure (sim framing), London mulligan + math, format constraints + banned list + staples. → [briefs/legacy-foundations.md](briefs/legacy-foundations.md)
- ✅ **[brief] legacy-metagame** — 2026 tier list, per-archetype mechanics + goldfish clocks, data-source ecosystem, how-to-attack-the-meta. → [briefs/legacy-metagame.md](briefs/legacy-metagame.md)

## Pre-architecture research (run BEFORE /architecture)

1. **Ingestion + archetype-parser data contracts** — `/research` *(load-bearing)*
   - **Question:** What is the exact JSON schema of the fbettega `MTG_decklistcache` tournament files, and what is the MTGOFormatData archetype-rule schema + MTGOArchetypeParser matching logic — enough to port the rule engine to Python and design the `ingestion/` and `archetype/` modules?
   - **Rationale:** This is the key architectural delta from edh-engine and the data backbone of the whole MVP. The `archetype/` and `ingestion/` modules cannot be designed without the real schemas. The metagame brief identified *that* these are the sources; this pins down their *shape*.
   - **Output:** brief at `docs/briefs/ingestion-archetype-contracts.md` (blocks_phase the ingestion/parser phase).

2. **Advisory statistics & optimization methods** — `/research` *(can run alongside /architecture)*
   - **Question:** What's the right statistical treatment for matchup-matrix cells (Wilson vs Agresti-Coull CI, minimum sample thresholds, how mtgdecks computes its matrix), and the cleanest formulation for the sideboard recommender (weighted set-cover / max-coverage over a hoser→target graph, including the anti-hate second order)?
   - **Rationale:** The advisory pillar is the differentiator and ships in the MVP. The metagame brief sketches the model; this firms up the math so /architecture can specify it.
   - **Output:** brief at `docs/briefs/advisory-methods.md`.

## No research needed (reuse from edh-engine)
- **Scryfall card-data ingestion** — port `edh-engine/ingestion/scryfall.py` (bulk download + batch resolution). Well-understood, shared dimension.
- **Pydantic models / CLI / local-file conventions** — mirror edh-engine's patterns directly.

## Deferred follow-ups (post-architecture, per-pillar)
- **Goldfish pillar** — `/brief` when the Deck Mechanics pillar starts: porting edh-engine's bipartite-matching mana solver, adapting the mulligan to **straight London (no free mull)**, and clock calibration against the Oops-All-Spells anchor. Rules grounding already exists in legacy-foundations.
- **Deck Generation pillar** — `/research` when that pillar starts: gap-discovery + build-tuning methods (likely reuses edh-engine's deferred optimizer thinking).

## Suggested sequence
```
/research-pipeline:research  (ingestion + archetype-parser contracts)   ← do this next
  └─ (optionally in parallel) /research advisory statistics
      └─ /research-pipeline:architecture   (firm up detailed modules + storage decision)
          └─ /agile-workflow:convert  (bootstrap substrate)
              └─ /research-pipeline:epicize  (decompose into epics)
```
