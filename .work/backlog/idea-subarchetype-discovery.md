---
id: idea-subarchetype-discovery
created: 2026-06-29
tags: [analytics, archetype]
---

Identify **subarchetypes within a main deck archetype** — systematically distinguish
the tempo / combo / control (etc.) variants that all collapse onto a single parent
label today. Likely a whole project unto itself: needs `/research` and `/scout` to do
well.

**Why it matters:** the engine currently carries a flat archetype label per deck.
Subarchetypes that play completely differently get pooled into one matchup row, which
distorts matchup accuracy. Concrete example surfaced during the Doomsday/Dimir
two-mode analysis (2026-06-29): "Doomsday" tempo-combo vs a storm-flavored Doomsday
build are very different decks but share one label; same risk lurks in broad buckets
like Eldrazi, Painter, the *Delver family, and the Midrange labels.

**Existing primitives (not a solution):**
- `report subgroup` — splits an archetype on a single signature card (manual, one axis).
- variant registry (`data/variants/legacy.json`) — hand-authored variant tags.

Neither does data-driven discovery *or* classification of subarchetypes at corpus
scale. The project would likely cover: clustering decklists within a parent label,
naming/validating the resulting clusters, deciding how subarchetypes interact with the
matchup matrix + field composition, and how thin-sample honesty gates apply when a
parent splits into smaller cells.
