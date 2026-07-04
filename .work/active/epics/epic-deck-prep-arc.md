---
id: epic-deck-prep-arc
kind: epic
stage: drafting
tags: [advisory, analysis, dogfooding]
parent: null
depends_on: [feature-archetype-sweep-backtest]
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-04
---

# Deck-prep dogfooding arc — Dimir + Doomsday Tempo across both metas, then the loop pattern

## Brief

Andrew's queued arc (2026-07-04, direction locked via an only-questions round): a five-stage
analysis campaign using shipped engine tools (no engine-code features), running AFTER the
archetype-sweep arc completes (hence the depends_on — the boards should use the
determinism-fixed solver and inherit any scorer findings).

## Strategic decisions

- **Collection**: collection data in the engine is CURRENT. Every "optimize sideboard" step
  produces TWO boards: Board A unconstrained (may include unowned cards — doubles as the
  acquisition-target list), Board B constrained to currently-owned cards.
- **"Build 2 decks per meta" = 4 lists**: BOTH Dimir Tempo tuned per meta AND the engine's
  `whattoplay` best-pick per meta. Metas: Boulder paper field
  (`decks/boulder-field-since-518.txt`) and online (MTGO-provenance current-regime field).
- **Doomsday Tempo**: use the meta/consensus version as a SUBARCHETYPE of Doomsday (to be
  contrasted with the Doomsday combo version). The prior two-mode "transform" build is
  unreliable — ignore it; defer to consensus. Check whether the corpus distinguishes the
  subarchetype (decks.variant or archetype label); if not, subarchetype identification is
  part of the stage.
- **Sequencing**: sweep arc first (validation gate + copy-count study), then this arc.

## Planned decomposition (epic-design formalizes; chain is serial)

1. **Dimir Tempo sideboard refresh** — fresh optimized board for Andrew's deck
   (`decks/dimir-tempo-optimized.txt` is prior art): Board A (unconstrained + acquisition
   targets) and Board B (owned-only).
2. **Meta decks, 4 lists** — Dimir Tempo tuned for Boulder + online; `whattoplay` best-pick
   deck generated + board-optimized for Boulder + online.
3. **Doomsday Tempo per-meta** — consensus-based Doomsday Tempo subarchetype: generation,
   two collection boards (A/B), Boulder + online versions
   (`decks/doomsday-tempo-boulder.txt` is prior art).
4. **Dimir vs Doomsday comparison** — optimized Dimir Tempo vs optimized Doomsday Tempo,
   compared across BOTH metas (matchup matrix, positioning, divergence surfaces — honest
   sample-tier gating throughout).
5. **Reflection: the loop + simulation feed** — codify stages 1-4 as a repeatable loop to
   process ALL meta decks (absorb/relate [[idea-dogfood-loop-as-autonomous-process]]), and
   design the pattern for feeding the generated knowledge into the simulation engine /
   synthetic data generator (relates to epic-goldfish-simulation, deferred + needs-brief —
   this stage produces its input, not its implementation).
