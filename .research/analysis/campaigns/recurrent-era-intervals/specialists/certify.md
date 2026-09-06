---
description: Statistical certification contract for reuniting non-contiguous archetype intervals
type: research
summary: Certify only outcome-free, independently tested equivalence with hard affectedness, context, multiplicity, support, and abstention guards.
updated: 2026-08-13
decisions:
  - Use equivalence rather than failure-to-detect-difference as the statistical burden for interval reunion.
  - Keep matchup outcomes out of discovery and certification; use held-out or future outcomes only after certificates freeze.
  - Control the chance of any false certified reunion across the candidate family, and treat FDR as exploratory only.
  - Represent insufficient support, failed overlap, or unresolved context shift as inconclusive rather than equivalent.
key_findings:
  - Discovery and certification must use independent event-level partitions or selection-adjusted simultaneous inference even when both operate only on deck features.
  - Equivalence margins, support floors, power targets, concentration caps, and error budgets are versioned calibration parameters, not imported constants.
  - Pairwise deck equivalence cannot establish matchup transport if the surrounding field or the conditional win process changed.
provenance: agent-synthesis
---

# Certifying recurrent stable-era intervals

## Recommendation

Treat every proposed reunion as a three-state decision: **certified**, **rejected**, or
**inconclusive**. Certification should mean that an independently evaluated historical interval is
inside prespecified practical-equivalence margins on deck configuration and relevant external
context, passes hard legality/affectedness and support guards, and survives family-level error
control. Ordinary failure to reject a difference is not certification: equality-null tests can miss
real differences through Type II error, especially at limited sample size
[recur-certify-mmd-two-sample]{1} [recur-certify-mmd-two-sample]{3}. Equivalence reverses that
burden by making “different by at least the margin” the null and requiring affirmative evidence to
reject it [recur-certify-fda-equivalence]{1} [recur-certify-kernel-equivalence]{1}.

For a nonnegative discrepancy `D(old, reference)`, the load-bearing hypothesis is:

```text
H0: D >= theta_equiv       # too different to reunite
H1: D <  theta_equiv       # practically equivalent
```

`theta_equiv` is not a universal number. It is a versioned tolerance tied to how much configuration
or context drift the reporting decision can withstand. The FDA guidance's numerical drug margins
are explicitly application judgments; what transfers is the prespecification, power, interval, and
error-control logic, not those values [recur-certify-fda-equivalence]{1}
[recur-certify-fda-equivalence]{3}. Symmetric reunion therefore calls for equivalence, not
noninferiority. A one-sided noninferiority gate is appropriate only for a separately justified
metric with a genuinely directional notion of harmful degradation. `{inferred: maps equivalence
logic to interval reunion}`

## The certification boundary

The reported matchup outcome—game or match win/loss—must be unavailable to all discovery and
certification code. Candidate interval IDs, features, margins, kernels, support rules, and
multiplicity families freeze before any pooled matchup estimate is computed. Response-driven
selection invalidates ordinary inference, while the fixed-design result in Berk et al. shows the
value of screening without the response [recur-certify-posi]{1} [recur-certify-posi]{3}.
`{extends}` For this system, outcome-free nomination protects the downstream matchup estimand from
direct cherry-picking; it does **not** by itself make feature-equivalence inference valid.

If discovery nominates intervals by looking at the same deck-feature observations used for an
ordinary equivalence test, the feature test is still post-selection. Use one of these contracts:

1. **Preferred first implementation:** split by independent sampling clusters, not individual
   decks. Discovery gets one set of events; certification gets disjoint events from both candidate
   and reference intervals. The split rule is fixed before the campaign runs.
2. **When support permits:** repeat event-level splits and require stability of the binary decision,
   while reserving one untouched final partition for the actual certificate. Repeated exploratory
   results do not replace the final untouched test.
3. **Later alternative:** use a method with simultaneous post-selection coverage over the full
   candidate universe. Berk et al. establish the underlying simultaneous-inference principle, but
   their PoSI theorem is for linear regression and is not directly an interval-equivalence method
   [recur-certify-posi]{4}. `{extends}` A purpose-built derivation would be required before using it
   instead of sample splitting.

## Certification gates

Apply gates in this order. A failure stops the candidate; missing power or unresolved evidence
returns `inconclusive`, never `certified`.

### 1. Hard semantic guards

- Veto any interval that crosses a confirmed affectedness boundary for the subject archetype or the
  opponent representation being certified.
- Veto incompatible rules, legality, taxonomy version, deck-construction contract, or material data
  provenance unless an explicit mapping was frozen before discovery.
- Require the candidate's full interval endpoints and the certification `as_of` time to precede
  matchup outcome access.

Distributional similarity cannot establish semantic correspondence by itself; Gretton et al. make
the same caution in a database-matching application [recur-certify-mmd-two-sample]{5}. `{extends}`
The hard guards therefore precede statistics rather than becoming features a similarity score can
average away.

### 2. Prespecified representation and margins

Freeze a feature dictionary before testing. It should include configuration features used by
discovery plus held-out structural checks that discovery did not optimize, such as card-role
composition, companion or deck-size contract, engine/payoff density, mana structure, and sideboard
role vectors. Freeze a separate context vector for field composition, event/source mix, geography or
platform where available, and time-relative rules or publication policy.

Two defensible test shapes are available:

- **Interpretable component equivalence:** simultaneous confidence intervals for each declared
  feature difference must lie inside feature-specific `[-delta_j, +delta_j]` bounds. This makes the
  reason for rejection auditable and follows the two-sided interval logic used in regulatory
  equivalence [recur-certify-fda-equivalence]{1}.
- **Distribution-level equivalence:** a two-sample MMD-equivalence test asks whether the entire
  multivariate feature distribution lies inside an MMD radius. Liu and Gandy provide a direct test
  shape, but their 2026 work is a recent preprint and their normal approximation shows Type I
  inflation for small margins and high-dimensional examples; their bootstrap variant is safer but
  more conservative in those experiments [recur-certify-kernel-equivalence]{2}
  [recur-certify-kernel-equivalence]{4} [recur-certify-kernel-equivalence]{5}.

`{inferred: combines interpretability and omnibus protection}` A candidate should pass both a small
set of load-bearing component bounds and one calibrated omnibus discrepancy guard. Passing only an
equality-null MMD test is prohibited because that test is designed to detect difference, not certify
similarity [recur-certify-mmd-two-sample]{1}.

Margins must be chosen without candidate-specific matchup outcomes or observed candidate distances.
Calibrate them by perturbing reference-era deck/context distributions, having domain owners label
the boundary change that should break transport, and simulating the test's false-reunion and
abstention behavior over those perturbations. This is a composed operational proposal, not a
source-prescribed threshold. `{extends}`

### 3. Support and dependence guard

Do not equate raw deck count with information. Before testing, require prespecified floors for:

- distinct events in both candidate and reference partitions;
- distinct time buckets and, where known, pilots or publication sources;
- effective sample size after any context weighting;
- maximum event/source concentration; and
- simulated power to reject non-equivalence for a declared set of safely-inside alternatives.

The FDA guidance treats sample size as design-specific, permits simulation when no analytic
solution exists, and requires sensitivity analysis over assumed variance and effects
[recur-certify-fda-equivalence]{3}. MMD experiments likewise show that Type II error changes with
sample size and method [recur-certify-mmd-two-sample]{3}. `{inferred: applies design-based power to
clustered deck samples}` Estimate power by resampling whole events/time buckets, preserving the
dependence structure the report will face. A candidate below any floor is `inconclusive`; a minimum
`n` alone is not a reunion rule.

Every support floor, concentration cap, target power, and simulation scenario belongs in a versioned
calibration profile. This research supplies no universal constant.

### 4. Family-level error guard

Define the multiplicity family as every interval reunion that could enter the same generated report
under one calibration/profile version, including all component tests used to pass a candidate.
Shared current-reference observations make those tests dependent.

`{inferred: risk choice}` Use strong family-wise control for certification, implemented by a
simultaneous max statistic or cluster bootstrap over the full frozen family. One false certified
interval can contaminate many matchup rows, so an error criterion that permits some false
discoveries is misaligned with the gate. Berk et al. show how simultaneous coverage yields strong
post-selection family-wise control in their setting [recur-certify-posi]{4}.

Benjamini–Hochberg FDR is useful for an exploratory queue of candidates, not the production
certificate. It controls the expected false fraction among rejections under its theorem's
independence conditions and trades stricter family-wise protection for power
[recur-certify-bh-fdr]{1} [recur-certify-bh-fdr]{3}. Its original dependency assumptions are
load-bearing when candidates reuse intervals [recur-certify-bh-fdr]{4}. No fixed error level is
recommended here; calibrate it against tolerated false-reunion risk.

### 5. External-context and transport guard

Deck equivalence is necessary but not sufficient. Compare the candidate and reference context
distributions with the same positive-equivalence burden. Then audit overlap by estimating the
reference-to-candidate density ratio and recording effective sample size, maximum weight, and the
share of reference context outside candidate support. If overlap fails, veto or abstain; do not let
large weights manufacture evidence.

Importance weighting is only a sensitivity tool under an explicit assumption. Covariate-shift
theory allows the input distribution to change while requiring the conditional outcome distribution
given inputs to remain unchanged [recur-certify-covariate-shift]{1}. Under that condition,
importance-weighted validation can correct target-risk estimation [recur-certify-covariate-shift]{3}.
It cannot repair a change in the conditional matchup process, and even under covariate shift its
variance and estimated density ratios remain practical weaknesses
[recur-certify-covariate-shift]{4} [recur-certify-covariate-shift]{5}.

`{inferred: transport guard}` Therefore:

- use context equivalence and overlap as admission gates;
- use capped or stabilized importance weights only in labeled sensitivity estimates;
- never allow weighting to override a hard affectedness/rules failure; and
- require future outcome validation to test the conditional-invariance assumption after interval
  certificates have frozen.

## Certificate payload

Persist a certificate rather than only a boolean. At minimum it records:

```yaml
candidate_interval: [start, end]
reference_interval: [start, end]
certification_as_of: timestamp
status: certified | rejected | inconclusive
feature_schema_version: string
calibration_profile_version: string
discovery_partition: event_ids_or_hash_rule
certification_partition: event_ids_or_hash_rule
hard_guards: {affectedness, legality, taxonomy, provenance}
equivalence_tests: {component_bounds, omnibus_method, margins, intervals, adjusted_error}
support: {raw_n, events, time_buckets, effective_n, max_event_share, simulated_power}
context_overlap: {method, effective_n, max_weight, unsupported_share}
outcome_columns_accessed: []
```

The generator may consume only `certified` intervals. `Rejected` and `inconclusive` remain visible
in diagnostics so missing historical data is not silently converted into evidence.

## False-reunion red-team cases

Before deployment, construct outcome-blind negative controls that must fail certification:

- same headline archetype label but a changed win condition or engine/payoff balance;
- similar maindeck aggregate with a materially different sideboard-role distribution;
- unchanged subject deck across a confirmed subject-affecting rules or ban boundary;
- configuration match drawn from a different event/source mixture with poor context overlap;
- one dominant event duplicated into many published records; and
- many overlapping candidates nominated around the same historical pocket.

Also construct positive controls by splitting one known-stable interval at event boundaries; these
should usually certify when support is adequate. `{extends}` Calibration should optimize the whole
three-state confusion matrix—false reunion, missed reunion, and abstention—rather than raw pass rate.

## Disconfirming analysis

The fetched evidence does not support a simple “similar decklists imply transportable win rate”
claim. Gretton et al. explicitly caution that distribution matching need not establish semantic
correspondence [recur-certify-mmd-two-sample]{5}. Covariate-shift correction assumes the conditional
outcome relationship is unchanged, precisely the fact a changed metagame can violate
[recur-certify-covariate-shift]{1}. Thus even a statistically certified configuration reunion needs
future, outcome-based validation; it is an admissibility decision, not proof that historical and
current matchup win probabilities are identical.

I also sought evidence against using an omnibus kernel test as a turnkey gate. The recent
equivalence preprint reports Type I inflation for its normal approximation in small-margin and
high-dimensional regimes and presents its bootstrap approach as more conservative
[recur-certify-kernel-equivalence]{4} [recur-certify-kernel-equivalence]{5}. The component-plus-
bootstrap-omnibus recommendation therefore deliberately favors auditability and abstention over a
single high-dimensional p-value.

Finally, strict sample splitting spends scarce historical data and can cause many inconclusive
results. Simultaneous post-selection inference offers a possible future efficiency path, but the
fetched PoSI result is not a ready-made theorem for clustered MMD equivalence. Pretending otherwise
would replace an honest power cost with an unsupported validity claim.

## Contradictions

| Relationship | Position A | Position B |
|---|---|---|
| `contradicts` for certification use | Equality-null MMD tests reject when distributions differ and can have substantial Type II error at limited sample sizes [recur-certify-mmd-two-sample]{1} [recur-certify-mmd-two-sample]{3}. | Equivalence MMD reverses the null so rejection supports similarity inside a prespecified margin [recur-certify-kernel-equivalence]{1}. |
| `tension` error criterion | FDR gains power by controlling the expected false fraction rather than the chance of any false rejection [recur-certify-bh-fdr]{1}. | Simultaneous inference supplies strong family-wise protection after selection, at greater conservatism [recur-certify-posi]{1} [recur-certify-posi]{4}. |
| `qualifies` transport correction | Importance weighting can recover almost-unbiased target-risk estimation under covariate shift [recur-certify-covariate-shift]{3}. | The result requires an unchanged conditional output distribution, has variance, and relies on a density ratio that must be estimated in practice [recur-certify-covariate-shift]{1} [recur-certify-covariate-shift]{4} [recur-certify-covariate-shift]{5}. |
| `incommensurable` thresholds | FDA guidance contains numeric margins for regulated bioequivalence settings and makes sample-size calculation design-specific [recur-certify-fda-equivalence]{1} [recur-certify-fda-equivalence]{3}. | No fetched source establishes a numeric deck-era equivalence margin or event-count floor; those require project calibration. |

These positions are not averaged. The production contract uses equivalence rather than equality-
null nonrejection, family-wise rather than FDR control for admission, and abstention when the
covariate-shift assumptions or support cannot be defended.

## Acquisition candidates

No blocking or proactive enrichment candidate remains after the fetched source set for this facet.
The recent kernel-equivalence method itself should be treated as provisional until replicated in
the project's clustered, mixed-source setting; that need is validation work, not a missing-citation
acquisition.

## Revisit if

- certification must reuse the same events as discovery because independent partitions are too
  sparse;
- a peer-reviewed correction or replacement for the 2026 kernel-equivalence preprint appears;
- the consumer chooses FDR rather than family-wise control for production admission;
- context density ratios are extreme enough that effective support collapses;
- pilot identity or complete event entry data becomes available and changes the sampling cluster;
- a historical report mode requires as-known-then certification rather than retrospective
  certification; or
- forward validation shows certified reunions are systematically miscalibrated or regret-increasing.
