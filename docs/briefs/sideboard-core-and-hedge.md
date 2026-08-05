---
description: How should the sideboard solver decide how many copies to commit and how to spend leftover slots? Read before designing the two-stage core+hedge sideboard rework (epic-sideboard-core-and-hedge).
type: brief
kind: research
slug: sideboard-core-and-hedge
research_method: /brief
verification_status: attested
provenance: agent-synthesis
updated: 2026-06-15
blocks_phase: epic-sideboard-core-and-hedge
summary: |
  Curated context for reworking the sideboard recommender into a two-stage core+hedge solver.
  Extends advisory-methods.md (which already owns max-coverage / greedy-1−1/e / Dirichlet). Resolves
  four deferred decisions: the per-copy access-probability curve, sideboard construction theory (the
  "natural budget"), the hedge's field-uncertainty objective, and the core/hedge boundary τ. Recommends
  defaults where evidence is strong (the copy curve, the construction principles); stays neutral where
  the call is judgment (hedge aggressiveness, τ).
key_findings:
  - "The naive 'P(≥1 access)' hypergeometric curve is only MILDLY concave (opening-7 marginal per copy ≈ 11.7→10.5→9.4→8.4%); it does NOT by itself justify capping copies. The real saturation driver is the disutility of redundant DRAWN copies (a 2nd hate card in hand is often a dead draw crowding out threats) + 15-slot scarcity."
  - "Sideboard practice: dedicated swap packages run 3-4 copies; flexible/overlapping answers run as 1-2-ofs; over-sideboarding ('too many answers, not enough threats') is a named failure. The padding bug = 4-of THREE overlapping hate pieces (12 cards) with zero flex, not any single 4-of."
  - "Recommended Stage-1 marginal value of copy k of card C = swing(C) · ΔP_access(k) · U_redundancy(k), where ΔP_access is the hypergeometric increment and U_redundancy decays sharply after the 1st-2nd in-hand copy. This keeps the objective submodular (greedy 1−1/e holds; ILP via piecewise-linear concavity)."
  - "Hedge (Stage 2) is naturally framed as optimizing coverage over a WIDER field than the point estimate: reuse positioning.py's Dirichlet share draws as the ambiguity set; expected-coverage is the simple dial, CVaR/worst-tail is the conservative dial (coherent risk measure). How wide / how conservative is a genuine judgment call — expose it, don't hardcode."
  - "τ (core/hedge boundary) options: confidence-tier-linked (reuse tier_for_sample), a swing-floor, or operator-tunable. No evidence forces one; recommend operator-tunable with a tier-aware default and surface the marginal-coverage curve so the human can see the knee."
---

# Brief: Sideboard solver — core + hedge

## Purpose

Curated context to design `epic-sideboard-core-and-hedge` — the rework of `recommend_sideboard`
from "weighted max-coverage padded to a forced 15" into a two-stage **dedicated core + hedge**
solver that may return fewer than 15 cards. This brief resolves the four design decisions the epic
deferred. It is a **focused extension** of [`advisory-methods.md`](advisory-methods.md): that brief
already owns matchup-cell estimation, the positioning score, the Dirichlet share posterior, and the
sideboard-as-weighted-max-coverage / greedy-(1−1/e) / ILP foundations. **Do not re-derive those
here** — this brief adds only the per-copy value curve, the construction theory behind the "natural
budget", the hedge objective, and τ.

> **Key context from advisory-methods.md §3:** the original design already specified the coverage
> value as a **"SATURATING (submodular) coverage function"**. The padding pathology is, in part,
> that the implementation never made the *per-copy* value actually saturate. This brief makes that
> saturation principled and adds the hedge layer the original design didn't have.

---

## 1. Sideboard construction theory (decision 2) — recommended

How strong players actually build a 15-card board, and why the "natural budget" is real.

**Dedicated vs flexible vs free.** Sideboard cards split by role:
- **Dedicated silver bullets / hate** — "the type of card you bring in to stop a specific part of
  your opponent's gameplan" `[sb-construction-fusco]{2}`. Run as a *swap package*: "your sideboard
  usually has three or four copies of specific cards to make dedicated swaps" `[sb-construction-fusco]{2}`.
- **Flexible / overlapping answers** — cards live in several matchups. "cards like Devout Decree are
  both good against Mono-Red ... and Dimir ..., making it a flexible removal spell"
  `[sb-construction-fusco]{2}`; broad hate "attack[s] nearly all graveyard strategies, without being
  weak to any one in specific" `[sb-construction-walton]{1}`. These stretch the effective board and
  are typically **1-2-ofs**.
- **Narrow single-target** — "a waste of space ... only truly effective against one deck"
  `[sb-construction-walton]{1}` unless that deck is a large, *known* share.

**The over-sideboarding failure (this is the bug, named by the domain).** "If you oversideboard,
you run the risk of having too many answers and not enough threats, which is often worse than just
not having a board" `[sb-construction-walton]{1}`. And: "Make every card earn its slot. If you don't
know when you're bringing it in, it shouldn't be there" `[sb-construction-fusco]{2}`. "You can't try
to beat everything; you have to pick a lane" `[sb-construction-fusco]{2}`.

**Implication for the solver — the precise diagnosis.** The engine's `4 Hydroblast / 4 Damping
Sphere / 4 Harbinger` is NOT wrong because 4-ofs are wrong (dedicated swaps *are* 3-4 copies
`[sb-construction-fusco]{2}`). It is wrong because it commits **4-of three overlapping hate pieces
(12 of 15 cards) to the same correlated big-mana cluster with zero flexible/insurance slots left** —
the textbook over-sideboard. So the fix is NOT a hard per-card copy cap. It is: (a) make redundant
copies *within and across overlapping answers* hit diminishing returns, and (b) stop committing once
the field's coverable value is captured (the **natural budget**, empirically ~6-8 cards for a
concentrated field per the marginal-coverage curve in the epic), leaving the rest for the hedge.

---

## 2. The access-probability curve (decision 1) — recommended, with a correction

The epic proposed weighting copies by `P(draw/side-in ≥1 | k copies)`. Research says: **that term
alone is too weak**, and the brief corrects the model.

**Hypergeometric `P(≥1 of k copies)` in a 60-card deck** (computed; reproducible — `1 −
C(60−k, seen)/C(60, seen)`):

| copies k | opening 7 | by ~T1 (8 seen) | by ~T3 (10 seen) | by ~T5 (12 seen) |
|---|---|---|---|---|
| 1 | 11.7% | 13.3% | 16.7% | 20.0% |
| 2 | 22.1% | 25.1% | 30.8% | 36.3% |
| 3 | 31.5% | 35.4% | 42.7% | 49.5% |
| 4 | 39.9% | 44.5% | 52.8% | 60.1% |

The canonical "a 4-of is ≈39.9% to appear in the opening 7" cross-checks community figures. **But
the marginal gain per copy is only gently concave** — opening-7 increments are +11.7 / +10.5 / +9.4
/ +8.4%. A pure access-probability objective would happily keep adding copies (each still adds ~8-10%
access), which is exactly the padding we're trying to kill. **So `P(≥1 access)` is not the saturation
source.**

**The real saturation source.** Two effects make copy ≥3 of a hate card net-cheap or net-negative,
neither captured by access probability:
1. **Redundant-draw disutility.** *Analytically* (this brief's reasoning, not a sourced claim): you
   side in a small block and want ≥1 in play; the *second* copy in hand is frequently a dead draw
   that displaces a threat, so the marginal *utility* of the 2nd drawn copy is far below the 1st and
   the 3rd often negative. This is the per-copy face of the deck-level failure the domain does name —
   over-committing answer slots leaves you with "too many answers and not enough threats, which is
   often worse than just not having a board" `[sb-construction-walton]{1}`.
2. **Slot scarcity.** 15 slots across ~8 likely matchups; a copy spent here is a flex/insurance slot
   not spent elsewhere `[sb-construction-fusco]{2}`.

**Recommended Stage-1 marginal-value model.** Value of the k-th copy of card C against element e:

```
Δvalue(C, k) = share(e) · swing(C, e) · ΔP_access(k) · U_redundancy(k)
  ΔP_access(k) = P(≥1 | k copies, by turn-N) − P(≥1 | k−1 copies)   # hypergeometric increment, mildly concave
  U_redundancy(k) = a utility weight that decays sharply after the 1st-2nd in-hand copy
```

`U_redundancy` is the term that actually produces "commit ~2-3, not 4+ of overlapping hate" and is
what `advisory-methods.md`'s "saturating coverage" needed but lacked. The product of concave terms
stays **submodular**, so the greedy solver keeps its 1−1/e guarantee and the ILP stays
LP-representable via piecewise-linear concavity (preserves the existing solver shape).

**Calibration inputs the build needs:** (a) turn-N "cards seen" assumption for `ΔP_access`
(opening 7 + draws — turn 3 / 10-cards-seen is a defensible default for a tempo deck that wants its
answer early); (b) the `U_redundancy` decay shape — recommend a tunable that hits ~1.0 at copy 1,
~0.5-0.6 at copy 2, ≤0.25 at copy 3, calibratable later against real 15-card boards (how many copies
of a given hoser top decks actually run). Do **not** hardcode a per-card cap; let the curve decide.

---

## 3. The hedge — robustness over field uncertainty (decision 3) — NEUTRAL (judgment dial)

Stage 2 fills slots up to 15 (operator-capped) by hedging the field you're *unsure* about, rather
than padding the field you've already covered. The framing is **optimization under distributional
uncertainty**: the point-estimate field is one distribution; the model should also do well if the
real field differs.

**The ambiguity set is already in the codebase.** `advisory-methods.md` §2 / `positioning.py`
already sample field shares `w ~ Dirichlet(counts + γ)`. That Dirichlet posterior **is** a ready-made
set of plausible fields — Stage 2 can score flex candidates against *sampled* fields rather than the
point estimate, with no new machinery. A second, complementary widener: blend the local field toward
the global/online field (the test-drive showed the local meta ≈ online but ≠ general paper — the blend
direction matters).

**Two objective dials (present both; let the operator/epic-design choose):**
- **Expected coverage over sampled fields** — average marginal coverage across Dirichlet draws.
  Simple, smooth, mildly hedging. The natural default.
- **Worst-tail (CVaR) coverage** — maximize coverage in the worst q% of sampled fields. CVaR is "the
  expected return ... in the worst q% of cases" `[cvar-expected-shortfall]{3}` and is a *coherent*
  risk measure (unlike VaR) `[cvar-expected-shortfall]{3}`, so it rewards diversification — exactly
  the breadth a hedge wants. The α level is a clean **risk-appetite dial**: α→1 = expected-coverage,
  small α = paranoid hedging.

**Diversity preference.** Whatever the objective, hedge slots want breadth (1-ofs covering distinct
uncovered tail), not depth — reuse the same `U_redundancy` concavity from §2 (it falls off fastest
exactly here).

**Why neutral.** "How wide should the ambiguity set be" and "expected vs CVaR + which α" are genuine
judgment calls with no forcing evidence — and the user's stance is that hedging is primarily the
operator's job, the model only hedges in flex slots. Recommendation: **expose the dial** (off /
expected / CVaR-α), default to a mild expected-coverage hedge, and never let the hedge override a
dedicated-core commit. Don't bake in an aggressiveness constant.

---

## 4. The core/hedge boundary τ (decision 4) — NEUTRAL (recommend operator-tunable + tier-aware default)

τ is the floor on marginal value below which Stage 1 stops adding dedicated cards (the "natural
budget" knee). Options, none forced by evidence:
- **Confidence-tier-linked** — gate on `tier_for_sample` (the project's speculative<30 / evolving /
  established≥100 from [`confidence-metadata`]): only commit a dedicated copy when the matchup cell
  driving it clears a tier. Honest (ties commitment to data depth) and on-brand.
- **Swing-floor** — stop when the best remaining marginal `share·swing·ΔP·U` falls below an absolute
  floor. Simple, but the floor is arbitrary.
- **Operator-tunable** — expose τ (or a target dedicated-count) directly.

**Recommendation:** operator-tunable τ with a **tier-aware default** (don't commit dedicated copies
off speculative-tier cells), and — most important — **surface the marginal-coverage curve** (the
15→11→8→6 budget→coverage table the epic already demonstrated) in the output so the human can see the
knee and override. This is the honest-degrade move: show the curve, name the natural budget, let the
operator decide. The boundary is then a *visible* call, not a hidden constant.

---

## Implementation Notes (for the build)

- **Submodularity is preserved.** §2's product-of-concave value and §3's diversity term are both
  submodular; the existing greedy path keeps 1−1/e and the ILP (PuLP/CBC) stays valid via
  piecewise-linear concave segments. No solver-class change — this is an objective + a second pass,
  not a rewrite. See [`objective-search-split`] (heavy DB work → dict → pure scored loop) for the seam.
- **Reuse, don't rebuild:** `advisory/field.py` `FieldDistribution` + Dirichlet `counts` (the
  ambiguity set), `advisory/positioning.py` Monte-Carlo Dirichlet draws (sample fields for the
  hedge), `confidence.py` `tier_for_sample` (τ default), the empirical presence-correlational swing
  proxy + `card_swing_overrides` already in `advisory/sideboard.py`.
- **Output contract** (honest-degrade — see [`honest-degrade-marker`]): may return <15; label each
  card **commit** (core) vs **insurance** (hedge); print the **marginal-coverage curve**, the
  **natural dedicated count**, and the **uncovered-field tail with sizes**. Keep the existing
  per-matchup OUT/IN plan and "Considering" pool.
- **Gating** (see [`gated-additive-augmentation`]): land behind an opt-in flag, byte-identical to
  today's forced-15 behavior until opted in; flip the default once trusted.
- **Don't hardcode** the per-copy cap, the hedge aggressiveness, or τ — all three are curves/dials,
  per the honesty NFR and the decisions above.

## Sources

- Sideboard construction theory: Walton, [Building Sideboards in Legacy](https://www.coolstuffinc.com/a/building-sideboards-in-legacy/) `[sb-construction-walton]{1}`; Fusco, [Maximizing Your MTG Sideboard](https://www.coolstuffinc.com/a/maximizing-your-mtg-sideboard-04232026) `[sb-construction-fusco]{2}`; [Sideboarding in Legacy (Hipsters of the Coast)](https://www.hipstersofthecoast.com/2017/03/sideboarding-in-legacy/).
- Draw probability: hypergeometric table computed in-repo (`1 − C(60−k, seen)/C(60, seen)`); cross-checked against community figures (4-of ≈ 39.9% in opening 7). Karsten's "how many copies" hypergeometric work is the canonical reference; [Intro to the Hypergeometric Distribution for Magic players (orkerhulen)](https://orkerhulen.dk/onewebmedia/An%20Introduction%20to%20the%20Hypergeometric%20Distribution%20.pdf).
- Robustness/risk: [Expected shortfall / CVaR (Wikipedia)](https://en.wikipedia.org/wiki/Expected_shortfall) `[cvar-expected-shortfall]{3}`; distributionally-robust optimization overview ([ScienceDirect topic](https://www.sciencedirect.com/topics/engineering/distributionally-robust-optimization)).
- Inherited foundations (do not duplicate): [`advisory-methods.md`](advisory-methods.md) §2 (Dirichlet shares), §3 (max-coverage / greedy-1−1/e / ILP).
