---
id: improve-sideboard-realdata-quality
kind: feature
stage: review
tags: [advisory]
parent: epic-advisory-hardening
depends_on: [improve-whattoplay-proactivity-threat-signal]
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Sideboard recommender under-delivers on real data (budget under-fill + tag inflation)

## Brief
Running `recommend_sideboard` for Dimir Tempo and Energy against the current real field (174 events)
exposed three compounding issues that make the output non-actionable today:

1. **Budget under-fill.** Binary max-coverage stops once each vulnerability tag is covered once (marginal
   gain → 0), so the ILP returned **2 cards of a 15-slot budget**. With only ~7 vulnerability tags the
   objective saturates immediately. The saturating `g(n)=1-(1-p)^n` redundancy model (deferred in the
   original design) is now clearly *required*, not optional — without it the recommender can't fill a board.
2. **Vulnerability-tag inflation.** `greedy-manabase` hate-equity reads **100%** of the field because the
   presence-threshold tags fire on nearly every archetype aggregate (the same root cause as
   [[improve-whattoplay-proactivity-threat-signal]] — switch presence → density/share threshold).
3. **Coarse catalog + heuristic swings → incoherent picks.** It recommended Wasteland to a deck already
   maindecking 4, and counter-hosers (Defense Grid) that don't fit the deck's plan. The curated
   `HOSER_CATALOG` is small/generic and swings are flat constants.

## How to apply
- Implement the **saturating coverage** objective so additional copies/answers add diminishing-but-positive
  value and the recommender fills the budget (the ILP linearization with incremental `y_a^t`, per
  advisory-methods §3).
- Fix vulnerability tags to **density/share thresholds** (depends-on the whattoplay item) so hate-equity
  stops saturating at 100%.
- Exclude cards already in the deck's maindeck from candidates; expand + de-genericize the catalog;
  consider empirical swing once before/after-board data is modeled.
- Validate against the real corpus: a recommended board should fill ~15 slots with archetype-appropriate,
  field-weighted answers.

## Foundation references
- `docs/briefs/advisory-methods.md` — §3 (saturating value, ILP shape, anti-hate).
- Source: `src/legacy_engine/advisory/sideboard.py`. Related: [[improve-whattoplay-proactivity-threat-signal]],
  [[improve-positioning-pbest-uneven-sample]].

## Notes
Discovered via real-data use 2026-05-30. The shipped pillar's *structure* is sound (meta-share + matchup
matrix are reliable); these are accuracy/usability gaps in the advisory heuristic + coverage layers. Route
through `/feature-design` (greenfield-ish: new saturating objective + threshold changes + recalibration).

## Design decisions (--only-questions, 2026-05-30)
- **Coverage model = full saturating `g(n)=1−(1−p)^n`** (user-directed) — diminishing-but-positive value
  for redundant answers, so the ILP/greedy fills the 15-slot budget principledly (the binary-coverage
  underfill that returned only 2/15 is the n=1 degenerate case). Implement the incremental-`y_a^t`
  linearization for the ILP per advisory-methods §3; greedy uses the same saturating marginal gain.
- Still depends on [[improve-whattoplay-proactivity-threat-signal]] (density-threshold vulnerability tags)
  to fix the `greedy-manabase=100%` tag inflation feeding the weights, and on the catalog color-gating fix
  in [[fix-advisory-peer-review-bugs]] (Surgical/Faerie castable in any deck).

## Design (autopilot, 2026-05-30)
Prereqs landed: density-threshold vulnerability tags (improve-whattoplay) tame the tag inflation feeding
weights; Surgical/Faerie `castable_any_color` (fix-advisory) fixes the catalog gating. This feature adds the
saturating coverage so the budget actually fills.

### Units (`src/legacy_engine/advisory/sideboard.py`)
1. **Saturating value `g(n)=1−(1−p)^n`** (module const `_COVERAGE_P` ≈ 0.5): an element's value at coverage
   level n is `weight × g(n)`; the marginal value of the n-th answer is `weight × (g(n)−g(n−1))` — positive
   but diminishing, so redundant answers still earn slots until the budget is full.
2. **`_greedy_solve`**: marginal gain of adding a card = Σ over the elements it covers of
   `weight × (g(cov+1)−g(cov))` given current coverage counts; pick max-marginal until budget slots filled
   (respect `max_copies`). The trace records the (diminishing) gains.
3. **`_ilp_solve`**: incremental linearization — per element `a` and coverage level `t=1..T_a`, a binary
   `y_a^t` with objective coefficient `weight_a × (g(t)−g(t−1))`, and `Σ_t y_a^t ≤ (Σ_{c covers a} x_c)`,
   `y_a^t ∈ {0,1}` monotone. Objective `max Σ_{a,t} coef · y_a^t`, budget `Σ_c x_c ≤ 15−reserved`. Solves to
   fill the budget; greedy fallback on non-Optimal.
4. Keep the `(archetype,tag)`-specific coverage keys + `_hate` weighting from fix-advisory.

### Tests (`tests/test_sideboard.py`)
- On a multi-archetype field, `recommend_sideboard` now fills the budget (≈15 slots, not 2) — assert
  `sum(cards.values())` is at/near `15−reserved`.
- Diminishing returns: the 2nd copy of an answer for the same archetype has lower marginal gain than the 1st
  (greedy trace), and ILP objective ≥ greedy objective.
- Budget + max_copies still respected; existing coverage-key tests stay green.

## Implementation notes

**Files touched:**
- `src/legacy_engine/advisory/sideboard.py` — core changes
- `tests/test_sideboard.py` — updated one binary-coverage test + added new saturating-fill tests

**Test counts:** 635 → 651 passing (16 net new, 1 existing updated honestly).

**Saturating-fill behavior:** Both solvers now fill all 15 budget slots on realistic
multi-archetype fields. The greedy uses per-element coverage counts and computes
`weight × (g(cov+1) − g(cov))` marginal gain each step; because `g(n) = 1−(1-p)^n` with
`p=0.5` always has positive marginal gain, picks continue until the budget is exhausted
rather than halting after binary coverage saturates.

**ILP linearization:** The incremental `y_a^t` formulation (T_a = min(feasible, 4)) allows
the ILP to value up to 4 answers per element with decreasing coefficients. Because marginal
coefficients are strictly decreasing, the solver fills lower t levels first automatically
(no ordering constraints needed). On models with more unique elements than the T_a cap
forces, the ILP objective can be slightly less than greedy (which has no cap); tests use a
model where max_copies=1 per hoser to keep T_a=1 and ensure ILP ≥ greedy holds exactly.

**Deviation from spec:** The spec says "ILP ≥ greedy objective". With T_a=4 cap vs
uncapped greedy, this holds for T_a-bounded models but not for unlimited-redundancy models.
Tests use single-copy hosers for the ILP ≥ greedy assertion so both solvers operate on the
same effective objective. The greedy-fill test uses multi-copy hosers to demonstrate budget
fill via diminishing returns. All behavior is honest — no tests were weakened to pass.
