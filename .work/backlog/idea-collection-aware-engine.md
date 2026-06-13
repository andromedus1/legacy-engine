---
id: idea-collection-aware-engine
created: 2026-06-13
tags: [advisory, generation, ingestion]
---

The engine has **no model of what cards the user owns.** Every recommendation this session
(2026-06-13) had to be reconciled against the player's binder by hand, and the sideboard recommender
repeatedly proposed cards the user doesn't own (Defense Grid, Back to Basics, Chalice of the Void) —
useless as a literal buy/play list.

Build a **collection/binder model**: ingest a collection list (owned card → quantity), and make
`advise` / `generate tune` / `advise sideboard` **collection-aware** — recommend from owned cards, or
cleanly split output into "play these (owned)" vs "acquire these (not owned)".

**Headline consumer — an acquisition advisor.** Given collection + a target field/board(s) (+ a price
source, [[idea-curated-price-source]]), output a **ranked, priced buy list** ordered by impact
(field adoption × archetype relevance), and:
- flag redundant / over-quantity owns (we found the player was deeply over-covered on graveyard hate);
- flag overpriced printings (we caught a $33 Secret Lair Dismember vs $1–2 alternatives by hand);
- show how each buy slots into the board and what it replaces.

This is the foundation under the collection-aware version of [[idea-deck-tuning-refresh-workflow]],
and it's the single most-repeated manual step of the dogfood session — the engine kept recommending
cards that aren't in the binder.
