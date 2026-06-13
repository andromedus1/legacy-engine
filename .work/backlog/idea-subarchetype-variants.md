---
id: idea-subarchetype-variants
created: 2026-06-04
tags: [archetype]
---

Archetype labels collapse meaningful sub-variants: "Smallpox" lumped Loam Pox and non-Loam Pox together (57%/43% split — strategically distinct, and exactly what a user asked about). Add sub-archetype resolution (variant tags by signature cards, e.g. Loam vs non-Loam) so meta/overlap/matchup queries can distinguish builds within a parent archetype.

**Worked method (validated 2026-06-13):** cluster an archetype's decks by presence of a signature
card, then diff the two subgroups' *average* compositions to expose the variant. Splitting Dimir Tempo
on Mishra's Bauble revealed a coherent variant, not a one-card swap: Bauble decks ran +2.43 Nethergoyf,
+0.52 Daze, and −1.06 maindeck Barrowgoyf vs non-Bauble decks (and more fetchlands, for delirium/delve
fuel). That "diff the subgroup averages" output is exactly the analysis a sub-archetype feature should
produce automatically. Pairs with [[idea-card-count-outlier-advisor]] (compare counts within the right
variant, not the whole parent).
