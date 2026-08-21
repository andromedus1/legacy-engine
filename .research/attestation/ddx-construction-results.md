---
source_handle: ddx-construction-results
fetched: 2026-08-20
source_path: .research/analysis/campaigns/doomsday-variant-experiments/experiments/construction/results.json
provenance: source-direct
substrate_confidence: source-direct
---

# Deterministic construction experiment results

The generated result contains composition metrics and exact unordered seven-card-hand
probabilities for all 14 canonical registered candidates.

## Key passages

1. **Method and boundary.** The script parsed each registered path, required exactly 60 maindeck and 15 sideboard cards,
  recomputed its canonical hash, and required legality under both the pinned 2026-08-10 snapshot
  and the repository's current snapshot. Every candidate passed all four checks. Hand probabilities
  use exact multivariate hypergeometric enumeration with no random seed. The model explicitly
  excludes mulligans, sequencing, mana-spending order, Doomsday piles,
  opponent interaction, matchups, and win-rate inference.
  Access means copies of Doomsday plus Personal Tutor. Selection, protection, interaction,
  value/tempo, and sideboard-pivot groups are analyst-composed card-name roles and not claims that
  each card is equivalent within a group.
  Colored-source counts include unrestricted direct land sources and fetchlands that can find a
  typed land producing that color. Lotus Petal is excluded from the land-source count and included
  only in the compound access-plus-black-or-Petal opening event.

2. **Principal-arm comparison.** Personal Tutor turbo has 16 lands, seven access cards, 13 selection cards, 12 protection cards,
  and a 53.906% exact opening probability of access plus a black land source or Lotus Petal.
  Current Dimir has 17 lands, six access, 14 selection, 11 protection, and a 49.320% probability
  of that same compound opening event.
  Current Esper has four access, 13 selection, eight protection, ten maindeck value/tempo cards,
  and a 34.855% compound access-plus-black-or-Petal probability.
  Light green-white has five access, 15 selection, ten protection, and 13 black, ten white, and
  nine green fetch-enabled land sources; its compound probability is 41.516%.
  Four-color shield has four access, ten selection, 14 protection, and 12 black, ten white, and
  ten green fetch-enabled land sources; its compound probability is 34.855%.
  The inferred BUG construction has seven access, 13 selection, ten protection, and a 53.906%
  compound probability. Its reconstruction status remains load-bearing.
  Historical Grixis has four access, 15 selection, 12 protection, ten fetch-enabled red land
  sources, and a 35.589% compound probability.
  Wasteland/Murktide has 19 lands, seven acceleration cards, four access, 13 selection, eight
  protection, ten maindeck value/tempo cards, and a 34.855% compound probability. Its chance of
  at least two lands is 72.058%, compared with 60.833–64.821% for the principal non-Wasteland arms.

3. **Alternate branches.** The inferred Moonshadow construction has eight access cards and the highest compound
  access-plus-black-or-Petal probability in the registry, 59.767%; it is not an observed 75.
  The inferred Cori-Steel Cutter construction has 17 selection cards and ten sideboard-pivot
  cards; it is not an observed 75.
  Paradigm Shift has seven cards in the alternate-combo sideboard role. Chancellor has nine cards
  in the sideboard-pivot role. The historical value-threat list has eight.
  These role counts measure registered capacity and possible displacement, not a boarding recipe,
  card quality, or post-board win rate.

## Revisions

- 2026-08-20: Grouped method, principal-arm, and alternate-branch specifics into stable numbered
  passages after the full-rigor adversarial review found that cited ordinals were absent.
