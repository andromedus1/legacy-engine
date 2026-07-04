---
id: epic-deck-prep-arc-doomsday-tempo
kind: feature
stage: drafting
tags: [advisory, analysis, dogfooding]
parent: epic-deck-prep-arc
depends_on: [epic-deck-prep-arc-meta-decks]
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-04
---

# Doomsday Tempo — consensus subarchetype, same per-meta pattern

## Brief

Doomsday Tempo as the meta/consensus SUBARCHETYPE of Doomsday, contrasted with the
combo/turbo camp. The corpus does NOT label subarchetypes (`decks.variant` is NULL for all
1849 Doomsday decks — verified 2026-07-04), so the first step is mechanical subarchetype
identification: split the current-regime Doomsday pool (58 online + 17 paper decks) by
tempo markers via card co-occurrence (the with-Murktide/Tamiyo camp vs Personal Tutor/One
Ring turbo, per the 2026-06-27 session's camp analysis), label the split's sample sizes
honestly, then run the established pattern on the tempo camp: consensus generation, two
collection boards (A unconstrained/acquisitions, B owned-only), the local meta + online versions.
Prior art: `decks/doomsday-tempo.txt`, `decks/doomsday-tempo-local.txt` + primers. The
old two-mode "transform" build is dead — ignore it entirely.

Relates to [[idea-subarchetype-discovery]] (this stride is a manual instance of it).

## Epic context

- Parent epic: `epic-deck-prep-arc`
- Position: consumer of meta-decks (reuses its per-meta generation+board pipeline).

## Inherited design decisions

- Consensus-based, transform build ignored; compare tempo camp against combo camp within
  the archetype (copy-count histograms + matchup shape where sample permits).
- local paper Doomsday sample will be thin (17 paper regime-wide) — honest-degrade
  labeling required, no fabricated local-field-specific claims.
