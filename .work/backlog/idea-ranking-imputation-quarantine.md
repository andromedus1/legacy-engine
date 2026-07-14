---
id: idea-ranking-imputation-quarantine
created: 2026-07-13
tags: [advisory]
---

**Ranking surfaces need an imputation quarantine.** `rank_decks`' headline Q25 sort put Mystic
Forge Combo #1 overall (S=0.83 at min_row_share default / 0.68 at 0.003, P(best)=0.85) with
`data_coverage=0.00` — pure marginal-winrate imputation, zero measured cells vs the current
field. The CLI suppresses P(best) below 5% coverage but S itself carries the same noise. Any
ranking surface (`advise positioning --candidates-file`, future reports) should split measured
vs imputation-only rows (the hand-built `decks/best-deck-best-call-ranking.html` from the
2026-07-13 session did this manually), and surface n<30 thin cells as labeled leans instead of
hiding them entirely — at camp level only 4 of 92 camps have any display-grade cell vs the
young post-ban field, so thin-cell leans are most of the available signal.
