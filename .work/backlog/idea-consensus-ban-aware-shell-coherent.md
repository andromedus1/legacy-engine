---
id: idea-consensus-ban-aware-shell-coherent
created: 2026-07-13
tags: [generate]
---

**`generate consensus` should be ban-aware and shell-coherent.** Two findings from the Mystic
Forge session (2026-07-13):

- `generate consensus --archetype "Mystic Forge Combo" --since 2026-04-20` emitted a 75
  containing banned Candelabra of Tawnos with only a footer `[LEGALITY]` warning. The pool
  should be legality-filtered (or default-clamp to the current ban regime, with the explicit
  window override loudly caveated).
- The post-ban n=5 pool spans three distinct shells (Chalice/City-of-Traitors vs
  Trinisphere/partial-Tron vs white splash) and the modal reconciliation produced a
  Franken-list (4 Chalice AND 4 Trinisphere AND 1 lone Urza's Tower — no real list looks
  like that). Consensus should cluster the pool for shell coherence first and refuse/branch
  when the pool is multimodal. Workaround used: shipped a single winner's exact 75 instead
  (`decks/mystic-forge-combo.txt`).
