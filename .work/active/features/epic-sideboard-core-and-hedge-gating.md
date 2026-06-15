---
id: epic-sideboard-core-and-hedge-gating
kind: feature
stage: drafting
tags: [advisory, sideboard]
parent: epic-sideboard-core-and-hedge
depends_on: [epic-sideboard-core-and-hedge-dedicated-core, epic-sideboard-core-and-hedge-output-contract]
release_binding: null
gate_origin: null
created: 2026-06-15
updated: 2026-06-15
---

# Gating + operator controls (core wave)

## Brief

Wire the new core behavior behind an opt-in flag and expose the core's operator dials, then flip the
default once trusted. Gated-additive: with the flag off, `recommend_sideboard` is **byte-identical**
to today's forced-15 max-coverage output, so every existing test and caller is unaffected; with the
flag on, it returns the dedicated core (<15) with the new output contract. Exposes the core dials:
the natural-budget floor τ (tier-aware default), a total budget cap, and the access/redundancy curve
parameters (sensible defaults from the brief). Completes the v1 (core-first) wave; the "flip the
default once trusted" step is the closing move once the core path is validated on real prep.

This feature covers ONLY the core's flag + dials. The hedge feature adds its own dials
(hedge on/off, risk-appetite α, blend width) when it lands.

## Epic context
- Parent epic: `epic-sideboard-core-and-hedge`
- Position in epic: closes the v1 core wave — depends on the core solver and the output contract.
  The default flip is the last v1 step.

## Inherited design decisions
- Opt-in flag first, byte-identical until opted in; flip default once trusted (gated-additive).
- Operator-tunable τ + curve params with brief defaults; don't hardcode.

## Research briefs
- `docs/briefs/sideboard-core-and-hedge.md` §"Implementation Notes" (gating) + §4 (τ as a dial).

## Foundation references
- `src/legacy_engine/advisory/sideboard.py` (`recommend_sideboard` signature), `src/legacy_engine/cli.py`
  (`advise sideboard` flags).
- Patterns: [[gated-additive-augmentation]] (the defining shape — no-op path byte-identical to
  baseline, existing tests stay green untouched), [[cli-nested-groups]].
