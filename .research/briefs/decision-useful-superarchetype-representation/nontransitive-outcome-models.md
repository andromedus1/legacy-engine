---
description: "Model families for estimating sparse member-pair matchup probabilities while preserving reciprocity and strategic cycles"
type: brief
kind: research
slug: decision-useful-superarchetype-representation-nontransitive-outcome-models
research_method: /deep-research
verification_status: attested
provenance: agent-synthesis
updated: 2026-08-01
summary: "A superarchetype model should estimate an antisymmetric member-pair log-odds surface, using fixed composition families as a shrinkage hierarchy rather than collapsing matchups to scalar strength or relearning taxonomy from outcomes. A structured family-pair model and a low-rank skew model deserve empirical comparison against transitive and cellwise baselines; none is justified without a sparse-data falsification pass."
key_findings:
  - "Reciprocity is an algebraic contract: model one skew-symmetric log-odds surface so reversing a matchup negates the logit and complements the probability."
  - "Scalar Bradley-Terry structure cannot retain rock-paper-scissors behavior; family-pair interactions or another explicitly antisymmetric residual are required."
  - "The most legible candidate decomposes member-pair log odds into member strength, a skew family-pair interaction, opponent-family member deviations, and an optional strongly shrunk pair residual."
  - "Low-rank blade-chest or skew-matrix models preserve cycles and share evidence across cells, but their latent dimensions are assumptions and their coordinates are not substantively identified."
  - "Composition-derived membership can safely define the hierarchy if membership remains fixed during outcome fitting; outcome-response clustering is a separate behavioral taxonomy, not the same superarchetype construct."
  - "Independent cell estimates, Bradley-Terry, and no-pair-residual structured models are necessary falsification baselines, not disposable straw models."
confidence: speculative
status: draft
related:
  - {slug: .research/briefs/decision-useful-superarchetype-representation/estimand-target-population.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/sparse-selective-evidence.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/dynamic-metagame-representation.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/validation-decision-utility.md, relationship: parallel-to}
---

# Non-transitive hierarchical outcome models

## Scope and first-principles decomposition

The required output of this subproblem is not a ranking. It is a set of member-pair probabilities
that a later estimand can combine into a family-versus-family statement. Let archetypes be (i,j),
fixed composition-defined families be (g(i),g(j)), observed wins be (y_{ij}) out of (n_{ij}),
and (p_{ij}) be the chance that (i) beats (j) under the model's other conditioning choices.
The irreducible structural contract is

\[
\eta_{ij}=\operatorname{logit}(p_{ij}),\qquad
\eta_{ij}=-\eta_{ji},\qquad
p_{ij}=1-p_{ji},\qquad \eta_{ii}=0.
\]

**Algebraic derivation — structural diagonal.** `eta_ii=0` means `p_ii=0.5` for decision
standardization under randomized reversal-invariant orientation. It is not a likelihood parameter:
observed mirror rows are excluded from fitting and all-case proper-score evaluation. Same-archetype
opponent field mass nevertheless remains in theta, phi, member utility, and oracle utility at the
structural 0.5 value.

Chen and Joachims explicitly formulate a matchup matrix as a real skew-symmetric matrix on the
log-odds scale; any real matchup function that reverses sign when the competitors reverse preserves
the probability-complement relation.[superrep-chen-intransitivity]{4} This is the leverage point:
reciprocity should be true by construction, not repaired after two directional models disagree.

The four questions that then distinguish model families are:

1. **Expressiveness:** which cyclic probability surfaces can the model represent?
2. **Information sharing:** which observed pairs inform an unobserved or thin pair?
3. **Identification:** which parameters are determined by the likelihood, and which are merely one
   coordinate system for the same predictions?
4. **Small-data behavior:** what does the model shrink toward when evidence cannot support its full
   expressiveness?

These questions prevent a common category error: a representation can be universal at high
dimension and still be unusable with sparse observations.

**Algebraic derivation — context reversal.** Antisymmetry applies only after the model contract
defines the reversal transform for context. For oriented context `z`, `R(z)` swaps member, pilot,
first-play/draw, seat, and every other side-specific field while retaining shared event, rules,
match-format, round, and time fields. The modeled contract is
`eta(i,j,z) = -eta(j,i,R(z))`. An unknown orientation-sensitive field is typed missingness to be
marginalized under a named target or used to refuse a conditional prediction; it is not silently
treated as symmetric. The current engine supplies decisive match orientation and aggregate scores
but does not establish all of those context fields, so richer conditional models remain an
acquisition-blocked empirical hypothesis.

## Why scalar hierarchy is an insufficient endpoint

Bradley–Terry uses one positive ability per competitor, so matchup log odds are a difference of two
scalar abilities.[superarchetype-bradley-terry2]{1} Player covariates and player-level random effects
can make that scalar model hierarchical and share evidence among competitors, but the underlying
matchup still has subtractive form. Balduzzi and collaborators identify subtractive rating
differences as the transitive component of an antisymmetric game and distinguish it from a cyclic
component.[superrep-balduzzi-gamescapes]{2}

Therefore, a hierarchy over scalar member abilities can be useful as a baseline or one component,
but it cannot be the complete representation when matchup-specific counters matter. Partial pooling
does not by itself cure transitivity; the pooled quantity must include an interaction that can cycle.

## Candidate model families

### 1. Independent antisymmetric cells

The least structured non-transitive baseline assigns one parameter to each unordered archetype
pair:

\[
y_{ij}\sim\operatorname{Binomial}(n_{ij},\operatorname{logit}^{-1}(\eta_{ij})),
\qquad \eta_{ji}=-\eta_{ij}.
\]

A common shrinkage distribution centered at zero can stabilize observed cells, but there is no
cross-pair prediction beyond that shared center. This baseline can represent any finite matchup
matrix and has directly interpretable cells. Its cost is quadratic parameter growth, no principled
imputation for an unseen pair, and large posterior uncertainty for thin pairs.

It remains essential because it falsifies a structured model's claimed sharing benefit. If a
hierarchical or latent model cannot improve future predictions over honest cellwise shrinkage, the
extra structure has not earned its assumptions.

### 2. Scalar Bradley–Terry and hierarchical scalar Bradley–Terry

The transitive baseline is

\[
\eta_{ij}=s_i-s_j.
\]

Family membership can enter through (s_i\sim N(\mu_{g(i)},\sigma_s)), or member features can
predict (s_i), which is the standard structured-ability move documented by BradleyTerry2.
[superarchetype-bradley-terry2]{1} This model is economical, identified after fixing a location
constraint, and can predict unseen pairs as long as both members have evidence elsewhere. Its
falsifiable assumption is severe: every counter relationship is explainable by a single global
merit order.

This baseline is informative precisely when it performs well. It would indicate that the available
sample does not support—or the decision does not benefit from—additional cyclic structure.

### 3. Fixed-family antisymmetric interaction hierarchy

A legible design hypothesis is to add structure in layers while preserving sign reversal at every
layer:

\[
\eta_{ij}=
(s_i-s_j)
+\Phi_{g(i),g(j)}
+\bigl(u_{i,g(j)}-u_{j,g(i)}\bigr)
+\rho_{ij}.
\]

Here:

- (s_i-s_j) is a transitive member-strength component;
- (Phi_{AB}=-\Phi_{BA}) is a family-pair interaction, allowing family-level cycles;
- (u_{i,B}) is member (i)'s deviation specifically against opponent family (B), paired with
  the reverse term so the whole surface remains antisymmetric; and
- (\rho_{ij}=-\rho_{ji}) is an optional archetype-pair residual with substantially stronger
  shrinkage than the higher levels.

**Empirical hypothesis — structured family model.** This exact decomposition is synthesized for
comparison, not a model claimed
by one source. Its advantage is inspectability: predictions can be attributed to global member,
family-pair, member-by-opponent-family, and residual terms. It interpolates between useful
baselines: removing all interactions yields Bradley–Terry; removing (\rho) tests whether the fixed
families explain the remaining counter structure; retaining only (\rho) approaches cellwise
estimation.

The corresponding identification obligations are not optional:

- fix the additive location of the (s_i);
- impose zero-sum constraints on member deviations within each family and opponent-family column,
  so (Phi) remains a family mean rather than an arbitrary transfer between levels;
- make (Phi) and (\rho) skew-symmetric with zero diagonals; and
- recognize that variance components and residual allocations may be weakly identified even after
  algebraic constraints, especially in disconnected or thin comparison graphs.

Spearing and collaborators provide an existence proof for a related decomposition: Bradley–Terry
log odds plus antisymmetric pair adjustments, with Bayesian clustering of both ability and
intransitivity levels.[superrep-spearing-intransitive-bt]{23} Their simulation discussion also gives
the warning this candidate needs: the learned intransitivity structure was harder to recover with
few repeated round robins and improved as evidence increased.[superrep-spearing-intransitive-bt]{23}

### 4. Discrete intransitivity-level models

The ICBT model of Spearing and collaborators assigns pair effects to a learned finite set of
antisymmetric intransitivity levels and competitors to learned skill levels. It nests
Bradley–Terry when no intransitivity level is needed and can be parsimonious when many pairs share
the same adjustment.[superrep-spearing-intransitive-bt]{23}

This is different from the fixed-family hierarchy above. Its clusters are learned from outcomes,
apply to pair effects rather than composition families, and use reversible-jump inference over the
number and allocation of levels. That can discover repeated counter magnitudes without requiring a
continuous latent geometry. It also creates a harder inference surface and yields discrete pair
classes whose relationship to a domain taxonomy is indirect. The paper's reference-team constraint
is a concrete reminder that an identified parameterization can contain fixed values that must not
be given substantive meaning.[superrep-spearing-intransitive-bt]{23}

### 5. Blade-chest and low-rank skew relational models

Chen and Joachims represent each member with multidimensional “blade” and “chest” vectors and use
an antisymmetric bilinear interaction, optionally plus scalar strength. They prove that dimension at
least the item count can represent any matchup matrix, while lower dimensions regularize by forcing
shared relational structure.[superrep-chen-intransitivity]{4}

A closely related algebraic form is

\[
\eta=UV^T-VU^T + (s\mathbf{1}^T-\mathbf{1}s^T),
\]

which is skew-symmetric for any (U,V). Lee and Chen develop a likelihood-based approximately
low-dimensional skew-matrix family specifically for sparse observed pairs and report theoretical
sparse-recovery guarantees plus simulation and application evidence.[superrep-lee-chen-skew-matrix]{16}
That source is a recent preprint, so the result is a method worth testing rather than a settled
default.

These models share across pairs without forcing transitivity and can discover a compact counter
geometry. Their small-data behavior depends heavily on chosen dimension and regularization. Their
latent coordinates are also non-unique: transformations can change the embeddings without changing
the matchup matrix. **Algebraic derivation — factor invariance.** This invariance follows from the
factorized form; predicted
pair probabilities, not coordinate labels or axes, are the interpretable target.

Low rank is itself falsifiable. Balduzzi and collaborators show that long strategic cycles can force
the rank—and therefore the dimension of a faithful gamescape—close to the population size.
[superrep-balduzzi-gamescapes]{2} If Legacy's useful counter structure consists of numerous local
niches, aggressive low-rank compression may erase exactly the effects of interest.

### 6. Response-graph and category approaches

Response-graph methods compare strategies by their relational roles against all other strategies,
then spectrally cluster and contract the graph while retaining directed group relations.
[superrep-response-graphs]{22} They directly express the intuition that two members are behaviorally
similar when their entire counter profiles are similar, not merely when they have equal average
win rates.

These methods are better understood here as descriptive compression or a diagnostic alternative
taxonomy than as a complete probability estimator. Their graph is constructed from the outcome
surface that this subproblem is trying to estimate. Using its clusters as the production
composition families would therefore let outcomes redefine the taxonomy. That is legitimate only
if the product explicitly changes the meaning of “superarchetype” from composition family to
behavioral role.

## Comparison matrix

| Family | Cycles | Shares evidence across pairs | Unseen-pair behavior | Main identification burden | Thin-data failure mode |
|---|---:|---:|---|---|---|
| Independent antisymmetric cells | Yes | Only through common shrinkage | Reverts to prior | One orientation per unordered pair | Mostly uncertainty; little borrowing |
| Bradley–Terry / scalar hierarchy | No | Yes | Strength difference | Global location; variance components | Confidently smooths genuine counters away |
| Fixed-family interaction hierarchy | Yes | Yes, through fixed families | Family and member hierarchy | Cross-level centering; connectedness; variance separation | Negative transfer within heterogeneous families |
| Discrete intransitivity levels | Yes | Yes, through learned pair classes | Prior over class allocation | Label/order constraints; reference choices; model dimension | Unstable class count or allocations |
| Low-rank skew / blade-chest | Yes | Yes, through latent factors | Factor geometry | Factor-basis invariance; rank selection | Underfit niches or overfit factors |
| Response-graph clustering | Yes, descriptively | Compresses relational roles | Requires an estimated graph first | Spectral and clustering choices | Clusters noise or changes with missing edges |

No row wins on first principles. The validation sibling deterministically selects the least-complex
inner-qualified candidate using nested training only, freezes it before each outer holdout, and
evaluates it once; the outer holdout never chooses among these rows.

## Composition taxonomy as hierarchy, not outcome target

**Project decision — primary taxonomy.** The primary fit uses the composition-only registry frozen
at the forecast origin. Ambiguous membership is tested only through the estimand brief's versioned,
complete `TaxonomyScenarioRegistry`; outcomes neither update membership probabilities nor choose
among those scenarios inside the evaluated fit. Outcome-based policy selection is prohibited
globally and must be nested inside rolling training folds when it is used at all.

Composition-based family membership can enter the outcome model without becoming outcome-defined:

1. Freeze (g(i)) before fitting outcome parameters.
2. Use (g(i)) only to index prior means, variance pools, and family-pair interactions.
3. Fit outcome parameters conditional on that fixed mapping.
4. Treat response-profile disagreement as evidence that the hierarchy does not share well, not as
   permission to silently move a member.

Under this separation, outcomes can falsify the usefulness of a composition family for matchup
borrowing while leaving the taxonomy's meaning intact. An outcome-derived response-graph cluster
may be displayed as a diagnostic or proposed later as a different ontology, but it must not replace
the family label inside the same fit-and-evaluate pass. This separation is a methodological
inference from the difference between fixed covariate hierarchy and outcome-response clustering,
not a claim directly tested by the cited papers.

## Falsifiable assumptions and minimum candidate set

**Empirical hypothesis — candidate ladder.**

The modeling comparison should include at least these nested or contrasting candidates:

1. **Cellwise:** independent antisymmetric pair cells with honest shrinkage.
2. **Transitive:** scalar Bradley–Terry, with and without family hierarchy.
3. **Family structured:** family-pair plus member-by-opponent-family deviations, initially without
   the archetype-pair residual.
4. **Family structured plus residual:** the same model with a strongly shrunk pair residual.
5. **Relational latent:** a low-dimensional skew factor model with dimension selected without using
   the final evaluation period.

The discrete ICBT and response-graph approaches are useful secondary candidates if the primary set
exposes repeated residual levels or coherent behavioral roles. They need not be assumed superior
to the simpler models.

The assumptions are falsifiable in plain terms:

- **Family exchangeability:** after known terms, members of the same composition family borrow
  information without systematic predictive harm.
- **Opponent-family smoothness:** a member's results against one member of opponent family (B)
  inform its results against other members of (B).
- **Residual sparsity:** most archetype-pair peculiarities are small enough to shrink toward zero.
- **Low relational dimension:** a small number of latent counter dimensions predicts held-out pairs
  without erasing local niches.
- **Stationarity within the fitted slice:** pair effects do not average incompatible regimes; the
  dynamics sibling owns how to form or model that slice.

## Implementation-relevant implications

**Project decision — model contract.**

- The model-facing data contract should orient each unordered pair once and derive the reverse
  probability, rather than fitting two directional cells.
- Every candidate should return member-pair predictive distributions or draws. A downstream family
  representation should aggregate predictions with uncertainty, not aggregate fitted component
  coefficients.
- Family membership is an input with provenance and a frozen version. It is not a latent label in
  the primary outcome fit.
- The fit should retain component diagnostics: transitive contribution, family-pair contribution,
  member deviation, and residual where present. These are diagnostics, not independent probabilities.
- A disconnected comparison graph or weak cross-level identification should produce an explicit
  refusal or prior-dominated marker. A numerically converged fit is not sufficient evidence.
- Latent embeddings should not be given semantic axis names. Only their induced pair probabilities
  and predictive behavior are stable targets.
- Candidate selection must use the validation sibling's nested inner rolling algorithm and fixed
  complexity/tie order. Outer future predictions evaluate the already frozen candidate exactly once;
  table coverage cannot select or replace it.

## Disconfirming analysis

Several observations could overturn the case for a non-transitive hierarchy:

- A scalar Bradley–Terry hierarchy could match or beat the cyclic candidates on held-out pair
  probabilities. That would mean the available data do not justify cyclic parameters, even if
  historical point estimates contain apparent cycles.
- Honest cellwise shrinkage could outperform family borrowing. That would falsify the claim that
  composition families are exchangeable enough to improve outcome estimation.
- Apparent cycles could disappear after the dynamics and selective-observation siblings account for
  regime mixing and who chooses to enter which events. A more expressive static model might otherwise
  encode those biases as “strategy.”
- A low-rank model could improve average log loss while damaging the few matchup reversals that drive
  actual decisions. Average predictive improvement would not by itself validate the representation's
  decision use.
- The family hierarchy could be too small to estimate: a family-pair interaction plus
  member-by-opponent-family deviations may consume more effective degrees of freedom than the current
  corpus supports. Spearing and collaborators' recovery difficulty at lower repeated-match counts is
  direct evidence against assuming that Bayesian regularization makes structure identifiable.
  [superrep-spearing-intransitive-bt]{23}

Searches for disconfirming evidence found both explicit thin-data difficulty in an intransitive
Bayesian model and a theoretical reason low-dimensional compression can fail for long cycles.
[superrep-spearing-intransitive-bt]{23}[superrep-balduzzi-gamescapes]{2} No attested source establishes
that composition-derived MTG families are outcome-exchangeable; that remains an empirical hypothesis.

## Contradictions

| Issue | Position A | Position B | Relationship |
|---|---|---|---|
| Universal expression versus sparse recovery | Blade-chest can represent any matchup matrix when dimension is at least the item count.[superrep-chen-intransitivity]{4} | Sparse recovery requires exploitable structure such as approximate low dimension; long cycles can require dimension near the population size.[superrep-lee-chen-skew-matrix]{16}[superrep-balduzzi-gamescapes]{2} | tension |
| Fixed taxonomy versus behavioral categories | A composition family can be a fixed hierarchy used to share parameters without moving members. | Response-graph clustering groups strategies by outcome-relative roles against the full population.[superrep-response-graphs]{22} | incommensurable: they define different kinds of group |
| Smooth geometry versus discrete pair classes | Blade-chest and skew-factor models represent counter structure continuously in a latent space.[superrep-chen-intransitivity]{4}[superrep-lee-chen-skew-matrix]{16} | ICBT allocates pair effects to a learned finite set of intransitivity levels.[superrep-spearing-intransitive-bt]{23} | incommensurable modeling assumptions |
| Scalar ranking versus matchup surface | Bradley–Terry represents each competitor by one ability.[superarchetype-bradley-terry2]{1} | Intransitive models admit that no single obvious ranking follows from pair interactions.[superrep-spearing-intransitive-bt]{23} | contradicts when cycles are materially present |

These conflicts should not be resolved by averaging the models. They define hypotheses for empirical
comparison and, in the taxonomy case, different product semantics.

## Suggested cross-references to sibling subdomains

- **Estimand and target population:** consumes member-pair predictive draws and defines the member
  mixtures used to produce family-versus-family quantities.
- **Sparse and selectively observed evidence:** owns comparison-graph support, observation bias,
  prior domination, and refusal rules for thin cells.
- **Dynamic metagame representation:** determines whether parameters vary by regime or which time
  slice is coherent enough for a static fit.
- **Validation and decision utility:** adjudicates the candidate set using held-out predictions,
  calibration, and decision-sensitive comparisons rather than served-cell count.

## Attested source map

1. `[superarchetype-bradley-terry2]{1}` — structured and random-effect Bradley–Terry.
2. `[superrep-chen-intransitivity]{4}` — blade-chest antisymmetric representation.
3. `[superrep-spearing-intransitive-bt]{23}` — clustered intransitive Bradley–Terry.
4. `[superrep-lee-chen-skew-matrix]{16}` — sparse low-dimensional skew-matrix model (preprint).
5. `[superrep-balduzzi-gamescapes]{2}` — transitive/cyclic decomposition and population geometry.
6. `[superrep-response-graphs]{22}` — relational-role response graphs and contraction.
