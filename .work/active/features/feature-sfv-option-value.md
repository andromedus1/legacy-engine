---
id: feature-sfv-option-value
kind: feature
stage: done
tags: [advisory]
parent: epic-scorer-flexibility-valuation
depends_on: [feature-sfv-breadth-objective]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Option value: CVaR tail-robustness over the Dirichlet field

## Brief

Add the pure-mechanics flexibility-under-uncertainty lever: a card that answers many archetypes hedges *which* matchups actually appear, so it has lower-variance value across draws of the uncertain (Dirichlet) field. Add a **CVaR-style tail-robustness objective term** — score a board/card by its coverage in the worst-tail field draws (reuse the Dirichlet from advisory/positioning.py; closed-form Beta-marginal preferred over Monte-Carlo for determinism) — with a tunable risk-appetite dial α (α→1 = tune to the expected field; small α = hedge the field you fear). This is the mechanism that lets the engine value flexibility from uncertainty (not just observed breadth) and **see past consensus** — with zero empirical winning-board input. Keep it a strictly separate axis from the copy-count draw-probability taper to avoid re-introducing deflation.

## Epic context

- Parent epic: `epic-scorer-flexibility-valuation`
- Position: additive modeling term on the repaired objective — depends on breadth-objective

## Inherited design decisions

- **Pure mechanics; NO empirical prior in scores** — value flexibility from first principles; the backtest is a divergence diagnostic + acceptance gate, never a score input.
- **Breadth mechanism = reformulate the coverage objective to true submodular marginal-gain** (a card credited by its total marginal coverage across every element it answers; inherits the 1−1/e greedy guarantee).
- **Make protective cards coverable** (`_hate:` self-protection becomes real coverage, not uncoverable crowding).


## Research briefs

- [`docs/briefs/scorer-flexibility-valuation.md`](../../docs/briefs/scorer-flexibility-valuation.md) — the design foundation (submodular breadth = marginal gain; CVaR option value under the Dirichlet field; the three distortions; pure-mechanics guardrail). The novel 'see-further' lever; grounds on the brief's CVaR / expected-shortfall section. Keep separate from the copy-taper axis.

## Acceptance (epic-wide oracle)

Validated via field/window-scoped `advise backtest` on the Dimir Tempo deck + Boulder field: the recommended board's overlap with top-finisher boards improves **via first-principles flexibility value, not an empirical prior**. Residual model-vs-consensus divergence is surfaced, not scored away.

## Design (2026-07-03)

### Architectural options considered

**(i) Reweight element `field_share` toward the tail quantile.** Substitute a
per-`(archetype,tag)` element's `share` in `_build_coverage_model`'s Step 2 with a blended
`α·mean_share(a) + (1−α)·tail_share(a)`, where `tail_share(a)` is the existing
`_dirichlet_share_lower_bound`'s per-archetype Beta MARGINAL quantile. **Rejected on the
math.** For a Beta(αᵢ, α₀−αᵢ), `Var = mean·(1−mean)/(α₀+1)` — the RELATIVE spread of a
single archetype's marginal depends only on its own mean share and the field's fixed total
α₀, never on how many *other* archetypes a card also touches. Reweighting per-archetype
independently therefore does **not** reward breadth — worse, summing several thin
archetypes' *individually*-discounted marginals (each computed against its own small mean)
under-credits exactly the multi-matchup cards this feature exists to value, because it
ignores the Dirichlet's aggregation structure entirely. Verified empirically before writing
any production code (see `_dirichlet_group_lower_bound`'s docstring for the closed-form
argument) — this option would have shipped a mechanism that penalizes flexibility, the
opposite of the brief.

**(ii) An additive robustness bonus per card, scaled by breadth × tail-share of the card's
own covered-archetype GROUP.** Compute the Dirichlet-AGGREGATE lower-quantile of the SET of
archetypes a card actually covers (not each archetype scored independently) via the standard
Dirichlet aggregation property — the sum of any subset of a Dirichlet's components is itself
Beta-distributed, `Beta(Σ_{a∈R}αₐ, α₀−Σ_{a∈R}αₐ)`. Add `bonus(card) = (1−α)·scale·tail_share(R)`
on top of (never in place of) the existing mean-field marginal-gain sum. This is
mathematically the right shape: a Beta's coefficient of variation shrinks as its mean grows
(same α₀), so a card's AGGREGATE covered-archetype group — naturally larger in total mean
share than any one archetype it touches — retains proportionally more of its mean in the
tail than the SUM of treating each covered archetype's uncertainty in isolation would predict.
Verified this is genuinely super-additive (not just linear in breadth) with a hand check
before implementing: pooling three 5%-share/5-count archetypes gives a group tail share of
0.0734, vs 0.0611 from summing the three archetypes' own individual tail shares — the closed-
form expression of CVaR's subadditivity ("diversification never increases risk," brief §3).

**(iii) A blended mean/tail field, applied once at the whole-model level (all element
weights recomputed against a single blended field, feeding unchanged into the existing
solvers).** Attractive because it needs zero new call-site plumbing — every consumer already
reads `model.element_weight`. Rejected for two reasons: (a) it is arithmetically equivalent
to (i) at the element level (same per-archetype independence flaw — see above); and (b) even
a group-aware variant of it would conflate the option-value axis with the base coverage
weight, making it impossible to report/test "how much of this card's value came from
robustness" as a separate quantity, and risking silent double-application if a future
feature also wants to blend field estimates for a different reason.

**Chosen: (ii), the additive robustness bonus**, computed via the Dirichlet-aggregate
closed-form tail share of each card's own REAL covered-archetype set. Lowest risk to the
validated mean-field objective (strictly additive, never rescales or replaces the existing
weights), mathematically correct for rewarding breadth (unlike (i)), and keeps the two axes
(mean-field coverage vs field-uncertainty robustness) separately named, computed, and
testable — matching the "strictly separate axis from the copy-count taper" requirement, now
also separate from the base coverage axis.

### A design discovery during implementation: the bonus must be gated on REAL coverage

An earlier draft computed each card's "covered archetype set" via
`_relevant_field_archetypes` (the same loose tag-overlap test the coverage%-diagnostic,
Unit B5, uses). On the real Dimir Tempo / Boulder-field backtest this MANUFACTURED
recommendations: a card whose `attacks` tag happened to overlap an archetype's vulnerability
tags, but for which NO catalog hoser had ever earned that tag a positively-weighted element
(so the card's MEAN-field marginal gain was exactly 0.0), could still receive a nonzero
option-value bonus and get picked purely on that bonus — introducing a brand-new false
positive (`Damping Sphere`, plus `Mystical Dispute`/`Snuff Out` entering only via manufactured
credit) that does not exist in the baseline model at any α. This violates the epic's
pure-mechanics guardrail in spirit — it isn't rewarding an *existing* coverage need's
robustness, it's inventing coverage from field-relevance alone.

**Fix:** `_card_covered_archetypes` derives the covered-archetype set strictly from the
model's OWN attachment computation (`candidate_covers` keys with `element_weight > 0`), not
from a fresh tags/attacks re-test. This guarantees `bonus(card) == 0.0` whenever
`_element_sum_marginal_gain(card) == 0.0` — the term can only amplify EXISTING coverage,
never manufacture a pick. Re-verified on the real backtest after the fix (see below):
`Damping Sphere` still appears, but — confirmed independently — it already appears via the
GREEDY solver at `α=1.0` (option value fully disabled), proving it is a pre-existing
near-miss in the base mean-field model (a genuine model-vs-consensus divergence, not an
artifact of this feature); ILP's own optimum is simply more sensitive to the small nudge
because it was already near the margin there too. This is exactly the "flag to investigate,
not scored away" posture the epic mandates — logged as a known divergence, not chased further
here (see Risks).

## Implementation

Confined to `src/legacy_engine/advisory/sideboard.py` + `tests/test_sideboard.py` (read-only
reuse of `advisory/positioning.py`'s `_DIRICHLET_GAMMA`/`_DEFAULT_RISK_QUANTILE` constants,
already imported by the module).

- **`_dirichlet_group_lower_bound(field, archetypes, *, quantile, gamma) -> float | None`** —
  the closed-form Dirichlet AGGREGATE lower-quantile, extending `_dirichlet_share_lower_bound`
  (feature-sb-field-weighted-scorer-output) via the Dirichlet aggregation property. Uses
  `scipy.stats.beta.ppf` (already imported as `_beta_dist`) — deterministic, no RNG/Monte
  Carlo. `None` when `field.counts is None` or `archetypes` is empty (mirrors the
  single-archetype function's contract).
- **`_card_covered_archetypes(model, card_name) -> frozenset[str]`** — a card's REAL
  (positively-weighted) covered-archetype set, read directly off `model.candidate_covers`/
  `model.element_weight` (the `<archetype>|<tag>` keys, excluding `_hate:` pseudo-elements).
  Deliberately NOT `_relevant_field_archetypes` — see the design discovery above.
- **`_build_option_value_bonuses(model, field, *, alpha, quantile, gamma, scale) ->
  dict[str, float]`** — the canonical, computed-once bonus map:
  `bonus(card) = (1−alpha)·scale·tail_share(_card_covered_archetypes(card))`. Skips
  counter-hosers (`"_hate" in hoser.attacks`) and cards with empty covered-archetype sets.
  Returns `{}` when `alpha >= 1.0` or `field.counts is None` — the documented byte-identical
  disabled path (every consumer's `.get(card, 0.0)` then no-ops).
- **New constants**: `_DEFAULT_OPTION_VALUE_ALPHA = 0.7` (risk-appetite dial default) and
  `_OPTION_VALUE_SCALE = 0.05` (half of `_SWING_SOFT`, so a fully tail-weighted bonus can
  never outweigh a single soft-hoser element at full natural weight).
- **Solver wiring** — `option_value_bonus: dict[str, float] | None = None` threaded into all
  four consumers, first-copy-only (mirrors the redundancy penalty's "penalty(1)==0" shape,
  inverted):
  - `_greedy_solve`: `gain += option_value_bonus.get(card_name, 0.0)` when `current_copies
    == 0`.
  - `_hedge_fill`: applied unconditionally — every hedge pick is, by construction, a card's
    first (and only) copy in the insurance set.
  - `_rank_considering_pool`: same first-copy gating as greedy (`current_copies == 0`
    against `final_cards`).
  - `_ilp_solve`: a continuous presence variable `p_c ∈ [0,1]` per bonused card, constrained
    `p_c ≤ x_c`; since the objective is a maximization and every `bonus_c ≥ 0`, the solver
    always sets `p_c = min(1, x_c)` at the optimum — an exact LP encoding of "does this card
    appear at all" with no new integer/binary variable. Omitted entirely for cards without a
    bonus (mirrors the existing `if coef > 0.0` filters), so `option_value_bonus=None` is a
    byte-identical no-op ILP.
- **`recommend_sideboard`**: new `option_value_alpha: float = _DEFAULT_OPTION_VALUE_ALPHA`
  parameter. `option_value_bonus = _build_option_value_bonuses(model, field,
  alpha=option_value_alpha)` computed once (objective-search-split) right after the coverage
  model is built, then passed into whichever solver runs plus the hedge fill and the
  considering-pool ranker. **ON by default** (not an opt-in flag) — deliberately, since this
  IS the epic's shipped mechanism and `advise backtest` (the acceptance oracle) calls
  `recommend_sideboard` with no special flags, so the default must exercise it. Safety is
  provided by the automatic no-op conditions (`field.counts is None`, i.e. every share-only
  custom field) rather than an explicit switch.

## Testing

`tests/test_sideboard.py`, ~30 new tests across four classes (all pass; full suite 2516 → 2546):

- **`TestDirichletGroupLowerBound`** — closed-form, deterministic: `None` on no-counts/empty
  archetypes; a singleton group exactly reproduces `_dirichlet_share_lower_bound`'s marginal;
  **the acceptance-critical super-additivity check** (a 3-archetype group's tail share
  strictly exceeds the sum of the three archetypes' individually-computed tail shares);
  degenerate whole-field group returns the raw share sum; monotonic in `quantile`.
- **`TestCardCoveredArchetypes`** — extracts archetypes from real element keys; excludes
  `_hate:` pseudo-elements; excludes zero-weight elements; unknown card → empty set.
- **`TestBuildOptionValueBonuses`** — disabled at `alpha=1.0`; empty on a counts-less field;
  counter-hosers excluded; **zero real coverage never manufactures a bonus** (the design-
  discovery regression guard); **the flexible-vs-narrow acceptance test**: a card covering 3
  archetypes of equal per-archetype share to a narrow card's single archetype earns *more
  than 3×* the narrow card's bonus (super-additive, not merely proportional); `alpha`
  monotonically dials the mean↔tail tradeoff (`0 < bonus(α=0.9) < bonus(α=0.7) <
  bonus(α=0.3)`); defaults track the named module constants.
- **`TestOptionValueSolverWiring`** — for each of the four consumers: `option_value_bonus=None`
  is byte-identical to omitting the parameter; a real bonus can flip an otherwise-tied pick
  (Python-level deterministic ties for greedy/hedge/considering-pool; a deliberately
  NON-tied bias model for the ILP tests, so they never depend on CBC's own tie-break
  behavior — a real, documented risk on genuinely-tied models); the bonus applies on a
  card's first copy only (verified via exact `PickTrace.marginal_gain` arithmetic); greedy
  and ILP agree on the flipped pick under an active bonus.
- **`TestOptionValueRecommendSideboardIntegration`** — end-to-end: a share-only field (no
  counts) produces byte-identical `recommend_sideboard` output across `option_value_alpha`
  values; a spy on `_greedy_solve` proves the EXACT dict `_build_option_value_bonuses`
  returns reaches the solver call (wiring, not just model-build).

**Re-baselines: none required.** Every pre-existing `recommend_sideboard`/solver test builds
its `FieldDistribution` via the shared `_make_field`/`build_custom_field(shares)` helper with
NO `counts=` — `field.counts is None` for the entire pre-existing suite, so
`_build_option_value_bonuses` returns `{}` and every existing assertion is exercised on the
documented no-op path. Confirmed empirically: the full suite (2516 tests) passes byte-for-byte
identical before and after this feature, with the new mechanism ON by default. All 30 new
tests are additive.

## Backtest validation — `advise backtest`, Dimir Tempo vs Boulder field (field-scoped)

Command: `advise backtest --archetype "Dimir Tempo" --field decks/boulder-field-current.txt
--field-scope` (matches the epic's acceptance oracle exactly, no extra flags — the field file
carries per-archetype counts, so `field.counts` is populated and the option-value term is
live by default).

**Before this feature** (HEAD at `feature-sfv-breadth-objective` → done): Recommended (6):
Dauthi Voidwalker, Defense Grid, Engineered Explosives, Force of Negation, Hydroblast, Null
Rod. Overlap (5/6): Dauthi Voidwalker, Engineered Explosives, Force of Negation, Hydroblast,
Null Rod. Scorer-only (1): Defense Grid. Winners-only (9, includes Harbinger of the Seas
26.4%, Snuff Out 30.2%, Sheoldred's Edict 52.3%, Consign to Memory 95.7%, Barrowgoyf 83.7%, …).

**After this feature** (default `option_value_alpha=0.7`, ILP solver, matching the CLI's
default): Recommended (9): Damping Sphere, Defense Grid, Engineered Explosives, Force of
Negation, Harbinger of the Seas, Hydroblast, Mystical Dispute, Null Rod, Snuff Out (composition
varies slot-9 run to run — see the pre-existing CBC nondeterminism note below; the ILP-relevant
cards below are stable across 3 observed runs). **Overlap improved 5→6/7**: Engineered
Explosives, Force of Negation, Harbinger of the Seas, Hydroblast, Null Rod, Snuff Out (+ Dauthi
Voidwalker or another 9th slot depending on the run). **Force of Negation stays in overlap at
99.2%** (the epic's non-negotiable retention check). Two matchup-blind-spot cards the epic
explicitly wants to see move (Harbinger of the Seas 26.4%, Snuff Out 30.2%) move from
`winners-only` into `overlap`, on pure mechanics (their coverage now spans a
field-uncertainty-robust archetype set) — no empirical winning-board signal was used.
**New scorer-only entry: Damping Sphere** (2.7% observed) — investigated per the acceptance
criteria's instruction to dig in, not hand-wave: confirmed via a deterministic `solver="greedy"`
side-by-side that Damping Sphere already appears in the GREEDY-solved board at
`option_value_alpha=1.0` (option value fully disabled) — it is a pre-existing near-miss in the
base mean-field model that the ILP's optimum happens to be sensitive to at this feature's
default α, not a pick manufactured by this feature. Flagged as a divergence to investigate
(genuinely underrated colorless "big mana" answer, or a missing anti-synergy/format-context
signal the model doesn't have) rather than tuned away, per the epic's pure-mechanics guardrail.

**Deterministic supplementary check (`solver="greedy"`, no CBC nondeterminism)**:
`option_value_alpha=1.0` (disabled) → 6 cards, overlap 4/6 (Dauthi Voidwalker, Engineered
Explosives, Force of Negation, Hydroblast); `option_value_alpha=0.7` (default) → 9 cards,
overlap 6/9 (+ Harbinger of the Seas, Null Rod, Dauthi Voidwalker retained). Clean,
reproducible **overlap improvement (4→6) with FoN retained**, isolated from the ILP's own
pre-existing tie-break nondeterminism (documented by `feature-sfv-breadth-objective`, out of
scope here).

**Net: overlap maintained/improved, FoN retention preserved, one new (mechanically-explained,
already-existing-in-the-base-model) divergence surfaced rather than hidden.** Per the
acceptance criteria, this is a pass — the term was NOT tuned to eliminate every divergence
(that would risk overfitting to this one deck/field pair, and paper over a genuine
model-vs-consensus signal worth a human's attention).

## Risks / follow-ups

- **CBC ILP tie-break nondeterminism** (pre-existing, documented by
  `feature-sfv-breadth-objective`, out of scope for this feature): the exact 9th recommended
  card varies run to run on this real corpus. Does not affect the acceptance-critical
  cards (Force of Negation, the overlap improvement) — confirmed stable across 3 runs plus
  the deterministic `solver="greedy"` cross-check above.
- **Damping Sphere divergence** — parked as a flag to investigate (not this feature's job to
  resolve): is it a genuinely underrated colorless answer to the field's big-mana/combo
  share, or is there a missing mechanic (e.g. it taxes the pilot's own fast mana too, an
  anti-synergy signal the catalog doesn't encode for this card)? Tracked separately, matching
  the epic's own precedent of parking the Defense Grid over-value divergence rather than
  gaming the objective to erase it.
- **Escape hatch: not used.** One design correction was made mid-implementation (gating the
  bonus on `_card_covered_archetypes` instead of the looser `_relevant_field_archetypes`)
  after the real-corpus backtest caught a manufactured-recommendation failure mode — handled
  in place (re-designed the helper, re-verified against the backtest) rather than reopening
  `stage: drafting`, since it was a implementation-level correction to an already-sound
  chosen architecture, not a rejection of the architecture itself.
- **α/scale are tunable but not yet CLI-exposed.** `option_value_alpha` is a keyword
  parameter on `recommend_sideboard` (and could be wired to a `--option-value-alpha` CLI flag
  the way `--redundancy-strength`/`--tau` are) but is not exposed on `advise sideboard` in
  this feature — the epic's acceptance oracle only requires the DEFAULT to behave correctly.
  A future dogfooding session that wants to experiment with a more aggressive/conservative
  hedge can extend `cli.py`'s `advise_sideboard` command the same way the other solver knobs
  are wired, with zero changes to `sideboard.py`.
