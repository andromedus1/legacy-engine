---
id: idea-archetype-empirical-recommendations
created: 2026-06-13
tags: [advisory, generation]
---

The sideboard / coverage recommender draws cards from a **global card universe** via a heuristic
coverage solver, and this session (2026-06-13) it repeatedly proposed cards that were both not-owned
**and anti-synergistic with the archetype**:
- **Chalice of the Void** into a deck full of 1-mana spells (Brainstorm/Ponder/Push/Daze);
- **Back to Basics** into a nonbasic-heavy Underground Sea manabase;
- **Defense Grid** into a reactive deck that wants to counter on the opponent's turn.

The *actual winning archetype lists* (the empirical in-regime card pool) were a far better guide — zero
current Dimir Tempo lists run any of those three. The lesson: **data beats the global heuristic.**

Build: ground recommendations in **what real archetype lists in-regime actually run** (an empirical
per-archetype card pool with adoption rates), or add an **archetype-fit / anti-synergy filter** to the
coverage solver so it stops proposing cards the deck would never play. Relies on
[[idea-oracle-text-grounded-reasoning]] for synergy/anti-synergy facts (e.g. "deck runs N one-drops →
Chalice is anti-synergistic"), complements [[idea-strong-player-signal]] (weight the empirical pool
toward strong players), and feeds [[idea-collection-aware-engine]] (recommend owned + archetype-fit +
field-relevant, in that priority).
