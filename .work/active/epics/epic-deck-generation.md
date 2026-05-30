---
id: epic-deck-generation
kind: epic
stage: drafting
tags: [generation, needs-brief]
parent: null
depends_on: [epic-advisory, epic-goldfish-simulation]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Deck Generation (deferred pillar)

## Brief

The Deck Generation pillar — **deferred**, the furthest-out capability. Find under-explored shells and
tune existing builds against the (current or projected) meta: the knowledge layer identifies structural
gaps, deck-mechanics knowledge constrains the build (mana, roles, consistency floor), and the matchup +
goldfish layers validate candidates. Analytically guided, not brute force.

Marked `[needs-brief]`: no research brief covers generation methods yet. Depends on both the advisory
pillar (positioning/matchups to validate against the meta) and the goldfish pillar (consistency/clock
validation of candidates). Bottom of the dependency graph; design only after the MVP arc and goldfish
ship and a generation-methods brief is written.

## Research briefs
- **[needs-brief]** — a deck-generation-methods brief: gap-discovery techniques, constrained build search, candidate validation against matchups + goldfish. Run `/research-pipeline:research` (likely reuses edh-engine's deferred-optimizer thinking) before `/epic-design`.

## Foundation references
- `docs/ARCHITECTURE.md` — the deferred `generation/` module (consumes advisory + goldfish outputs).
- `docs/VISION.md` — Deck Generation pillar.

## Anticipated child features
(provisional — real decomposition after the generation brief + `/epic-design`)
- Meta-gap discovery (structural gaps in the archetype/card space)
- Constrained build search (mana/role/consistency constraints)
- Candidate validation (positioning + goldfish clock + consistency floor)
