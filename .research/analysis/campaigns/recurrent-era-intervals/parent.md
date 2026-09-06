---
description: Cross-specialist synthesis for recovering compatible historical matchup evidence through non-contiguous stable-era intervals.
type: research
summary: Discover recurrent deck states without outcomes, certify historical intervals with positive equivalence and abstention, intersect both archetypes' interval sets, and validate expanded evidence prospectively before promotion.
updated: 2026-08-13
provenance: agent-synthesis
decisions:
  - Represent an archetype era as a certified union of disjoint half-open intervals rather than one stable-since suffix.
  - Use outcome-firewalled segmentation plus complete-link segment similarity for first-pass discovery; retain sticky-state models as challengers.
  - Require independently evaluated positive equivalence, hard affectedness guards, family-wise error control, context overlap, and an inconclusive state before reuniting intervals.
  - Select matchup evidence from the pairwise intersection of subject and opponent interval sets and preserve current-only, expanded, and added-history views.
  - Separate data_until from knowledge_as_of in historical reports and label retrospective reconstruction distinctly from as-known-then reconstruction.
key_findings:
  - A ban is a candidate boundary and hard affectedness signal, not a universal reset for every archetype.
  - Minimum matchup n remains a display/evidence threshold; recurrent-era recovery changes which matches are admissible before that threshold is applied.
  - Raw added match count is insufficient because event and interval-component concentration can overstate independent support.
  - Historical snapshots cannot be honestly reproduced by truncating outcomes alone; classifications, certificates, code, configuration, and ingestion state also need time/version contracts.
---

# Recurrent stable-era intervals — campaign synthesis

## Decision result

Replace the scalar concept “this archetype has been stable since date X” with a versioned set of
certified disjoint intervals. A current Doomsday configuration could therefore admit a compatible
2025 pocket, exclude an intervening materially different build, and admit the current 2026 pocket.
For matchup reporting, history is usable only where the focal archetype's interval set overlaps the
opponent archetype's own certified interval set. `{inferred: cross-synthesis}`

This does not duplicate the existing minimum-matchup-`n` filter. The interval model decides which
rows are admissible evidence; the `n` filter decides whether an already selected cell is sufficiently
supported to display or count as measured. {inferred: cross-synthesis}

`{inferred: cross-synthesis}` The first production candidate should be outcome-firewalled multivariate segmentation followed by
segment fingerprint comparison and complete-link grouping. Energy-based change-point methods can
nominate joint distribution shifts rather than only mean shifts, but their stated inference assumes
independent observations, which tournament-derived time buckets may violate
[recurrent-ecp-james-matteson]{1}[recurrent-ecp-james-matteson]{2}. Treat the boundaries as
candidates until event-aware calibration exists. Equal-weight Jensen–Shannon divergence supplies an inspectable
symmetric comparison for normalized card-slot and field-share distributions
[recurrent-lin-jensen-shannon]{1}[recurrent-lin-jensen-shannon]{2}
[recurrent-lin-jensen-shannon]{4}; deck-level distribution checks
must accompany it so similar averages do not hide different mixtures.

## End-to-end contract

### 1. Discover without matchup outcomes

For each archetype and explicit `as_of` cutoff, segment its timeline using only deck construction,
legality, parser/data provenance, event support, and contemporaneous field composition. Persist
separate main-deck and sideboard fingerprints, deck-level configuration samples, source/event mix,
and exact hard boundaries. Match winners, game winners, standings, conversion, and derived matchup
rates must be rejected at the discovery schema boundary. `{extends}`

Nominate completed historical segments against the current segment on named distance channels:
main deck, sideboard, deck-mixture shape, field context, and exact semantic compatibility. Use a
complete-link rule so a chain of small changes cannot connect endpoints that are not mutually close.
Sticky HDP-HMMs can directly represent returning latent states
[recurrent-fox-sticky-hdphmm]{1}[recurrent-fox-sticky-hdphmm]{3}, while TICC jointly segments and
clusters recurring dependency states [recurrent-hallac-ticc]{1}[recurrent-hallac-ticc]{2}; keep
both as cutoff-refit challengers because their additional fit assumptions and instability reduce
auditability on sparse weekly traces. `{inferred: cross-synthesis}`

### 2. Certify with a positive equivalence burden

`{inferred: cross-synthesis}` A nominated reunion becomes `certified`, `rejected`, or `inconclusive`. Ordinary failure to detect a
difference is not enough: equality-null two-sample tests can miss real differences with limited
power [recur-certify-mmd-two-sample]{1}[recur-certify-mmd-two-sample]{3}. Certification instead
tests whether discrepancy is affirmatively below a prespecified practical-equivalence margin
[recur-certify-fda-equivalence]{1}[recur-certify-kernel-equivalence]{1}.

`{inferred: cross-synthesis}` The first implementation should split independent events between discovery and certification.
Certification then applies, in order:

1. hard confirmed-affectedness, legality, rules, taxonomy, and provenance vetoes;
2. prespecified component-wise and omnibus distribution-equivalence checks;
3. distinct-event, time-bucket, effective-support, concentration, and power guards;
4. family-wise control over every candidate reunion able to enter one report; and
5. external-context equivalence and overlap diagnostics.

`{inferred: cross-synthesis}` This ordering is the campaign's project contract; the cited sources
support its statistical pieces but do not prescribe this particular pipeline.

`{inferred: cross-synthesis}` All tolerances, support floors, power targets, concentration caps, and error budgets are versioned
calibration parameters. This research does not import universal numeric constants from another
domain. Importance weighting may be a labeled sensitivity analysis, but its validity requires the
conditional outcome relationship to remain unchanged and can suffer high variance or density-ratio
error [recur-certify-covariate-shift]{1}[recur-certify-covariate-shift]{4}
[recur-certify-covariate-shift]{5}; it cannot override a semantic or affectedness veto.

### 3. Consume pairwise overlap, visibly

Store each certificate as half-open intervals plus its `as_of`, feature/profile versions, event
partitions, guards, adjusted error, support, and context-overlap result. For report cutoff `u` and
knowledge cutoff `k`: `{extends}`

```text
eligible(A, B, u, k) = eras(A, u, k) ∩ eras(B, u, k) ∩ (-∞, u)
```

Disjoint interval intersection preserves excluded gaps; reducing a union to its earliest and latest
date would silently re-admit them [recurrent-consume-pg-multirange]{1}
[recurrent-consume-pg-multirange]{3}. Each selected match retains the subject certificate, opponent
certificate, and overlap-component IDs. `{extends}`

Every matchup exposes three views:

- current-only baseline;
- certified expanded estimate; and
- added-history slice, showing exactly what the expansion contributed.

`{inferred: cross-synthesis}` These views are a reporting contract, not a feature prescribed by the
range-operation source.

`{inferred: cross-synthesis}` The expanded estimate is initially diagnostic, not automatically the headline. Display raw matches,
distinct events/days, source and pilot coverage when available, maximum event share, maximum interval-
component share, and an effective event count. Clustered observations can make nominal `n` overstate
precision, especially with few clusters [recurrent-consume-cluster-inference]{1}
[recurrent-consume-cluster-inference]{3}. `{inferred: applies clustered-regression cautions to
matchup estimates}` The existing minimum-`n` control remains downstream and
applies to the selected view.

## Historical report selector

The proposed dropdown is valuable, but its semantics need two clocks:

- `data_until`: the latest event outcome allowed in the report;
- `knowledge_as_of`: the latest ingestion, classification, certificate, configuration, or other
  fact allowed to construct it.

Point-in-time temporal queries establish the need to constrain participating data at one historical
instant [recurrent-consume-sql-temporal]{1}[recurrent-consume-sql-temporal]{3], while provenance
also needs to record derivation, generation, use, revision, and time
[recurrent-consume-w3c-prov]{1}[recurrent-consume-w3c-prov]{2}. Therefore an outcome cutoff alone
cannot support the label “what we knew then.” `{inferred: cross-synthesis}`

Use a compact target dropdown:

```text
Current
Before <latest ban>
Before <previous ban>
...
```

and an adjacent mode badge or control:

- **Today's model** — selected historical outcome cutoff analyzed retrospectively with current
  classifications and certificates;
- **As known then** — every input and derived fact constrained to the selected knowledge cutoff;
- **Archived** — an immutable previously published artifact.

`{extends}` These labels translate the temporal/provenance distinction into this report's UI.

The first shippable mode should be **Today's model**, labeled in the header as “Before [ban], analyzed
with today's model.” It is useful immediately and does not pretend to be time-travel. Add **As known
then** only after classifier assignments, ingestion state, era certificates, method/config versions,
and selected-row digests are reproducible at the historical cutoff. Store compact immutable manifests
and addressable artifacts instead of embedding a full additional report payload for every option.
{inferred: implementation sequencing}

## Validation and promotion

Run date-based chained historical origins. Inside every origin, rebuild discovery and certification
using only information available by that cutoff, then score only the later horizon. Merely computing
today's certificates once and truncating outcomes is leakage. Forward time splits establish the
ordering principle, but irregular event dates require custom duration-based folds rather than an
equal-spacing splitter [recurrent-consume-sklearn-timeseries]{1}
[recurrent-consume-sklearn-timeseries]{3}. `{inferred: adapts forward splitting to irregular event
dates and cutoff-refit certificates}`

Compare recurrent expansion with current-only and the existing monotone contiguous-era baseline on
identical folds. Promotion requires added event coverage without material degradation in proper
score, calibration, interval coverage, or downstream decision regret. Proper scores assess forecast
quality rather than narrowness alone [recurrent-consume-calibration]{1}
[recurrent-consume-calibration]{3}. Fallback remains per matchup: unsafe overlap against one opponent
does not discard safe historical overlap against another. `{inferred: cross-synthesis}`

## Contradictions

- **Discovery — `tension`:** change-point methods provide a general multivariate segmentation
  procedure under independence [recurrent-ecp-james-matteson]{1}, while event-derived observations
  can be serially and cluster dependent. Use them for nomination until dependence-aware calibration.
  `{inferred: applies the source assumption to the project corpus}`
- **Model family — `qualifies`:** sticky latent-state and TICC models encode recurrence directly
  [recurrent-fox-sticky-hdphmm]{1}[recurrent-hallac-ticc]{1}, but introduce persistence, emission,
  state-count, optimization, and cutoff-refit uncertainty. They challenge rather than silently replace
  the inspectable two-stage candidate. `{inferred: cross-synthesis}`
- **Certification — `contradicts`:** equality-null tests support detecting difference, whereas
  equivalence reverses the null to require positive evidence of practical sameness
  [recur-certify-mmd-two-sample]{1}[recur-certify-kernel-equivalence]{1}. Production uses the latter.
  `{inferred: project policy}`
- **Multiplicity — `tension`:** FDR trades strong any-error protection for power
  [recur-certify-bh-fdr]{1}, while simultaneous inference targets family-wise protection
  [recur-certify-posi]{4]. Reunions use family-wise control; FDR may prioritize exploratory review.
  `{inferred: project risk choice}`
- **Consumption — `qualifies`:** exact multirange intersection solves eligibility
  [recurrent-consume-pg-multirange]{2}, not statistical transport. Heterogeneity and concentration
  checks remain separate [recurrent-consume-heterogeneity]{1].
- **Time travel — `qualifies`:** database `AS OF` constrains table state
  [recurrent-consume-sql-temporal]{2}, but reproducible analysis also requires versioned derived
  artifacts and code provenance [recurrent-consume-w3c-prov]{2}.

## Disconfirming analysis

`{inferred: cross-synthesis}` The evidence disconfirms four tempting shortcuts. Visual or average decklist similarity can hide
variant mixtures; a nonsignificant difference is not equivalence; raw expanded `n` does not prove
independent support; and truncating outcomes does not reconstruct historical knowledge. The resulting
proposal is intentionally abstention-friendly: many old pockets may remain inconclusive until event
support and calibrated margins are adequate.

`{inferred: cross-synthesis}` Strict event splitting can also spend too much sparse data. That is the main cost of the first valid
certification design. Simultaneous post-selection inference may recover efficiency later, but the
attested result is not a ready-made theorem for clustered deck-distribution equivalence
[recur-certify-posi]{4}. Do not trade an honest inconclusive result for unsupported precision.

## Revisit if

- independent event partitions make almost every candidate inconclusive;
- parser or card normalization cannot be reproduced consistently across historical cutoffs;
- chained validation shows expanded evidence improves coverage but worsens calibration or decisions;
- stable pilot identity materially changes effective-support estimates;
- a challenger recurrent-state model is consistently more cutoff-stable than segment similarity; or
- exact archived-report reproduction becomes a product requirement rather than retrospective analysis.
