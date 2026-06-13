---
id: idea-deck-tuning-refresh-workflow
created: 2026-06-13
tags: [advisory, generation, workflow]
---

Build a **deck-tuning refresh workflow**: one command/run that pulls current data and emits a
ready-to-play tuning package for attacking the current meta. For a given archetype it should produce:

1. **Recommended maindeck** (field-tuned, current-regime-aware).
2. **Recommended sideboard** (15, field-tuned).
3. **A concise plain-speak primer** explaining how the sideboard attacks each meaningful opponent —
   in readable prose, not a stat dump — **including the exact OUT/IN swaps** for each matchup.

Crucially, produce this main+sideboard+primer **for each meaningful split of the data.** Today the
splits we've identified are **online vs paper**; the future target is **online / paper / local
(Boulder, CO) / big tournament**. The workflow should iterate the same recipe per split and label
each output by venue.

Constraints / context (from the 2026-06-13 dogfood session that motivated this):
- Must be **ban-regime-correct** by default (current regime field + adaptive matchup windows) — see
  [[idea-ban-regime-everywhere]]. Loudly state the window + thinness.
- The per-split fields are exactly the three-venue frame in [[idea-three-venue-meta-frame]]; local
  and big-tournament splits depend on `epic-local-meta-support` geo + event-tier dimensions, so the
  workflow ships online/paper first and expands as those land.
- The plain-speak primer is the new deliverable beyond what exists: `advise sideboard` already emits
  OUT/IN plans, but they're terse, presence-correlational, and per-card-noisy in thin regimes. This
  wants a synthesized, human-readable "here's how you beat X, and here's what comes in/out" writeup.
- Manual workflow done by hand this session: build per-venue `--field` files from `report meta`,
  run `advise`/`generate tune`/`advise sideboard` per field, then map recommendations to the
  player's actual collection and write the primer. Automating + collection-awareness is the ask.
- Could be a natural first consumer of the [[idea-web-interface]] surface (per-venue tuning pages).
