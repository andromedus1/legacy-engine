---
description: "Synthesis of the estimand, non-transitive modeling, sparse-evidence, temporal, and validation contracts required to test a decision-useful superarchetype representation."
type: brief
kind: research
content_type: campaign-parent
slug: decision-useful-superarchetype-representation
research_method: /deep-research
verification_status: attested
provenance: agent-synthesis
updated: 2026-08-01
summary: |
  A superarchetype should be tested as a population-standardized prediction over an antisymmetric
  member-pair matchup surface, not as a pooled family win rate or representative deck. The leading
  hypothesis freezes composition-derived membership, estimates member-pair probabilities with a
  non-transitive family hierarchy, and averages posterior predictions under explicitly versioned
  current member shares. Family comparison screens and explains; the playable action remains a
  member archetype selected by a frozen second-stage rule. That hypothesis has no production license
  yet: it must be predictively noninferior without calibration harm and strictly improve the
  two-stage member action over deployed Best Call, member-only, and same-model-direct policies in a
  preregistered future-only benchmark.
key_findings:
  - "The public headline should target the current-regime member mixture; equal, tempered, and overlap-supported mixtures are distinct sensitivity or fallback estimands, not interchangeable renderings."
  - "The modeled primitive is a reciprocal, matchup-specific member-pair probability surface; scalar family strength cannot preserve strategically important cycles."
  - "Composition families may structure partial pooling only after membership is frozen outcome-blind; all active represented members contribute evidence and may falsify, but not silently rewrite, the family."
  - "A finite hierarchical estimate is not an evidence license: direct support, prior dependence, member and player concentration, leave-member-out behavior, selection sensitivity, and typed refusal remain separate outputs."
  - "Outcome state, target-member weights, and taxonomy are separately versioned as-of snapshots; fixed-window and causal-decay baselines must precede more elaborate changepoint machinery."
  - "The next artifact is a Stage-0 feasibility check followed, only if feasible, by an offline benchmark; a production three-level page remains blocked unless family structure is predictively safe and strictly improves the final member-archetype action."
  - "Decision launch is one conjunction over evaluability, predictive safety, decision value versus deployed/member-only/same-model-direct comparators, recurrence, valid nulls, and unanimity across the versioned sensitivity registry; not-evaluated blocks launch."
confidence: speculative
status: draft
related:
  - {slug: .research/briefs/decision-useful-superarchetype-representation/estimand-target-population.md, relationship: depends-on}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/nontransitive-outcome-models.md, relationship: depends-on}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/sparse-selective-evidence.md, relationship: depends-on}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/dynamic-metagame-representation.md, relationship: depends-on}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/validation-decision-utility.md, relationship: depends-on}
  - {slug: .research/briefs/superarchetype-representation-prior-art/scout-landscape.md, relationship: depends-on}
---

# Decision-useful superarchetype representation

## Context

The shipped superarchetype layer provides an outcome-blind composition taxonomy and an honest
opponent-side fallback. The attempted subject-family preview exposed a different problem: pooling
member records does not by itself define whose win probability a family cell reports, preserve
member-specific counters, or establish that sparse family estimates are decision-worthy.

This campaign therefore treats “represent the superarchetype” as five coupled questions:

1. Which population and member-selection policy does the family result describe?
2. Which member-pair probability model preserves reciprocity and strategic cycles while borrowing
   evidence?
3. Which observations support the estimate, and when must the product refuse it?
4. Which time boundary, member shares, and taxonomy version make the claim current and reproducible?
5. Is the representation predictively safe, and does it improve actual member-archetype decisions?

The synthesis is a research contract for an empirical spike. It does not select a production model
from literature, manufacture launch thresholds, or authorize a third ranking table.

**Project decision — playable action.** A user plays an eligible member archetype/deck, not a family
mixture. The family surface is a first-stage screen and explanation. The frozen operational policy
scores each family by posterior-mean common-field `phi_S_current`; chooses a nested-training-selected
tuple from `{0,0.01,0.02} x {0.5,0.8} x {1,3}` for practical-equivalence delta, posterior
probability, and shortlist cap; then chooses the shortlisted eligible member with maximum
posterior-mean common-field `M_a`, breaking ties by stable id. Eligibility is origin legality,
classification, and field share `>=0.001`; the public benchmark has no unobserved pilot restriction.
Refusal falls back to the reconstructed deployed Best Call policy. Validation compares the final
member action with `D0_deployed`, member-only `A0`, and `A1_same_model_direct`, which disables the
screen while retaining identical family-aware predictions. Standalone family regret is out of
contract, and the screen earns decision use only if it beats `A1`.

## Decomposition

- **Estimand and target population** —
  [estimand-target-population.md](estimand-target-population.md) defines two-sided standardization,
  current and synthetic member mixtures, support, and composition sensitivity.
- **Non-transitive outcome models** —
  [nontransitive-outcome-models.md](nontransitive-outcome-models.md) defines the reciprocal
  member-pair surface and the structured, cellwise, scalar, and latent candidate models.
- **Sparse and selectively observed evidence** —
  [sparse-selective-evidence.md](sparse-selective-evidence.md) separates observation, borrowing,
  falsification, influence, and typed refusal.
- **Dynamic metagame representation** —
  [dynamic-metagame-representation.md](dynamic-metagame-representation.md) separates outcome,
  composition, and taxonomy clocks and defines causal as-of reconstruction.
- **Validation and decision utility** —
  [validation-decision-utility.md](validation-decision-utility.md) specifies the future-only,
  coverage-aware benchmark and whole-idea rejection gates.

## Key findings

### 1. The family result is a standardized experiment, not a pooled record

For family `S` against family `T`, the coherent primitive is

\[
\theta_{S,T}^{r,z}(u,v)=
\sum_{a\in A_S}\sum_{b\in A_T}u_a^S v_b^T p_{ab}^{r,z},
\]

where `p_ab` is a member-pair win probability, `u` and `v` are named member-selection policies,
and `(r,z)` identifies the time and target context. Marginal standardization obtains its meaning
from the target distribution; predicting at an average or modal profile targets a different and
sometimes artificial population `[superrep-target-populations]{24}`. Population weighting likewise
requires explicit cell sizes and within-cell representativeness rather than treating regression as
a universal repair `[superrep-estimand-gelman-weighting]{8}`.

**Project decision — estimable `WeightSnapshot`.** Current member shares come from a named
classified-deck sampling frame, half-open as-of window, provenance strata, taxonomy version, raw
counts, and a preregistered multinomial baseline plus simple Dirichlet or event-block-bootstrap
smoothing candidate. The snapshot carries weight draws, uncovered mass, effective member count,
method, and seed. Weight uncertainty remains separate from outcome uncertainty until a
preregistered pairing/nesting step standardizes the draws. Thin or frame-mismatched shares produce
typed refusal or sensitivity, not fixed certainty.

For “which strategy family is well positioned now?”, use current-regime member shares within the
subject family and one common current-field opponent distribution when comparing families. Use
current conditional shares on both sides for explanatory family-by-family cells. Equal-member and
tempered policies remain labeled sensitivity estimands. Overlap restriction can improve precision
under weak support, but it changes the represented population rather than rescuing the original
one `[superrep-estimand-balancing-weights]{7}` `[superrep-estimand-limited-overlap]{9}`.

A modal or medoid deck remains useful for explaining what a family looks like. It is not the
family-performance estimand: sampling a typical representative and sampling heterogeneous units to
cover a target population are different designs `[superrep-estimand-target-generalizability]{11}`.

### 2. Preserve the matchup surface before aggregating it

The outcome model must fit one antisymmetric log-odds surface, so reversing a matchup negates the
logit and complements the probability. Antisymmetric relational models can preserve cyclic
advantages that scalar ratings cannot `[superrep-chen-intransitivity]{4}`. A Bradley–Terry strength
difference is therefore a necessary transitive baseline, not an adequate endpoint; transitive and
cyclic components are mathematically distinct `[superrep-balduzzi-gamescapes]{2}`.

**Algebraic derivation — oriented context.** Reciprocity is
`p(a,b,z)=1-p(b,a,R(z))`, where `R` swaps p1/p2 and every side-specific field while retaining shared
event, rules, format, round, and time fields. **Project decision — current observability:** the
engine currently extracts date/provenance, player-name strings, aggregate decisive result, and
archetype/variant, while its tally drops draws/byes/forfeits and ambiguous/unmatched rows and does
not retain event/round/player/repeated-pair dependence or play/draw, game-state, or match-format
fields. Missing required context is typed and audited at Stage 0; it is not claimed as a fitted
covariate. The current decisive-match estimand excludes draws. A future draw-aware outcome requires
a separately declared reversal contract. Here `Y=1` is subject win conditional on a recorded,
successfully joined, non-mirror, decisive eligible match; `Y=0` is subject loss. Draws/ties,
byes/forfeits, ambiguous/unmatched rows, and mirror rows are outside the fitted/proper-score target
and require exclusion coverage by member pair/source/time. Decision standardization nevertheless
retains same-archetype opponent field mass as structural `eta_aa=0`, `p_aa=0.5` under randomized
reversal-invariant orientation. Theta, phi, `M_a`, reverse cells, and oracle utility include that
diagonal target mass without fitting or scoring mirror observations. If context is marginalized
under `q`, reverse orientation uses
the pushforward `R#q`, not untransformed `q` unless it is reversal-invariant.

Stage 0 emits a field-disposition schema for outcome, event/date/source, players, round/record,
play/draw, match format, game state, repeated pair, and taxonomy: raw observation, retained/model-
ready state, typed missingness, marginalization target, reversal, dependence consequence, claim
scope, and `model_ready|weaker_claim:<name>|claim_blocking`. Event id must be rehydrated for event-
block uncertainty; absent stable player identity is the named
`weaker_claim:event_clustered_player_dependence_unresolved` only if Stage-0 simulation validates the
frozen bound, otherwise it blocks launch. Any audit-pending or claim-blocking row makes
`EVALUABLE=false`.

**Empirical hypothesis — structured family model.** The leading interpretable candidate is

\[
\eta_{ij}=(s_i-s_j)+\Phi_{g(i),g(j)}+
(u_{i,g(j)}-u_{j,g(i)})+\rho_{ij},
\]

with a scalar member component, skew family-pair interaction, member-by-opponent-family deviations,
and an optional strongly shrunk pair residual. This exact layering is a campaign hypothesis, not a
claim supplied by one source. Related Bayesian intransitive models show both that antisymmetric pair
adjustments can be learned and that recovery deteriorates when repeated comparisons are thin
`[superrep-spearing-intransitive-bt]{23}`.

A low-rank skew model is the principal non-family challenger because it shares evidence without
forcing transitivity. Its rank is a substantive assumption: long strategic cycles can require a
high-dimensional representation, so a compact embedding may erase local counters
`[superrep-balduzzi-gamescapes]{2}`. Outcome-response graph contraction is valuable as a diagnostic
behavioral taxonomy `[superrep-response-graphs]{22}`, but using it as the composition family would
change the ontology and reuse outcomes to define the hierarchy they are meant to test.

### 3. Membership fixes the population; outcomes test the sharing claim

Composition-derived membership must be frozen before fitting outcomes. Defining, curated, and
assigned roles remain provenance, but every active member with positive target weight contributes
its observed outcomes and enters concentration, prediction, and influence checks. Excluding an
assigned member's outcomes while weighting that member into the result would make the evidence and
estimand describe different families.

This does not grant all members equal ability to lend evidence to one another. Leave-member-out
prediction, member residuals, and direct-versus-indirect comparisons must be allowed to falsify the
family exchangeability hypothesis. Posterior predictive checks can target concrete discrepancies,
but passing them never proves adequacy `[superrep-posterior-predictive]{19}`. A family that fails is
refused or reviewed later through an outcome-blind taxonomy process; it is not repaired by moving a
member inside the same outcome fit.

### 4. Sparse evidence needs a ledger, not a single gate

The matchup matrix reflects participation, pairing and progression, repeated pilots, reporting,
classification, and structural absence. Informatively observed matrices can be biased without
additional identifying structure, but the available result depends on low-rank and covariate
assumptions not established for Legacy `[superrep-informative-missingness]{15}`. Nonrandom assignment
can also leave residual bias after random-effects adjustment `[superrep-nonrandom-scheduling]{18}`.
The immediate obligation is therefore to audit these mechanisms and run structured sensitivity
analyses, not to assume missing-at-random or deploy an unearned correction.

Weak priors can keep separated logistic cells finite `[superrep-weak-priors-separation]{32}`; that is
useful regularization, not observational identification. The evidence contract separately records
direct matches, players and events; borrowed versus extrapolated target mass; prior sensitivity;
member, player and event concentration; deletion influence; direct-versus-indirect conflict; and
uncertainty. Node splitting supplies the shape of a direct/indirect diagnostic
`[superrep-node-splitting]{17}`, but its indirect side must come from the chosen non-transitive model,
not scalar path consistency.

Typed outcomes include directly supported, model-supported lean, prior-dominated, concentrated,
family-inconsistent, selection-sensitive, unidentified, computationally unreliable, and not
assessed. Low measured heterogeneity cannot license pooling when contributors are too few to reveal
disagreement `[superrep-heterogeneity-i2]{14}`.

### 5. “Current” binds three different temporal states

Every result references separate immutable `OutcomeSnapshot`, `WeightSnapshot`, and
`TaxonomySnapshot` identities. An as-of claim may use only evidence and classification decisions
available at that boundary. A causal fixed window and causal exponential decay are mandatory
baselines; geometrically weighted paired-comparison models support sequential prediction and can be
competitive with more parameterized dynamics `[superrep-dynamic-bt-ewma]{5}`.

**Project decision — historical labels.** An actual archived registry is a
`contemporaneous_registry`. A later composition-only policy rerun with origin-available inputs is a
`retrospective_policy_replay`, never historical truth. They receive different source/version labels;
missing contemporaneous snapshots remain acquisition gaps. The primary analysis freezes one
taxonomy at each origin, while preregistered composition-only boundary scenarios test ambiguous
members without letting outcomes choose membership.

Probabilistic run-length/changepoint mixtures are challengers, not defaults. Their reset assumptions
conflict with smooth-evolution assumptions and must compete empirically
`[superrep-bocpd-boundary]{3}` `[superrep-dynamic-bt-kernel]{6}`. Taxonomy review is separately
scheduled and versioned, with bounded hysteresis, stale-state escape conditions, and old/new
definition bridges. Continuity can lag real present structure, so smoothness is not evidence of
currency `[superrep-temporal-persistence-lag]{25}`.

Published drift should show both current-weight and fixed-reference standardizations. Their
difference separates composition movement from changes in the modeled matchup surface without
numerically splicing different family definitions into one apparently continuous probability.

### 6. Future-only evidence decides whether the idea ships

**Project decision — authoritative launch conjunction.** Stage 0/nested training freezes
`alpha`, `eps_LL`, `eps_CAL`, regret non-harm `eps_R`, strict utility margin `delta_J>0`, top-k weight
`lambda`, recurrence `r_min`, `k_action`, `delta_oracle`, `n_CAL`, subgroup/dependence definitions,
null repeats, and the complete sensitivity registry. The practical top-k set includes the top
`k_action` future members plus those within `delta_oracle` of best; calibration is the maximum
absolute cumulative `(y-p)` divided by group size for groups of at least `n_CAL`. With
`J=-regret + lambda*top_k_hit` and one-sided `(1-alpha)` bounds, launch
requires exactly:

- `EVALUABLE`: Stage 0, required origins, nested-training `candidate_C_id`, `D0_deployed`, `M0/A0`,
  matching `A1_same_model_direct`, fits, bounds, nulls, context disposition, and scenario closure all
  complete with no claim-blocking row;
- `PREDICTIVE_SAFE`: `UCB(LL_C-LL_M0)<=eps_LL` and
  `UCB(CAL_C-CAL_M0)<=eps_CAL` globally and in every preregistered supported subgroup;
- `DECISION_VALUE`: for each `d in {D0,A0,A1}`, `LCB(J_C-J_d)>=delta_J` and
  `UCB(regret_C-regret_d)<=eps_R`;
- `RECURRENT`: positive point utility difference versus every comparator in at least `r_min`
  origins and no era block with regret-harm bound above `eps_R`;
- `NULL_VALID`: `LL_B0_market-LL_C` and `J_C-J_D0` exceed their outcome-null quantiles, and the
  comparable screen increment `J_C-J_A1` exceeds the shuffled-hierarchy quantile under the fixed
  external mapping; comparable shuffled member-pair `LL_M0-LL_C` is also reported; and
- `SENSITIVITY_PASS`: every preceding statistical clause passes by unanimity/worst case in every
  versioned taxonomy, weight, prior, and context scenario.

The status is `NOT_EVALUATED` when `EVALUABLE` is false, `PASS` when it is true and every other
conjunct is true, and `FAIL` otherwise. Launch is allowed only for `PASS`. Thus pass, fail, and
not-evaluated are logical complements; missing evidence blocks launch. Coverage and abstention are
secondary and cannot replace a conjunct.

The benchmark reconstructs taxonomy, target weights, temporal state, hyperparameters, and refusal
thresholds at rolling forecast origins. Ordinary leave-one-out can use later observations to predict
earlier ones, whereas leave-future-out preserves the intended time order
`[superrep-validation-leave-future-out]{28}`.

Held-out log loss is the primary predictive score, with Brier score, calibration, interval behavior,
coverage, regret, top-k uncertainty, and recommendation stability reported separately. Proper scores
reward honest probabilities `[superrep-validation-proper-scores]{30}`, but better prediction error
can coexist with worse downstream regret `[superrep-validation-decision-regret]{27}`. Top-k recovery
also depends on real separation at the selection boundary, so an unresolved future ranking is not
evidence for or against a candidate `[superrep-validation-robust-topk]{31}`.

All candidates are compared on identical forecast cases before applying refusal. This all-case
score is diagnostic only and does not license unsupported claims; evidence gates govern the served
policy and frozen archetype-only fallback. Outcome permutation and size/prevalence-matched
outcome-blind family shuffles rerun the whole pipeline; permutation tests
probe whether learned association survives destruction of the hypothesized signal
`[superrep-validation-permutation]{29}`.

**Project decision — shuffled-null comparability.** Member-pair predictive metrics remain comparable
across shuffled hierarchies. Family and decision metrics are launch-comparable only under a fixed
external production-taxonomy target, eligible member action set, and two-stage member-selection
rule. Metrics over each shuffled partition's own synthetic families describe different populations
and are diagnostic only.

## Candidate-method comparison

| Candidate | Structure retained | Borrowing claim | Primary failure test | Role |
|---|---|---|---|---|
| Current production ladder | Existing direct, pooled, and imputed member cells | Existing licensed fallbacks | Future-only score, calibration, and coverage on identical cases | Product baseline |
| Independent antisymmetric cells | Full pair-specific cycles | Common shrinkage only | Does family structure improve beyond honest cellwise regularization? | Member-only baseline |
| Scalar hierarchical Bradley–Terry | Global transitive strength | Member/family strength hierarchy | Does it erase predictive matchup reversals? | Parsimonious baseline |
| `C01/C02` fixed-family hierarchy | Family cycles and member deviations, without/with pair residual | Composition families predict related counter behavior | Leave-member-out failure, negative transfer, prior domination | Ordered production candidates |
| `C03/C04/C05` skew rank 1/2/4 | Learned cyclic geometry | A small latent dimension predicts unobserved pairs | Future loss in local niches; unstable rank/dimension | Ordered production challengers |
| Outcome-response graph contraction | Directed behavioral roles | Similar response profiles form useful categories | Instability under missing edges; ontology leakage | Diagnostic/alternative taxonomy, not primary estimator |

Temporal policy is an orthogonal comparison layered onto a fixed outcome candidate: expanding
history, recent windows, causal decay, and full/partial-reset changepoint variants are selected only
inside each outer origin's nested training, never by the outer era. Standardization is also held
constant across model candidates so a score difference cannot be caused by silently changing
populations.

**Project decision — frozen candidate selection.** For each outer origin, inner rolling training
runs feasibility, convergence, predictive-safety, decision-value, and recurrence qualification over
fixed order `C01_family_no_pair_residual`, `C02_family_pair_residual`, `C03_skew_rank1`,
`C04_skew_rank2`, `C05_skew_rank4`; chooses the first inner-qualified id, then the
lowest-complexity hyperparameter tuple and lexicographically smallest configuration hash; and
freezes that `candidate_C_id` before opening the outer holdout. No qualified candidate or a missing
selection result makes selection `NOT_EVALUATED`. The outer holdout evaluates exactly that candidate
once and never selects “any passing model.” `A1` uses the identical selected model with screening
disabled. Every null and sensitivity pipeline reruns the same selection algorithm on its own
transformed inner training data.

## Integrated research contract

**Project decision — ordered benchmark.** The next implementation is a reproducible offline benchmark with these ordered contracts:

0. **Stage-0 feasibility.** Count effective independent origins; simulate detectable paired log-loss
   and two-stage regret/top-k differences; budget nested tuning, null repeats, leave-member-out and
   scenario refits; audit context fields and historical registries; and abort or downscope before
   model competition if power, independence, or compute is inadequate.
1. **Freeze the question.** Name the decisive-match outcome, current target population, exact
   two-stage policy ladder, `D0_deployed`, `M0/A0`, `A1_same_model_direct`, forecast horizon, common
   opponent field, sensitivity policies, every gate margin, and uncertainty rule.
2. **Freeze origin state.** Load an actual `contemporaneous_registry` or explicitly label a
   `retrospective_policy_replay`; reconstruct outcome cutoff, weight draws, classification cutoff,
   boundary scenarios, and eligible population using only origin-available information.
3. **Build an evidence ledger.** Retain member-pair wins/losses, unique players and events, temporal
   weights, graph connectivity, family roles, and exposure strata where available; type absent
   play/draw, format, game-state, player/event/round, and repeated-pair context instead of assuming it.
   Keep mirror rows in exclusion coverage but out of fitting and proper-score cases.
4. **Select once inside training.** Fit `C01..C05` on inner rolling folds, apply the full inner
   qualification and deterministic complexity/hyperparameter/hash tie rule, and freeze one
   `candidate_C_id` before each outer holdout. Orient each unordered pair once, preserve reciprocity,
   emit member-pair draws, and keep diagnostics. Missing selection is `NOT_EVALUATED`; outer results
   never choose or retune the candidate.
5. **Standardize posterior predictions.** Compute current, balanced, tempered, and supported-target
   family quantities using separately generated outcome and `WeightSnapshot` draws. Store sampling
   frame, uncovered mass, taxonomy and snapshot identities with every result. Preserve
   same-archetype opponent mass at structural 0.5 in theta, phi, member action, and oracle utility;
   never renormalize it away because mirror rows were excluded from evidence.
6. **Falsify family borrowing.** Run member-level predictive checks, leave-member-out tests,
   direct/indirect comparisons, three concentration ledgers, and observation-process sensitivities.
   Emit typed states; never infer caveats from provenance strings.
7. **Validate the full conjunction.** On common future cases compute `PREDICTIVE_SAFE` against
   `M0`; compute `DECISION_VALUE` and regret non-harm against `D0_deployed`, `A0_member_only`, and
   `A1_same_model_direct`; then compute `RECURRENT` with the frozen `r_min` and era-block rule.
   This explicitly tests whether the screen adds value beyond identical predictions without it.
8. **Run nulls and every sensitivity.** Refit complete outcome-permutation and family-shuffle
   pipelines, including their own identical nested candidate selection; do the same in every
   sensitivity scenario; bind each `A1` to that pipeline's selected candidate; compare screen nulls
   only under the fixed external mapping; then require `NULL_VALID` and unanimity/worst-case
   `SENSITIVITY_PASS`.
9. **Apply the exact status function before rendering.** `NOT_EVALUATED` iff `EVALUABLE` is false;
   otherwise `PASS` iff predictive safety, decision value, recurrence, null validity, and sensitivity
   all pass; otherwise `FAIL`. Emit every metric, bound, threshold, null quantile, scenario result,
   and typed missing reason. Only `PASS` may inform a production three-level decision page.

Numeric thresholds for useful coverage, tolerable regret, calibration error, composition reversal,
and unsupported target mass are intentionally absent. They are project decisions to preregister
from operational costs and early folds, not literature constants.

## Contradictions and tensions

### Current-population fidelity versus estimable support

Current-share standardization answers the recognizable product question, but weak support may make
that population model-dependent. Overlap restriction can improve precision only by changing the
population `[superrep-estimand-balancing-weights]{7}`. This tension is not resolved by choosing the
more stable number: serve the current target or refuse it; label any supported-subset result as a
different estimand.

### Fixed composition taxonomy versus behavioral grouping

The product's superarchetypes are outcome-blind composition families. Response-graph methods group
strategies by their outcome relations `[superrep-response-graphs]{22}`. These constructs may disagree
without either algorithm being defective. The campaign keeps composition membership fixed and uses
behavioral disagreement to test borrowing; it does not paraphrase one ontology into the other.

### Frozen primary taxonomy versus membership uncertainty

An evaluable primary fit needs one outcome-blind taxonomy fixed at the origin, while composition
evidence can leave borderline assignments genuinely uncertain. **Project decision:** the versioned
generator uses legal/classified/current-share-`>=0.001` members, a frozen numeric composition
inclusion threshold and boundary band, and `assigned` provenance to identify candidates; assigns one
composition-only runner-up-or-exclusion alternate; takes at most four by absolute margin/stable id;
and emits the complete at-most-16 primary/alternate Cartesian closure. Overflow blocks launch.
Every scenario is hashed with policy/origin/provenance. Every launch clause must pass in every
scenario by unanimity/worst case. Outcome-based global policy selection is prohibited or nested
entirely inside training folds; outcomes never choose a member's preferred scenario.

### All represented members contribute versus family coherence

Including assigned members makes evidence match the represented current population, but may destroy
apparent homogeneity and reduce coverage. Excluding them would produce a cleaner estimate for a
different family. The unresolved empirical question is whether frozen composition families predict
their assigned members out of sample; the benchmark must allow a negative answer.

### Finite regularized predictions versus observational identification

Weak priors can solve separation `[superrep-weak-priors-separation]{32}`, while selective observation
can still bias the estimand `[superrep-informative-missingness]{15}`. Computational existence and
evidential support are different properties. A converged posterior cannot replace support,
selection, and prior-dependence diagnostics.

### Smooth adaptation versus discrete reset

Kernel dynamics assume smooth temporal evolution `[superrep-dynamic-bt-kernel]{6}`; online
changepoint models represent discrete resets `[superrep-bocpd-boundary]{3}`. Legacy plausibly has
both adaptation and ban-driven breaks. The campaign does not reconcile incompatible transition
assumptions in prose: fixed windows, decay, full reset, and partial reset compete at future
boundaries.

### Identity continuity versus present-state fidelity

Hysteresis reduces taxonomy churn, but persistent history can bias inferred groups toward past
structure `[superrep-temporal-persistence-lag]{25}`. Bounded continuity therefore needs a stale-state
escape hatch; neither low churn nor a smooth chart is a quality metric.

### Broad prediction versus selective service

Proper scores require candidates to face common forecast cases
`[superrep-validation-proper-scores]{30}`, while honest evidence gates may refuse decisions. Both are
required: compare latent predictive quality on all common cases, then evaluate the served policy
with coverage and fallback cost. The all-case result is never a display license; the served evidence
gate remains hard. Served-only accuracy would reward hiding difficult cells.

### Probabilistic accuracy versus decision utility

Proper scoring and downstream regret can disagree `[superrep-validation-decision-regret]{27}`.
Neither result may be collapsed into the other. A candidate must satisfy both the probabilistic
contract and the deck-selection contract, with practical indifference when future rankings are not
separated.

## Challenge: what would make the recommendation fail?

The evaluated recommendation fails exactly when `EVALUABLE=true` and at least one of
`PREDICTIVE_SAFE`, `DECISION_VALUE`, `RECURRENT`, `NULL_VALID`, or `SENSITIVITY_PASS` is false. This
includes predictive harm, calibration harm, failure to clear `delta_J` or regret non-harm versus any
of `D0/A0/A1`, insufficient recurrence, null-indistinguishable gains, or one failed versioned
sensitivity scenario. In particular, failure versus `A1_same_model_direct` means the family screen
has not earned decision use even if family borrowing improves member predictions.

The recommendation is `NOT_EVALUATED`, not failed, exactly when Stage 0, a required comparator or
origin, nested candidate selection, context disposition, fit/bound, null repeat, or scenario closure
is missing. Selecting or retuning a candidate from outer-holdout results is a protocol violation and
also yields `NOT_EVALUATED`. That distinction
preserves epistemic honesty but has the same deployment result: launch is blocked. Only the complete
conjunction is `PASS`. If `FAIL` or `NOT_EVALUATED`, superarchetypes remain navigation and explanation
while decisions stay at member-archetype resolution.

## Coverage

The campaign covers:

- current, balanced, tempered, overlap-supported, and user-policy estimands;
- reciprocal cellwise, scalar, fixed-family, discrete-intransitivity, low-rank, and response-graph
  model families;
- sparse support, selective exposure, repeated pilots, concentration, influence, heterogeneity,
  direct/indirect conflict, uncertainty, and typed refusal;
- causal windows, exponential decay, run-length uncertainty, taxonomy lifecycle, bridges, and
  composition/performance drift decomposition; and
- rolling future validation, proper scores, calibration, abstention, regret, top-k uncertainty,
  leakage checks, and negative controls.

The campaign does not establish:

- the actual MTGO/Legacy pairing, drop, publication, and classification selection mechanisms;
- whether stable player, event, round, bracket, and play/draw identifiers exist across the corpus;
- an identified missing-not-at-random correction for this dataset;
- numeric launch thresholds or the number of independent origins available;
- that composition-derived families are outcome-exchangeable;
- a universal low-rank dimension, temporal half-life, or changepoint policy; or
- enough future evidence to estimate a definitive family-cell “truth.”

Those are explicit empirical acquisition and benchmark gaps. They are not filled by stronger prose
or by a denser preview.

## Related

- [Scout landscape](../superarchetype-representation-prior-art/scout-landscape.md) supplied the
  prior-art map and decomposition lens; it is not a citation source for this synthesis.
- [Estimand and target population](estimand-target-population.md) owns population meaning and
  composition sensitivity.
- [Non-transitive outcome models](nontransitive-outcome-models.md) owns the candidate probability
  surfaces and reciprocity contract.
- [Sparse and selectively observed evidence](sparse-selective-evidence.md) owns support,
  falsification, influence, and refusal.
- [Dynamic metagame representation](dynamic-metagame-representation.md) owns causal as-of state and
  taxonomy continuity.
- [Validation and decision utility](validation-decision-utility.md) owns the benchmark, negative
  controls, and rejection criteria.

## Campaign Metadata

- **Seed:** decision-useful superarchetype representation.
- **Method:** `/deep-research`; five specialist branches followed by synthesis.
- **Date:** 2026-08-01.
- **Specialist verification:** all five briefs attested; each remains `status: draft` with
  `confidence: speculative`.
- **Synthesis provenance:** agent synthesis over the five attested briefs; no additional research.
- **Independent evaluation:** first isolated evaluation returned `NEEDS-REVISION`; its methodological
  blockers are incorporated here, with fresh reevaluation pending.
- **Citation-chain and adversarial verification:** pending campaign-level checks.
- **Final campaign report:** pending; this section is a placeholder for evaluator score, verified
  citation count, final edge count, unresolved gaps, and promotion disposition.
