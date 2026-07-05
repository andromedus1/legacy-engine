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

**Concrete validated split found (2026-07-05, best-call/best-deck analysis):** Doomsday.
The Legacy rule labels any maindeck-Doomsday deck "Doomsday" (one-card rule). All 1,170
corpus decks since 2024-12-16 share the combo core (Dark Ritual/Thassa's Oracle 100%,
LED 97%, Daze 98%) — but `report subgroup --archetype Doomsday --signature "Murktide
Regent"` shows a clean 292/878 split (both established tier): the Murktide subgroup
runs Tamiyo +2.7 avg copies, Wasteland +2.1, Bowmasters +1.0 (tempo/mana-denial plan B)
while cutting Personal Tutor -1.8, Lotus Petal -1.4, Cabal Ritual -0.7 (all-in mana).
Upstream "Tempo"/"Turbo" name-tags corroborate (Murktide in 85% of Tempo-tagged, 0% of
Turbo-tagged), but only 8% of decks carry tags — signature-card split is the reliable
classifier. First slice when scoped: register Murktide/non-Murktide under parent
Doomsday in the variant registry, then wire variant-aware matchup rows — note
`analytics/match_results.py` keys on `decks.archetype` only today, so registry entries
alone don't split the matrix. Relevant to Andrew's Doomsday-Tempo brew: the corpus
confirms a tempo-pivot Doomsday exists at scale (~25% of the archetype).
