---
description: "A preregistered future-only validation protocol for deciding whether superarchetype representations improve probabilistic forecasts and real deck-selection decisions."
type: brief
kind: research
slug: decision-useful-superarchetype-representation-validation-decision-utility
research_method: /deep-research
verification_status: attested
provenance: agent-synthesis
updated: 2026-08-01
summary: |
  A superarchetype representation should ship only if it is predictively safe and strictly improves
  a predeclared two-stage family-screen-to-member-archetype decision over deployed Best Call, the
  member-only policy, and the same family-aware predictions with screening disabled.
  The comparison must be preregistered, rolling-origin, and coverage-aware: log loss, Brier score,
  calibration, abstention, agency/rank stability, and decision regret are separate outcomes rather
  than substitutes. Shuffled taxonomy and outcome-permutation controls test whether any gain comes
  from real family structure. The whole representation idea should be rejected if it cannot beat
  simpler baselines out of time on the playable member action or if valid shuffled-label controls
  explain the gain; coverage remains a secondary policy diagnostic.
key_findings:
  - "Use rolling forecast origins with all taxonomy, target weights, hyperparameters, and refusal thresholds reconstructed from information available at each origin; ordinary leave-one-out validation leaks the future into the past."
  - "Compare every candidate on an identical intersection of forecast cases using strictly proper log loss as the primary predictive score, with Brier score, calibration diagnostics, interval performance, and explicit coverage as complementary outcomes."
  - "Abstention must be evaluated as a secondary risk-coverage policy with predeclared costs; it can diagnose service quality but cannot substitute for strict member-action improvement."
  - "The playable action is an eligible member archetype: family ranking only screens a frozen shortlist before a same-origin second-stage member choice, whose future regret/top-k utility is compared with the archetype-only policy."
  - "The family screen earns decision use only if it beats the deployed Best Call policy, the member-only action, and the same family-aware outcome model selecting members with screening disabled, while preserving regret non-harm."
  - "Outcome permutation and outcome-blind family-label randomization are negative controls: a proposed family model must outperform its own null pipeline, not merely produce coherent-looking tables."
  - "Failure criteria apply to the representation concept, not just one estimator: predictive harm, no strict two-stage member-action gain, or gains indistinguishable from valid shuffled-taxonomy controls should stop the three-level page."
confidence: speculative
status: draft
related:
  - {slug: .research/briefs/decision-useful-superarchetype-representation/estimand-target-population.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/nontransitive-outcome-models.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/sparse-selective-evidence.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/dynamic-metagame-representation.md, relationship: parallel-to}
---

# Validation and decision utility

## Scope and conclusion

This branch defines how to decide whether a superarchetype representation is useful. It does not
choose the target population, outcome-model architecture, evidence gates, or temporal regime
algorithm. Those are inputs supplied by sibling branches and frozen before the final evaluation.

The validation target is deliberately stronger than “more nonblank cells.” A representation must:

1. predict genuinely future matches at least as well as simpler member-level alternatives;
2. remain probabilistically calibrated rather than merely rank cells plausibly;
3. improve the decisions the ranking is meant to support;
4. report coverage and abstention without allowing either to substitute for decision value; and
5. beat negative controls that preserve superficial data structure while destroying the family
   signal.

If it does not, the correct result is to retain the archetype-level product and treat family labels
as navigation or explanation only. A polished third table is not evidence.

**Project decision — one launch rule.** Section 7 is the sole authoritative machine-evaluable gate:
`status = PASS` only when `EVALUABLE AND PREDICTIVE_SAFE AND DECISION_VALUE AND RECURRENT AND
NULL_VALID AND SENSITIVITY_PASS`; `NOT_EVALUATED` and `FAIL` both block launch. The authoritative
deployed comparator is `D0_deployed` Best Call. `M0/A0` and the same-model screen ablation `A1` are
additional required comparators, not optional diagnostics. Coverage, abstention, narrower intervals,
or a better-looking family table are secondary and cannot satisfy any missing conjunct.

## Stage 0 — feasibility before model competition

**Project decision — abort/downscope gate.** Before finalizing the candidate ladder, preregister and
run a feasibility artifact that:

- counts candidate forecast origins and estimates their effective independence under overlapping
  training windows, repeated events, and any available player or pairing identifiers;
- simulates or bootstraps detectable paired differences in log loss and the two-stage member-action
  regret/top-k endpoint over plausible effect sizes and dependence blocks;
- budgets nested tuning for model structure, temporal policy, weight smoothing, refusal thresholds,
  and the family-to-member rule without spending the final holdout;
- specifies the outcome-permutation and shuffled-family null repeats needed for stable tail
  comparisons;
- estimates fit, refit, leave-member-out, sensitivity-scenario, and null-pipeline compute cost; and
- records which required context fields and historical registry snapshots are actually available.

If Stage 0 cannot support a credible noninferiority margin and strict decision-improvement test,
retain only simpler candidates, reduce the claim, or stop before the model contest. Reusing the same
few origins as tuning, power analysis, and final evidence is not an acceptable workaround.

## 1. Preregister the comparison before the final holdout

### 1.1 Candidate set

**Empirical hypothesis — model ladder.**

The study should compare a small, frozen ladder rather than repeatedly tuning one preferred model:

- **`B0_market` market/base-rate baseline:** one global or regime-specific win probability;
- **member-only baseline:** regularized archetype-pair estimates with no family borrowing;
- **current production baseline:** the existing direct/pooled/imputed ladder and refusal rules;
- **scalar hierarchical baseline:** a reciprocal but transitive member-strength model;
- **`C01_family_no_pair_residual`:** family-pair effects plus member deviations;
- **`C02_family_pair_residual`:** the same hierarchy plus the strongly shrunk pair residual; and
- **`C03_skew_rank1`, `C04_skew_rank2`, `C05_skew_rank4`:** predeclared low-rank antisymmetric
  challengers.

All candidates must emit member-pair predictive distributions. The estimand branch then applies the
same target weights to every candidate. This prevents a model comparison from silently becoming a
comparison between different represented populations.

**Project decision — final candidate selection.** For each outer forecast origin, run the following
algorithm using only its training prefix:

1. Run inner rolling feasibility, convergence, candidate-specific tuning, `PREDICTIVE_SAFE`,
   `DECISION_VALUE`, and `RECURRENT` for `C01` through `C05`. Null and sensitivity gates are not
   selection inputs; excluding them prevents recursive selection inside a null/scenario pipeline.
2. Mark a candidate `inner_qualified` only when every inner clause passes. Choose the first qualified
   id in fixed least-complex order `C01 < C02 < C03 < C04 < C05`. Within an id, choose the lowest-
   complexity hyperparameter tuple, then lexicographically smallest configuration content hash.
3. Freeze `candidate_C_id`, its complete model/prior/temporal/weight configuration, and its screened
   policy tuple before opening the outer holdout. Evaluate that frozen candidate exactly once.

If no candidate qualifies or any required inner selection result is missing, selection returns
`NOT_EVALUATED` and outer launch is blocked. The outer holdout may reject the frozen candidate but
may never choose another candidate, choose “any model that passes,” or retune the selection rule.
`A1_same_model_direct` always binds to that exact `candidate_C_id` and configuration with screening
disabled.

### 1.2 Locked protocol

**Project decision — preregistration contract.**

Before opening the final evaluation window, record:

- forecast origins and horizons;
- eligible events, matches, pilots, archetypes, and outcome definition;
- taxonomy versioning and how an origin reconstructs the taxonomy available at that date;
- candidate formulas, prior families, hyperparameter search spaces, and convergence rules;
- fixed `C01..C05` complexity order, inner-qualification clauses, hyperparameter/hash tie rule, and
  per-origin `candidate_C_id` selection record;
- target-weight policies and composition-sensitivity scenarios;
- predictive and decision metrics, their priority, and uncertainty procedure;
- refusal reasons and thresholds;
- minimum useful coverage and maximum tolerable decision regret;
- negative controls;
- model-, family-, and whole-idea rejection criteria;
- the two-stage family shortlist and member-selection algorithm, tie breaks, fallback, and the
  archetype-only comparator over the identical eligible member set;
- the fixed external action/target mapping used for shuffled-family decision controls; and
- the Stage-0 origin, power, null-repeat, and compute-budget disposition.

Exploratory folds may set these choices, but the final future block may not. Bürkner, Gabry, and
Vehtari show why ordinary leave-one-out validation is wrong for future prediction: later
observations can influence a prediction for an earlier time. Leave-future-out instead respects the
past-to-future information order, and its origin and horizon must match the intended use
`[superrep-validation-leave-future-out]{28}`.

Preregistration here is a project protocol, not a claim that one source prescribes these exact
Legacy thresholds. Its purpose is to keep post-hoc model, horizon, and refusal choices from turning
the test set into another training set.

## 2. Rolling-origin evaluation

### 2.1 Fold construction

Use expanding or bounded training windows ending at a sequence of chronological origins. At each
origin:

1. expose only data available by that timestamp;
2. load an actual archived `contemporaneous_registry` when available; otherwise run and label a
   `retrospective_policy_replay` using only origin-available composition data—never historical truth;
3. reconstruct eligible archetypes, temporal regime state, and member-share draws from the origin's
   declared sampling frame;
4. fit or update every candidate without future outcomes;
5. issue predictions and refusal states for the predeclared horizon; and
6. score against matches that occur inside that horizon.

The primary horizon should match the operational refresh-to-decision interval. Additional shorter
and longer horizons are sensitivity analyses, not pooled replicas. Exact leave-future-out is a
family of tasks whose origin and horizon must reflect the use case
`[superrep-validation-leave-future-out]{28}`.

Keep the newest contiguous block untouched while choosing hyperparameters and thresholds on earlier
rolling folds. If the corpus is too small for both tuning and a credible final block, report that
the method is not yet validated rather than reusing the same future windows indefinitely.

### 2.2 Comparable forecast cases

Proper-score differences are interpretable only when candidates are scored on the same forecast
situations; changing the set changes its intrinsic predictability
`[superrep-validation-proper-scores]{30}`. Therefore report two views:

- **all-case predictive comparison:** every candidate supplies a probability for the common set of
  eligible held-out decisive non-mirror matches, even if its product policy would abstain; and
- **served-decision comparison:** each candidate applies its frozen refusal policy, with coverage
  and the cost of non-service retained in the utility calculation.

Never compare one model's score on easy served cases with another model's score on all cases. Also
publish results for the fixed intersection served by all candidates and a risk-coverage curve over
common thresholds.

**Project decision — hard boundary.** The all-case distribution exists solely for predictive model
comparison and does not confer evidence or display permission. Evidence gates operate only on the
served policy. A model that cannot emit an all-case probability has a computational failure for that
case; a model that emits one but fails evidence gates may still be scored, while the decision policy
must abstain and execute its frozen archetype-only fallback. Coverage diagnostics cannot turn an
unsupported scored probability into a recommendation.

### 2.3 Dependence and uncertainty

Match rows from the same event, player, or repeated pairing are not automatically independent.
Uncertainty around score differences should use a predeclared block bootstrap or an equivalent
cluster-aware resampling unit supported by the available identifiers. Report fold-level differences
as well as the aggregate: a small average driven by one era is not repeatable evidence.

**Project decision — dependence uncertainty.** This resampling rule is derived from the corpus
structure; the six attested validation sources do not establish the correct dependence block for
Legacy. If player or
event identifiers are unavailable, record that limitation and do not present naive row-level error
bars as independent evidence.

**Project decision — context availability.** Current extraction observes tournament date and
provenance, player-name strings, aggregate decisive result, and archetype/variant, but the modeled
tally does not retain event/round/player/repeated-pair dependence fields and has no play/draw,
game-one/postboard, or match-format field. Stage 0 records each as present, typed missing, or
acquisition-blocking before selecting resampling units or conditional claims. For reciprocity, any
future oriented context must use a declared reversal that swaps sides and all side-specific fields;
presently there are no such orientation-sensitive covariates in the tally beyond p1/p2 orientation.

### 2.4 Stage-0 field disposition

**Project decision — required schema.** Stage 0 emits one row per field in
`context-field-disposition.json` with:

`field`, `raw_status`, `retained_status`, `typed_missing_reason`, `target_or_marginalization`,
`reversal_rule`, `dependence_block_consequence`, `claim_scope`, and `launch_effect`, where
`launch_effect` is exactly `model_ready`, `weaker_claim:<name>`, or `claim_blocking`.

The initial audit table is:

| Field | Current raw / retained status | Target or marginalization | Reversal | Dependence and launch disposition |
|---|---|---|---|---|
| Aggregate result / `Y` | raw score observed; decisive non-mirror win/loss retained; draws/byes/removals and mirror rows excluded from fit/score | likelihood/proper-score target is recorded decisive eligible non-mirrors; decision target additionally retains same-archetype field mass at structural 0.5; publish exclusion coverage by member pair/source/time | swap p1/p2, `Y -> 1-Y`; diagonal is reversal-invariant | model-ready only after exclusion ledger closes and evidence/target denominators are separate |
| Tournament/date/provenance | raw observed; date/provenance filter retained; event id not in tally | named source/time target | shared under reversal | benchmark must rehydrate event id for event-block uncertainty; failure is `claim_blocking` |
| Player1/player2 names | raw observed; normalized for join; not retained as model effects | no pilot-effect claim; recorded-pilot mixture only | swap names | without stable cross-event id, emit `weaker_claim:event_clustered_player_dependence_unresolved`; Stage-0 simulation must show the frozen bound remains valid or mark `claim_blocking` |
| Round/bracket/record | availability not established; not retained | recorded eligible-round mixture only | shared round, swap side-specific record | audit raw schema; material unbounded progression dependence is `claim_blocking` |
| Play/draw or seat | unavailable; not retained | unconditional recorded-match mixture only | swap play/draw or seat; marginalized reverse uses `R#q` | no conditional first-play claim; any such claim is `claim_blocking` |
| Match format / best-of | unavailable; not retained | named corpus mixture only | shared | format-specific claim is `claim_blocking` |
| Game-one/postboard state | unavailable; not retained | match-level aggregate only | swap side-specific state | game/postboard claim is `claim_blocking` |
| Repeated pair | derivable only if event and player keys are rehydrated; not retained | no independent-row assumption | pair is unordered under reversal | unresolved repeated-pair dependence is the named weaker claim above or `claim_blocking` after Stage-0 simulation |
| Archetype/variant/taxonomy | raw labels observed; archetype/variant retained; taxonomy joined later | frozen origin registry plus scenario registry | swap subject/opponent | model-ready only with version/hash and complete scenario closure |

For any marginalized oriented context distribution `q`, the reverse uses its pushforward `R#q`.
The table must name the empirical or synthetic `q`; “unknown but assumed balanced” is not a valid
entry. Any row left `audit_pending` makes `EVALUABLE=false`.

## 3. Probabilistic forecast quality

### 3.1 Primary and secondary proper scores

Use held-out match **log loss** as the primary predictive metric, with **Brier score** as a secondary
metric. Strictly proper scores reward honest probability distributions; logarithmic and quadratic
scores are proper examples for categorical outcomes `[superrep-validation-proper-scores]{30}`.
Predeclare numerical clipping for log loss and apply it identically to every candidate.

Proper scores and calibration use decisive non-mirror held-out rows only. Mirror rows cannot improve
a candidate by contributing known 0.5 predictions; their field mass appears only in decision
standardization.

Report paired score differences by fold with uncertainty, not just absolute totals. A candidate
does not pass because its posterior intervals are narrower. Forecast quality is sharpness subject
to calibration, and interval scores should penalize both excessive width and misses
`[superrep-validation-proper-scores]{30}`.

### 3.2 Calibration

For match probabilities and standardized family probabilities, report:

- cumulative observed-minus-expected traces with uncertainty bands;
- calibration slope/intercept or another preregistered global summary;
- conventional reliability plots only as a sensitivity over several defensible bin widths; and
- calibration by era, forecast horizon, evidence status, and major family where support permits.

Reliability diagrams and scalar calibration metrics depend on bin or kernel width. Cumulative
difference diagnostics avoid choosing bins and expose local discrepancy through their slope and
departure from zero `[superrep-validation-calibration]{26}`. A nearly flat overall curve can still
hide opposing subgroup errors, so aggregate calibration is necessary but insufficient.

### 3.3 Family-level aggregation checks

The downstream family cell is a standardized sum of member-pair probabilities, not an observed
Bernoulli outcome for one synthetic match. Validate it by forecasting the realized future matches
and aggregating those forecasts under the frozen target policy. Where the future window supplies
enough direct member-pair support, also compare predicted and realized standardized cells, with the
realized cell's sampling uncertainty visible.

Do not declare a model calibrated because a handful of large family cells average correctly. Check
whether member-level residuals cancel inside the aggregation and whether calibration changes under
the current-share, equal-member, and other predeclared target weights.

## 4. Abstention and coverage

Refusal is a product decision layered on a probabilistic model. Evaluate it explicitly:

- coverage of future matches, member-pair cells, family-pair cells, and field mass;
- proper-score risk as coverage expands;
- the distribution of typed refusal reasons;
- false-confidence rate among served recommendations;
- missed-opportunity rate among abstained cases that later prove decision-relevant; and
- downstream utility with the predeclared fallback action for an abstention.

A model can make served accuracy arbitrarily attractive by refusing every difficult case. For this
reason, no served-only metric is a primary endpoint. Compare candidates at common coverage levels,
publish the full risk-coverage curve, and report performance at a predeclared reference field-mass
coverage. If the real product falls back to archetype-level evidence on refusal, score that
composite decision rather than treating refusal as costless.

**Project decision — abstention thresholds.** Thresholds should be selected on earlier rolling
folds. Conditional on the model already satisfying
predictive safety and strict two-stage member-action improvement, a refusal rule is preferred only
if it lowers secondary served-policy risk enough to justify its lost coverage. It cannot create a
launch pass for a model without decision value. The attested scoring-rule source establishes honest
probability comparison, not the business value of an unanswered Legacy cell
`[superrep-validation-proper-scores]{30}`.

## 5. Decision utility, agency, and rank stability

### 5.1 Define the two-stage playable action and regret

**Project decision — two-stage policy.** Freeze one operational policy at each origin:

1. For every family `S`, compute the posterior-mean current-field positioning score
   `F_S = E[phi_S_current]` from the exact common-field standardization in the estimand brief.
2. Let `S*` maximize `F_S`, breaking an exact numeric tie by stable family id. For one policy tuple
   `(delta_F, pi_F, L)` from the finite grid
   `{0, 0.01, 0.02} x {0.5, 0.8} x {1, 3}`, shortlist `S*` plus each family satisfying
   `Pr(phi_S* - phi_S <= delta_F) >= pi_F`; order by `F_S` then stable id and cap at `L`.
3. For each eligible member `a` inside the shortlist, compute
   `M_a = E[sum_b m_b p_ab]`, its posterior-mean win probability against the same origin field,
   including `b=a` field mass with structural `p_aa=0.5` and no mirror-row fit contribution.
   Choose the maximum `M_a`, breaking exact numeric ties by stable canonical archetype id.

The policy tuple is selected only by nested rolling training folds using the frozen scalar decision
utility below and is then frozen before the final holdout. If no tuple is estimable, the screened
policy is `not-evaluated`; the final holdout cannot choose a tuple.

The public benchmark's eligible member set is the origin-legal, classified archetype/camp action
universe with current field share at least `0.001`. It applies no unobserved pilot-skill adjustment
and no personal availability restriction. A user-specific pilot or availability set is permitted
only when supplied and frozen at the origin and applied identically to every comparator. If the
family score is refused, the shortlist is empty, or every shortlisted member is refused, the policy
executes the authoritative deployed fallback below.

Required comparators are:

- `D0_deployed`: the current deployed **Best Call agency policy** defined by
  `docs/analysis/best-call-ranking.md`, reconstructed at the origin with its documented gates and
  knobs; choose the first served eligible row in the order grounded+current,
  grounded-but-not-current, ungrounded, then Agency descending within that stratum, then stable
  canonical id. This is the authoritative deployed decision comparator and refusal fallback.
  Failure to reconstruct it or obtain a served eligible row at a required origin is
  `not-evaluated` and blocks launch.
- `M0_member_only` / `A0_member_only`: the preregistered antisymmetric member model with family terms
  disabled, and its direct maximum-`M_a` action over the identical eligible set. `M0` is the
  authoritative all-case proper-score/calibration comparator; `A0` is a required decision comparator.
  It applies the same member-level service gates and `D0` fallback.
- `A1_same_model_direct`: use the selected family-aware outcome model's identical member-pair
  predictive draws but skip family scoring and select the maximum `M_a` over all eligible members.
  It retains the screened policy's member-level service gates and `D0` fallback. This isolates the
  decision contribution of the family screen from any predictive benefit of family borrowing.

Both screened and comparator policies end in a playable member-archetype action and are evaluated
against the same future field target. For model `m`, one simple regret is

\[
R_m(o) = U_o(a_o^*) - U_o(\hat a_{m,o}),
\]

where `a_o^*` is the best eligible member archetype under the predeclared future evaluation target
and `\hat a_{m,o}` is the member archetype chosen by the two-stage policy from information at origin
`o`. Because the future “oracle” is
itself estimated from finite matches, report uncertainty and tie/indifference bands rather than
pretending its ordering is exact.

The future utility `U_o(a)` and therefore the oracle use the same unrenormalized opponent field:
same-archetype target mass contributes structural 0.5. Realized mirror rows are not scored or used
to estimate that utility; diagonal uncertainty comes from field weights, not a fitted mirror cell.

Prediction error and decision regret can move differently. Mandi and colleagues demonstrate
predict-and-optimize examples where lower pointwise mean-squared error accompanies worse regret
`[superrep-validation-decision-regret]{27}`. Thus proper scores remain the predictive endpoint while
regret directly tests the ranking's stated use. Standalone family regret is prohibited because a
family label is not a playable action and does not specify which member produced its utility.

### 5.2 Agency decomposition

Compute the existing agency or positioning score from each posterior/bootstrap draw, preserving the
same candidate set, target distribution, and legality constraints. Evaluate:

- calibration and interval coverage of the resulting future positioning quantity where estimable;
- regret of the final member archetype selected by the two-stage policy;
- top-k membership and pairwise order agreement;
- probability that each recommended action is within a practical indifference margin of the best;
- rank turnover between adjacent origins; and
- sensitivity of the selected action to taxonomy, target weights, priors, and refusal policy.

Do not score a ranking against a single noisy realized win-rate ordering without uncertainty. Shah
and Wainwright show that top-k recoverability depends on the gap between the kth and (k+1)th targets
as well as observation density and repetition, even without Bradley–Terry or stochastic-transitivity
assumptions `[superrep-validation-robust-topk]{31}`. When the future window contains no meaningful
separation, label top-k recovery unresolved rather than a model failure or success.

### 5.3 Stability is not correctness

A recommendation that never changes can be stably wrong. Rank stability is therefore diagnostic,
not a substitute for proper scores or regret. Desired behavior is conditional stability: resist
changes caused by sampling noise, but respond when the estimated future utility difference crosses
a predeclared practical threshold. Report both unnecessary turnover and missed meaningful change.

## 6. Negative controls

Every negative control reruns the **entire** training, tuning, standardization, refusal, and scoring
pipeline. Reusing fitted components after permutation would leave real outcome information in the
null.

“Entire” includes the identical nested `C01..C05` selection algorithm and tie rules. Each outcome-
permutation repeat, shuffled-family repeat, and taxonomy/weight/prior/context sensitivity pipeline
selects and freezes its own `candidate_C_id` from its transformed inner training data before its
outer holdout. It may not reuse the observed pipeline's winner. Its `A1` ablation binds to its own
selected candidate. Failed or missing inner selection is retained as `NOT_EVALUATED`, not discarded
from the null or scenario distribution.

### 6.1 Outcome-association null

Within each permissible temporal/event stratum, permute match outcomes in a way that destroys the
deck-outcome association while retaining the predeclared exposure structure. Refit every candidate
and build a null distribution for score improvement and decision utility. Label permutation is a
standard way to test whether a classifier learned outcome structure; restricted permutations can
instead probe whether dependence structure contributes information
`[superrep-validation-permutation]{29}`.

The exact exchangeability block is a design choice: unrestricted permutation may destroy first-play
balance, event strength, or repeated-player structure. If no defensible exchangeability scheme is
available, use simulation from a fitted null and label its assumptions.

### 6.2 Family-structure null

Freeze member outcomes and exposures but randomize family assignments among archetypes subject to
predeclared constraints such as family-size profile and, if necessary, member prevalence bands.
Rebuild the borrowing hierarchy from those outcome-blind shuffled registries. This asks the pivotal
question: does the composition-derived taxonomy provide predictive sharing beyond an equally sized
arbitrary partition? Standardization follows the comparability rule below.

**Empirical hypothesis — shuffled-family transfer.** This control is not a procedure directly
validated in Ojala and Garriga. It follows the same logic of destroying the hypothesized
relationship while rerunning the
full evaluation `[superrep-validation-permutation]{29}`. Constraints must not use held-out outcomes.

**Project decision — comparability boundary for this null.** Member-pair log loss, Brier score, and
calibration remain directly comparable because every shuffled fit predicts the same held-out
member-pair cases. Family-level and decision metrics are comparable only when evaluation freezes an
external mapping: the production-taxonomy target weights, eligible member action set, and two-stage
member-selection rule stay fixed while only the hierarchy used for borrowing is shuffled. If
standardization instead uses each shuffled partition's own synthetic families, those cells and
rankings describe different populations and are descriptive null diagnostics only; they must not
enter the launch comparison.

### 6.3 Leakage and placebo controls

- Intentionally compare a future-leaking random/leave-one-out split with the rolling-origin result;
  a large advantage only under leakage is a failure, not encouragement
  `[superrep-validation-leave-future-out]{28}`.
- Shift family labels or member weights to an implausible predeclared placebo lag and verify that the
  claimed improvement does not persist mechanically.
- Include singleton/pass-through families separately; they cannot count as evidence that grouping
  added information.
- Compare against a model with family terms disabled but identical complexity where possible, so
  improvements are not credited merely to added regularization or parameters.

## 7. Pass, refusal, and rejection criteria

**Project decision — authoritative conjunction.** The protocol manifest freezes these values using
only Stage-0 simulation and nested training folds: one-sided error level `alpha`; log-loss
noninferiority margin `eps_LL`; maximum calibration-harm margin `eps_CAL`; regret non-harm margin
`eps_R`; strict decision-improvement margin `delta_J > 0`; top-k utility weight `lambda`; minimum
recurrence count `r_min`; action-set `k_action` and practical-indifference margin `delta_oracle`;
minimum calibration subgroup size `n_CAL`; supported calibration subgroups; dependence-aware
uncertainty procedure; null-repeat counts; and the complete versioned sensitivity registry. No
value is chosen from the final holdout.

For origin `o`, let `R_p(o)` be future regret of policy `p`. The practical future set contains the
top `k_action` members by the frozen future utility plus any member within `delta_oracle` of the
future best. Let `H_p(o)=1` when the policy's chosen member is in that set and `0` otherwise. The
sole decision utility is

\[
J_p(o)=-R_p(o)+\lambda H_p(o),
\]

with `lambda` expressed in the same win-probability-point units as regret. This resolves the
tradeoff explicitly: strict composite improvement is required, and regret must separately be
non-harmful. Let `UCB(x)` and `LCB(x)` be one-sided `(1-alpha)` bounds from the frozen
dependence-aware origin/block procedure.

For any common-case group `G` with `|G|>=n_CAL`, define the calibration statistic by sorting its
predictions and taking
`CAL_m(G)=max_j |sum_{i<=j}(y_i-p_i)| / |G|`. Global `G` and every preregistered supported subgroup
are gate inputs; a preregistered subgroup below `n_CAL` is `not-evaluated`, not silently dropped.

For screened candidate `C`, define the required clauses:

- `EVALUABLE`: Stage 0 passed; `D0_deployed`, `M0/A0`, and `A1_same_model_direct` were reconstructed
  at every required origin; nested training selected and froze exactly one `candidate_C_id` before
  each outer holdout; the final case manifest, scenario closure, null repeats, model fits, and
  uncertainty calculations completed; and no context-disposition row is `claim_blocking`. Failed or
  missing inner selection makes this clause false by missingness, not by optimistic imputation.
- `PREDICTIVE_SAFE`: on identical all-case held-out decisive non-mirror member matches,
  `UCB(LL_C - LL_M0) <= eps_LL`, and for global calibration plus every preregistered supported
  subgroup `UCB(CAL_C - CAL_M0) <= eps_CAL`. `M0_member_only` is the authoritative statistical
  comparator. `D0_deployed` is additionally reported wherever it emits comparable probabilities,
  but its selective service cannot replace `M0` in this conjunct.
- `DECISION_VALUE`: for every required decision comparator
  `d in {D0_deployed, A0_member_only, A1_same_model_direct}`,
  `LCB(J_C - J_d) >= delta_J` **and** `UCB(R_C - R_d) <= eps_R`. Thus a composite gain may not buy
  materially worse regret, and the family screen earns decision use only by beating identical
  family-aware member predictions with screening disabled.
- `RECURRENT`: for every required comparator, the point difference `J_C(o)-J_d(o)` is positive in
  at least `r_min` preregistered origins, and no preregistered era block has
  `UCB(R_C-R_d) > eps_R`.
- `NULL_VALID`: define `T_out_pred=LL_B0_market-LL_C` and
  `T_out_dec=J_C-J_D0_deployed`; both exceed their one-sided `(1-alpha)` outcome-permutation null
  quantiles. Define `T_screen=J_C-J_A1_same_model_direct`; it exceeds the `(1-alpha)` shuffled-
  hierarchy null quantile under the fixed external target/action mapping. Also report the comparable
  member-pair statistic `LL_M0-LL_C` across shuffled hierarchies. Metrics over shuffled families'
  own populations never enter this clause.
- `SENSITIVITY_PASS`: every preceding statistical clause passes under every entry in the versioned
  `SensitivityScenarioRegistry`, including the complete `TaxonomyScenarioRegistry`, preregistered
  weight-smoothing/prior variants, and any context-marginalization variants. Aggregation is
  unanimity/worst case; no averaging across scenarios is allowed. Every scenario reruns nested
  candidate selection and binds `A1` to its selected candidate.

The status function is exhaustive and mutually exclusive:

```text
if not EVALUABLE:
    status = NOT_EVALUATED
elif PREDICTIVE_SAFE and DECISION_VALUE and RECURRENT and NULL_VALID and SENSITIVITY_PASS:
    status = PASS
else:
    status = FAIL

launch_allowed = (status == PASS)
```

`NOT_EVALUATED` is not a softer pass. It blocks launch until the missing requirement is acquired or
the project explicitly downscopes to a different claim and preregisters a new gate.

### A family or cell is refused if

its frozen evidence, composition-sensitivity, calibration, influence, or stability gate fails. The
reason remains typed. Failed computational diagnostics are not converted to a statistical refusal,
and insufficient future support is “not evaluated,” not “validated.”

### Reject or withhold

`FAIL` rejects the evaluated production candidate because at least one required conjunct is false.
`NOT_EVALUATED` withholds judgment but blocks the same three-level decision surface. In either case,
family-aware predictions may continue as research diagnostics; families remain explanation and
navigation if `A1_same_model_direct` matches or beats the screened policy, even when family borrowing
helps member-pair prediction.

## 8. Minimal validation artifact

The first implementation should be an offline, reproducible benchmark—not renderer work. Its durable
outputs should include:

- a machine-readable protocol manifest and hash;
- frozen `alpha`, `eps_LL`, `eps_CAL`, `eps_R`, `delta_J`, `lambda`, `r_min`, `k_action`,
  `delta_oracle`, `n_CAL`, subgroup, origin/block, comparator, policy-ladder, null-repeat, and
  sensitivity-registry definitions;
- origin-by-origin training and forecast case manifests;
- inner-fold qualification results, deterministic tie-break trace, frozen `candidate_C_id`, and
  configuration hash for every observed, null, and sensitivity outer run;
- taxonomy, regime, and target-weight versions at each origin;
- candidate predictions before refusal and final served/refused outputs;
- foldwise proper scores, calibration traces, interval scores, and coverage;
- agency draws, selected actions, top-k uncertainty, and regret;
- permutation seeds, shuffled registries, and null results;
- convergence and approximation diagnostics;
- a decision table mapping every preregistered gate to pass, fail, or not-evaluated evidence;
- the Stage-0 feasibility report;
- `context-field-disposition.json` with every weaker-claim or claim-blocking consequence; and
- the frozen two-stage policy and external action/target mapping specification.

The final `launch-gate.json` stores every raw metric difference, bound, threshold, per-origin
recurrence flag, null quantile, per-scenario result, and comparator id. It emits exactly one of
`PASS`, `FAIL`, or `NOT_EVALUATED` using the Section-7 pseudocode, plus a typed reason for every false
or missing conjunct. Section 8 does not reinterpret that status. A missing comparator, incomplete
scenario closure, invalid uncertainty calculation, or unavailable claim-blocking field must appear
as `NOT_EVALUATED`, never a skipped row.

Nested training selects one candidate before each outer holdout; the outer holdout evaluates that
frozen candidate exactly once and never chooses among outer results. Only a `PASS` for that contract
may flow into the three-level page. The UI may display experimental results during research, but it
must not create an implied production license.

## Disconfirming analysis

The research sought reasons that a family representation could appear useful without being useful.
Proper scores can favor a model whose chosen action has worse regret
`[superrep-validation-decision-regret]{27}`; served-case accuracy can improve merely by abstaining;
ordinary cross-validation can leak future observations into past predictions
`[superrep-validation-leave-future-out]{28}`; and apparent top-k failures or wins can be artifacts of
an unresolved boundary with too little separation `[superrep-validation-robust-topk]{31}`. The
protocol therefore refuses to make any one of prediction, coverage, or ranking the sole success
criterion.

It also tests whether the taxonomy contributes anything. If a family-aware model beats a
member-only baseline but not size- and prevalence-matched shuffled registries on common member-pair
predictions—or on decision metrics under the fixed external mapping—the gain is evidence for generic
pooling, not for these superarchetypes. Metrics over the shuffled partitions' own family populations
are not comparable. If outcome permutation retains the claimed
advantage, the pipeline is exploiting leakage, imbalance, or an invalid evaluation procedure rather
than matchup signal `[superrep-validation-permutation]{29}`.

There are also reasons not to demand dramatic rank stability. Properly updating evidence can change
the best action, and top-k identity is intrinsically fragile when candidates are nearly tied
`[superrep-validation-robust-topk]{31}`. Hence the protocol measures regret and practical
indifference, not raw rank correlation alone.

Finally, this brief cannot establish numeric launch thresholds from literature. Decision costs,
available field coverage, refresh cadence, and corpus size are project facts. Freezing thresholds on
early rolling folds and allowing the final holdout to reject the entire idea is more honest than
importing generic cutoffs.

## Contradictions

| Issue | Position A | Position B | Relationship |
|---|---|---|---|
| Predictive accuracy versus decisions | Strictly proper scores elicit honest probabilities and compare forecast quality `[superrep-validation-proper-scores]{30}`. | Pointwise prediction error and downstream regret can move in different directions `[superrep-validation-decision-regret]{27}`. | **qualifies** — use proper scores for probabilistic truthfulness and regret for the intended action; neither replaces the other. |
| Stable top-k versus responsive rankings | Top-k recovery requires sufficient separation at the selection boundary `[superrep-validation-robust-topk]{31}`. | A dynamic decision system should change when future positioning genuinely changes. | **tension** — judge turnover relative to uncertainty and practical separation, not stability in isolation. |
| Calibration plots | Familiar reliability plots localize observed-versus-expected differences. | Their conclusions depend on bin or kernel width; cumulative differences avoid explicit binning `[superrep-validation-calibration]{26}`. | **qualifies** — use cumulative diagnostics as the primary display and binned plots as resolution sensitivity. |
| Broad prediction versus selective service | Proper scores compare predictions on common forecast situations `[superrep-validation-proper-scores]{30}`. | Evidence gates may responsibly refuse unsupported decisions. | **complementary with accounting** — retain all-case predictions for model comparison and score the served policy with explicit coverage and fallback cost. |

## Acquisition gaps

- No source established a universal minimum useful coverage, regret tolerance, or practical
  calibration margin for Legacy deck selection; these require project-level elicitation and early
  folds.
- No primary source was acquired for selective prediction under exactly this mixture of typed
  refusals and fallback actions. The risk-coverage protocol is an inference from proper-score and
  decision-utility principles.
- No source establishes the exchangeability blocks for MTGO outcome permutation or uncertainty
  resampling. Event, player, round, and play/draw identifiers must be audited before choosing them.
- Future family-cell “truth” is itself sparse. The protocol can score individual held-out match
  probabilities cleanly, but standardized cell and oracle-regret estimates need uncertainty and may
  remain unresolved.
- The number of independent metagame regimes and forecast origins in the corpus was not measured in
  this research leaf. Insufficient temporal replication may block a decisive model comparison.
- Distribution shift caused by bans, set releases, tournament policy, or classifier changes may make
  historical folds nonexchangeable with deployment; the dynamic branch must specify these states.

## Suggested cross-references to sibling subdomains

- **Estimand and target population:** provide the primary current-share estimand, sensitivity weight
  policies, unsupported-target-mass rule, and operational decision/action definition.
- **Non-transitive outcome model:** expose comparable member-pair predictive distributions for every
  candidate, including family-disabled and scalar baselines, plus convergence diagnostics.
- **Sparse and selectively observed evidence:** supply typed refusal states, direct/indirect support,
  influence checks, and observation-process sensitivities; validation calibrates their thresholds
  without letting them game coverage.
- **Dynamic metagame representation:** define as-of regime reconstruction, forecast cadence, origin
  spacing, change-boundary behavior, and whether an interrupted regime is scored or marked outside
  scope.
- **Campaign synthesis:** treat the offline benchmark as a blocking modeling spike and reject the
  production three-level page unless the whole-idea gates pass.

## Attested sources

- `superrep-validation-leave-future-out` — future-only evaluation order and horizon design.
- `superrep-validation-proper-scores` — proper scores, calibration/sharpness, common forecast cases,
  and interval scoring.
- `superrep-validation-calibration` — bin-sensitive reliability diagnostics and cumulative
  calibration differences.
- `superrep-validation-decision-regret` — divergence between prediction error and downstream regret.
- `superrep-validation-robust-topk` — top-k recovery without transitivity and the role of separation.
- `superrep-validation-permutation` — full-pipeline permutation nulls for learned association.
