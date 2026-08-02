---
description: "Which prior-art approaches can help turn heterogeneous archetype members into a decision-useful superarchetype matchup representation?"
type: landscape
kind: research
slug: superarchetype-representation-prior-art
research_method: /scout
verification_status: attested
provenance: agent-synthesis
updated: 2026-08-01
summary: |
  Maps direct game, statistical, and cross-domain precedents for representing a changing family of
  heterogeneous competitors without erasing sparse, non-transitive matchup structure. A working
  hypothesis combines a member-level matchup model with explicit target-population standardization
  and evaluates the resulting probabilities on future-only holdouts.
key_findings:
  - "A superarchetype rate has no stable meaning until its target member distribution is named; current-share and equal-member estimates answer different questions."
  - "Scalar ratings are structurally insufficient for cyclic metagames; useful precedents preserve a directed counter table or a multidimensional relational representation."
  - "The observed matchup matrix may be selectively missing because popularity and tournament participation determine which pairs are seen."
  - "Coverage is not a model-selection objective; candidate representations should compete on proper probabilistic scores, calibration, and future decision stability."
  - "Among the seven assessed sources, none jointly supplies outcome-blind taxonomy, non-transitive partial pooling, poststratification to a changing meta, and future-regime validation."
status: draft
---

# Scout Landscape: Decision-useful superarchetype representation

## Context

The shipped superarchetype layer successfully builds an outcome-blind strategy taxonomy and uses it
as an opponent-side fallback. An exploratory real-corpus preview showed that the same machinery
produced almost no displayable subject-family comparisons under the existing honesty gates. This
Scout asks a different question from the existing aggregation brief:
how can member archetypes become a representation of the family that is meaningful enough to compare
families and make deck-selection decisions?

## Search vectors

**Direct:** MTG archetype aggregation; sparse PvP counter tables; non-transitive matchup models;
response-graph contraction.

**Adjacent:** hierarchical paired comparisons; marginal standardization and poststratification;
informatively missing matrices; probabilistic calibration and temporal backtesting.

**Analogous:** financial index weighting and rebalancing; sports association aggregation;
epidemiologic target populations; ecological community distributions; mixture-of-experts and
predictive stacking.

## Landscape

### 1. Define the represented population before choosing the estimator

#### Muller & MacLehose — assessed

**Key insight.** An aggregate predicted probability is inseparable from the population weights used
to construct it: marginal standardization targets the observed population, while prediction at
representative inputs targets a different—sometimes nonexistent—stratum
`[superrep-target-populations]{1}`.

**Relevance.** “Superarchetype win rate” is underspecified. A current-meta mixture answers what a
random currently played member would do; equal-member weighting answers what a synthetic balanced
family would do. The headline must name one, while the other can serve as a sensitivity analysis.

#### Financial-index and epidemiologic analogues — brief mentions

Financial-index and epidemiologic target-population methods were included as orientation search
vectors. Their possible lessons about weights and changing populations remain questions for the
deep-research branches, not established transfers from this Scout.

### 2. Preserve relational matchup structure

#### Chen & Joachims — assessed

**Key insight.** A competitor can be represented by multidimensional offensive and defensive
features whose interaction produces a skew-symmetric matchup matrix. This retains cyclic advantages
that a scalar ability cannot express `[superrep-chen-intransitivity]{2}`.

**Relevance.** A family representation should not be a single strength number. The candidate model
must retain family-pair interactions, whether explicitly as pair effects or through a lower-dimensional
relational embedding. Expressiveness is not enough: dimension and regularization must be selected on
held-out predictions.

#### Omidshafiei et al. — assessed

**Key insight.** Strategies can be grouped by similarity of their relationships to every other
strategy, then contracted while retaining directed inter-group edges
`[superrep-response-graphs]{3}`.

**Relevance.** Composition similarity and outcome-role similarity answer different questions. The
project should keep composition-only taxonomy as the membership authority, but response-role
agreement can become an outcome-side validation diagnostic: members claimed to form a family should
occupy compatible relational roles.

#### Lin et al. — assessed

**Key insight.** A large PvP game can be compressed into a manageable category-by-category counter
table while retaining an explicit counter table `[superarchetype-pvp-counter-clustering]{4}`.

**Relevance.** This is a direct precedent for the desired surface shape—a smaller directed counter
table—but it does not establish an honest sparse-data estimator for this corpus.

#### Other game precedents — brief mentions

Nash clustering, incomplete-information response graphs, online counter-category learning,
Hearthstone archetype representatives, and operational MTG analytics remain discovery leads. Their
specific methods were not promoted to evidence in this landscape and should be assessed directly if
the deep-research campaign chooses to rely on them.

### 3. Treat absence of matchups as data-generating structure

#### Jin, Ma & Jiang — assessed

**Key insight.** Matrix completion can explicitly model response-dependent observation; the cited
method is analyzed under low-rank and sparse-covariate assumptions
`[superrep-informative-missingness]{5}`.

**Relevance.** Legacy pairings are not a designed all-pairs experiment, so the observation mechanism
must be investigated rather than assumed ignorable. A dense model must either justify its missingness
assumption or label the resulting limitation. Sparsity alone does not establish low rank.

### 4. Validate forecasts, not coverage

#### Gneiting & Raftery — assessed

**Key insight.** Strictly proper scoring rules reward honest predictive distributions; calibration
and sharpness are distinct forecast qualities `[superrep-proper-scoring]{6}`.

**Relevance.** Model selection should use held-out log score and Brier score plus calibration, not
the number of newly filled cells. Coverage remains a downstream utility statistic and honesty gate.

#### Bürkner, Gabry & Vehtari — assessed

**Key insight.** Ordinary leave-one-out validation can let future observations influence predictions
of the past and therefore overestimate future predictive accuracy; leave-future-out is designed for
the past-to-future task
`[superrep-leave-future-out]{7}`.

**Relevance.** The required validation is rolling-origin across Legacy regimes. Random match splits
would let a model learn future metagame structure before predicting the past.

## Cross-landscape synthesis

The campaign will test this cross-literature working hypothesis:

1. Fit member-pair outcome probabilities with partial pooling while retaining non-transitive
   matchup interactions.
2. Convert those probabilities into family-pair quantities by standardizing over a named target
   distribution of subject and opponent members.
3. Propagate predictive uncertainty through positioning and agency calculations.
4. Compare candidate models on future-only outcomes and decision stability.

This would make the family representation a predictive distribution over matchups, not an average
decklist and not a pooled historical rate. The current-share standardized result is the natural
headline for “what is well positioned now”; an equal-member result is a useful composition-sensitivity
diagnostic. This is a research hypothesis to test, not a selected production design.

## Research recommendations

- **Estimand and target population** — specify current-share, balanced-member, and sensitivity
  estimands and the conditions under which each is identifiable.
- **Non-transitive hierarchical outcome model** — compare explicit family-pair interactions,
  member deviations, and relational embeddings against simple baselines.
- **Sparse and selectively observed evidence** — study informative missingness, direct-versus-
  indirect inconsistency, concentration, and refusal criteria.
- **Dynamic metagame representation** — define regime-aware fitting, weight drift, taxonomy churn,
  and update continuity.
- **Validation and decision utility** — preregister rolling-origin splits, proper scores,
  calibration, coverage, agency error, and rank stability.

## Disconfirming analysis

The Scout actively looked for counterexamples to its working hypothesis. Direct game precedents show
that a useful grouped surface can instead be built by learning counter categories from outcomes,
without poststratifying a pre-existing taxonomy. That weakens
any claim that hierarchical standardization is the uniquely correct construction. Conversely, the
target-population literature does not establish that its estimands remain useful under cyclic
adversarial interactions. Both questions therefore remain explicit comparisons for the campaign.

## Contradictions and transfer limitations

No direct contradiction among the seven attested sources was found; they address different layers.
There is, however, a load-bearing transfer limitation: the response-graph and counter-category
methods may use outcomes to define groups, while legacy-engine intentionally fixes membership from
deck composition to avoid outcome-driven taxonomy and post-selection leakage. Their outcome-side
structure may validate or model a fixed family, but cannot silently replace the membership authority.

## Gaps

Within the bounded sources reviewed, the Scout did not locate one method combining all four required
properties: membership fixed without outcomes, non-transitive partial pooling, standardization to a
changing target mixture, and future-regime validation. The campaign must therefore test whether the
pieces compose instead of assuming that their integration is valid.

## Sources

1. Muller & MacLehose (2014), target populations for predicted probabilities.
2. Chen & Joachims (2016), modeling intransitivity in matchup data.
3. Omidshafiei et al. (2020), clustered and contracted response graphs.
4. Lin et al. (2024), clustered PvP counter relationships.
5. Jin, Ma & Jiang (2022), matrix completion with informative missingness.
6. Gneiting & Raftery (2007), strictly proper scoring rules.
7. Bürkner, Gabry & Vehtari (2020), leave-future-out cross-validation.
