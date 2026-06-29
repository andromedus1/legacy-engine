---
id: epic-sb-config-evaluation-config-comparator
kind: feature
stage: drafting
tags: [advisory]
parent: epic-sb-config-evaluation
depends_on: [epic-sb-config-evaluation-matchup-slot-test]
release_binding: null
gate_origin: null
created: 2026-06-29
updated: 2026-06-29
---

# Configuration / transform comparator (general engine, transform-first)

## Brief

A general engine that computes **field-weighted EV for a deck configuration**, with
**per-matchup sideboard-lift adjustments**, and **compares two configurations** against the
field — surfacing a per-matchup contribution diff and a **break-even**. The motivating special
case is a **transform-alternate**: one 75 modeled in two modes (e.g. Doomsday-tempo that
sideboards into Dimir Tempo), scored as `max(mode_A_native, mode_B_with_stripped_SB)` per
matchup, against the alternative of "base deck + a dedicated silver-bullet sideboard."

Generalizes `advisory/positioning.py::score(deck, field)` from one deck to two configs. The
engine is general internally either way — you cannot compute the transform envelope without
computing each config's full per-matchup vector, which *is* the general two-config comparison.

### Delivery sequence (per the epic's strategic decision — design carves child stories)
1. **Transform break-even first** (the validated need, robust to thin data): model the
   transform-alternate, output per-config field EV + per-matchup diff + the break-even — "the
   hate package must lift its target matchups by ≥X points to beat transforming." Break-even is
   the deliverable that stays decision-useful under the data ceiling, because the operator
   supplies confidence in the SB cards from play experience.
2. **General two-config comparison surface second**, exposing the same engine for
   build-A-vs-build-B / pre-tune-vs-post-tune comparisons.

Design the "config" abstraction grounded in **both** uses (transform + build-A-vs-B) so it's
pinned by ≥2 real uses, not one.

## What's new vs reused
- **Reuses** positioning's field-EV / Bayesian-MC machinery (Beta cells + Dirichlet shares).
- **New**: (a) a per-matchup **SB-adjustment layer** that applies measured lifts (consuming the
  `matchup-slot-test` feature where reliable) or operator-supplied assumptions where thin;
  (b) **two-config diff**; (c) **transform-alternate modeling** — `max` per matchup + the
  **stripped-SB** model (mode B plays *without* the silver bullets you spent on the transform
  package, so its bad matchups stay bad); (d) the **break-even solver**.

## Subsumes backlog idea `idea-sb-transformational-sideboarding`

That idea flagged that the sideboard recommender's coverage model is structurally blind to
**transformational sideboarding** — crediting *threats* (e.g. board in Barrowgoyf, dodge
removal, grind better vs control/midrange), not just *answers* to vulnerability tags (it even
mis-tagged Barrowgoyf `combo` via the promoted-card fallback). This feature is where
threat-swap / transform packages become representable and valued: a "config" can be a
threat-swapped or transformed 75, and the comparator scores it on field EV rather than
answer-coverage. Design should connect the transform-alternate model back to
`advisory/sideboard.py`'s OUT/IN plans so a recommended transform reads as a coherent package.

## Known constraint
Honors the parent epic's data ceiling. The break-even framing is the robust deliverable
*because* the underlying SB-lift numbers are presence-correlational proxies on thin samples —
the tool structures the operator's judgment rather than claiming the data decides.

## Reference finding (what the tool should reproduce)
Session hand-calc over the n≥30 local field: Config A (Dimir + hate SB) ≈ 52.7% (the hate SB
added only +0.7 field-EV points — only Toxic Deluge vs D&T moved, and D&T is 5.6% of field);
Config B (Doomsday-transform) ≈ 56.1%. Break-even: the hate package would need to lift each of
D&T/Energy/Artifacts by ~32 points to match transforming; measured best was Toxic Deluge at
+11. The comparator should make this calculation first-class, repeatable, and honest about its
assumptions.
