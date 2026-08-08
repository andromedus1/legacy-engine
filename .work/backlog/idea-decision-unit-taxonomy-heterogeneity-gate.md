---
id: idea-decision-unit-taxonomy-heterogeneity-gate
created: 2026-08-08
updated: 2026-08-08
tags: []
---

# Decision-unit taxonomy: systematic heterogeneity gate over archetype labels

## Motivation

The Energy colour split (PR #87) proved a pooled label can blend two decks with contrasting
matchup profiles. The bias is structural, not incidental: a pooled matchup cell is a
share-weighted average of the branch cells, so blending systematically **overstates agency**
(the floor of an average sits above the average of floors) and **undercounts blowout
exposure** — Boros Energy's 30.8% raw vs Show and Tell was hidden inside a pooled ~48% cell
by Mardu's 59.4%.

Andrew's framing: **you can only play one deck at a time** — the taxonomy unit must be a
pilotable decision, or a whattoplay read on a blended label is a read on nothing.

## Evidence beyond Energy (2026-08-08 probes, field window since 2026-06-29)

Color-identity scan (mainboard nonland cast colors, archetypes n>=40, 2nd identity >=15%):
- **Death & Taxes**: WB 45% / W 41% — classic mono-W vs black-Overlord builds
- **Blue Artifacts**: UR 60% / U 29%
- **Tron**: U 54% / UB 32% / C 12%
- **Show and Tell**: WUBRG 75% / WUBG 22% (= Sneak vs no-Sneak red)

Camp-divergence sweep over the ranking page blob's already-computed camp rows (sibling camps
of one parent, measured-vs-measured on shared opponents, both n>=15):
- **Show and Tell** [Sneak Attack] 27% vs [non-Sneak Attack] 44% against Dimir Tempo
  (Δ17pp, n=28/93 — against the biggest field deck)
- **Dimir Tempo** [Flow State] 77% vs [non-Bauble] 55% vs Show and Tell (Δ22pp, n=37/65)
- **Painter** [Mountain] 52% vs [unlabeled] 35% vs Red Stompy (Δ17pp)

**Caveat**: these are max-gaps cherry-picked across many camp-pair×opponent comparisons at
n=15-30 — some are noise. The layer needs a real test, never eyeballed max-gaps.

## Proposed shape (raw notes, not a decomposition)

1. Per archetype above a field-share floor, enumerate candidate partitions — color axes
   (the Energy-style bimodality test) AND staged discovery camps.
2. Test matchup-**vector** divergence across the partition (chi2 or two-proportion per
   shared opponent with the page's n gate), with Benjamini-Hochberg FDR across the whole
   sweep — mirroring the eras ensemble's discipline.
3. Gate on the split cost: both branches must clear a size floor so the grounding loss is
   bounded (Energy's branches fell to 76/79% coverage vs the 80% bar — acceptable; splitting
   a 1.5% archetype is not).
4. Remedy depends on axis:
   - color-axis divergence → colour-split registry entry
     (`src/legacy_engine/data/color_splits/legacy.json`, archetype-level, opponent-side visible)
   - composition-axis divergence → **open design question**, since camps are subject-side
     only. Options: a card-condition analog of the colour-split registry
     ("composition-split registry"), or promoting the camp into the curated variant taxonomy.
     Neither exists today.
5. Surface as a gate/report emitting split candidates for operator confirm, never
   auto-applied — same human-confirm-hook discipline as `discover promote`.

## Top candidates to validate first

- Show and Tell Sneak/non-Sneak (composition axis)
- Death & Taxes W/WB (color axis)
