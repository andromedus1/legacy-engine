---
id: epic-sideboard-core-and-hedge
kind: epic
stage: drafting
tags: [advisory, sideboard, needs-brief]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-15
updated: 2026-06-15
---

# Sideboard solver: two-stage core + hedge

## Brief

The sideboard recommender (`advise sideboard` / `recommend_sideboard`) maximizes
`Σ field_share × swing` as **weighted max-coverage with a hard, must-fill 15-card budget**.
A dogfooding test-drive surfaced that it pads the budget with redundant copies — it recommended
**4 Hydroblast / 4 Damping Sphere / 4 Harbinger of the Seas**, quantities no real sideboard runs.

Demonstrated empirically against the Boulder field: cutting the recommendation from **15→8 cards
loses only ~7% of covered weight** (0.444 → 0.413), and covered weight ~0.44 means **>55% of the
field is uncovered even at the full 15**. So the last ~7 cards are near-pure padding, and the slots
a human reserves for flexibility are instead spent on redundancy.

Two root causes:
1. **Value is linear-in-copies** — copy #4 of a hoser is modeled as worth exactly copy #1. False:
   you draw/side-in only a handful, so marginal value of extra copies should be steeply concave.
2. **The budget is forced full** — "cover as much as possible with *exactly* 15" is the wrong
   problem. A real sideboard is "bring the answers you'll actually side in; leftover slots are
   *deliberately* flexible." With no concept of a flex slot, the solver pads.

This epic reworks the solver into a two-stage **core + hedge** architecture and changes the output
contract to be honest about how many cards the field actually justifies.

## Strategic decisions
- **Whose job is hedging — model or operator?**: Primarily the operator's, but the model MAY hedge
  — confined to the flex slots. — keeps the engine advisory/honest (the operator holds the local-meta
  read the model can't), while still letting the model insure the region of least conviction.
- **May the recommendation return fewer than 15 cards?**: Yes. — this is the conceptual crux: it lets
  the dedicated core (concave coverage) and the hedge (robustness over field uncertainty) coexist
  instead of one padding over the other. Output labels each card commit (core) vs insurance (hedge).
- **Gating**: opt-in flag first (gated-additive — byte-identical to today until opted in), then flip
  the default once trusted. — see [[gated-additive-augmentation]].
- **Foundation roll-forward — DEFERRED to epic-design**: this epic is `[needs-brief]`; the
  access-probability and field-robustness models are unresolved, so rolling SPEC/ARCHITECTURE forward
  now would document intent the brief may reshape. Current docs are still true (they describe today's
  set-cover solver). `/epic-design` rolls them forward once the brief lands (rolling-foundation: docs
  describe present intent, not planned phases). Anticipated foundation impact, for epic-design:
  - SPEC §"Built capability set" / "Sideboard recommender": the "weighted set-cover over the expected
    field" framing becomes two-stage core+hedge; the `SideboardPackage` entity ("a recommended 15")
    becomes "up to 15".
  - SPEC/ARCHITECTURE HONEST-DEGRADE NFR: add the new honest shape — returning fewer than 15 with a
    named reason + commit/insurance labels + the marginal-coverage curve (this is honest-degrade
    applied to SB construction; see [[honest-degrade-marker]]).

## Architecture (agreed shape)

### Stage 1 — Dedicated core (optimize against the confident read)
Diminishing-returns coverage against the point-estimate field. Add `(card, copy)` increments while
marginal **access-value** clears a floor `τ`; stop at the "natural budget" (~6–8 cards). The value of
`k` copies of card `C` against element `e` is `share(e) × swing(C,e) × P(access ≥1 | k copies)`, where
`P(access)` is a concave draw/side-in probability that saturates ~2–3 copies. This makes extra copies
correctly cheap and **naturally diversifies** (once a card's copies hit diminishing returns, the next
slot goes to a card covering a new element). Sum of concave coverage functions is **submodular**, so
the existing greedy solver keeps its 1−1/e guarantee and the ILP stays LP-representable via
piecewise-linear concavity — low blast radius on [[objective-search-split]].

### Stage 2 — Hedge (optimize against uncertainty)
Leftover slots up to 15 are NOT padded. They fill against **robustness over a wider/uncertain field**
— sample field shares from their confidence bands and/or blend the local read toward the global field
— with a strong **1-of diversity preference** (insurance wants breadth, not depth). This is where the
model hedges, confined to the region the operator is least sure about. Reuses the Monte-Carlo
field-uncertainty machinery `positioning.py` already has (Dirichlet shares).

### Output contract (honest-degrade aligned)
Return fewer than 15 when justified; label each card **commit** (core) vs **insurance** (hedge);
surface the **marginal-coverage curve** (budget→coverage), the **"natural" dedicated count**, and the
**uncovered-field tail with sizes** (so flex slots are spent deliberately). The existing per-matchup
OUT/IN plan + "Considering" flex pool stay.

## Deferred design decisions (WHY this carries [needs-brief])
Resolve in `/research-pipeline:brief` (sideboard-construction theory + the two models) before design:
1. **Access-probability curve** — principled hypergeometric draw model (P(see ≥1 of k by some turn /
   side-in count) vs a simpler tunable saturation; its calibration (the cards-seen / side-in-count
   assumption). Project ethos favors principled + calibrated.
2. **Hedge field distribution** — sampled-from-confidence-bands vs local→global blend, and how wide.
   This is the dial for how aggressively the model hedges (bounded per the strategic decision above).
3. **Core/hedge boundary `τ`** — confidence-tier-linked vs swing-floor vs operator-tunable default.
4. **Gating / controls** — the opt-in flag, plus operator dials (total budget cap, core/hedge split,
   hedge on/off, risk appetite).

## Relevant code
- `src/legacy_engine/advisory/sideboard.py` — `recommend_sideboard` (weighted max-coverage ILP +
  greedy), `_build_coverage_model`, swing constants `_SWING_DEDICATED`/`_SWING_SOFT`, the per-matchup
  plan + "Considering" flex pool already in the output; the empirical presence-correlational swing
  proxy and `card_swing_overrides`.
- `src/legacy_engine/advisory/field.py` — `FieldDistribution` (+ Dirichlet counts) for the hedge's
  field distribution.
- `src/legacy_engine/advisory/positioning.py` — Monte-Carlo Dirichlet-share machinery to reuse for
  Stage-2 robustness.
- Patterns: [[honest-degrade-marker]], [[gated-additive-augmentation]], [[objective-search-split]],
  [[confidence-metadata]].

## Anticipated child features
(provisional — real decomposition after the brief + `/epic-design`)
- Access-probability concavity term + Stage-1 dedicated-core solver (natural-budget stop at `τ`).
- Stage-2 hedge allocator (robustness over a sampled/blended field, diversity-preferring).
- Output-contract rework: <15 return, commit/insurance labels, marginal-coverage curve, uncovered tail.
- Operator controls + flag gating; flip default once trusted.

## Provenance
Surfaced during a dogfooding test-drive of `advise sideboard` for Dimir Tempo vs the Boulder
big-mana meta (2026-06-15). The padding finding and the budget→coverage curve (15/11/8/6 →
0.444/0.434/0.413/0.385) are the empirical motivation.
