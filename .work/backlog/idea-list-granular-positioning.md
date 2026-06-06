---
id: idea-list-granular-positioning
created: 2026-06-06
tags: [advisory, analytics]
---

Positioning `S` is computed purely from the **archetype** classification, so two different 75s that classify as the same archetype get an identical S (observed: a grindy Hymn/Strix Dimir Tempo build and a lean Daze/Nethergoyf build both scored S=0.464). This makes positioning useless for the most common real question — "is my exact list better-pointed at this field than that other list of the same deck?"

The per-card layer already exists (`report cards` presence-correlational lift) but isn't wired into positioning. Explore a list-aware adjustment: nudge the per-matchup win-rate by the deck's card composition (e.g. presence of matchup-relevant cards vs the archetype baseline), even as a clearly-labeled heuristic overlay on top of the archetype-level S. Surfaced dogfooding a list-vs-list comparison where the engine could rank the meta but not the two candidate builds. Honor the presence-correlational / not-causal caveat. Related to [[idea-hoser-catalog-expansion]].
