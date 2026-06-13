---
id: feature-personal-inventory-and-decks
kind: feature
stage: drafting
tags: [ingestion, data-model, advisory, foundation, hold-for-review]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

The engine needs **persistent storage for the user's own card inventory**, plus a way to **identify
which deck each card belongs to** — where "deck" means *the user's specific variation*, not just an
archetype label the engine infers from tournament data.

Two coupled needs:

1. **Persistent inventory.** A durable, stateful store of owned cards → quantities (and ideally
   printing/condition, given the $33-vs-$2 Dismember lesson). This session the "collection" was pasted
   into chat and re-reconciled by hand every time; it should live in the engine and persist across
   sessions. This is the storage layer beneath [[idea-collection-aware-engine]] (which assumed a
   collection could merely be passed in).

2. **Cards ↔ decks membership.** Model the user's **own decks as first-class persistent entities** —
   "my Dimir Tempo" with my exact 60 + my 15(s) — distinct from the engine's archetype classification.
   Track which physical copies are allocated to which deck vs free in the binder. This unlocks:
   - "Can I build deck X entirely from my collection?" (we checked this by hand repeatedly);
   - "What's free for the sideboard if I move these 2 Barrowgoyf to the board?";
   - registering/loading "my deck" instead of passing `/tmp/*.txt` files into every command;
   - tracking a deck's evolution over time (versions/variants), and supporting multiple decks that
     may share/contend for the same physical cards.

Note the distinction the user drew: a "deck" is *the user's variation* (their precise 75 and its
history), which the engine should store and version — separate from the archetype label
([[idea-subarchetype-variants]] is about engine-side variant detection; this is user-side deck
ownership). Foundational for [[idea-deck-tuning-refresh-workflow]] and the acquisition advisor, and a
likely first home for the [[idea-web-interface]] surface (manage inventory + decks in a UI). Has
foundation-doc impact (new persistent entities: Inventory, Deck) — route through scope/epic-design.
