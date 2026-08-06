---
id: bug-camp-autoname-picks-shared-not-discriminating-card
created: 2026-08-04
tags: [bug, discovery]
---

`discover run` names camps from their own within-camp signature ranking, so when two
camps share their top signature cards the names carry **zero** information about what
distinguishes them — actively misleading, not just unhelpful.

Live case (2026-08-04, `discover run --archetype Energy`, stability 0.955, all three
camps PASS both gates):

```
camp Sand Scout      n=377  signature: Sand Scout (+2.78), Static Prison (+2.29)
camp Cabal Therapy   n=131  signature: Cabal Therapy (+2.03), Thoughtseize (+1.90), ...
camp Thoughtseize    n=174  signature: Thoughtseize (+3.15), Orcish Bowmasters (+3.07), ...
```

The camps named "Cabal Therapy" and "Thoughtseize" **both run ~3 Cabal Therapy and
3-4 Thoughtseize.** Diffing their average compositions, only four cards differ by even
0.4 copies:

| card | [Cabal Therapy] | [Thoughtseize] | delta |
|---|---|---|---|
| **Hexing Squelcher** | **3.00** | **0.31** | **+2.69** |
| Voice of Victory | 2.95 | 3.88 | −0.93 |
| Orcish Bowmasters | 3.03 | 3.86 | −0.83 |
| Thoughtseize | 3.15 | 3.96 | −0.81 |

The real split is "3 Hexing Squelcher, paid for with −1 Thoughtseize / −1 Bowmasters /
−1 Voice of Victory". These should be named `[Squelcher]` and `[no-Squelcher]`.

Root cause: naming ranks a card by its signature strength *within* the camp
(|deck avg − parent avg|), which is high for any staple the camp runs at 3-4 copies.
It never asks whether the other camps also run it. `bug-discover-camp-name-collision`
(fixed) made names *unique* by walking down the same within-camp list — that fix does
not make them *discriminating*.

Suggested fix: name each camp by the card maximizing |this camp's avg − max(other
camps' avg)| (or the mean of the other camps), i.e. rank on cross-camp separation
rather than parent-deviation. Keep the existing tie-break walk for collisions.

Cost of not fixing: an operator reading `Energy [Cabal Therapy]` vs
`Energy [Thoughtseize]` will conclude the split is about discard configuration and
board/mulligan accordingly, when the actual axis is a 3-of uncounterable-ward creature.
