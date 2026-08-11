---
id: idea-missing-goblin-card-metadata
created: 2026-08-11
updated: 2026-08-11
tags: [ingestion, cards, benchmark]
---

The current repository corpus contains 615 pre-2024-12-16 `deck_cards` rows, affecting 615
distinct decks, for `_____ Goblin` without a matching `cards` dimension row. This blocks the
cutoff-safe retrospective benchmark snapshot from replaying pinned parent rules: the snapshot
correctly fails closure with `snapshot has 615 deck-card rows without observed card metadata`.

Observed while running protocol `best-deck-decision-trust-current-corpus-v1`, protocol/artifact hash
`6416fe6141d3f572c5c8f68a52021147a63639a6e2b2eba3482c2a1d0a2ac561`, under
`data/benchmarks/best-deck-decision-trust-current-corpus-v1/`. Repair must preserve raw/provider
authority and exact card identity; do not invent placeholder metadata, weaken snapshot closure, or
mutate the locked source DB/protocol as part of the decision-trust epic.
