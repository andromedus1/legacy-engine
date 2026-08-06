---
id: feature-camp-floor-observability-banner
created: 2026-08-04
tags: [analysis, honesty, discovery]
---

When a camp's marginal win rate is displayed, also state **how many of its matchup
cells are actually observable**, because a small camp's apparent lack of bad matchups
is a sample artifact that reads as a strength.

This is the presentational cousin of the already-recorded shrinkage-floor mirage: that
one is about not trusting a *shrunk floor*; this one is about a floor that is not
present at all.

Live misread (2026-08-04). `Energy [Cabal Therapy]` posts 60.1% (raw 101-67, n=168,
established marginal) and the operator concluded "it doesn't seem to have any
weaknesses." Cell census:

| cohort | matches | cells n>=30 | cells n>=10 | cells n<10 |
|---|---|---|---|---|
| Energy [Cabal Therapy] | 168 | **0** | 3 | 46 of 49 opponents |
| Energy [Sand Scout] | 272 | 0 | 9 | 50 of 59 |
| Mardu cohort (color-filtered) | 965 | 9 | 17 | 84 of 110 |

The camp's only three n>=10 cells are Dimir Tempo / Show and Tell / Izzet Delver —
matchups this family is known-good at. Give the same deck family 6x the data and seven
cells appear below 42% (Oops! All Spells 19.2% n=26, Mystic Forge Combo 31.6% n=38,
Red Stompy 39.4% n=33, Dimir Reanimator 40.0% n=45, Lands 40.7% n=27, Tron 33.3% n=12,
Post 33.3% n=12). The camp is not cleaner; it is smaller.

Proposed output, wherever a camp/entity marginal is printed (`report matchups
--split-variant`, camp rows in the ranking page, `discover run` per-camp lines):

```
// cell observability: 0/49 opponents at n>=30, 3/49 at n>=10 —
// this camp's matchup FLOOR IS UNOBSERVED; absence of bad cells is not evidence of none
```

Plus a derived scalar worth having: **observed-floor confidence** = share of the
weighted field sitting on cells this entity has n>=30 for. Ties naturally into the
existing positioning coverage number.

Related: `idea-hierarchical-cell-shrinkage`, the triple-display rule, and
`bug-camp-autoname-picks-shared-not-discriminating-card` (same discovery surface).
