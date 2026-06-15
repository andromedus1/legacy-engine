---
id: epic-sideboard-core-and-hedge
kind: epic
stage: done
tags: [advisory, sideboard]
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

Demonstrated empirically against the local field: cutting the recommendation from **15→8 cards
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
- **Foundation roll-forward — DONE at epic-design (2026-06-15)**: brief landed, decisions resolved,
  so the SPEC/NFR intent was rolled forward: SPEC "Sideboard recommender" capability → two-stage
  core+hedge / up-to-15; `SideboardPackage` entity → "up to 15" + commit/insurance labels +
  marginal-coverage curve; SPEC HONEST-DEGRADE NFR decision + ARCHITECTURE HONEST-DEGRADE POLICY →
  added the SB returns-fewer-than-15 shape. **Deferred to implementation:** the ARCHITECTURE
  `sideboard.py` module row (line ~185) still accurately describes the current max-coverage module;
  it updates when the code lands (rolling-foundation: a concrete architecture row matches code, so it
  rolls at build time, not design time — unlike the capability spec/NFR which lead).

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

## Decomposition

Split by capability into a sequential core path plus a separable hedge fast-follow. Decision (scope +
brief): **core-first** — the dedicated-core fix alone ends the padding bug, so v1 ships the proven
core path and the model-hedging (the speculative part) lands as a clearly-separable second wave. The
chain is mostly linear because a solver rework genuinely builds on itself (value model → core solver
→ output contract → gating); see Decomposition risks.

### Child features

- `epic-sideboard-core-and-hedge-concave-value` — concave per-copy value model (`share·swing·ΔP_access·U_redundancy`; the brief's correction that `U_redundancy` — not access prob — is the saturation driver); submodularity preserved — depends on: `[]`
- `epic-sideboard-core-and-hedge-dedicated-core` — Stage-1 dedicated-core solver + natural-budget τ stop (tier-aware default, tunable); may return <15 — depends on: `[concave-value]`
- `epic-sideboard-core-and-hedge-output-contract` — <15 return, commit/insurance labels, marginal-coverage curve, uncovered-field tail; `SideboardPackage` shape + renderer — depends on: `[dedicated-core]`
- `epic-sideboard-core-and-hedge-gating` — opt-in flag (gated-additive, byte-identical until opted in) + core dials (τ, budget cap); flip default once trusted — closes the v1 core wave — depends on: `[dedicated-core, output-contract]`
- `epic-sideboard-core-and-hedge-hedge-allocator` — **FAST-FOLLOW** (tagged `fast-follow`): Stage-2 hedge over a wider field (Dirichlet ambiguity set / local→global blend; expected vs CVaR-α dial; diversity-preferring); adds the insurance label. Separable from v1; carries the epic's most open design judgment — depends on: `[dedicated-core, output-contract]`

### Decomposition risks
- **Mostly-linear critical path.** v1 is concave-value → dedicated-core → output-contract → gating, which limits parallelism. This is inherent to a solver rework (each stage consumes the prior's output), not a slicing error — accepted. The hedge-allocator parallelizes against gating once the core + output-contract land.
- **The concave-value feature is the riskiest.** It's the foundation everything consumes and the place the brief's key correction lives (`U_redundancy`, not access-prob, drives saturation). If its calibration is wrong, the core's natural budget is wrong. Its `/feature-design` pass should pin the `U_redundancy` decay shape carefully and lean on [[objective-search-split]] so it's unit-testable with hand-built inputs (no DB).
- **Hedge design judgment is deferred, not resolved.** The hedge-allocator's "how wide / expected vs CVaR / which α" is intentionally unpinned (brief decision 3, NEUTRAL). Its feature-design owns that call against the brief's framing; flagged so it isn't mistaken for a settled spec.

## Provenance
Surfaced during a dogfooding test-drive of `advise sideboard` for Dimir Tempo vs the the local meta
big-mana meta (2026-06-15). The padding finding and the budget→coverage curve (15/11/8/6 →
0.444/0.434/0.413/0.385) are the empirical motivation.

## Epic complete (2026-06-15)
All 5 child features done: concave-value → dedicated-core → output-contract → gating (v1 core wave) + hedge-allocator (fast-follow). The deferred ARCHITECTURE `sideboard.py` module row was rolled forward at code-landing time (now matches the two-stage solver). End-to-end on real local-meta data, `advise sideboard --smart` produces a 5-card dedicated core + 10 diversity insurance picks + coverage curve + uncovered-field tail — replacing the original 4/4/4 padding. Gated-additive throughout: `--smart` off (default) is byte-identical to the forced-15 model (full suite 2242 green; sideboard suite byte-identical). The padding pathology that motivated the epic is fixed.
