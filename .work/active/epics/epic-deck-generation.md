---
id: epic-deck-generation
kind: epic
stage: drafting
tags: [generation]
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

Brief gate satisfied (2026-05-30): `docs/briefs/deck-generation-and-moxfield.md` now covers both the
Moxfield surfacing path and the generation/tuning approach over our existing advisory layers. Note the
brief's finding that the **consensus-baseline + Moxfield export sub-arc can ship independently** (pure data
aggregation, no goldfish, no advisory-heuristic dependency), while the **tune/discover modes depend_on** the
three advisory-improvement items filed this session — `/epic-design` should likely split the epic along that
line and may relax the hard `epic-goldfish-simulation` dependency (goldfish-validation is a later cross-pillar
enhancement, not a blocker for consensus+export+field-tuning).

## Research briefs
- `docs/briefs/deck-generation-and-moxfield.md` — **(written 2026-05-30)** Moxfield integration (no official
  API → export-as-import, support@moxfield.com for sanctioned reads) + generation modes (consensus baseline →
  field-tuning → gap discovery) consuming meta-share / matchup / positioning / sideboard, with the advisory
  heuristic gaps as hard prerequisites for the tuning modes.
- `docs/briefs/advisory-methods.md` — the positioning / matchup / sideboard methods the generator orchestrates.

## Foundation references
- `docs/ARCHITECTURE.md` — the deferred `generation/` module (consumes advisory + goldfish outputs).
- `docs/VISION.md` — Deck Generation pillar.

## Anticipated child features
(provisional — real decomposition after the generation brief + `/epic-design`)
- Meta-gap discovery (structural gaps in the archetype/card space)
- Constrained build search (mana/role/consistency constraints)
- Candidate validation (positioning + goldfish clock + consistency floor)
