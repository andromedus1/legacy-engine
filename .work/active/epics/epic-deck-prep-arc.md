---
id: epic-deck-prep-arc
kind: epic
stage: implementing
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

## Design decisions (epic-design, 2026-07-04, autopilot)

- **"Online meta" definition**: `tournaments.provenance = 'online'` over the current-regime
  window (corpus vocabulary is online/paper, verified; 58 online Doomsday regime decks).
- **Best-pick collision rule**: if `whattoplay`'s top pick for a meta is Dimir Tempo, the
  best-pick list uses the top NON-Dimir archetype, with the collision noted honestly.
- **Doomsday subarchetype reality check** (verified 2026-07-04): `decks.variant` is NULL
  for all 1849 Doomsday decks — the corpus does NOT label subarchetypes. Stage 3 therefore
  identifies the tempo camp mechanically (co-occurrence split on tempo markers — the
  with-Murktide/Tamiyo camp vs Personal Tutor/One Ring turbo) with honest split sample
  sizes. A manual instance of [[idea-subarchetype-discovery]].
- **Board B mechanism**: use the collection-aware engine surface; if no hard owned-only
  solver mode exists, restrict the candidate pool to owned cards and label the constraint
  (feature-design call).
- Cross-model advisory pass skipped: strategic direction fully pinned by Andrew's
  only-questions answers; the epic is analysis-stride composition of shipped tools.

## Decomposition

Split by deliverable stride, serial chain (each stage consumes the previous stage's
outputs and tooling; no parallelism intended — this is a dogfooding narrative arc, and
the deliverables build on each other).

### Child features

- `epic-deck-prep-arc-dimir-boards` — Dimir Tempo SB refresh, Boards A/B — depends on: `[]`
- `epic-deck-prep-arc-meta-decks` — 4 lists: Dimir + whattoplay best-pick × Boulder/online — depends on: `[dimir-boards]`
- `epic-deck-prep-arc-doomsday-tempo` — consensus Doomsday Tempo subarchetype, same pattern — depends on: `[meta-decks]`
- `epic-deck-prep-arc-comparison` — Dimir vs Doomsday Tempo across both metas — depends on: `[dimir-boards, doomsday-tempo]`
- `epic-deck-prep-arc-loop-reflection` — codify the loop + simulation-feed pattern — depends on: `[comparison]`

### Decomposition risks

- **Doomsday tempo-camp split may be thin or ambiguous** (17 paper regime decks total;
  co-occurrence split shrinks it further) — honest-degrade labeling is mandatory; if the
  split is speculative-tier everywhere, say so rather than fabricating a "Boulder Doomsday
  Tempo meta".
- **Board B may be over-constrained** (owned pool could lack whole answer classes) — the
  A-vs-B delta is itself a deliverable (what the collection is missing), not a failure.
- **whattoplay best-pick is a lean, not a verdict** (P(best) has been ≤12.6% historically)
  — present per [[analysis-statistical-context-gates]].
