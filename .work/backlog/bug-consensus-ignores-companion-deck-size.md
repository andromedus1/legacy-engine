---
id: bug-consensus-ignores-companion-deck-size
created: 2026-08-04
tags: [bug, generation, advisory]
---

`generate consensus` and the sideboard impact model both hardcode a 60-card maindeck
and produce wrong output for companion (80-card) archetypes. **Death & Taxes is
currently such an archetype: 100% of top-finishing current-regime lists are 80 cards
with Yorion, Sky Nomad as companion.**

Reproduce:

```
legacy-engine generate consensus --archetype "Death & Taxes"
# ...
# 1 Yorion, Sky Nomad          <- in the emitted sideboard
# // Maindeck: 60  Sideboard: 15
# // Legality: OK
```

The emitted list is self-contradictory and the legality banner is wrong. Yorion's
companion clause is "Your starting deck contains at least twenty cards more than the
minimum deck size" — a 60-card main with Yorion in the board has no companion, so the
generated deck is not the deck the archetype plays.

Two code sites, neither ever overridden by a caller:

- `src/legacy_engine/generation/consensus.py:370` — `main_size: int = 60`; filled at
  `:468` / `:481-482`. Nothing in the tree passes `main_size`.
- `src/legacy_engine/advisory/impact.py:392` — `deck_size: int = 60` in the
  hypergeometric draw-probability factor. Nothing in `advisory/` passes `deck_size`.
  Every sideboard-scoring draw-probability term for an 80-card deck is inflated
  (a 4-of is seen ~34% of the time in 7 cards at 60 cards vs ~27% at 80).

Suggested fix shape:

1. Derive the archetype's modal maindeck size from the pool instead of assuming 60
   (the corpus already stores exact counts in `deck_cards`), and thread it into
   `main_size` and `deck_size`.
2. Add a companion-coherence check to the legality banner: if the emitted sideboard
   contains a card with a companion clause, assert the maindeck satisfies it, else
   emit an honest-degrade line rather than "Legality: OK".
3. Cheap interim guard: a test that `generate consensus --archetype "Death & Taxes"`
   never emits Yorion alongside a 60-card main.

Discovered 2026-08-04 while building `decks/death-and-taxes-yorion-overlord-moxfield.txt`
by hand from the modal current-regime list, because consensus output was unusable.
Relates to `bug-sb-combined-fourof-guard` (the other consensus/legality correctness item).
