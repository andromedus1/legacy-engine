---
id: idea-pbest-zero-coverage-flag
created: 2026-06-04
tags: [advisory]
---

In positioning --candidates ranking, decks with zero matchup data (cov=0.00) surfaced spuriously high raw P(best) (~0.17) from imputation. The risk-adjusted Q0.25 sort correctly sank them, but the raw P(best) column is a footgun for anyone reading it directly. Suppress or visually flag P(best) (and the wide imputed CIs) when coverage is ~0.
