---
description: "How sparse and selectively observed matchup evidence can support—or refuse—a family-level Legacy claim."
type: brief
kind: research
slug: decision-useful-superarchetype-representation-sparse-selective-evidence
research_method: /deep-research
verification_status: attested
provenance: agent-synthesis
updated: 2026-08-01
summary: |
  Separates three questions that sparse family matchups otherwise blur: whether a matchup was
  observed, whether member outcomes can borrow strength, and whether the resulting family claim is
  identified well enough to serve. Recommends an evidence ledger, direct-versus-indirect and
  leave-member-out checks, explicit concentration and prior-dependence diagnostics, and typed
  refusal states. Outcome-blind assigned members may contribute their own matches after membership
  is frozen, but their fit must be allowed to falsify the family claim.
key_findings:
  - "A sparse matchup matrix is not automatically missing at random: popularity, pairing structure, event progression, reporting, and repeated-player participation must be audited as observation mechanisms rather than absorbed into a single sample-size gate."
  - "Partial pooling can stabilize separated and tiny cells, but a finite regularized estimate is not evidence that the cell or the family contrast was identified by observations."
  - "Low measured heterogeneity is weak evidence when members and matches are few; diagnostics should seek positive contradictions through member-level posterior predictive checks, direct-versus-indirect splits, leave-member-out influence, and design-sensitivity analyses."
  - "Concentration has at least three distinct meanings—observed match contribution, target-population weight, and posterior influence—and each needs its own diagnostic."
  - "Assigned members may contribute after outcome-blind membership is fixed; excluding their direct outcomes while weighting them into the represented population would make evidence and estimand describe different families."
  - "Refusal should distinguish insufficient direct evidence, prior domination, family inconsistency, observation-process sensitivity, concentration, and computational failure rather than collapsing them into blank cells."
confidence: speculative
status: draft
related:
  - {slug: .research/briefs/decision-useful-superarchetype-representation/estimand-target-population.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/nontransitive-outcome-models.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/dynamic-metagame-representation.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/validation-decision-utility.md, relationship: parallel-to}
---

# Sparse and selectively observed evidence

## Scope and conclusion

The central evidence problem is not merely that most archetype-pair cells are small. It is that the
observed cells are the result of a participation and pairing process, and that a hierarchical model
can produce a precise-looking answer even when the relevant family contrast is learned mostly from
assumptions. This brief addresses observation, borrowing, diagnostics, and refusal. It does not
select the family estimand, specify the outcome-model architecture, define temporal regimes, or
choose the final validation score; those belong to sibling subdomains.

**Project decision — evidence contract.** The recommended evidence contract has four layers:

1. audit why each match could enter the matrix;
2. preserve direct member-pair evidence separately from model-borrowed evidence;
3. try to falsify the proposed family exchangeability with member-, player-, and design-level
   diagnostics; and
4. serve a family probability only when its uncertainty, concentration, influence, and sensitivity
   are compatible with the intended decision.

Partial pooling belongs inside that contract, but it cannot be the license by itself.

## 1. The observation process is part of the evidence

### 1.1 Missing cells are not one phenomenon

At least five mechanisms should remain distinguishable in an evidence ledger:

- **composition frequency:** uncommon members create few possible pairings even under neutral
  scheduling;
- **event entry:** archetype choice and player participation determine which strategies are exposed
  to the tournament process;
- **pairing and progression:** the realized opponent set depends on event structure and, potentially,
  on earlier results;
- **recording and classification:** a played match can be absent or assigned to a coarse label; and
- **structural absence:** some family-member combinations may not coexist in the relevant population
  or window.

The first is unequal exposure, not missing data in the ordinary sense. The later mechanisms can make
the observed cells systematically different from the unobserved cells. Jin, Ma, and Jiang show that
missingness can itself be informative; their method jointly completes the response matrix and
assesses covariate effects under low-rank-matrix and sparse-covariate-effect assumptions
`[superrep-informative-missingness]{15}`. Their result does **not** establish that Legacy matchups are
missing-not-at-random or low-rank. It establishes that “fit the observed matrix and fill its holes”
is not assumption-free.

Nonrandom schedules can bias even familiar mixed models. Karl's schedule-conditioned simulations
found that modeling team ability reduced but did not eliminate bias caused by stronger teams
receiving systematically different assignments; restricting to a more comparable schedule changed
the population to which the estimate applied `[superrep-nonrandom-scheduling]{18}`. The direct
transfer is a diagnostic obligation, not a claim that Swiss pairings reproduce that sports example.

### 1.2 Player effects are exposure and dependence, not noise to ignore

Repeated matches by one player are correlated evidence, and strategy selection may correlate player
ability with deck identity. Lancaster and Quade's random-effects extension to paired comparisons was
motivated precisely by repeated judgments: a subject-level random effect both induces within-subject
correlation and separates subject variation from treatment variation
`[superrep-random-effects-paired]{21}`. For this project, “subject” maps imperfectly to a
player; the relevant point is that match rows sharing a pilot should not automatically count as
independent deck evidence.

The evidence ledger should therefore retain player, event, round, pairing bracket or record (when
available), archetype label, family assignment version, and reporting source. If those fields are
unavailable, the output should name the untested selection mechanism instead of silently assuming it
away.

**Project decision — current observability boundary.** The current `match_results.py` extraction
observes tournament date/provenance, the two player-name strings, aggregate result, and each deck's
archetype/variant. Its modeled tally drops draws/byes/forfeits and ambiguous or unmatched joins and
does not carry tournament, round, player, or repeated-pair identifiers forward into each cell. It
also lacks play/draw, game-one/postboard, match-format, and stable player identity fields. Required
but absent fields enter the Stage-0 audit as typed `missing_player_id`, `missing_round_context`,
`missing_play_draw`, `missing_match_format`, or `missing_game_state`; they cannot be named as fitted
effects or independent resampling blocks until acquired and verified.

The benchmark outcome is explicitly conditional on a recorded decisive eligible match. Rehydrate
the raw pairing ledger before aggregation and report drawn/tied scores, byes/forfeits, mirrors,
ambiguous joins, unmatched decks, and other removals by member pair where labels resolve, by source,
and by time window. When a removal prevents a member-pair label, retain an `unresolved_pair` stratum
rather than reallocating it. Failure to close this exclusion ledger is `claim_blocking`, not merely
lower coverage.

**Project decision — mirror boundary.** Mirror rows belong in that exclusion ledger but never in
the fitted evidence, heterogeneity tests, direct-support counts, leave-member-out tests, or all-case
proper-score cases. This exclusion does not delete same-archetype decision-target mass: downstream
standardization retains it as structural `p_aa=0.5`. Evidence coverage and target coverage therefore
have different denominators and must be reported separately.

### 1.3 Audits before corrections

Before fitting a missingness correction, describe the observation graph:

- match counts and unique players by member pair;
- the fraction of evidence contributed by each event, player, round band, and member;
- pair exposure relative to what member prevalence alone predicts;
- disconnected components and member pairs with no direct path;
- classification and reporting coverage by source; and
- whether later-round or positive-record matches have different member-pair composition.

These are falsification probes. A correction model is warranted only after an observed deviation is
identified and its identifying covariates are available. The informative-missingness method above
depends on structural assumptions that have not been established for this corpus
`[superrep-informative-missingness]{15}`.

## 2. Partial pooling under extreme sparsity

### 2.1 What pooling buys

Hierarchical or regularized estimates can keep sparse binomial cells finite and propagate
information from related cells. Weakly informative priors, for example, return finite logistic
estimates under complete separation and shrink higher-order interactions
`[superrep-weak-priors-separation]{32}`. That is useful numerical and predictive behavior.

### 2.2 What pooling does not buy

A finite answer under separation is partly a prior result. It does not show that the sparse cell
identified its own direction or magnitude. Every family-pair result should therefore carry, at
minimum:

- direct wins, losses, matches, players, and events;
- the model's no-pooling estimate when finite;
- posterior uncertainty for the served estimate;
- sensitivity to the versioned preregistered prior-scale and pooling-strength scenarios;
- the change from direct-only to borrowed estimate; and
- a direct-evidence fraction or an equivalent attribution of where predictive information came
  from.

The final item cannot always be uniquely decomposed in a nonlinear hierarchical model. In that case,
prior sensitivity and structured case deletion are more honest diagnostics than a fabricated
percentage.

### 2.3 Direct and indirect evidence must be compared, not merged invisibly

Network meta-analysis supplies a useful diagnostic shape. Node splitting estimates one parameter
from direct evidence and another from the remaining indirect network, then examines their agreement
`[superrep-node-splitting]{17}`. Applied here, “direct” means observed matches involving the member or
family pair; “indirect” means predictions obtained through the rest of the fitted relational
structure after withholding those matches.

This transfer has two boundaries:

- a split is possible only where both direct and indirect support exist; a disconnected or
  one-path-only comparison is **untested**, not consistent; and
- the source's consistency equations rely on exchangeability. A non-transitive matchup model must
  define indirect evidence within its own relational structure rather than infer `A > C` from
  scalar transitivity through `B` `[superrep-node-splitting]{17}`.

Report the direct estimate, indirect estimate, their difference distribution, and the amount of
support behind each. A conflict should block or relabel the family claim; absence of a detected
conflict should not certify it.

## 3. Heterogeneity is not identifiability

The conventional heterogeneity test depends on the number of contributing studies. I-squared is the
proportion of total variation attributable to heterogeneity, and interval uncertainty around it
matters `[superrep-heterogeneity-i2]{14}`. **Project inference — thin families.** With two or three
thin family members, a low point estimate can arise because there is little information with which
to detect disagreement. Conversely, one comparatively informative member can dominate the family
summary.

Accordingly:

- high, directional member disagreement is useful positive evidence against pooling;
- low estimated heterogeneity with wide uncertainty is “not falsified,” not “homogeneous”;
- a family with one informative member and several nearly unobserved members is concentrated, not
  replicated; and
- incompatibility and non-identifiability need separate states. Members can appear consistent
  because all are weakly identified.

The system should preserve the uncertainty interval or posterior distribution of its heterogeneity
quantity. A point band alone turns weak evidence into a false gate.

## 4. Diagnostics that can falsify exchangeability

No single diagnostic licenses a group. The following battery searches for specific failure modes.

### 4.1 Member-level posterior predictive discrepancies

Generate replicated member-pair outcomes under the fitted family model and compare statistics chosen
for the hypothesized failure modes:

- largest standardized member residual;
- number and size of sign reversals around 50%;
- dispersion across member effects;
- longest coherent row- or column-wise residual pattern; and
- event-, player-, and round-stratified residual dispersion.

Posterior predictive checks are designed to compare observed discrepancies with replicated-data
distributions and to direct model revision `[superrep-posterior-predictive]{19}`. Passing a check does
not prove the model adequate; Gelman, Meng, and Stern explicitly caution against accepting a model
because it passes posterior predictive assessment `[superrep-posterior-predictive]{19}`.

### 4.2 Leave-one-member-out prediction

For each active member, refit or validly approximate the model without that member's outcomes, then
predict its observed matchups. This asks the exchangeability question directly: can the family and
the rest of the network predict a member they have not seen? Track predictive residuals and the
change in the family-pair probability after removing the member.

Importance-weighted approximations require their own reliability check. Pareto-smoothed importance
sampling supplies effective-sample-size, error, and Pareto-k convergence diagnostics for estimates
that may be dominated by a few weights `[superrep-psis-influence]{20}`. A bad Pareto-k is a
computational warning requiring an exact refit or a different approximation; it is not itself proof
that the member is substantively anomalous.

### 4.3 Direct-versus-indirect conflict

Perform the node split in §2.3 wherever graph support permits. Examine practical difference and
uncertainty, not only a thresholded tail probability. Mark unsupported splits explicitly. Shared
heterogeneity can make a split estimable with little direct evidence
`[superrep-node-splitting]{17}`, but that same borrowing means the direct side's weakness must remain
visible.

### 4.4 Three concentration ledgers

Keep separate concentration measures for:

1. **observed evidence:** shares of matches, players, and events by member;
2. **represented population:** the target weights assigned to members; and
3. **posterior influence:** change in the family result under deletion of each member, player, or
   event.

For any normalized shares `w_i`, `1 / sum(w_i^2)` is an interpretable effective contributor count,
while maximum share identifies a single dominant source. These are algebraic concentration
summaries, not variance corrections. They should be reported for members and for players: ten
matches from one pilot are not ten independent strategic replications.

The three ledgers answer different questions. A currently popular member may appropriately dominate
the target population while still leaving little evidence that the remaining members share its
matchup behavior. Conversely, evenly distributed match counts do not prevent one observation from
having high posterior influence.

### 4.5 Observation-process sensitivity

Recompute or reweight the family result across defensible views of the observation process:

- unique-player-balanced versus match-weighted;
- early-round versus later-round evidence;
- event-balanced versus match-weighted;
- reported-source strata; and
- models with and without available player effects.

Material decision changes indicate selection sensitivity. Karl's result shows why merely including
random effects may not remove bias from a nonrandom assignment structure
`[superrep-nonrandom-scheduling]{18}`. The relevant action is to label or refuse the claim, not to
choose whichever view gives more coverage.

### 4.6 Prior and support sensitivity

Sparse interactions should be rerun over defensible prior scales and pooling structures. If the
family probability, sign, or downstream decision changes materially while predictive fit remains
indistinguishable, the claim is prior-sensitive. If the comparison graph is disconnected, report the
connection supplied by the prior or shared hierarchy. Regularization can make an estimate finite
under separation `[superrep-weak-priors-separation]{32}`; only observed connectivity and replication
show how much the data constrain it.

## 5. Refusal and abstention

**Project decision — typed service states.**

Refusal should be a typed evidence result, not a generic blank. Candidate states are:

- **directly supported:** replicated direct evidence and no material diagnostic conflict;
- **model-supported lean:** sparse direct evidence, useful indirect support, and diagnostics do not
  falsify the family claim;
- **prior-dominated:** direction or magnitude depends materially on regularization;
- **concentrated:** one member, player, or event supplies most evidence or influence;
- **family-inconsistent:** member predictive checks or direct-versus-indirect splits conflict;
- **selection-sensitive:** reasonable observation-process views change the decision;
- **unidentified:** disconnected support, separation, or uncertainty leaves the decision unresolved;
- **computationally unreliable:** convergence or approximation diagnostics fail; and
- **not assessed:** required identifiers or strata are unavailable.

Thresholds should be calibrated in the validation branch against downstream decision loss; this
brief does not select numeric cutoffs. Two rules are already defensible. First, a failed falsification
check can refuse a claim. Second, a check with insufficient power cannot grant it. The system may
serve a labeled model-supported lean when evidence is weak but stable, provided the label and
uncertainty propagate into every downstream calculation.

**Project decision — hard comparison boundary.** Refusal never removes a probability from the
all-case model comparison: every candidate must emit a predictive distribution on the common
eligible held-out matches or fail computationally. Evidence gates apply only to the served decision
policy. Thus an unsupported cell may be scored for model diagnostics but cannot become a displayed
claim or a two-stage recommendation; the served policy falls back to the preregistered archetype-only
action. Coverage and abstention are secondary policy diagnostics, never substitutes for improving
the final member-archetype action.

## 6. Assigned family members after outcome-blind membership

**Project decision — assigned-member evidence.** Once membership is fixed without match outcomes,
assigned members should be allowed to contribute their **own direct outcomes** to a family
representation. This follows from estimand
coherence, not a conclusion established by the attested papers: if assigned members receive target
population weight but their matches are excluded, the evidence model and the represented family
refer to different populations.

**Project decision — membership boundary.** The safeguards are:

1. freeze the taxonomy and assignment rule before inspecting outcome fit;
2. keep defining, curated, and assigned roles in metadata;
3. let every active member participate in concentration, predictive, and influence diagnostics;
4. do not remove an assigned member because its outcomes hurt family coherence—record the conflict
   and refuse or revise the taxonomy in a later outcome-blind cycle; and
5. distinguish “contributes direct evidence” from “lends prior support to another member.” The latter
   requires the family exchangeability checks above.

The primary taxonomy is frozen at each origin. The estimand brief's versioned
`TaxonomyScenarioRegistry` supplies the complete at-most-16 primary/alternate Cartesian closure,
provenance, eligibility floor, overflow refusal, and unanimity/worst-case aggregation. Outcome fit
may falsify robustness across those scenarios, but may not select a preferred boundary. Policy
selection uses no outcomes or is nested entirely inside rolling training folds.

This answers the narrow contribution question while preserving the composition-only membership
authority. Misclassification remains a risk and should be tested as assignment sensitivity rather
than hidden by contributor-role exclusions.

## 7. Uncertainty propagation

**Algebraic derivation — uncertainty composition.** Family probabilities should be computed for
each outcome posterior or bootstrap draw and each separately generated `WeightSnapshot` draw, and downstream
positioning quantities should be computed on the same draws. Summarizing member cells first and then
plugging point estimates into a nonlinear ranking discards covariance and understates decision
uncertainty. Observation-process and taxonomy sensitivity are not automatically captured by a
conditional posterior; they require separate scenarios whose decision spread is surfaced alongside
sampling uncertainty.

Implementation-facing outputs should therefore preserve:

- direct evidence counts and unique-source counts;
- posterior draws or sufficient summaries including covariance-relevant identifiers;
- target and evidence weights separately;
- weight-draw method and identity separately from outcome-draw method and identity;
- heterogeneity and concentration distributions or intervals;
- deletion and observation-sensitivity results;
- typed refusal reasons; and
- the exact taxonomy, observation window, and model version.

This is an evidence contract, not a prescription for module boundaries or storage layout.

## Disconfirming analysis

The research actively sought evidence against aggressive refusal and against the claim that sparse
cells are unusable. Weakly informative priors can produce stable finite logistic estimates under
separation `[superrep-weak-priors-separation]{32}`, and node-splitting models can estimate a direct
side with few observations by sharing heterogeneity `[superrep-node-splitting]{17}`. Therefore a hard
raw-`n` rule would discard potentially useful predictive information. The recommended alternative is
a labeled model-supported lean with propagated uncertainty, not universal abstention.

The research also sought support for treating the observation matrix as nonignorable. The
informative-missingness source proves results only under explicit low-rank, covariate, and sparsity
conditions `[superrep-informative-missingness]{15}`; none has been established for Legacy. The correct
conclusion is to audit and run sensitivity analyses, not to deploy an MNAR completion method by
analogy.

Posterior predictive and heterogeneity checks can miss misspecification. Passing them does not prove
exchangeability `[superrep-posterior-predictive]{19}`. Leave-member-out prediction and structured
deletions are included because they expose failures that in-sample dispersion tests can conceal.

Finally, allowing assigned members to contribute can weaken apparent family coherence. That is
disconfirming evidence the representation needs to see. Excluding those members would improve the
metric by changing the population rather than improving the claim.

## Contradictions

| Issue | Position A | Position B | Relationship |
|---|---|---|---|
| Random effects and assignment bias | Repeated-subject random effects can separate subject variation and account for dependence `[superrep-random-effects-paired]{21}`. | In nonrandom sports schedules, conditioning on team random effects reduced but did not eliminate assignment bias `[superrep-nonrandom-scheduling]{18}`. | **qualifies** — dependence modeling is necessary but not a general correction for selective exposure. |
| Finite sparse estimates | Weakly informative priors provide finite estimates under complete separation `[superrep-weak-priors-separation]{32}`. | Informative observation can make the observed-data objective miss the true response parameters without additional identifying structure `[superrep-informative-missingness]{15}`. | **tension** — computational existence is not observational identification. |
| Network consistency and non-transitive games | Node splitting tests direct evidence against indirect evidence constructed under network consistency and exchangeability `[superrep-node-splitting]{17}`. | The project requires matchup-specific non-transitive relations, so scalar path consistency is not assumed. | **incommensurable unless adapted** — the diagnostic shape transfers, but its indirect model must come from the selected relational architecture. |
| Heterogeneity and model fit | I-squared summarizes observed between-unit variation `[superrep-heterogeneity-i2]{14}`. | Posterior predictive checks target chosen discrepancies and can pass a model that is wrong in unchecked ways `[superrep-posterior-predictive]{19}`. | **qualifies** — neither low heterogeneity nor a passed check is a general pooling license. |

## Acquisition gaps

- No primary source on the exact MTGO/Legacy pairing, drop, publication, and classification process
  was acquired. Claims about event progression remain hypotheses to audit in corpus data.
- The availability and stability of player identifiers across the project's sources were not
  established.
- No source established an identified MNAR correction for this corpus's covariates; the fetched
  matrix-completion method's low-rank and sparse-effect assumptions may not transfer.
- No source directly studied the “composition-fixed taxonomy, outcome-side family representation”
  workflow. The assigned-member recommendation is explicitly an inference from population coherence.
- Full text for Lancaster–Quade and Higgins–Thompson was not acquired through the fetched records;
  their attestations rely on abstracts and indexed extracts for the claims used here.

## Suggested cross-references to sibling subdomains

- **Estimand and target population:** target-population weights must remain distinct from observed
  evidence weights; assigned-member inclusion depends on the estimand's population.
- **Non-transitive outcome model:** define how direct evidence is withheld, how indirect predictions
  are generated without scalar transitivity, and how player effects enter the likelihood.
- **Dynamic metagame representation:** decide which observation-process sensitivities are regime
  changes versus within-regime selection effects.
- **Validation and decision utility:** calibrate refusal thresholds, evaluate model-supported leans,
  and test whether typed abstention improves downstream decisions rather than merely reducing
  coverage.
