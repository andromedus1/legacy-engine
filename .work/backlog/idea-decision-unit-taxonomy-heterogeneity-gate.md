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

## Addendum (2026-08-08, same-day discussion)

Andrew's additions after the initial park:

1. **Pilot stickiness is in.** "You play one deck at a time" operationalized literally: for a
   candidate partition, do the same humans pilot both halves? Same pilots floating across →
   one deck with a knob; disjoint pilot populations → two decks. Orthogonal to composition and
   matchup divergence; `player_aliases` / `normalize_player` already exist.

2. **Slot-distance metric as the tunable knob.** Distance between camps = mean difference in
   card count: `0.5 * Σ_c |mean_copies_A(c) − mean_copies_B(c)|` over mainboards = "slots you'd
   swap to move between the two consensus lists." Interpretable units (card slots). Tune the
   threshold for best differentiation — or expose it as a filterable field/knob on the page.
   Statistical form: separation ratio = between-consensus distance / mean within-cohort radius.

Same-day calibration (field window since 2026-06-29, mainboard only):

| pair | between (slots) | separation ratio |
|---|---|---|
| Energy Boros/Mardu (CONFIRMED split) | 18.9 | 2.02 |
| SnT Sneak/non-Sneak (candidate) | 23.5 | 1.95 |
| D&T W/WB (candidate) | 37.9 | 1.80 |
| NULL — random 50/50 of Boros Energy, 20 draws | 4.3 | 0.33 (max 0.57) |
| NULL — random 50/50 of SnT [Sneak], 20 draws | 1.6 | 0.25 (max 0.36) |

Real splits land ~1.8–2.0; the permutation null never exceeded 0.57. Wide gap — the knob's
useful range is inside it, and known-knob pairs (e.g. Bauble/non-Bauble, unavailable in the
current window because camp labels overwrote the curated variants) should pin the lower edge.
Threshold tuning has natural labels: the behavioral gate's FDR-passing verdicts.

Role in the gate: slot distance is the cheap SCREEN (computable for every candidate partition
instantly) and prioritizes/pre-filters what the expensive matchup-vector test runs on — it is
NOT the decision line itself (Energy proved composition alone can't adjudicate; the seam was
invisible to composition clustering while three non-seam camps were visible).

Anomaly worth chasing at validation time: D&T mono-W's internal radius is 30.5 slots (vs 5.7
for Mardu Energy, 6.5 for SnT Sneak) — the mono-W cohort is itself heterogeneous; there may be
a third D&T deck inside it.

## Addendum 2 (2026-08-08): Doomsday sideboard-transform probe — zones are channels

Andrew asked whether the slot metric catches the Doomsday group whose sideboard transforms
into a Dimir Tempo shell, given the swap lives mostly in the 15. Findings (field window):

- **The transform won.** 145/162 window Doomsday decks (90%) carry the tempo board package
  (Barrowgoyf ~3.6 mean copies, Dauthi Voidwalker, Murktide); the 17 residual old-school
  boards (Carpet of Flowers / StP / Surgical) are the minority. The archetype row already IS
  the transform deck.
- **Zone-split ratios, transform vs residual** (matched null: random 17-vs-145, 50 draws,
  p95 0.49, max 0.55 both zones): main-only **0.85**, side-only **1.32**, combined-75 **1.07**.
  The metric catches it ONLY with a per-zone channel — concatenating all 75 slots DILUTES a
  sideboard-resident seam below its side-only reading. Design rule: compute per zone, report
  both, never only the 75-slot concat.
- **Main echo is real but sub-split**: 0.85 beats the null ceiling (fetch mix, Fantasticar /
  Thoughtseize counts co-vary with the board plan) yet sits far below the 1.8–2.0
  different-deck band.
- **Murktide-in-side vs not = knob confirmed**: 0.56/0.71/0.63 across zones, at or near the
  null band. First measured knob anchor for the threshold's lower edge.
- **Interpretation for the gate**: a sideboard transform is a genuinely intermediate object —
  same game-1 deck, different games 2–3 — and lands between the knob band (~0.6) and the
  split band (1.8–2.0). Default verdict: one decision unit (you sleeve one 60), with the
  transform surfaced as a labeled property, unless matchup-vector divergence independently
  clears the gate. Pilot stickiness should also read "same humans" here — worth confirming.
