---
id: epic-deck-prep-arc-meta-decks
kind: feature
stage: done
tags: [advisory, analysis, dogfooding]
parent: epic-deck-prep-arc
depends_on: [epic-deck-prep-arc-dimir-boards]
release_binding: v0.3.0
gate_origin: null
created: 2026-07-04
updated: 2026-07-04
---

# Meta decks — 4 lists: Dimir Tempo + whattoplay best-pick, per meta

## Brief

Engine-built decks for both followed metas: (1) Dimir Tempo tuned for the local field,
(2) Dimir Tempo tuned for the online field (consensus 60 + optimized board per meta —
reuses the dimir-boards stride's machinery with per-meta fields), (3) the engine's
`whattoplay` best-pick archetype for the local meta, (4) best-pick for online — each generated via
`generate consensus` + `advise sideboard`, with honest positioning caveats (P(best) leans,
coverage%, sample tiers per [[analysis-statistical-context-gates]]). Deliverables: 4
decklists + a compact analysis note in `decks/`.

Does NOT cover: the Doomsday Tempo work (next feature) or cross-deck comparison.

## Epic context

- Parent epic: `epic-deck-prep-arc`
- Position: consumer of dimir-boards (shares its per-meta board tooling and the refreshed
  Dimir reference).

## Inherited design decisions

- Best-pick collision rule: if `whattoplay`'s top pick for a meta IS Dimir Tempo, take the
  top-ranked NON-Dimir archetype for the distinct best-pick list and note the collision
  honestly (the Dimir version already exists as lists 1-2).
- Metas: the local meta = `decks/local-field-since-518.txt`; online = `provenance='online'`,
  current-regime window. Prior best-deck context: D&T topped both lenses on the regime-clean
  local field (2026-06-27 session; re-run, don't assume).

## Design + results (2026-07-04, single-stride)

Executed per the epic's decisions (design folded into the stride — composition of shipped
surfaces; the only design call was the best-pick ranking surface: `advise positioning
--candidates` over each field's archetypes, seed 42, since `whattoplay` is deck-relative).
Best-picks: **Painter** (the local meta, S*=0.528 Q0.25-ranked lean) and **Doomsday** (online,
S*=0.580, cov≈0 caveat) — no Dimir collision, so the collision rule stayed dormant.
Deliverables: decks/meta-{local,online}-{dimir-tempo,bestpick-*}.txt +
decks/meta-decks-analysis.md. Overrides applied mechanically and labeled per file; the
1-of-pitch-counter scorer bias is deliberately left visible in these reference lists (the
personal board hand-corrects it) so the arc's final study can show before/after.
