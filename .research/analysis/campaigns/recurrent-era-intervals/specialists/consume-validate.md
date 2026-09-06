---
title: Consume and validate recurrent stable-era intervals
description: Pairwise interval consumption, pooling diagnostics, forward validation, and historical-report time semantics.
type: research
summary: Treat each archetype era as an interval set, intersect both sides before selecting matches, preserve a current-only baseline, validate expansion prospectively, and make historical report knowledge time explicit.
updated: 2026-08-13
provenance: agent-synthesis
campaign: recurrent-era-intervals
facet: consume-validate
---

# Consume and validate recurrent stable-era intervals

## Decision

Represent every certified archetype era as a normalized set of disjoint half-open intervals. For a
matchup `A` versus `B`, admit a match only when its event time lies in the intersection of the
certified interval sets for **both** `A` and `B`, after applying the report's outcome-time cutoff.
Multirange intersection is a closed operation that preserves disjoint output; collapsing the result
to its earliest and latest bounds would silently re-admit the excluded gap
[recurrent-consume-pg-multirange]{1} [recurrent-consume-pg-multirange]{2}
[recurrent-consume-pg-multirange]{3}.

Expanded evidence should not replace the current-era estimate invisibly. Report the current-only
posterior beside an expanded-era posterior, their change, and the provenance and concentration of
the added observations. `{inferred: recommendation}` A certification decision supports
transportability, not literal identity: evidence synthesis literature treats between-source
heterogeneity as a separate quantity worth measuring rather than assuming away
[recurrent-consume-heterogeneity]{1} [recurrent-consume-heterogeneity]{4}.

## Consumption contract

### Interval representation

For archetype `a`, target cutoff `u`, and knowledge cutoff `k`, define:

```text
E(a, u, k) = normalize({ [start_i, end_i) : certificate_i is admissible at (u, k) })
P(A, B, u, k) = E(A, u, k) ∩ E(B, u, k) ∩ (-∞, u)
```

`normalize` sorts intervals, merges overlapping or adjacent components when their certificate
semantics permit it, and retains true gaps. PostgreSQL's multirange behavior provides an explicit
implementation precedent for disjoint union, intersection, difference, and empty values
[recurrent-consume-pg-multirange]{1} [recurrent-consume-pg-multirange]{2}
[recurrent-consume-pg-multirange]{4}.

The match-selection predicate is then:

```text
match.event_at ∈ P(subject_archetype, opponent_archetype, data_until, knowledge_as_of)
```

with the ordinary orientation, data-quality, and legality predicates applied afterward. Do not
form a subject-only expanded sample and then label the opponent by its current name; the opponent's
own certified interval set is equally load-bearing. `{inferred: consequence of set intersection}`

Each selected row should retain `subject_certificate_id`, `opponent_certificate_id`, and the
specific overlap-component ID. This makes it possible to explain which historical pocket admitted
a match and to retract one certificate without recomputing unrelated eras. `{extends}`

### Three evidence views

1. **Current-only baseline.** The existing post-boundary/current contiguous interval for both
   archetypes. This remains the primary fallback.
2. **Certified expansion.** All matches in the pairwise interval intersection. This is the proposed
   headline candidate only after prospective validation.
3. **Added-history slice.** Expanded minus current-only. This is diagnostic: show its outcome,
   event sources, dates, and contribution, but never use it to discover or certify its own interval.

This three-view split makes a false reunion visible: a misleading historical pocket can no longer
hide inside a single larger `n`. `{inferred: design consequence}`

## Pooling and weighting

### Estimand first

The system must name whether it estimates:

- the win probability for the **current** environment, borrowing historical information;
- an average win probability over all certified environments; or
- the probability for a future event drawn from a declared target event mix.

These are not interchangeable. A raw pooled proportion targets the observation-weighted mixture
of admitted events. It targets the current environment only if admitted observations are
exchangeable with current play or are reweighted to a declared current target. `{inferred:
statistical consequence}`

### Recommended staged implementation

**Initial implementation.** Pool eligible match outcomes with the same existing weak prior used by
the current report, but expose the era component and event composition. Keep the current-only
posterior next to it and do not award expanded evidence the same confidence solely because raw
`n` increased. `{extends}`

**Model-capable implementation.** Fit an era-stratified binomial model with a matchup-level mean
and between-component variation, using current era as the prediction target rather than treating
all components as exact replicates. Report a heterogeneity summary and a predictive interval or
posterior predictive check across components. Higgins and Thompson distinguish the uncertainty of
the pooled mean from source-to-source variation and derive measures of heterogeneity's impact
[recurrent-consume-heterogeneity]{2} [recurrent-consume-heterogeneity]{3}.

Do not estimate historical borrowing weights from the same matchup outcomes and then present the
result as if interval selection were outcome-free. Outcome-adaptive commensurability is a different
methodological contract. If later adopted, it requires its own prospective calibration and a
visible no-borrowing component. `{inferred: guard derived from engagement constraint}`

### Independence and concentration diagnostics

Tournament matches are clustered: shared event, metagame, pilots, and sometimes repeated players
can make nominal matches less independent than their count suggests. Cluster-inference literature
warns that default errors can overstate precision when errors correlate within groups, and that the
choice of cluster level is substantive [recurrent-consume-cluster-inference]{1}
[recurrent-consume-cluster-inference]{2}. Few clusters can also produce variance estimates and
intervals that are too optimistic [recurrent-consume-cluster-inference]{3}
[recurrent-consume-cluster-inference]{4}. `{inferred: applies clustered-regression cautions to
matchup estimates}`

For every current-only and expanded estimate, report:

- raw matches and wins;
- distinct events and distinct event-days;
- distinct pilots when stable pilot identity exists, otherwise an explicit unavailable flag;
- maximum single-event match share;
- matches by overlap component and maximum component share;
- an **effective event count**, proposed as
  `N_event_eff = (Σ_e n_e)^2 / Σ_e n_e^2`, which equals the event count under equal contribution
  and falls toward one as one event dominates; `{extends}`
- uncertainty clustered or resampled at the coarsest defensible available unit, with sensitivity
  to event and pilot clustering where both identifiers are usable. `{extends}`

No universal “safe” event-count threshold follows from the cluster source; it explicitly rejects a
single count that settles the few-cluster problem [recurrent-consume-cluster-inference]{4}. Set
warning and fallback thresholds from the chained backtest, then freeze them before live use.
`{inferred: recommendation}`

## Validation design

### Leakage-free chained evaluation

At a sequence of historical origins `t_1 ... t_j`:

1. Freeze the source corpus, archetype assignments, ban registry, feature transforms, and era
   certificates to information available by `t_j`.
2. Discover and certify interval sets without matchup outcomes.
3. Produce matchup posteriors and deck/call rankings for a fixed forward horizon after `t_j`.
4. Score only outcomes arriving in that future horizon, then advance the origin.
5. Compare recurrent expansion against current-only and the monotone contiguous-era baseline on
   identical folds.

Forward time splits prevent training on the future and testing on the past; expanding windows and
an optional gap are established API semantics [recurrent-consume-sklearn-timeseries]{1}
[recurrent-consume-sklearn-timeseries]{2} [recurrent-consume-sklearn-timeseries]{4}. Because Legacy
events are not equally spaced, use date-duration folds rather than applying the documented
equal-spacing assumption mechanically [recurrent-consume-sklearn-timeseries]{3}. `{inferred:
adaptation}`

The evaluation must rerun discovery and certification inside every fold. Computing today's
certificates once and merely truncating match outcomes at old dates is retrospective leakage.
`{inferred: consequence of forward validation}`

### Metrics

Evaluate each method on:

- **Brier score** for match-win probabilities;
- calibration-in-the-large and calibration slope, with uncertainty;
- interval coverage and width for declared posterior/credible intervals;
- ranking stability and realized downstream utility;
- **decision regret**: realized forward utility of the method's selected call minus the ex-post
  utility envelope over the same eligible calls, reported as a distribution across origins rather
  than one aggregate; `{extends}`
- evidence gain: additional match and event coverage, always paired with concentration measures.

Calibration is consistency between probability forecasts and observations, while sharpness is the
concentration of the forecast; proper scores evaluate both rather than rewarding narrow forecasts
alone [recurrent-consume-calibration]{1} [recurrent-consume-calibration]{2}. The Brier score is a
proper binary-event score with a calibration/refinement decomposition
[recurrent-consume-calibration]{3} [recurrent-consume-calibration]{4}.

### Promotion and fallback

Predeclare tolerances from an initial development period, then evaluate them on held-out origins.
Promote expanded evidence only when it improves coverage without a material degradation in proper
score, calibration, interval coverage, or decision regret. `{extends}`

At report time, fall back to current-only for a matchup when any of these empirically calibrated
conditions holds:

- pairwise interval intersection adds no certified history;
- expanded evidence is dominated by too few events or one overlap component;
- the fitted heterogeneity or posterior predictive conflict exceeds its validation-derived guard;
- required certificate or snapshot provenance is missing;
- a confirmed ban/legality boundary invalidates either archetype's certificate;
- the forward-monitoring score crosses a predeclared degradation rule after enough delayed
  outcomes accrue.

The fallback should be per matchup, not all-or-nothing for the whole report. One opponent's unsafe
historical overlap need not discard safe overlap against another. `{inferred: consequence of
pairwise intersection}`

## Historical report selector

### Time has two axes

The selector must not use one ambiguous “era” date for both the report target and the information
available to construct it. Define:

- `data_until`: latest event time whose matchup outcome may enter the report;
- `knowledge_as_of`: latest transaction/ingestion time for any fact, classification, ban record,
  certificate, or derived feature used to build it.

System-versioned temporal queries demonstrate point-in-time reconstruction with `AS OF` and
distinguish overlap from containment queries [recurrent-consume-sql-temporal]{1}
[recurrent-consume-sql-temporal]{2} [recurrent-consume-sql-temporal]{4}. Applying one point-in-time
constraint across a joined view is necessary because participating tables change on different
cadences [recurrent-consume-sql-temporal]{3}. It is not sufficient if classifier code,
configuration, or derived artifacts are unversioned. `{inferred: qualification}`

### Explicit modes

Offer the historical target dropdown separately from a mode label:

| Mode | `data_until` | `knowledge_as_of` | Honest label |
|---|---:|---:|---|
| Current | now | now | Current |
| Retrospective historical | selected boundary | build time | “Before [ban], analyzed with today's model” |
| Reconstructed as-of | selected boundary | selected boundary | “Before [ban], using only information available then” |
| Archived publication | embedded in artifact | embedded in artifact | “Snapshot published [timestamp]” |

“Reconstructed as-of” is leakage-free with respect to information time but is not the same as an
archived publication if it uses a model version created later. If later code is used, label it
“current method on then-available information,” record that method version, and do not call it
“what the report said then.” `{inferred: temporal semantics}`

The default historical dropdown can therefore contain:

```text
Current
Before <latest ban effective date>
Before <previous ban effective date>
...
```

and show a compact adjacent badge, `Today's model` or `As known then`. Do not duplicate every
option into two long labels. The report header and export metadata must spell out both timestamps.
`{extends}`

### Required reproducibility manifest

Every generated report or embedded snapshot needs immutable identifiers for:

- mode, `data_until`, `knowledge_as_of`, and `generated_at` in UTC;
- input data snapshot/hash and latest included event timestamp;
- ingestion snapshot/hash and latest included ingestion timestamp;
- ban/legality registry version and effective-time policy;
- archetype classifier version and assignment snapshot;
- feature schema and transformation version;
- era discovery/certification code, configuration, random seed, and certificate IDs;
- matchup estimator/prior version;
- report generator and template version;
- selected match-row digest and overlap-component counts.

The PROV vocabulary records generation, use, derivation, revision, and time, and distinguishes a
dated specialization from its general entity
[recurrent-consume-w3c-prov]{1} [recurrent-consume-w3c-prov]{2}
[recurrent-consume-w3c-prov]{3} [recurrent-consume-w3c-prov]{4}. The project need not serialize
full RDF to follow the underlying contract: an immutable JSON manifest with equivalent identifiers
is enough for this report surface. `{inferred: implementation recommendation}`

### Storage strategy

Prefer a small snapshot manifest plus separately addressable data/model artifacts over embedding a
full duplicate analytical payload for every dropdown option. An archived publication may point to
immutable artifacts; a retrospective view may be regenerated from its manifest. `{extends}` This
keeps historical navigation from multiplying the existing report payload while preserving exact
reproducibility.

## Disconfirming analysis

The search actively tested the recommendation against four alternatives:

1. **One bounding interval.** PostgreSQL's range documentation explicitly shows that a single range
   cannot represent a disjoint result without filling its gap; multirange is the appropriate
   representation [recurrent-consume-pg-multirange]{3}.
2. **Trust raw expanded `n`.** Cluster dependence can make default precision optimistic, especially
   with few clusters [recurrent-consume-cluster-inference]{1}
   [recurrent-consume-cluster-inference]{3}. This disconfirms raw match count as a sufficient
   evidence diagnostic.
3. **Treat certified components as identical.** Heterogeneity methods exist precisely because
   pooled sources can vary beyond sampling error [recurrent-consume-heterogeneity]{1}
   [recurrent-consume-heterogeneity]{2}. Certification cannot eliminate the need to check this.
4. **Regenerate an old report by outcome cutoff only.** Forward splitting forbids future training
   data, while temporal systems constrain the state of all participating inputs at a past instant
   [recurrent-consume-sklearn-timeseries]{1} [recurrent-consume-sql-temporal]{3}. Outcome truncation
   alone therefore fails the leakage-free claim.

No source disconfirmed the feasibility of pairwise interval-set intersection. The principal risk is
not the set operation but false confidence after pooling sparse or concentrated overlap.
`{inferred: synthesis}`

## Contradictions

| Relationship | Position A | Position B | Implication |
|---|---|---|---|
| qualifies | PostgreSQL multirange intersection gives exact closed set semantics for disjoint intervals [recurrent-consume-pg-multirange]{2}. | Statistical transportability is not implied by exact set membership; heterogeneity remains measurable across admitted components [recurrent-consume-heterogeneity]{1}. | Use interval intersection for eligibility, then validate pooling separately. |
| tension | Expanding-window time splits accumulate all prior training data [recurrent-consume-sklearn-timeseries]{2}. | The engagement deliberately excludes uncertified historical gaps, and scikit-learn also assumes equal spacing for comparable folds [recurrent-consume-sklearn-timeseries]{3}. | Implement custom date-based chained origins whose training procedure rebuilds certified interval sets; do not use the splitter unmodified. |
| qualifies | SQL `AS OF` can reconstruct the joined temporal table state at a past instant [recurrent-consume-sql-temporal]{2} [recurrent-consume-sql-temporal]{3}. | W3C provenance separately represents derivation, generation, revision, and use [recurrent-consume-w3c-prov]{2} [recurrent-consume-w3c-prov]{4}. | Database system time is necessary but insufficient for a reproducible analytical report; version derived artifacts and code too. |
| incommensurable | Proper scores and calibration evaluate probability forecasts [recurrent-consume-calibration]{1} [recurrent-consume-calibration]{3}. | Decision regret evaluates the downstream ranking choice under a declared utility function. `{extends}` | Report both; neither metric can be substituted for the other. |

## Acquisition candidates

No blocking acquisition remains for this facet.

- **Enriching:** W3C PROV-DM Recommendation. Source-bound via the PROV-O Recommendation's PROV
  family list [recurrent-consume-w3c-prov]{1}. Class: standard. Web availability: publicly
  available from W3C. It would complete a formal mapping from the proposed JSON snapshot manifest
  to the entity/activity/agent data model if interoperable provenance becomes a requirement.

## Revisit if

- certification begins using matchup outcomes or adaptive borrowing weights;
- stable pilot identity becomes reliable enough to support pilot-level dependence models;
- the report estimates a declared current event mix rather than the observation-weighted corpus;
- interval certificates can be revised retroactively without immutable versions;
- the historical selector must reproduce exactly what a previously published artifact displayed;
- chained validation shows narrower posteriors but worse calibration or decision regret;
- one report must serve both analyst-facing retrospective reconstruction and archival audit.
