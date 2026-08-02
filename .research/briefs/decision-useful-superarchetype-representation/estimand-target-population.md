---
description: "Candidate estimands and target populations for comparing heterogeneous superarchetypes without confusing weighting choices with statistical regularization."
type: brief
kind: research
slug: decision-useful-superarchetype-representation-estimand-target-population
research_method: /deep-research
verification_status: attested
provenance: agent-synthesis
updated: 2026-08-01
summary: |
  A family matchup is best defined as a two-sided standardized probability over member-pair
  matchup probabilities. Current member shares produce a direct descriptive answer to which
  family population is well positioned in the current field; equal, capped, and overlap-oriented
  weights describe different synthetic or restricted populations and belong as sensitivity or
  secondary estimands. A representative deck is an exemplar, not an aggregate estimand. Any
  positive target weight on unsupported member pairs makes the result model-dependent, so target
  coverage and composition sensitivity must accompany the estimate.
key_findings:
  - "The estimand must bind the outcome, regime, subject-member distribution, opponent-member distribution, and population of pilots/events; changing any weighting vector changes the quantity being claimed."
  - "For 'what family is well positioned now', use current-regime member shares on both sides of each family matchup and a common current-field opponent mixture for cross-family positioning."
  - "Equal-member weighting is interpretable as a synthetic random-member policy, not an intrinsic or composition-free family strength."
  - "Capping, trimming, or overlap weighting can stabilize estimates only by targeting a different population; it must never be presented as the original current-meta mixture."
  - "A modal or representative deck estimates one member-pair matchup and cannot represent a heterogeneous family unless a separately tested homogeneity condition holds."
  - "Composition-sensitivity diagnostics should refuse a family-level decision label when versioned preregistered weighting scenarios reverse the decision or a single member dominates it."
confidence: speculative
status: draft
related:
  - {slug: .research/briefs/decision-useful-superarchetype-representation/nontransitive-outcome-models.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/sparse-selective-evidence.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/dynamic-metagame-representation.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/validation-decision-utility.md, relationship: parallel-to}
---

# Estimand and target population

## Scope and first-principles framing

The primary object is not a pooled historical rate. It is the probability of a win under a named
experiment: draw a subject member from one family according to a stated policy, draw an opponent
member from another family according to another stated policy, place both in a stated tournament,
pilot, game, and time population, and observe the stated match outcome. Statistical modeling may
estimate the member-pair probabilities, but it does not select those drawing policies.

This separation matters because marginal standardization deliberately averages conditional
predictions over the distribution of a target population. Predicting at a mean or modal profile
instead describes a different stratum and can describe no real unit at all
`[superrep-target-populations]{24}`. Survey poststratification gives the same algebraic lesson: a
population mean is a population-count-weighted sum of cell means, under assumptions about sampling
within cells `[superrep-estimand-gelman-weighting]{8}`.

This brief treats the desired quantities as **descriptive predictive estimands**, not causal effects
of forcing players to adopt deck families. That distinction avoids importing treatment-effect
language that the tournament data cannot support. It does not remove the need to define who, where,
and when the prediction describes.

## Formal family-versus-family estimand

**Algebraic derivation — standardized family probability.**

Let family `S` contain subject members `a in A_S`, and family `T` contain opponent members
`b in A_T`. Let

\[
p_{ab}^{r,z} = \Pr(Y=1 \mid a,b,r,z)
\]

be the member-pair match-win probability in regime `r` for a named target context `z`. Context
`z` must fix or average over relevant event, rules, game-one/postboard, and pilot populations; a
bare archetype-pair probability silently averages over whichever mixture generated the data.

**Project decision — likelihood versus decision target.** For fitted evidence and all-case proper-
score evaluation, `Y=1` means the oriented subject won a recorded, successfully joined, non-mirror
match whose aggregate score is decisive and whose event, date, provenance, legality,
classification, and origin/horizon filters are eligible; `Y=0` means the oriented subject lost that
same kind of match. Drawn/tied scores, byes/forfeits, ambiguous player joins, unmatched decks, and
mirror rows are excluded from this conditional likelihood/evaluation population, not losses and not
zero-weight observations. The benchmark publishes their counts and rates by member pair, source,
and time window.

The **decision target is broader in one structural respect**: the current opponent field retains
same-archetype mass. Set `p_aa=0.5` deterministically under randomized reversal-invariant
orientation, without treating observed mirror rows as fitted evidence. Thus theta, phi, `M_a`, and
future oracle utility include any target term with `a=b` at 0.5, while log loss, Brier score,
calibration, and model fitting exclude mirror observations. A claim about draws, all scheduled
matches, or match points remains blocked until a separately specified draw/removal model supplies
that target.

For normalized subject weights `u^S_a` and opponent weights `v^T_b`, define

\[
\theta_{S,T}^{r,z}(u,v)
= \sum_{a \in A_S}\sum_{b \in A_T}
u^S_a v^T_b p_{ab}^{r,z}.
\]

This is **two-sided standardization**. It is the chance that a random subject generated by policy
`u` beats a random opponent generated by policy `v`, within `(r,z)`. The double average is an
application of marginal standardization, whose meaning comes from the target weights rather than
from the estimator used to obtain each `p_ab` `[superrep-target-populations]{24}`.

Useful invariants follow from the definition:

- Weights are nonnegative and separately sum to one within each family.
- A displayed `S x T` cell and its reverse must use compatible context and weight
  snapshots. If the underlying match outcomes are complementary and draws are handled consistently,
  the standardized reverse should also be complementary.
- For any shared member `a` on both sides, its `u_a v_a` diagonal target mass contributes structural
  `p_aa=0.5`; no observed mirror tally updates that constant.
- Uncertainty in `p_ab`, membership, and estimated weights must be propagated through the sum;
  averaging point estimates first hides uncertainty rather than eliminating it.
- The weight snapshot and eligible-member set are part of the result's identity. A number without
  them is not reproducible.

## Operational action and context contract

**Project decision — playable action.** The action optimized by the product is the choice of an
eligible member archetype (and ultimately a legal decklist), not the choice of an abstract family.
The family quantity is a screening and explanation surface. A predeclared two-stage policy first
ranks or shortlists families, then chooses one eligible member archetype from the shortlisted
families using only information available at the same as-of origin. Its decision estimand is the
future utility of that final member-archetype action. A standalone “family regret” has no playable
meaning unless it includes a member-selection policy, so it is excluded from the primary contract.

**Project decision — observed versus required context.** The current engine's
`match_results.py` reads tournament date and provenance, player names, archetype/variant labels, and
an aggregate score string. It materializes both directions for decisive non-mirror matches, fixes
mirrors at 0.5 downstream, and drops draws, byes/forfeits, ambiguous player joins, and unmatched
rows with coverage counters. It does not currently establish first-play/draw assignment, match
format or best-of rules, per-game/postboard state, stable cross-event player identity, bracket or
record at pairing time, or repeated-pair identifiers. Those are acquisition facts to audit, not
assumed covariates.

“Fixes mirrors at 0.5” is a decision-target operation only: mirror rows never enter fitting or
proper-score cases, while same-archetype opponent field share is never discarded or renormalized.

**Algebraic derivation — coherent reversal.** Let the oriented context be
`z=(subject_context, opponent_context, shared_context)`. Reversing a decisive matchup applies a
declared involution `R(z)` that swaps every side-specific field—member, pilot, first-play/draw,
seat, and any side-specific game or deck state—while retaining shared event, rules, match-format,
round, and time fields. The contract is

\[
p_{ab}^{r,z}=1-p_{ba}^{r,R(z)}.
\]

If a required orientation-sensitive field is unavailable, it is represented by a typed
`context_missing` value and either marginalized under a named target distribution or used to refuse
the narrower conditional claim. Draw handling is a separate outcome decision: the current decisive-
match estimand excludes draws; any future three-outcome model must define its own reversal rather
than forcing a complement identity on win/draw/loss probabilities.

**Algebraic derivation — marginalized reciprocity.** If unavailable oriented context is integrated
under distribution `q(z)`, the reversed prediction must integrate under the pushforward
`R#q`, defined by `(R#q)(B)=q(R^{-1}(B))`. Using the same untransformed distribution in both
directions is valid only when `q=R#q`; otherwise it breaks the complement contract.

## Estimable `WeightSnapshot`

**Empirical hypothesis — current-member weights.** Current shares are estimates, not fixed facts.
Each `WeightSnapshot` must bind:

- a sampling frame: eligible classified deck entries from named source/provenance strata;
- an as-of cutoff and half-open time/event window aligned with, but not silently inherited from,
  the outcome snapshot;
- taxonomy version, eligible-member set, and inclusion/exclusion coverage;
- raw member counts and source/event strata;
- a preregistered estimation candidate, beginning with a multinomial empirical-share baseline and
  a simple Dirichlet or event-block bootstrap smoother;
- posterior or bootstrap weight draws, effective member count, maximum weight, and unclassified or
  uncovered target mass; and
- a `weight_snapshot_id` plus method and random-seed identity.

Outcome-parameter draws and weight draws represent different uncertainties and must be generated
and retained separately. Standardization pairs or nests those draws under a preregistered scheme;
it must not reuse one point weight vector across every outcome draw. If the sampling frame is not
credible for the claimed population, the window is too thin, or plausible smoothing choices reverse
the member action, emit `weight_unidentified`, `weight_frame_mismatch`, or
`weight_sensitive` and refuse or relabel the current-mixture claim.

## Candidate target populations

### 1. Current-meta mixture

Set `u^S_a` to member `a`'s share among eligible family-`S` decks in the current regime, and
`v^T_b` analogously for family `T`. Then

\[
\theta^{\text{current}}_{S,T}
= \sum_{a,b} s_{a\mid S,r}s_{b\mid T,r}p_{ab}^{r,z}.
\]

Interpretation: a random currently represented family-`S` deck faces a random currently represented
family-`T` deck. Current positioning includes composition: if a family is currently
concentrated in a member with favorable pairings, that is part of its present positioning rather
than a nuisance to remove.

When `S` and `T` share the same member label—or when a member is ranked against a field containing
itself—the corresponding target mass remains present at structural 0.5. Removing it would silently
renormalize the opponent field and answer a different decision question.

This is the natural headline for **what family population is well positioned now**, with two
qualifications. First, “now” means the named regime and share-estimation window, not an enduring
family property. Second, it is not the payoff from a user optimally choosing a member after choosing
the family. It describes an empirical random-member policy. A decision aid can use it to screen
families, then return to member-level recommendations.

To rank families against the field, each family needs the same opponent target. Let `m_b^r` be the
current field share of opponent archetype `b`. Define

\[
\phi_S^{\text{current}}
= \sum_{a \in A_S}s_{a\mid S,r}\sum_b m_b^r p_{ab}^{r,z}.
\]

The family-by-family matrix decomposes this field score, but comparing row averages that use
different opponent populations would not answer a common decision question. The common current
field distribution is therefore load-bearing for “which family is best positioned.”

### 2. Equal-member or balanced-family mixture

Set `u^S_a=1/|A_S|` and `v^T_b=1/|A_T|` over an explicitly eligible member set. This answers:
what happens if each named member is equally likely? It is useful for distinguishing matchup-role
coherence from current popularity and for comparing the same taxonomy across share changes.

It is not an “intrinsic family strength.” Equal weighting creates a synthetic population just as
surely as current-share weighting describes an empirical one. It can give a tiny fringe member the
same influence as a dominant member, and the result can jump when a low-volume member is added to or
removed from the taxonomy. Work on target-population inference explicitly distinguishes a typical
unit from a heterogeneous sample spanning the population; one typical representative does not
stand in for the heterogeneous average `[superrep-estimand-target-generalizability]{11}`.

Balanced-family results therefore belong as a labeled secondary estimand and sensitivity test, not
as the default answer to current positioning.

### 3. Capped-current or tempered mixture

A robust descriptive policy can cap each current share at `c` and renormalize, or temper shares as
`u_a proportional to s_a^gamma` for `0 < gamma < 1`. These constructions reduce dominance by high-share
member while retaining some relationship to current prevalence.

They are defensible only when named as synthetic policies. Capping does not produce a less biased
estimate of the uncapped current population; it changes the population. The weighting literature
shows the general principle directly: analyst-selected target weights define distinct estimands,
and trimming can leave a study-specific subpopulation `[superrep-estimand-balancing-weights]{7}`.

A capped result is useful as a sensitivity path between current and equal weights. It should not
replace the current estimate merely because its interval is narrower.

### 4. Overlap- or evidence-supported target

Weights may emphasize member pairs with support in both the observed and target populations, or the
target may be restricted to members and contexts with adequate evidence. Analogous overlap weights
are bounded and can improve precision for their selected population
`[superrep-estimand-balancing-weights]{7}`. Weak overlap otherwise creates imprecision and
specification sensitivity `[superrep-estimand-limited-overlap]{9}`.

This is an honest fallback estimand when the current-meta target cannot be supported, but it answers
“among the supported portion of these families,” not “for the whole current family mixture.” The
display must report excluded target mass and must not compare two cells whose support restrictions
silently define different populations. If restriction removes the member responsible for the
decision, a refusal is more informative than a stable-looking supported-subset estimate.

### 5. User-policy mixture

If a decision maker has an explicit policy `q^S`—for example, a shortlist of members they are
willing and able to pilot—standardization over `q^S` directly targets that user's policy. It
changes the question from current population positioning to expected performance under that user's
choice policy. This is a coherent extension, but no single user-policy quantity can serve as the
public family headline.

## A representative deck is a proxy, not this estimand

A modal deck, medoid list, or curated exemplar can represent family composition for explanation.
Its matchup probability against another exemplar is `p_(a*,b*)`, not
`theta_(S,T)(u,v)`. They coincide only under a strong and separately testable condition—for
example, all materially weighted member pairs have essentially the same predicted probability, or
the selected exemplar pair happens to equal the weighted average for that opponent target.

The distinction between sampling a “typical” unit and sampling heterogeneous units that reflect a
target population is explicit in generalizability design `[superrep-estimand-target-generalizability]{11}`.
For this application, the representative list is therefore a communication artifact. It must not
serve as statistical evidence that the family has the exemplar's matchup profile.

## Composition drift and interpretation

When member shares move from `(u_0,v_0)` to `(u_1,v_1)`, a changed standardized result can arise even
if every member-pair probability is unchanged. Conversely, stable weights can mask changing
member-pair behavior. The current-meta estimand intentionally combines both effects because both
affect present positioning. A stable-taxonomy estimand with fixed reference weights intentionally
removes composition change, but then describes the reference population rather than today's field.

Accordingly, comparisons across time should expose at least two quantities:

- **current-target result at each time**, which answers positioning in each contemporaneous field;
- **fixed-reference result**, using a common member distribution, which isolates changes in the
  modeled matchup surface from changes in family composition.

Their difference is a composition contribution, not necessarily an error. The dynamic choice of
windows and regime transitions belongs to the sibling dynamic-metagame brief; the estimand contract
here requires only that the chosen snapshot be explicit.

## Positivity, overlap, and identifiability

The standardized sum requires a value for every member pair with positive product weight
`u_a v_b > 0`. Direct identification is strongest when those pairs occur in the named target
context. When a positive-weight pair is absent, the result depends on structural borrowing or
extrapolation from the outcome model. No algebraic averaging rule creates evidence for it.

Survey poststratification assumes ignorable or known relative selection within cells
`[superrep-estimand-gelman-weighting]{8}`. MRP research likewise warns that accuracy depends on
correct population cell sizes and representativeness within poststratification cells
`[superrep-estimand-mrp-limits]{10}`. Transferred here, a member label alone may not make matches
exchangeable: pilot skill, event selection, build variants, and the game/postboard mix can differ
between observed matches and the target context.

The following states should remain distinct:

- **supported:** target-weighted member pairs have direct evidence in the target context;
- **borrowed:** sparse pairs are estimated through a declared model with connected evidence;
- **extrapolated:** positive target mass lies beyond observed support;
- **unidentified/refused:** the model cannot justify a target-population claim.

An overlap-restricted result can turn extrapolated into supported only by narrowing the target. The
limited-overlap literature is explicit that restriction identifies an optimally estimable
subpopulation rather than restoring the original population `[superrep-estimand-limited-overlap]{9}`.

## Composition-sensitivity diagnostics

**Project decision — diagnostic battery.** Every family comparison should be evaluated across the
versioned preregistered target-policy registry before receiving a
decision label. Useful diagnostics are:

1. **Current-versus-balanced delta:**
   `theta_current - theta_equal`, with uncertainty. This measures dependence on observed
   composition without declaring either estimand correct for all uses.
2. **Decision reversal:** whether current, equal, and one preregistered tempered policy fall on
   different sides of the decision threshold.
3. **Peak leave-one-member-out influence:** the maximum change over the finite set obtained by removing each eligible member and
   renormalizing.
4. **Peak pair influence:** the maximum `u_a v_b` contribution over eligible pairs and its
   uncertainty contribution.
5. **Effective member count:** `1 / sum_a(u_a^2)` on each side, reported alongside raw eligible
   member count. A nominally multi-member family can behave as a singleton under concentrated
   weights.
6. **Unsupported target mass:** `sum_(a,b) u_a v_b I_unsupported(a,b)`, split between borrowing
   and extrapolation.
7. **Membership-boundary sensitivity:** recompute under the complete versioned
   `TaxonomyScenarioRegistry` below without using outcomes to choose a preferred boundary.

**Project decision — membership uncertainty.** The primary analysis uses one taxonomy snapshot
frozen at the origin. Sensitivity uses a versioned `TaxonomyScenarioRegistry` generated as follows:

1. `TaxonomyPolicyVersion` freezes the composition-only assignment score, inclusion threshold,
   runner-up rule, and current-member eligibility floor (`field_share >= 0.001`) before outcome
   fitting. A member must also be legal, classified, and present in the origin's sampling frame.
2. A member is a boundary candidate only when its composition-only inclusion margin is inside the
   preregistered band `b` or the registry marks it `assigned` without defining/curated provenance.
3. Each candidate receives exactly one composition-only alternate: its eligible runner-up family,
   or exclusion when no runner-up clears the frozen inclusion threshold.
4. Rank candidates by absolute inclusion margin, then stable member id. Take at most `B=4` and emit
   the complete Cartesian primary/alternate closure (`2^B`, at most 16 scenarios), including the
   primary snapshot. More than four unresolved candidates yields
   `taxonomy_scenario_overflow` and blocks launch rather than silently truncating uncertainty.
5. Every scenario records generator version, origin, source registry, candidate margins, alternate
   reasons, membership map, and content hash. The set is closed only when every combination of the
   selected candidates' primary/alternate states is present.

Recompute weights, standardized cells, and the two-stage member action in every scenario. The launch
gate aggregates by unanimity/worst case: every required clause must pass in every scenario; a false
clause fails and a missing scenario result is `not-evaluated`, which blocks launch. Taxonomy-policy
parameters are set without outcomes or selected inside nested rolling training folds and frozen
before the final holdout. Global outcome-based selection on the evaluation origins is prohibited.

A family-level lean should be refused or downgraded when plausible policies reverse the decision,
one member controls the result, or unsupported target mass is material enough that the conclusion is
primarily extrapolation. Exact thresholds require empirical calibration in the validation sibling;
this brief does not prescribe them.

## When poststratification is misleading

Poststratification can produce a precise-looking but misleading family result when:

- the target population is unnamed, so readers interpret current-share and balanced estimates as
  the same property;
- weights come from a selectively observed tournament sample but the claim is about all potential
  Legacy players or events;
- the target cell counts are stale, estimated with unpropagated uncertainty, or inconsistent with
  the outcome regime;
- positive target mass occupies member pairs without support and the model's extrapolation is not
  surfaced;
- important within-member effect modifiers are omitted, violating the within-cell
  representativeness premise;
- a cap, trim, or overlap restriction is introduced for stability but the label still names the
  original current population;
- endogenous current popularity is interpreted as intrinsic family quality. Current share is valid
  for a descriptive current mixture, but not for a composition-invariant claim;
- a representative member is substituted for the two-sided average.

The target-population literature does not license weighting as a universal repair. MRP is explicitly
described as no silver bullet when cell totals or within-cell representativeness fail
`[superrep-estimand-mrp-limits]{10}`, and limited overlap can make estimators imprecise and
specification-sensitive `[superrep-estimand-limited-overlap]{9}`.

## Decision-useful conclusion

**Project decision — public estimand.**

For the public question **“what family is well positioned now?”**, the primary estimand should be:

- current-regime eligible-member shares within the subject family;
- a common current-regime field distribution on the opponent side for family ranking;
- current-regime conditional member shares on both sides for each family-by-family explanatory
  cell;
- an explicitly named tournament, pilot, game, and as-of population;
- posterior or sampling uncertainty propagated through both standardizations.

Equal-member and tempered-weight results should accompany the headline as composition-sensitivity
diagnostics. An overlap-restricted result may be shown only as a differently labeled supported-
population estimate. If these estimands disagree in a decision-relevant way, the honest output is
“composition-sensitive family,” followed by member-level detail—not an averaged lean.

**Project decision — decision use.** This headline screens or explains the field. The primary
playable recommendation is produced only after the frozen second-stage rule selects an eligible
member archetype. The validation target is regret and top-k utility of that final member action
against an archetype-only policy, not regret of a family label.

## Implementation-relevant implications

- Store the target member vectors and their as-of identity with every family result; do not store
  only the scalar probability.
- Store the `WeightSnapshot` sampling frame, estimation method, and weight draws separately from
  outcome-model draws, and propagate both through standardization.
- Keep member-pair prediction separate from standardization so the same predictive surface can
  answer current, balanced, and user-policy questions without refitting.
- Compute family positioning against one shared field target; use family-by-family cells as an
  additive explanation of that common-target score.
- Carry uncertainty and evidence-status indicators through the double sum.
- Treat cap, trim, and overlap policies as separately named estimands, not renderer options.
- Keep exemplar decklists on an explanatory surface and prohibit their values from substituting for
  standardized probabilities.
- Make composition sensitivity a typed decision gate, not caveat prose generated after ranking.
- Make the family-to-member selection rule an explicit origin-versioned policy; no renderer may
  turn a family score directly into a playable recommendation.

These implications specify contracts and evaluation targets. They do not select an outcome model,
missingness model, temporal update rule, or validation threshold; those belong to sibling briefs.

## Disconfirming analysis

The source search actively tested whether current-share standardization should always be preferred.
It should not. Lack of overlap can cause imprecision, and restricting inference to an optimal
subpopulation can estimate the effect for that subpopulation more precisely
`[superrep-estimand-limited-overlap]{9}`. **Campaign inference — target change.** Such a restriction
changes the target population; it does not recover the original whole-population quantity. Thus a
current-meta headline is not justified when its positive target mass is unsupported; refusal or a
clearly renamed restricted target is preferable.

The search also tested whether an equal-member target provides an objective composition-free family
property. No assessed source supports that interpretation. Standardization theory instead says
weights define a hypothetical population, and different choices produce different quantities
`[superrep-target-populations]{24}`. Equal weighting remains useful, but only as an explicit synthetic
policy.

Finally, a representative member is operationally attractive and may communicate a family better
than a probability mixture. Generalizability design distinguishes typical from heterogeneous
sampling rather than treating them as interchangeable `[superrep-estimand-target-generalizability]{11}`.
The representative-deck approach is therefore retained as an explanatory proxy but rejected as the
family matchup estimand absent demonstrated homogeneity.

## Contradictions

### C1 — recognizable current population versus estimable overlap population

Muller and MacLehose favor marginal standardization when inference is intended for the total
population `[superrep-target-populations]{24}`. Li, Morgan, and Zaslavsky emphasize that the automatic
whole-sample target can be questionable and develop an overlap population with bounded weights and
better precision properties `[superrep-estimand-balancing-weights]{7}`. This is a **tension**, not a
logical contradiction: the former prioritizes fidelity to the named population; the latter shows
why another population can be scientifically preferable. For superarchetypes, the positions must
remain visible as separate outputs—current-meta or refusal for the headline, supported-overlap only
under a changed label.

### C2 — heterogeneous population average versus typical representative

Target-population design distinguishes heterogeneous sampling that spans a population from typical
sampling centered on representative units `[superrep-estimand-target-generalizability]{11}`. These are
**incommensurable** estimands rather than rival estimators of one quantity. A representative deck can
answer “what does this family look like?” while two-sided standardization answers “how does this
family population perform?”

## Suggested cross-references to sibling subdomains

- **Non-transitive outcome model:** it should expose member-pair predictive distributions
  (p_{ab}^{r,z}) without collapsing them to scalar family strength, and it should support
  post-fit standardization under multiple weight policies.
- **Sparse and selectively observed evidence:** it should define the support graph and evidence
  states used by unsupported-target-mass diagnostics, including when structural borrowing becomes
  extrapolation.
- **Dynamic metagame representation:** it should define the as-of snapshot, share-estimation window,
  eligible-member lifecycle, and fixed-reference decomposition needed for composition drift.
- **Validation and decision utility:** it should calibrate refusal thresholds for weight-policy
  reversals, member influence, and unsupported target mass, and test whether current-share family
  scores improve future decisions.

## Attested sources

- `superrep-target-populations` — marginal predictions and target populations.
- `superrep-estimand-gelman-weighting` — survey weighting and population-cell assumptions.
- `superrep-estimand-balancing-weights` — analyst-selected targets and overlap weights.
- `superrep-estimand-limited-overlap` — limited overlap and target restriction.
- `superrep-estimand-mrp-limits` — MRP limitations and structured priors.
- `superrep-estimand-target-generalizability` — typical versus heterogeneous units.
