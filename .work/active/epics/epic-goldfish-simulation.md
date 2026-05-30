---
id: epic-goldfish-simulation
kind: epic
stage: drafting
tags: [goldfish, needs-brief]
parent: null
depends_on: [epic-foundations-card-data]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-29
---

# Goldfish Simulation (deferred pillar)

## Brief

The Deck Mechanics pillar — **deferred** until after the MVP meta+advisory arc ships. Port edh-engine's
lightweight goldfish engine (bipartite-matching mana solver, role-dispatch turn loop, deck-as-data
YAML) to Legacy, adapt the mulligan to **straight London (no free mull)**, and produce per-deck
goldfish clocks (turn-to-kill PMFs) and a format **meta-speed distribution** (per-archetype clock
weighted by meta share, with both a goldfish upper-bound and an effective clock convolved with
Force-of-Will/Daze survival).

Marked `[needs-brief]`: the rules grounding exists (`legacy-foundations.md`), but a port/calibration
brief is required before design — how to port the mana solver, adapt mulligan keep/bottom to straight
London, and calibrate clocks against the Oops-All-Spells anchor (66% T1 / 76% T2 / 83% T3). Depends
only on the foundations epic (card data + models); independent of the analytics/advisory arc.

## Research briefs
- `docs/briefs/legacy-foundations.md` — rules/turn-structure (sim framing), London mulligan math, the deck-as-data model, the ~8 core rules a goldfish sim must encode.
- **[needs-brief]** — a goldfish-port brief: porting edh-engine's `goldfish/` (mana solver, role dispatch), straight-London keep/bottom adaptation, and clock calibration. Run `/research-pipeline:brief` on this topic before `/epic-design`.

## Foundation references
- `docs/ARCHITECTURE.md` — the deferred `goldfish/` module (seam: deck-as-data YAML + role dispatch, ported from edh-engine).
- `docs/VISION.md` — Deck Mechanics pillar; the meta-speed distribution.

## Anticipated child features
(provisional — real decomposition after the port brief + `/epic-design`)
- Deck-as-data model + loader (straight-London mulligan, no free mull)
- Bipartite-matching mana solver (ported from edh-engine)
- Role-dispatch turn loop + payoff/clock detection
- Meta-speed distribution (goldfish vs effective clocks, weighted by meta share)
