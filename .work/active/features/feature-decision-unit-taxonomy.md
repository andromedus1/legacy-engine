---
id: feature-decision-unit-taxonomy
kind: feature
stage: drafting
tags: [analytics, advisory]
parent: null
depends_on: [feature-ranking-refresh-insights]
release_binding: null
created: 2026-09-05
updated: 2026-09-05
---

# Check whether ranked archetypes represent pilotable decks

## Brief
Investigate whether pooling materially different builds makes an archetype's matchup floor look safer than its actual camps. Build a repeatable comparison using existing camps and color partitions, main/side composition distance, overlap in pilots, and matchup evidence. Prioritize consequential current-field candidates and display concise linked build context in Deck Rankings. Analyze the real corpus and report which splits merit attention; statistical silence is not proof that builds are interchangeable.

## Outcome boundary
Compute parent-versus-build floor differences on a common opponent field; distinguish lack of evidence from disagreement. Summarize composition and support alongside the largest decision-relevant differences. Avoid automatically changing taxonomy on selected noisy results. Existing user instructions permit investigation and reviewable local improvements; global registry changes need concrete evidence.

## Simplification
Reuse camp rows, staged partitions, and existing taxonomy machinery. Replace the backlog's broad proposed gate with a compact diagnostic that improves the actual deck choice.

## Prior investigation (historical, must recheck current corpus)
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

## Authorized direction
Andrew approved the four-part sequence on 2026-09-05 and asked to execute it: improve historical borrowing and evaluate the exact current model; explain refresh changes concisely; examine pilotable archetype units; apply both independent priorities to custom fields. Keep estimates visible throughout. Existing data integrity and incompatible-era boundaries remain in force. Current report styling and interactions are the approved reference. No new audience, hosted product, or geographic ingestion is in scope.

## Execution
Standard feature review (default): one independent pass followed by verification of accepted fixes. Features run in the approved order. Reuse existing implementation and research before adding abstractions; preserve unrelated Hogaak files and uv.lock changes. Design records concrete interfaces before implementation.

## Design decisions (--only-questions directional pass)
No unresolved direction: examine the actual current corpus, keep both priorities and every camp visible, and do not auto-promote a noisy split. The first pass uses the current staged camps as modeled build partitions; existing curated color-split labels remain distinct archetypes. Summarize color/composition differences within those partitions without claiming a separately fitted matchup profile for an unmodeled color group. Add compact build context inside the existing archetype dropdown and link to its camps, reusing the approved details/table pattern (no new screen or mock required).

## Architectural choice
Options: a fleet-wide hypothesis-test gate that edits taxonomy; an offline prose-only audit; or a repeatable per-parent diagnostic attached to the report. Choose the third: it makes the deck-choice issue visible and provides concrete split candidates while avoiding an automatic taxonomy mutation. The trickiest distinction is genuine averaging uplift versus differences caused by separate priors/era support.

## Implementation units
- `src/legacy_engine/advisory/decision_units.py`: `analyze_decision_units(con, blob, *, since: str, until: str) -> dict`. Read current date-bounded deck/variant assignments, main and side deck-card counts, source-scoped normalized pilot handles using normalize_player, and already computed archetype/camp decisions. Never mutate classifications or era tables. Batch SQL inputs, then pure per-parent comparisons.
- `compare_build_floors(parent, camps, shares) -> dict`: use the same positive-share external-opponent set (exclude the parent on every build for a like-for-like comparison). Compare each camp's minimum, weighted mean of camp minima, minimum of the camp-weighted matchup vector, and the actual parent estimate on that SAME set. `pooling_uplift = min(sum(q_c*p_co)) - sum(q_c*min(p_co))` is nonnegative to tolerance and isolates aggregation; actual parent-minus-camp-floor gap is a separate metric that may also reflect priors or evidence windows. Normalize q over included current camps and expose modeled parent coverage. Missing opponent cells prevent that exact comparison; do not fill them with arbitrary zeros. Show per-build toughest pairing, direct n, current list count, and prior fraction/support alongside gaps.
- For each pair of current camps, report main and side mean slot distance `0.5*sum(abs(mean_copies_A-mean_copies_B))` separately, within-cohort radii, counts of lists with card records, pilot overlap/Jaccard with unknown pilots excluded and denominators named. Never concatenate main+side into the only distance. Priors and small samples can create apparent gaps; order diagnostic attention by current parent field share times positive pooling uplift, while retaining all computed summaries. These are descriptive candidate checks, not significance tests or proof of different decks.
- `scripts/refresh_best_call_ranking.py`: attach compact `decision_units` context to archetype rows and include it in the reading payload. `scripts/best_call_ranking_template.html`: one short parent/build-floor comparison plus a compact per-camp table in existing dropdown; optional detail reveals composition/pilot evidence. Do not add columns to every headline table or suppress parent estimates.
- `scripts/analyze_decision_units.py`: read an existing generated report plus date-bounded DB facts, emit JSON/Markdown audit ordered by decision relevance. Run against current corpus and document top candidates with actual support. Distinguish historical backlog examples from freshly verified observations; no global registry edits without a separately justified exact change.

## Testing and risks
Synthetic crossing matchup profiles establish averaging uplift, common opponent/mirror treatment, and separation from parent-estimator differences. Test missing cell, single camp, zero current support, main-only/side-only differences, missing deck cards, normalized/source-scoped pilot overlap, HTML escaping, and current cutoff isolation. Inspect the real report/browser expansion and actual candidate audit. Existing camp naming quality is separate backlog work; use exact labels rather than renaming by guess. One standard independent feature review follows verified implementation.
