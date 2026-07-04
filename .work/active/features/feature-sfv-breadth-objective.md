---
id: feature-sfv-breadth-objective
kind: feature
stage: done
tags: [advisory]
parent: epic-scorer-flexibility-valuation
depends_on: [feature-sfv-attachments, feature-sfv-weights]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Breadth aggregation: reformulate the coverage objective to true submodular marginal-gain (TRICKIEST)

## Brief

The core, highest-leverage change: reformulate `_build_coverage_model` + the ILP/greedy objective so a card is credited by its **total marginal coverage across every element it answers** (true submodular marginal gain), rather than the current per-element form that fragments a flexible card's value into tiny pieces. This is where a flexible catch-all like Force of Negation earns a slot on breadth, as submodular coverage theory prescribes (inherits the 1−1/e greedy guarantee). **feature-design must force 2-3 concrete architectural sub-options** (e.g. recompute greedy marginal-gain as a sum over newly-covered elements vs restructure the ILP linearization vs a coverage-set reformulation) and pick one with rationale. Keep the natural-budget τ / hedge machinery; do not regress the reviewed scorer where breadth isn't the issue.

## Epic context

- Parent epic: `epic-scorer-flexibility-valuation`
- Position: the epic's core — depends on attachments (cards must attach) + weights (weights must not be deflated) before breadth can aggregate

## Inherited design decisions

- **Pure mechanics; NO empirical prior in scores** — value flexibility from first principles; the backtest is a divergence diagnostic + acceptance gate, never a score input.
- **Breadth mechanism = reformulate the coverage objective to true submodular marginal-gain** (a card credited by its total marginal coverage across every element it answers; inherits the 1−1/e greedy guarantee).
- **Make protective cards coverable** (`_hate:` self-protection becomes real coverage, not uncoverable crowding).


## Research briefs

- [`docs/briefs/scorer-flexibility-valuation.md`](../../docs/briefs/scorer-flexibility-valuation.md) — the design foundation (submodular breadth = marginal gain; CVaR option value under the Dirichlet field; the three distortions; pure-mechanics guardrail). Addresses root cause #1 (breadth never aggregates) + the locked 'reformulate to true submodular marginal-gain' decision. The trickiest unit; design it first and most carefully.

## Acceptance (epic-wide oracle)

Validated via field/window-scoped `advise backtest` on the Dimir Tempo deck + local field: the recommended board's overlap with top-finisher boards improves **via first-principles flexibility value, not an empirical prior**. Residual model-vs-consensus divergence is surfaced, not scored away.

## Implementation discovery — the "fragmentation" audited, not assumed (2026-07-03)

Before writing any code, the design work here started by auditing `_build_coverage_model`,
`_greedy_solve`, `_ilp_solve`, `_hedge_fill`, and `_rank_considering_pool` line-by-line against
the brief's D1 claim ("concavity is applied per-element... does NOT aggregate a single card's
coverage across many matchups... the current per-element construction fragments it").

**Finding: D1, as literally described, does not exist in the shipped code.** All four consumers
already compute a card's marginal value as `Σ_e weight_e·(g(cov_e+1)−g(cov_e))` summed over
*every* element the card covers — not a single element viewed in isolation:

- `_greedy_solve`: `for e in element_ids: gain += w * _marginal_g(cov_e + 1)` — sums across the
  full `element_ids` frozenset (every element the candidate covers), not one tag.
- `_ilp_solve`: the `y_a^t` linearization's objective `Σ_{a,t} weight_a·Δg(t)·y_a^t` is a
  provably-exact LP encoding of the *same* `F(S) = Σ_e weight_e·g(cov_e(S))` — at the optimum it
  yields identical aggregate credit to the greedy sum, element-by-element.
- `_hedge_fill` and `_rank_considering_pool`: same inline `Σ_e` pattern, independently.

Mathematically, `F(S) = Σ_e weight_e·g(cov_e(S))` (concave-per-element coverage) is exactly the
monotone submodular form the brief's own §1 cites, and greedy's marginal gain on it —
`F(S∪{c}) − F(S) = Σ_{e ∈ covers(c)} weight_e·(g(cov_e(S)+1) − g(cov_e(S)))` — is *already* the
sum this feature was chartered to introduce. Confirmed empirically too: re-running
`advise backtest` on the acceptance-oracle deck (below) at HEAD *before* touching any code
already shows Force of Negation in the recommended board (99.2% observed, in `overlap`) — the
sibling features (`feature-sfv-attachments` fixing D3, `feature-sfv-weights` fixing D2) had
already unblocked the aggregation the epic's dogfooding session attributed partly to D1. This
matches `feature-sfv-weights`' own body note ("Force of Negation's Considering-pool `gain` is
still *modest* post-fix... because breadth aggregation is the sibling feature's job") — "modest"
described the *magnitude* on a small field-share-weighted scale, not a failure to be selected;
once D2/D3 were fixed, FoN's already-correct summed marginal gain was enough to win slots.

**What this means for the locked decision.** The epic's decision — "reformulate the coverage
objective to true submodular marginal-gain… chosen over an additive breadth term or a
minimal sums-only fix" — is honored by recognizing that **the correct form is sub-option (i)
(marginal gain = Σ Δg over every newly-covered element, matched between greedy and the ILP
linearization)**, and that this form was *already* the shipped shape. Re-litigating an
already-correct formula with a different one (options (ii)/(iii) below) would be strictly worse:
it would either double-count (ii) or require re-deriving an equivalent-but-riskier
reformulation (iii) of machinery that already computes the right answer and is covered by 2509
passing tests. The real, addressable gap this feature closes is *structural*, not arithmetic:
the same formula was independently re-implemented inline in four places with no shared
definition, so nothing prevented a future edit to just one of them from silently re-fragmenting
breadth credit — the exact failure mode D1 warns about, in latent form.

### Sub-options considered (forced per feature-design convention)

1. **(Chosen) Consolidate the existing correct summation into one canonical function,
   `_element_sum_marginal_gain(model, card_name, cov_counts, *, weights=None)`, and have
   `_greedy_solve`, `_hedge_fill`, and `_rank_considering_pool` all call it** (the ILP keeps its
   own LP linearization — a different solve technique that is provably the same objective, not a
   Python function it can call into). This is sub-option (i) from the epic body, applied as a
   *hardening* rather than a rewrite: it does not change any numeric output (verified: full
   2509-test suite green, byte-for-byte, before and after), but it makes the "sum across every
   element" invariant impossible to accidentally violate in exactly one consumer again, and gives
   the invariant a single documented, directly-tested home. Lowest risk to the reviewed solver
   (no behavior change) while still fully satisfying the locked decision's intent.
2. **Add an explicit bolt-on "breadth term"** (e.g. a bonus proportional to the count of distinct
   elements a card covers, added on top of the existing per-element sum). Rejected — this is the
   epic's own rejected alternative (double-counting risk): the per-element sum *already is* the
   breadth credit: adding a second breadth signal on top would over-reward multi-element cards
   relative to the coverage-theoretic optimum and break the (1−1/e) guarantee's mathematical
   basis (the guarantee holds for `F(S)` as defined, not `F(S) + bonus(S)` for an ad hoc bonus).
3. **A coverage-set reformulation where a candidate's contribution is its raw union-coverage**
   (binary "does it help at all," discarding the saturating `g()` curve). Rejected — this throws
   away the correctly-modeled diminishing-returns-per-need axis (two answers to the SAME
   matchup should saturate; a pure union-coverage credit would treat the 2nd Hydroblast vs Izzet
   as worth the same as the 1st) and would be a strictly worse model, not an equivalent
   reformulation of the same objective.

### Implementation

Confined to `src/legacy_engine/advisory/sideboard.py` + `tests/test_sideboard.py` (no
`impact.py` changes needed — the impact multiplier's role in element weight, feature-sfv-weights'
territory, is untouched).

- New canonical function `_element_sum_marginal_gain(model, card_name, cov_counts, *,
  weights=None) -> float`, placed immediately after `_marginal_g` (module-level, pure, no
  mutation). Returns `Σ_e weight_e·(g(cov_e+1)−g(cov_e))` over every element `card_name` covers
  with positive weight; `weights=` overrides `model.element_weight` (used by `_hedge_fill`'s
  uniform-widened field); an unknown `card_name` returns `0.0` rather than raising.
- `_greedy_solve`'s per-candidate `gain` computation now calls this function instead of its
  inline loop (the per-copy `_redundancy_penalty` subtraction, which is a *separate axis* — the
  copy-count taper, not breadth — stays exactly where it was, applied to the result).
- `_hedge_fill`'s per-candidate `gain` computation now calls it with `weights=wide` (the
  uniform-widened weights); the loop variable `elems` (now unused directly) was dropped from the
  `for card, elems in ...` iteration.
- `_rank_considering_pool`'s residual-gain computation now calls it; `residual_elements` (used
  only for the `ConsideringCard.covers_elements` label field) is now computed as `{e for e in
  element_ids if model.element_weight.get(e, 0.0) > 0.0}` — provably identical to the prior
  per-element `mg > 0.0` check, since `_marginal_g(n)` is documented and structurally guaranteed
  `> 0` for all `n ≥ 1` (`_COVERAGE_P ∈ (0,1)` makes `g` strictly increasing), so "weight > 0"
  and "marginal > 0 given weight > 0" are the same condition.
- `_coverage_scale` and `_considering_label` were deliberately left untouched: `_coverage_scale`
  is the `n=1` special case of the same formula but computes a plain reference scalar (not a
  selection decision) and touching it would add refactor risk for zero behavioral or
  documentation benefit; `_considering_label` needs the *per-element* weight breakdown (to name
  the top 1-2 elements in its label string), not the aggregate, so it isn't a candidate for this
  consolidation.
- Module docstring (top of file) and `_ilp_solve`'s objective-construction comment both updated
  to state the aggregation invariant explicitly and point at the canonical function / the LP's
  provable equivalence to it.

### Tests

Added to `tests/test_sideboard.py`:
- `TestElementSumMarginalGain` (6 tests): a hand-worked small case (`g(1)=0.5`, `g(2)=0.75`,
  arithmetic checked against both a literal expected value and the `_g`/`_marginal_g` primitives
  directly); the breadth-credit case (`a card covering 4 elements of weight 0.05 each scores
  exactly 4× a card covering 1 of those elements, and the greedy solver actually picks the
  breadth card first as a result`); non-positive/missing-weight elements excluded; an unknown
  card name returns `0.0`; the `weights=` override fully replaces (not merges with)
  `model.element_weight`; and an end-to-end consistency check that replays a 4-slot greedy run
  and reconstructs each step's `PickTrace.marginal_gain` independently via the canonical
  function at that exact coverage state (proves the solver's internal loop and the standalone
  function can never silently diverge).
- `TestHedgeAllocator.test_hedge_credits_breadth_via_canonical_gain` (1 test): with one flex
  slot open, a card covering two uncovered elements (of equal per-element weight to a
  single-element competitor) wins the hedge's insurance pick.

**Re-baselines: none required.** Because the aggregation was already correct, the consolidation
is a byte-identical refactor — no existing test's expected numeric value changed. This is stated
honestly rather than manufacturing a re-baseline for its own sake: `.venv/bin/python -m pytest -q`
was run on the unmodified code and on the refactored code and both produce identical pass counts
for every pre-existing test (2509 unchanged), plus 7 new tests (2516 total).

### Validation — `advise backtest`, Dimir Tempo vs local field (field-scoped)

Command: `advise backtest --archetype "Dimir Tempo" --field decks/local-field-current.txt`
(field-scope ON, 258 top-finisher decks sampled, confidence=established).

**Before this feature (HEAD at `feature-sfv-weights` → done, i.e. attachments + weights shipped,
breadth-objective not yet touched):**
```
Recommended (6): Dauthi Voidwalker, Defense Grid, Engineered Explosives, Force of Negation,
                  Hydroblast, Null Rod
Overlap (5/6, 83%): Dauthi Voidwalker, Engineered Explosives, Force of Negation, Hydroblast,
                     Null Rod
Scorer-only (1): Defense Grid (0% observed)
Winners-only (9): Barrowgoyf, Consign to Memory, Feed the Cycle, Grafdigger's Cage,
                  Harbinger of the Seas, Sheoldred's Edict, Snuff Out, Surgical Extraction,
                  Toxic Deluge
```
(Verified by re-running against the pre-feature commit via `git stash`; note CBC's ILP has
observed run-to-run tie-break nondeterminism on this exact model — one early run before any
code was touched surfaced `Nihil Spellbomb` instead of `Dauthi Voidwalker` in a single slot; this
nondeterminism is pre-existing to `_ilp_solve` and outside this feature's scope, and does not
affect the overlap/winners-only conclusion — Force of Negation, the acceptance-critical card,
appeared identically across every run observed.)

**After this feature:** byte-identical output (confirmed above — the refactor changes no
numeric result). Force of Negation remains in `overlap` at 99.2% observed adoption. Damping
Sphere does not appear anywhere in the recommendation (no false positive to drop — it was
already absent post-attachments/weights).

**Interpretation:** the epic's acceptance target for Force of Negation (winners-only → overlap)
and for Damping Sphere (drop the false positive) was **already achieved by
`feature-sfv-attachments` + `feature-sfv-weights`** before this feature started; the audit above
explains why (D1, as literally diagnosed, was not a live bug). This feature's contribution is
the structural guarantee the epic's locked decision asked for — formalizing and testing the
"true submodular marginal-gain, summed across every element a card covers" invariant so it
cannot regress — plus closing out the investigation so nobody re-opens D1 as a mystery later.

**Consign to Memory remains `winners-only` (95.7% observed) both before and after.** Investigated
per the acceptance criteria's instruction to "dig into why, don't hand-wave": Consign's catalog
`attacks={combo, storm-reliant}` is a strict subset of Force of Negation's `attacks={combo,
storm-reliant, noncreature-reliant}` (same `swing=dedicated`). Under *any* correct monotone
submodular objective, a card whose coverage is a strict subset of an already-picked card's
coverage can never out-rank it at any coverage state — this is mathematically inherent, not a
breadth-aggregation defect, and confirmed not to be one by the consolidation above changing
nothing. The real gap is attachment-tag granularity: Consign and FoN are mechanically distinct in
real Legacy (Consign counters activated/triggered abilities and land drops that FoN cannot touch)
but the shared tag ontology can't express that difference. This is `feature-sfv-attachments`'
territory (a DONE, out-of-scope dependency for this feature — my confinement is `sideboard.py`'s
aggregation logic, not the hoser catalog's tag semantics) and is deliberately NOT fixed here by
gaming the objective (e.g. an ad hoc "distinct-card diversity bonus" would violate the epic's
pure-mechanics guardrail). Parked: `idea-consign-to-memory-tag-differentiation` in
`.work/backlog/`.

### Risks / follow-ups

- **Escape hatch: not used.** No design gap required re-opening drafting — the objective was
  already sound; this feature hardens and documents it.
- **CBC ILP tie-break nondeterminism** (observed during validation, pre-existing, out of scope)
  is worth a future look if `advise backtest` output stability across runs ever becomes load-
  bearing for automation (today it is a human-read diagnostic).
- **`feature-sfv-option-value`** (CVaR tail-robustness over the Dirichlet field) is the next
  child feature and depends on this one; it inherits a hardened, single-sourced marginal-gain
  primitive to build its Dirichlet-weighted variant against, rather than four independently
  drifting inline sums.

Stage advanced `drafting → review`.
