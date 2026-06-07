---
id: idea-list-granular-positioning
created: 2026-06-06
tags: [advisory, analytics, spike]
---

**Deferred from `epic-advisory-output-honesty` (2026-06-06) as a research spike** — kept out of that
epic to avoid adding heuristic false-precision to an honesty-focused epic.

Positioning `S` is computed purely from the **archetype** classification, so two different 75s that
classify as the same archetype get an identical S (observed: a grindy Hymn/Strix Dimir Tempo build and
a lean Daze/Nethergoyf build both scored S=0.464). This makes positioning useless for the most common
real question — "is my exact list better-pointed at this field than that other list of the same deck?"

The per-card layer already exists (`report cards` presence-correlational lift) but isn't wired into
positioning. Spike: nudge the per-matchup win-rate by the deck's card composition (presence of
matchup-relevant cards vs the archetype baseline), as a clearly-labeled heuristic overlay on top of
the archetype-level S. Must honor the presence-correlational / not-causal caveat and not present the
overlay as causal precision. Promote to its own epic/feature once the approach is validated. Related
to [[idea-hoser-catalog-expansion]].
