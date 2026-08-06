---
id: idea-discovery-color-identity-feature
created: 2026-08-04
tags: [discovery, analysis]
---

`discover run` cannot find a camp whose defining axis is **color identity** when both
sides share the parent archetype's core. The flex-band representation excludes the
shared ubiquitous stratum, and the individual off-color cards are too sparse to steer a
TF-IDF/SVD/HDBSCAN embedding.

Live case (2026-08-04). `discover run --archetype Energy` returns three established
camps (Sand Scout 377 / Thoughtseize 174 / Cabal Therapy 131) plus 123 noise decks, and
surfaces **no Orzhov camp** — yet a hand query finds **77 W/B Energy lists**, 35 of them
a coherent Overlord/Solitude/Phelia value camp with its own 84-match record (57.1%) and
a distinct plan (grind/recursion, no Voice of Victory, no Amped Raptor). Those lists
share Guide of Souls / Ocelot Pride / Ajani / Bowmasters / Swords with every Boros and
Mardu list, so clustering either absorbed them into the black-splash camps or dropped
them to noise.

The hand query that finds it (note: `cards.colors` is a VARCHAR, **not** a list, and
there is no `color_identity` column — `list_contains` fails, use LIKE):

```sql
select dc.tournament_id, dc.deck_idx, sum(dc.count) rc
from deck_cards dc join cards c on c.name = dc.name
where c.colors like '%R%' group by 1,2
```

Two candidate shapes:

1. **Cheap:** add per-deck off-color-mass features (count of cards by color pip
   present, normalized) to the embedding alongside the flex-band TF-IDF vector. Colour
   mass is a handful of extra dimensions and would dominate exactly when a colour split
   is real.
2. **Explicit:** a `discover run --split-on-colors` pre-pass that partitions the parent
   by colour identity first, then clusters within each partition. More interpretable,
   and it composes with Gate C.

Either way the downstream consumer already exists — see
`idea-color-variant-conditioned-matchup-cells` for the measured payoff (a 19-point
hidden spread in the Energy-vs-Show-and-Tell cell).

Also worth carrying: the same 77-list cohort demonstrates why **camp recency must be
read alongside camp win rate.** The Orzhov value camp peaked at 13 lists in Dec 2025 and
produced 5 in all of 2026 — its 57.1% is 0% current-regime. An all-time aggregate makes
a dead camp and a live camp look identical. Gate C flags temporal *mixing between*
camps; it does not flag a camp that has simply stopped being played.
