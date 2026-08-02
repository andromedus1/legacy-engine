---
description: "Temporal contracts for keeping superarchetype matchup estimates current without conflating outcome drift, composition drift, and taxonomy churn."
type: brief
kind: research
slug: decision-useful-superarchetype-representation-dynamic-metagame-representation
research_method: /deep-research
verification_status: attested
provenance: agent-synthesis
updated: 2026-08-01
summary: |
  A current superarchetype result requires three separately versioned temporal states: the
  member-pair outcome surface, within-family target weights, and composition-derived membership.
  The production estimator should be causal at every as-of boundary, with a fixed window and a
  causal exponential-decay model as mandatory baselines and probabilistic changepoint mixtures as
  a candidate only if future-only validation earns their complexity. Taxonomy continuity should
  use scheduled review, hysteresis, explicit version changes, and overlap bridges; it must not
  smooth away real composition change or use outcomes to preserve a family label. Published drift
  should be decomposed into performance and composition components instead of hidden behind one
  moving family win rate.
key_findings:
  - "Outcome probabilities, target member shares, and family membership are distinct time-varying states with different evidence, update rules, and version identities."
  - "Every published historical value must be reproducible using only information available at its as-of boundary; centered temporal smoothers are retrospective diagnostics, not live estimators."
  - "A causal exponentially decayed estimator is a mandatory simple dynamic baseline; probabilistic changepoint mixtures are candidates, not presumed improvements."
  - "Regime changes should alter evidence borrowing without silently resetting taxonomy, while taxonomy changes should version the represented population rather than rewrite history."
  - "Current-weight and fixed-reference standardizations should be reported together so composition drift can be separated from changes in member-pair performance."
  - "Continuity mechanisms require an escape hatch: persistence and historical smoothing can lag genuine structural change and make a stable-looking family stale."
confidence: speculative
status: draft
related:
  - {slug: .research/briefs/decision-useful-superarchetype-representation/estimand-target-population.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/nontransitive-outcome-models.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/sparse-selective-evidence.md, relationship: parallel-to}
  - {slug: .research/briefs/decision-useful-superarchetype-representation/validation-decision-utility.md, relationship: parallel-to}
---

# Dynamic metagame representation

## Scope and first-principles framing

The dynamic problem is not one clock. A family result at as-of boundary `t` depends on at least
three changing objects:

1. **Outcome state**: the member-pair probability surface `p_ab(t)`.
2. **Composition state**: the target weights `u_a^S(t)` and `v_b^T(t)` used to standardize that
   surface.
3. **Taxonomy state**: the eligible-member sets `A_S(t)`, family assignments, and their provenance.

The current family matchup is therefore

\[
\theta_{S,T}(t)=
\sum_{a\in A_S(t)}\sum_{b\in A_T(t)}
u_a^S(t)v_b^T(t)p_{ab}(t).
\]

One observed change in `theta` can come from changing matchup behavior, changing prevalence within
either family, or changing the family boundary itself. Treating all three as one rolling aggregate
makes the result impossible to interpret. The implementation must estimate and version them
separately, then compose them at a named boundary.

The governing temporal contract is **causal reproducibility**: a value labeled “as of `t`” may use
only events, classifications, and review decisions effective by `t`. This is stricter than producing
a smooth historical chart after the fact. A retrospective kernel estimator explicitly smooths
pairwise observations across time periods around the evaluation time; as written, it is useful for
offline structure discovery but not for a live boundary forecast `[superrep-dynamic-bt-kernel]{6}`.

## An as-of result is a versioned bundle

**Project decision — snapshot identity.**

A scalar probability is insufficient provenance. Each family result should bind:

- `as_of`: the last event-time boundary included;
- `outcome_filter_id`: window, decay, or run-length posterior used for `p_ab(t)`;
- `regime_state`: fixed regime identifier or distribution over current run length;
- `taxonomy_version`: the composition-derived family mapping effective at the boundary;
- `weight_snapshot_id`: eligible members, within-family weights, and the interval used to estimate
  them;
- `target_context_id`: event, rules, game, and pilot population from the estimand;
- `data_cutoff` and `classification_cutoff`: separately recorded so late classification cannot
  masquerade as evidence available earlier;
- typed freshness, churn, and boundary-uncertainty diagnostics.

These identifiers prevent two silent forms of look-ahead. First, a later taxonomy must not be
backfilled into an earlier claim unless the result is explicitly labeled a retrospective restatement.
Second, a changepoint discovered with later observations must not be used to improve the score that
purportedly existed before those observations arrived.

**Project decision — estimable weights.** A `WeightSnapshot` additionally records its classified-
deck sampling frame, provenance strata, raw member counts, half-open estimation window, smoothing
candidate, bootstrap/posterior draws, unclassified mass, and effective member count. Weight draws
are versioned separately from outcome draws and combined only during standardization. Thin or
frame-mismatched shares produce typed `weight_unidentified`, `weight_frame_mismatch`, or
`weight_sensitive` states rather than a fixed current-mixture vector.

**Project decision — two kinds of historical taxonomy.** `contemporaneous_registry` means an
actual immutable registry snapshot and classification cutoff recorded at that historical origin.
`retrospective_policy_replay` means a later-specified composition-only policy rerun using only data
available by the origin. Replay can estimate how that policy would have behaved, but it is not the
registry participants saw and must never be labeled historical truth. The two have distinct
`taxonomy_source`, `taxonomy_version`, and result-series labels; missing contemporaneous snapshots
remain an acquisition gap rather than being silently filled by replay.

## Candidate temporal estimators for the outcome surface

### 1. Frozen recent window

The fixed-window baseline fits the chosen member-pair model on the trailing `W` eligible observations
or a fixed event-time interval. It is causal, inspectable, and has a clear discard boundary. Its
failure modes are equally clear: a short window is noisy and disconnected, while a long window
mixes obsolete regimes and changes discontinuously when observations cross the boundary.

The window length must be selected inside training history and evaluated on later events. It should
not be chosen because it makes the current table denser or more favorable.

### 2. Causal exponential decay

Assign an observation of age `d` a weight proportional to `lambda^d`, with the unit of `d` fixed as
event time, calendar time, or tournament boundary. Cattelan, Varin, and Firth use geometrically
decreasing weights so current abilities depend on past results and evaluate the models by fitting
through one competition day and predicting the next `[superrep-dynamic-bt-ewma]{5}`. Their examples
show that this compact causal baseline can be competitive with a much more parameterized dynamic
model, but not consistently superior to it `[superrep-dynamic-bt-ewma]{5}`.

For Legacy, decay applies to the sufficient statistics or likelihood contributions feeding the
non-transitive member-pair model; it does not justify replacing that model with scalar ability.
The half-life is a hyperparameter to validate, not a prose notion of “recent.” Effective evidence
under decay must be reported separately from raw match count.

### 3. Probabilistic run-length mixture

Bayesian online changepoint detection maintains a posterior over the elapsed run length and forms
the current predictive distribution by integrating over that uncertainty. The filter uses data
through the current boundary and therefore offers a causal alternative to selecting one
retrospective break `[superrep-bocpd-boundary]{3}`.

This suggests a candidate in which each possible current run length indexes an outcome-model fit or
its sufficient statistics, and predictions are averaged under the run-length posterior. It avoids
pretending that a noisy ban, set release, or metagame adaptation has a perfectly known onset.

The construction also assumes generative parameters on opposite sides of a changepoint are
independent `[superrep-bocpd-boundary]{3}`. A full reset is too strong by default here: some member
effects and matchup structure may persist across a ban while prevalence changes rapidly. The
candidate should therefore compare at least:

- full reset of dynamic outcome parameters;
- reset of short-term residuals with longer-lived hierarchical parameters retained; and
- no reset, represented by the decay baseline.

The changepoint model earns production use only if future-only validation improves calibrated
member-pair predictions or downstream decisions. Boundary probabilities should remain visible; a
single chosen break is not a substitute for uncertainty.

### 4. Retrospective kernel smoothing

Kernel smoothing supplies a useful offline comparator for smoothly changing pairwise systems. Its
bandwidth controls temporal borrowing, and its guarantees depend on design regularity and smooth
change `[superrep-dynamic-bt-kernel]{6}`. The same source warns that smoothing optimized for
estimation can miss ranking changes `[superrep-dynamic-bt-kernel]{6}`.

Consequently it has two bounded roles:

- an **offline diagnostic** that asks whether the causal estimators are materially rougher than a
  future-informed smoother; and
- a **model competitor** only if reformulated as a one-sided kernel and evaluated causally.

It must not generate the historical values shown as decisions available at those historical dates.

## Regime boundaries are not taxonomy boundaries

A regime boundary changes how outcome evidence should be borrowed. A taxonomy boundary changes
which decks the family name denotes. They may coincide after a ban or major set release, but neither
logically implies the other.

Known rule changes can be declared exogenously at their effective dates. Statistical drift signals
can supplement them, but they must be computed from information available at the boundary and kept
separate by state:

- outcome drift from predictive residuals or member-pair behavior;
- composition drift from member shares and deck features; and
- taxonomy pressure from composition-derived cohesion and boundary cases.

Outcome drift can reduce borrowing, widen uncertainty, or trigger review. It must not directly move
a member between composition families: that would let the outcomes being predicted redefine the
hierarchy that shares their evidence.

## Membership lifecycle and identity continuity

### Scheduled review plus hysteresis

Membership should update on an explicit review cadence, with separate effective and announcement
boundaries. Incumbency-aware thresholds can reduce gratuitous churn: a borderline incumbent needs
stronger evidence to leave than a non-member needs merely to remain excluded, while a new entrant
needs stronger evidence than a stable incumbent to join.

This resembles percentile banding in index methodology, where entry and incumbent thresholds differ
to limit unnecessary turnover; scheduled reviews separately reassess constituent eligibility and
weights `[superrep-ftse-index-continuity]{13}`. The analogy supports an operational design, not a
claim that finance rules optimize matchup forecasts.

The escape conditions are load-bearing. Evolutionary clustering frames temporal clustering as a
trade-off between current snapshot quality and historical continuity, while explicitly requiring
clusters to change when present structure changes materially `[superrep-evolutionary-clustering]{12}`.
Hysteresis therefore needs:

- maximum grace periods for unsupported incumbents;
- immediate paths for bans, parser corrections, and clear composition breaks;
- a surfaced `taxonomy_stale` state when review is overdue or cohesion evidence fails; and
- no outcome-based exception that silently preserves a convenient family.

### Entry, exit, and re-entry

A new archetype can be composition-assigned before it has direct matchup evidence. It may receive
hierarchical predictions, but its positive target mass is exposed as indirect or unsupported by the
evidence sibling's rules. An exiting member remains in immutable historical snapshots but receives
zero weight in a current population after its effective exit. Re-entry creates a new eligibility
episode linked to the same archetype identity; old outcomes may be borrowed only through the chosen
temporal model, not because the label string matches.

Assigned members should contribute their observed outcomes once membership is frozen for a fit.
Freezing prevents outcome-driven reassignment; excluding their outcomes would make the current
family population depend on only its historical definers and could conceal present-day
heterogeneity.

### Version changes and bridges

When a review materially changes membership, increment `taxonomy_version`. Compute both old- and
new-definition standardizations at the transition when evidence permits, producing a bridge:

\[
\theta^{old}_{S,T}(t^*) \quad\text{and}\quad
\theta^{new}_{S,T}(t^*).
\]

The difference is a definition effect, not a matchup trend. Historical results retain the taxonomy
effective when they were published; a separately labeled retrospective series may restate them
under a later fixed taxonomy.

Financial indexes adjust a divisor so their level remains comparable through additions, deletions,
and corporate events `[superrep-ftse-index-continuity]{13}`. Family win probability already has a
natural zero-to-one scale, so inventing a divisor-like numeric adjustment would change its meaning.
The transferable lesson is to isolate constituent change and publish continuity metadata, not to
force an apparently unbroken probability series.

## Decomposing performance drift from composition drift

Choose a reference member-weight snapshot `(u^0,v^0)` that remains meaningful over the comparison
interval. For an unchanged taxonomy, publish three quantities:

\[
\theta_t = \theta(p_t,u_t,v_t), \qquad
\theta_t^{fixed} = \theta(p_t,u^0,v^0), \qquad
\theta_0 = \theta(p_0,u^0,v^0).
\]

- `theta_t - theta_0` is total movement in the current represented family matchup;
- `theta_t_fixed - theta_0` is movement from the outcome surface under fixed composition; and
- `theta_t - theta_t_fixed` is the current composition effect relative to the reference.

Because changing outcome and composition together creates path dependence, a symmetric two-order
decomposition is preferable when a single additive attribution is required: average the
performance-first and composition-first paths. **Algebraic derivation — drift attribution.** This
decomposition follows from the standardized estimand; it is not a result established by the
temporal sources.

The reference snapshot must be named and retired when eligibility changes too much to retain common
support. A bridge at the taxonomy boundary is more honest than carrying fixed weights for members
that no longer define the same population.

## Temporal diagnostics and typed refusal states

The dynamic layer should produce typed values rather than infer caveats from prose or provenance:

- `causal_as_of`: whether every input was available at the declared boundary;
- `regime_boundary_probability` or `regime_age`;
- `outcome_half_life` / `window_start` and decayed effective evidence;
- `weight_window`, share uncertainty, effective member count, and maximum member weight;
- membership additions, removals, churn rate, and taxonomy age;
- `taxonomy_stale`, `boundary_ambiguous`, and `composition_shifted` booleans;
- the current-weight, fixed-reference, and balanced-weight results with decision-direction
  disagreement; and
- explicit reasons such as `noncausal_fit`, `taxonomy_stale`, `insufficient_common_support`,
  `boundary_ambiguous`, and `composition_sensitive`.

A result should lose a family-level decision label when any versioned preregistered current-boundary
or weight scenario reverses the decision, taxonomy review is stale, current target mass falls outside the
eligible/evidenced bridge, or the displayed historical value required future information. Exact
thresholds belong to the validation sibling and must be selected before the final evaluation era.

## Persistence can manufacture stale stability

Temporal continuity is not monotonically beneficial. In dynamic stochastic block models, persistent
observations can make snapshot inference identify past communities more strongly than present ones;
observation persistence and latent membership persistence are distinct processes
`[superrep-temporal-persistence-lag]{25}`. The exact network model does not transfer to Legacy, but
the counterexample invalidates the assumption that more smoothing necessarily improves identity.

For this application, old matchup evidence, stable labels, and slowly moving decklists can reinforce
one another even after the actionable counter profile changes. The model should therefore monitor
one-step-ahead residuals by family and member, compare causal estimates with shorter-memory
alternatives, and expose lag rather than interpreting smoothness as quality.

## Minimum empirical comparison

**Empirical hypothesis — temporal candidate ladder.**

The dynamic modeling spike should hold the outcome-model family fixed while comparing:

1. fixed recent windows over a predeclared grid;
2. causal exponential decay over a predeclared half-life grid;
3. a causal run-length mixture with full and partial-reset variants;
4. a static expanding-history baseline; and
5. a retrospective smoother only as an offline oracle/diagnostic.

All tuning occurs within past data. Evaluation advances boundary by boundary and scores the next
eligible events, retaining periods around known disruptions rather than deleting them as anomalies.
The comparison must report member-pair predictive quality, standardized family calibration,
decision utility, abstention, and latency after a real change. A method that increases apparent
stability by reacting too slowly should not win merely because its average score is close.

**Empirical hypothesis — taxonomy-policy replay.** Taxonomy policies need a separate retrospective
policy replay: compare no hysteresis, bounded hysteresis, and scheduled
review using composition evidence only, then measure churn, stale duration, bridge coverage, and
downstream forecast behavior. Outcome performance may evaluate a frozen policy after the fact, but
must not select individual membership changes in the same replay. Every output is labeled
`retrospective_policy_replay`; only an actually archived registry is
`contemporaneous_registry`.

Taxonomy-policy selection is composition-only by default. If global policy hyperparameters are
compared using outcomes, the complete comparison is nested inside rolling training folds and frozen
before the final holdout. The resulting origin snapshot then generates the exact versioned
`TaxonomyScenarioRegistry` defined by the estimand brief; no outcome-based per-member override is
allowed.

## Implementation-relevant implications

**Project decision — temporal contract.**

- Split `OutcomeSnapshot`, `WeightSnapshot`, and `TaxonomySnapshot`; a family result references all
  three rather than inheriting one global “current regime.”
- Make temporal filters accept an event-time cutoff and fail closed if later observations or later
  classification decisions enter the fit.
- Retain immutable historical snapshot identities; never recompute an old published cell in place.
- Implement fixed-window and causal-decay adapters before changepoint machinery, so complexity has
  honest baselines.
- Apply temporal weighting to the antisymmetric member-pair likelihood or sufficient statistics,
  then standardize; do not decay already-aggregated family rates.
- Version taxonomy reviews independently of outcome regimes and store entry/exit reasons plus
  effective dates.
- At membership changes, emit old/new-definition bridge cells and mark the time series boundary;
  do not numerically splice probabilities to look continuous.
- Compute composition and performance decompositions from aligned outcome and separately generated
  weight draws so uncertainty and covariance survive the calculation.
- Generate `WeightSnapshot` draws separately from outcome draws, then pair or nest them under a
  preregistered Monte Carlo scheme so share uncertainty is not treated as certainty.
- Keep all freshness, boundary, and continuity gates typed for renderers and downstream consumers.

## Disconfirming analysis

The search tested whether a sophisticated dynamic model is necessary. Direct counterevidence
comes from the dynamic Bradley–Terry study: its compact causal EWMA achieved predictive
scores close to or essentially equal to a much more parameterized alternative in the reported
sports examples `[superrep-dynamic-bt-ewma]{5}`. Those examples are scalar and not Legacy, but they
undercut any presumption that explicit latent dynamics will outperform well-tuned decay.

The search also tested whether temporal smoothing reliably detects strategically important change.
The dynamic kernel paper states that a smooth estimator may fail to capture ranking changes and
that design effects must be assessed case by case `[superrep-dynamic-bt-kernel]{6}`. The dynamic
community source goes further: persistent observations can systematically lag present latent
membership `[superrep-temporal-persistence-lag]{25}`. These findings favor future-only evaluation of
reaction time and an explicit stale-state diagnostic, not maximum continuity.

Finally, the index-continuity analogy does not establish a statistical correction for family win
rates. Its mechanisms are operational conventions for investable indexes
`[superrep-ftse-index-continuity]{13}`. This brief therefore rejects a divisor-like adjustment and
retains only the separations among review, reconstitution, weighting, and published continuity.

## Contradictions

### C1 — smooth evolution versus discrete regime reset

Bong and collaborators assume smoothly varying abilities and kernel-borrow observations across
nearby periods `[superrep-dynamic-bt-kernel]{6}`. Adams and MacKay instead model changepoints whose
opposite-side parameters are independent `[superrep-bocpd-boundary]{3}`. These are conflicting
transition assumptions, not interchangeable algorithms. Legacy may exhibit both gradual adaptation
and abrupt ban-driven breaks. The brief does not resolve the tension theoretically; it requires
causal decay, full-reset, and partial-reset candidates to compete on future boundaries.

### C2 — identity continuity versus present-state fidelity

Evolutionary clustering explicitly balances current snapshot quality against historical quality
`[superrep-evolutionary-clustering]{12}`. The persistence-lag result demonstrates that history can
bias inference toward past communities `[superrep-temporal-persistence-lag]{25}`. This is a genuine
operational tension. Bounded hysteresis with stale-state escape conditions preserves continuity only
while current composition evidence remains adequate; there is no assumption that continuity itself
is truth.

### C3 — comparable series versus unchanged estimand

FTSE Russell uses divisor adjustments to keep index levels comparable through constituent events
`[superrep-ftse-index-continuity]{13}`. A family win probability denotes a directly interpretable
randomized experiment over members; adjusting its level for continuity would no longer report that
experiment. The finance convention is therefore only partially transferable. The resolution here
is metadata and dual-definition bridges, not numerical splicing.

## Suggested cross-references to sibling subdomains

- **Estimand and target population:** bind every standardized result to a weight snapshot and use
  current, fixed-reference, and balanced weights as distinct temporal estimands rather than display
  variants.
- **Non-transitive outcome models:** require every candidate model to accept causal observation
  weights or run-length states while preserving reciprocity; temporal modeling must not collapse
  the member-pair surface to scalar strength.
- **Sparse and selectively observed evidence:** compute support and influence under decayed
  effective evidence, and treat new-member target mass and post-boundary disconnection as typed
  evidence states.
- **Validation and decision utility:** use rolling future boundaries, score reaction latency around
  disruptions, and calibrate taxonomy-staleness, boundary-ambiguity, and composition-sensitivity
  refusal thresholds without tuning on the final era.

## Attested sources

- `superrep-bocpd-boundary` — causal posterior uncertainty over current run length and reset
  assumptions.
- `superrep-dynamic-bt-ewma` — causal exponential decay and sequential predictive evaluation.
- `superrep-dynamic-bt-kernel` — smooth dynamic paired-comparison estimation and its limitations.
- `superrep-evolutionary-clustering` — current-fit versus temporal-continuity trade-offs.
- `superrep-ftse-index-continuity` — scheduled review, banding, reconstitution, and series continuity
  conventions.
- `superrep-temporal-persistence-lag` — persistence-induced lag in dynamic group inference.
