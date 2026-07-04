---
description: "How do you value a flexible catch-all (one card answering many matchups) in a coverage-based sideboard scorer, from first principles, without regressing to consensus? Read before designing epic-scorer-flexibility-valuation."
type: brief
kind: research
slug: scorer-flexibility-valuation
research_method: /brief
verification_status: attested
provenance: agent-synthesis
updated: 2026-07-03
blocks_phase: epic-scorer-flexibility-valuation
summary: |
  The sideboard scorer undervalues broad, flexible interaction: a card that answers many matchups
  (Force of Negation) has its value fragmented across tiny per-(archetype,tag) elements and scores
  ~0, though it is near-universal in winning boards. This brief shows the fix is NOT a "flexibility
  bonus" or an empirical prior — the coverage objective is already submodular, and submodular
  maximization credits breadth correctly via marginal gain. The gap is that three distortions starve
  the breadth signal (misapplied concavity, deflated/uncoverable element weights, missing
  attachments). It recommends: repair the objective so a card is credited by its TOTAL marginal
  coverage across all elements it answers; add a pure-mechanics option-value term (tail-robustness
  over the Dirichlet field) so flexibility is valued under uncertainty; keep empirical winning-board
  frequency as a divergence diagnostic only.
key_findings:
  - Coverage maximization is monotone submodular; the greedy/ILP solver ALREADY credits breadth via marginal gain (a card covering many needs has large marginal value) — the model is the right shape, so the fix repairs distortions rather than adding a flexibility heuristic.
  - The breadth signal is starved by three distortions, not by the model's form - (1) the concave saturation g() is applied per-element (diminishing returns on stacking copies for ONE matchup) instead of across the card's breadth; (2) opponent elements are deflated (uniform draw_prob≈0.4 factor) and the biggest weights are uncoverable `_hate` self-protection pseudo-elements that crowd out real coverage; (3) broad cards fail to ATTACH to the elements they answer (plays-blue never fires as an opponent vulnerability; no broad-interaction attribution).
  - Flexibility has first-principles OPTION VALUE under field uncertainty - a card that answers many archetypes has lower-variance value across draws of an uncertain (Dirichlet) field; a tail-aware / CVaR objective term rewards this hedge WITHOUT any empirical inclusion signal, letting the engine value breadth from mechanics alone.
  - MTG-domain expertise agrees - broad overlapping answers earn slots and "stretch" a 15-card board; over-dedicating to narrow hate is a known failure mode; if a matchup needs the whole board, change decks, don't spend the board (validates the punt/slot-ROI logic).
  - Keep the pure-mechanics guardrail - do NOT fold winning-board inclusion% into the score (regresses to consensus). The backtest stays a divergence diagnostic + acceptance gate: model≠consensus is a flag to investigate (missing mechanic OR a real edge), not an error to calibrate away.
status: draft
---

# Brief: Valuing flexibility / breadth in a field-weighted coverage optimizer

## Purpose

Unblocks `epic-scorer-flexibility-valuation`. The sideboard scorer (`advisory/sideboard.py`) scores
Force of Negation at `gain=0.0001` while it appears in 96% of winning boards — a ~1000× disagreement
on the format's most-played sideboard card. This brief answers the modeling question the epic turns
on: **how do you credit "one card answers many matchups" as first-class value, from first principles,
without regressing the engine to consensus?** It maps the relevant optimization theory onto our
scorer and hands the build session concrete, testable model changes.

---

## 1. The core insight: the objective is already submodular — breadth is *supposed* to be credited

Our scorer maximizes a weighted coverage objective (`Σ_e weight_e · g(coverage_e)`) over "elements"
(archetype × vulnerability-tag needs), picking ≤15 cards — this is precisely a **weighted maximum
coverage problem** `[max-coverage]{5}`. Coverage functions are the canonical example of a **monotone
submodular** function: value exhibits diminishing marginal returns, `f(X∪{x}) − f(X) ≥ f(Y∪{x}) −
f(Y)` for `X ⊆ Y` `[submodular-set-function]{4}`.

The consequence that matters: **submodular maximization credits breadth correctly, by construction.**
The greedy rule picks, each step, the card covering the **maximum weight of currently-uncovered
elements** `[max-coverage]{5}`; a card that answers many needs has a large *marginal gain* and is
selected precisely because of that breadth. Greedy achieves a `(1 − 1/e)` approximation, which is
essentially best-possible in polynomial time unless P=NP `[submodular-set-function]{4}`
`[max-coverage]{5}`.

**So the model is the right shape.** Force of Negation *should* win a slot because it marginally
covers the whole combo/control plurality at once. The fix is therefore **not** a bolted-on
"flexibility bonus" and **not** an empirical prior — it is to repair the three distortions that
currently starve the marginal-gain signal so breadth aggregates the way submodular coverage says it
should.

## 2. Why breadth is starved today (three distortions)

**(D1) Concavity is applied in the wrong place.** The saturating `g()` / redundancy curve models
diminishing returns on stacking *copies for one matchup* (the 2nd Hydroblast is worth less than the
1st vs Izzet). It does **not** aggregate a single card's coverage *across many matchups*. A broad
card's value is the **sum of its marginal contributions to every element it covers** — that sum must
be first-class, not flattened element-by-element. (Correct submodular coverage does this; the current
per-element construction fragments it.)

**(D2) The coverable weights are deflated and out-competed by uncoverable ones.** Opponent elements
are deflated to ~0.003–0.005 by a uniform `draw_prob(1)≈0.4` factor baked into the element-weight
impact multiplier (and baseline centrality 0.5). Meanwhile the **largest** weights are `_hate:`
self-protection pseudo-elements (~0.089 each — "protect my own manabase/colors") that **no catalog
card can cover**, so they sit uncovered and crowd the ranking. Net: the real, coverable combo/blue
needs a flexible counter would serve are tiny, and the dominant needs are unservable.

**(D3) Broad cards don't attach to the elements they answer.** Coverage credit requires the card to
be *connected* to a need. Two attachment bugs: `plays-blue` never fires as an *opponent* vulnerability
(only `plays-red` does, for the blasts), so Mystical Dispute attaches to nothing in a ~45%-blue field;
and there is no "broad free interaction" attribution, so Force of Negation, when present, attaches
only to a few tiny `combo` elements instead of the whole plurality it actually answers.

## 3. Adding first-principles flexibility value: option value under field uncertainty

Repairing D1–D3 lets *observed* breadth aggregate. But there is a second, genuinely-new
first-principles reason flexible cards are good that the current model misses entirely: **a flexible
card hedges the uncertainty in *which* matchups you'll face.**

We already compute the field as a **Dirichlet distribution** over archetype shares (in
`advisory/positioning.py`). A narrow hoser's value is high only if its one target shows up; a flexible
card retains value across *many* field realizations — i.e. it has **lower variance in the tail of bad
field draws**. This is exactly what a **coherent tail-risk measure** captures: Expected Shortfall /
CVaR is "the expected return in the worst q% of cases," is subadditive so *diversification never
increases measured risk*, and exposes a tunable risk-appetite dial `α` `[cvar-expected-shortfall]{3}`.

**Recommendation:** add an option-value term that scores a board (or a card's marginal contribution)
by its **coverage in the worst-tail field draws** from the Dirichlet, not just the mean field. A
flexible card raises worst-tail coverage more than a narrow one of equal mean value — so the engine
rewards flexibility *because it is robust to field uncertainty*, computed purely from mechanics +
the field distribution, with **zero empirical winning-board input**. The `α` dial lets the operator
choose "tune to the expected field" (α→1) vs "hedge the field I fear" (small α).

This is the mechanism that lets the engine *see further than consensus*: it will value a robust
flexible card the field hasn't adopted yet, on first principles, rather than only echoing what's
already popular.

## 4. Domain grounding (this isn't just optimization theory)

Legacy sideboard-construction expertise independently reaches the same conclusions, which is a good
sign the mechanics are modeling something real:

- **Broad overlapping answers earn their slots; narrow ones waste space.** A card that "attacks
  nearly all [a strategy class] without being weak to any one in specific" retains value across many
  opponents; a card good against only one deck wastes a slot unless that deck is a large known share
  `[sb-construction-walton]{1}`. This is the breadth thesis in domain terms.
- **Flexible cards stretch the effective size of a 15-card board;** dedicated hate runs in 3–4-copy
  blocks (so you reliably draw and swap them), while flexible answers are one-ofs covering several
  matchups `[sb-construction-fusco]{2}`. (Note the tie-in to the existing draw-probability copy-taper:
  the *copy count* logic and the *breadth* logic are distinct axes — D1.)
- **Over-dedicating is a failure mode; if a matchup needs your whole board, change decks.** "If you
  oversideboard, you run the risk of having too many answers and not enough threats" `[sb-construction-walton]{1}`;
  every slot must earn its place `[sb-construction-fusco]{2}`. This validates the existing slot-ROI /
  punt logic (`feature-sb-slot-roi-punt`) and argues the flexibility term should *complement*, not
  override, punt detection.

## 5. The hard guardrail: pure mechanics; backtest is a diagnostic, not a prior

Do **not** fold winning-board inclusion% into the score. It is tempting (it would "fix" FoN
instantly) but it regresses the engine to consensus and forfeits the ability to surface mispriced
cards — the project's reason to exist. (Precision: this guardrail is specifically about
winning-board inclusion%; the scorer's pre-existing, separately-labeled empirical components — the
adoption pool filter and presence-correlational swing proxies — are out of this brief's scope.) All of §1–§3 value flexibility from mechanics (marginal
coverage + Dirichlet tail-robustness), never from observed popularity. The empirical backtest
(`advisory/backtest.py`) stays a **divergence diagnostic + acceptance gate**: where the model and
winning boards disagree, that is a flag for a human — *missing mechanic* (fix it) or *genuine edge*
(keep it) — not an error to calibrate away.

## 6. Implementation notes (code map for the build session)

- **`advisory/sideboard.py` `_build_coverage_model` + the ILP/greedy objective (D1, D2):**
  - Ensure a card's score aggregates its marginal coverage across **all** attached elements (the
    submodular marginal-gain quantity), rather than being flattened per-element. Audit whether the
    concave `g()` / `_u_redundancy` curve is (correctly) per-matchup copy-taper vs (incorrectly)
    suppressing cross-matchup breadth.
  - Rebalance `_hate:` self-protection: make protective cards *coverable* (the epic's locked
    decision) so those weights become real coverage instead of uncoverable crowding; and/or cap their
    share of total weight.
  - Remove the `draw_prob(1)` deflation from the *element weight* (it belongs only in the per-copy
    taper — see `idea-scorer-element-weight-drawprob`, folded into the epic).
- **`advisory/impact.py`:** the multiplicative factors are fine as a per-(card,opponent) gate; the
  breadth aggregation is a *coverage-model* concern, not an impact-factor one. Keep impact for
  centrality/symmetry/castability; don't let draw-prob double-count (element weight vs copy taper).
- **`advisory/whattoplay.py` `_color_contingent_tags` (D3):** emit `plays-<color>` as an **opponent**
  vulnerability (a blue opponent is vulnerable to `plays-blue` interaction), not only for the deck's
  own protection; add a "broad free interaction" attribution so FoN/Spell Pierce attach to the whole
  combo/control plurality.
- **Option value (§3):** reuse the Dirichlet from `advisory/positioning.py`; compute board/card
  coverage over sampled or closed-form worst-tail field draws (a CVaR-style aggregation) as an
  additive objective term with a tunable `α`.
- **Validation:** the acceptance oracle is `advise backtest` on the Dimir Tempo deck + Boulder field —
  FoN/Consign should move from *winners-only* into *overlap*, and the Damping Sphere false-positive
  should drop, **with the mechanism being first-principles flexibility value, not an empirical prior.**
  Any residual divergence is surfaced, not scored away.

## 7. Worked example: Force of Negation, gain=0.0001 → competitive

Today, against the Boulder field: FoN attaches to a few `combo` elements (Show&Tell/Doomsday/Saga
Storm), each ~0.003 (deflated by D2), and its breadth across them isn't aggregated (D1) — total
`gain≈0.0001`. After the fixes: (D3) FoN attaches to the *full* combo/control plurality (and, with
the broad-interaction axis, the blue tempo decks it can counter); (D2) those elements carry real
weight once deflation + `_hate` crowding are fixed; (D1) its marginal coverage across all of them
**sums** into the score the way submodular coverage prescribes `[submodular-set-function]{4}`
`[max-coverage]{5}`; (§3) its option value under the Dirichlet field lifts it further as a hedge
`[cvar-expected-shortfall]{3}`. It becomes competitive on mechanics — and if the engine *still*
disagreed with the 96% consensus, that would now be a signal to investigate, not a hidden bug.

## 8. Open questions for design

- **Where does breadth aggregation live** — reformulate the objective so the ILP sees true submodular
  marginal gain, or add an explicit breadth term? (The former is cleaner and inherits the `1−1/e`
  guarantee `[max-coverage]{5}`; the latter is easier to bolt on but risks double-counting.)
- **Closed-form vs sampled CVaR** over the Dirichlet — positioning uses a Monte-Carlo draw; a
  closed-form tail bound may suffice and stay deterministic.
- **Interaction with the copy-taper** — keep the copy-count (draw-probability) axis and the
  breadth/option-value axis strictly separate to avoid re-introducing the deflation bug.
- **Does `_hate` self-protection belong in the *same* objective** as opponent coverage, or as a
  separate protective-coverage sub-objective with its own budget?

## Sources

1. `[sb-construction-walton]{1}` — Walton, "Building Sideboards in Legacy" (CoolStuffInc): broad overlapping answers earn slots; over-sideboarding failure mode.
2. `[sb-construction-fusco]{2}` — Fusco, "Maximizing Your MTG Sideboard" (CoolStuffInc): flexible one-ofs stretch the board; dedicated 3–4-of blocks; every slot earns its place.
3. `[cvar-expected-shortfall]{3}` — "Expected shortfall" (Wikipedia): CVaR/ES as a coherent tail-risk measure (worst q% expectation; subadditive; tunable α).
4. `[submodular-set-function]{4}` — "Submodular set function" (Wikipedia): diminishing-returns definition; coverage is monotone submodular; greedy `1−1/e` under cardinality (Nemhauser–Wolsey–Fisher 1978).
5. `[max-coverage]{5}` — "Maximum coverage problem" (Wikipedia): weighted maximum coverage; greedy picks max uncovered weight; `1−1/e`, best-possible unless P=NP.
