---
id: idea-color-variant-conditioned-matchup-cells
created: 2026-08-04
tags: [analysis, discovery]
---

Archetype-level matchup cells average across color variants that have genuinely
different matchup profiles, and the hidden spread can be large enough to flip a
boarding or deck-choice decision. Discovery cannot recover the split because it
clusters the flex band, which is blind to color identity when both variants share the
archetype core (see `idea-discovery-color-identity-feature`).

Measured 2026-08-04 on Energy, splitting by presence of red/black cards in the 75 and
tallying `rounds` by hand:

| opponent | Boros (no black) | Mardu (black splash) | archetype-level cell | hidden spread |
|---|---|---|---|---|
| **Show and Tell** | 13-25 n=38 · **34%** | 31-28 n=59 · **53%** | 47.8% shrunk / 46.9% raw n=113 est | **19 pts** |
| Doomsday | 5-10 n=15 · 33% | 13-15 n=28 · 46% | 44.2% / 41.2% n=51 evo | 13 pts |
| Mystic Forge Combo | 1-4 n=5 · 20% | 12-26 n=38 · 32% | — | 12 pts |
| Lands | 7-3 n=10 · 70% | 11-16 n=27 · 41% | 51.1% / 50.0% n=46 evo | 29 pts (reversed) |
| Post | 8-4 n=12 · 67% | 4-8 n=12 · 33% | — | 34 pts (reversed) |
| Dimir Reanimator | 6-3 n=9 · 67% | 18-27 n=45 · 40% | — | 27 pts (reversed) |
| Oops! All Spells | 2-7 n=9 · 22% | 5-21 n=26 · 19% | — | 3 pts |

Two coherent patterns, not noise: the black splash buys the **spell-combo** column
(Show and Tell, Doomsday, Mystic Forge) via discard, and gives back the
**resilient-permanent** column (Lands, Post, Reanimator) where the Boros prison package
(Static Prison, Sand Scout) does work discard cannot. It buys nothing against
graveyard combo — Oops is bad for both, marginally worse for Mardu.

The Show and Tell row is the operational sting: an archetype-level 47.8% reads
"unfavored" and would talk a pilot out of the matchup, when the Mardu configuration is
53% on the better-sampled side of the split. Show and Tell is 10.3% of the Boulder
field.

Shape of the work: the existing `(archetype, variant) x opponent` cell key from
`epic-subarchetype-resolution` is the right mechanism — it just needs a variant source
that is color-derived rather than clustering-derived. Cheapest path is a registered
color-identity variant (`legacy.json` conditions on off-color card presence) rather
than new machinery. Reuse the tier gates unchanged.

Caveat to carry: several Boros-side cells are n<15. The reversed column is directional.
