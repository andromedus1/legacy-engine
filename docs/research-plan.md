---
name: research-plan-legacy-engine
description: Read to understand which research grounds the current architecture and which deferred questions still require a fresh brief before implementation.
type: research-plan
kind: planning
summary: |
  Current research posture for legacy-engine. The pre-architecture ingestion, taxonomy, format,
  metagame, and advisory-method grounding is complete and reflected in the shipped architecture.
  New briefs are required only for still-deferred work or when a consequential assumption needs a
  fresh external check.
decisions:
  - "Pre-architecture grounding is complete: format/metagame briefs, the ingestion-archetype campaign, and advisory methods now support the current architecture."
  - "The canonical ingestion/archetype research root is docs/briefs/ingestion-archetype-contracts/parent.md with its specialist child briefs."
  - "Future consequential modeling work receives a fresh bounded brief before design rather than relying on this routing record."
  - "Scryfall card-data ingestion needs NO research — port edh-engine's scryfall.py directly."
  - "Goldfish-pillar research (mana-solver port, straight-London mulligan adaptation, clock calibration, and candidate validation) remains deferred to the Deck Mechanics pillar."
created: 2026-05-29
updated: 2026-08-16
related:
  - {slug: docs/ARCHITECTURE.md, relationship: depends-on}
  - {slug: docs/briefs/legacy-foundations.md, relationship: depends-on}
  - {slug: docs/briefs/legacy-metagame.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/parent.md, relationship: depends-on}
---

# Research Plan: legacy-engine

## Grounding that owns the current architecture

- ✅ **[brief] legacy-foundations** — rules/turn structure (sim framing), London mulligan + math, format constraints + banned list + staples. → [briefs/legacy-foundations.md](briefs/legacy-foundations.md)
- ✅ **[brief] legacy-metagame** — 2026 tier list, per-archetype mechanics + goldfish clocks, data-source ecosystem, how-to-attack-the-meta. → [briefs/legacy-metagame.md](briefs/legacy-metagame.md)
- ✅ **[campaign] ingestion + archetype-parser contracts** — cache/schema, classifier-rule,
  matching, port, Scryfall, and operational contracts. →
  [briefs/ingestion-archetype-contracts/parent.md](briefs/ingestion-archetype-contracts/parent.md)
- ✅ **[brief] advisory methods** — statistical support, matchup estimation, and optimization
  grounding for the advisory pillar. → [briefs/advisory-methods.md](briefs/advisory-methods.md)

These artifacts are inputs to the present [architecture](ARCHITECTURE.md); no pre-architecture
research remains pending.

## No research needed (reuse from edh-engine)
- **Scryfall card-data ingestion** — port `edh-engine/ingestion/scryfall.py` (bulk download + batch resolution). Well-understood, shared dimension.
- **Pydantic models / CLI / local-file conventions** — mirror edh-engine's patterns directly.

## Deferred research triggers

- **Goldfish pillar** — `/brief` when the Deck Mechanics pillar starts: porting edh-engine's bipartite-matching mana solver, adapting the mulligan to **straight London (no free mull)**, and clock calibration against the Oops-All-Spells anchor. Rules grounding already exists in legacy-foundations.
- **Goldfish-validated candidate evaluation** — research the validation contract alongside the
  goldfish pillar before synthetic evidence may gate generated candidates.
- **Research refreshes** — rerun a bounded research engagement when an upstream data contract,
  format rule, or consequential statistical assumption changes.

## Sequence for new research-backed scope

```
/research-pipeline:research or /brief  (answer the bounded open question)
  └─ update the relevant foundation contract
      └─ /agile-workflow:scope and feature design
          └─ implementation and review
```
