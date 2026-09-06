---
title: Discovering recurrent stable-era candidates
type: research
summary: Outcome-free candidate generation for non-contiguous archetype eras using temporal segmentation followed by segment similarity, with recurrent-state models as challengers.
updated: 2026-08-13
provenance: agent-synthesis
source_handles:
  - recurrent-ecp-james-matteson
  - recurrent-lin-jensen-shannon
  - recurrent-fox-sticky-hdphmm
  - recurrent-hallac-ticc
---

# Discovering recurrent stable-era candidates

## Decision answer

Use **segmentation followed by segment-level similarity** as the first discovery model. It is the
most inspectable way to nominate non-contiguous history without letting matchup outcomes select the
history: detect contiguous configuration regimes, describe each regime with deck-construction and
field-context distributions, then nominate old regimes close to the current regime. This is a
candidate generator, not an equivalence decision. Certification must remain a separate gate.

{inferred: recommendation} A sticky recurrent-state model should be kept as a challenger, not the
first production method. It directly represents a state returning after an intervening state, but
adds latent-state, prior, convergence, and time-travel complexity that is hard to audit on a short,
irregular metagame history. TICC is another direct segment-and-cluster challenger, but its Gaussian
inverse-covariance state model and dense-data demonstrations make it a poor initial fit for sparse
weekly archetype traces.

## Discovery contract

Discovery answers only: “which old contiguous segments deserve certification against the current
segment?” It must not answer: “which old matches should be pooled?” The latter depends on support,
equivalence tolerances, matchup-intersection rules, and forward validation owned by later stages.

The discovery job should have an outcome firewall:

1. Its input schema contains tournament time, deck identity, archetype assignment, main/side card
   counts, legality or ban metadata, and contemporaneously observable field composition.
2. Match winner, game winner, standings, conversion, and any derived matchup-rate field are rejected
   at the schema boundary.
3. The feature manifest, thresholds, random seed, source cutoff, and output interval candidates are
   persisted before any outcome-bearing validation job can read them.
4. Historical execution takes an explicit `as_of` cutoff and rebuilds all features and candidates
   using records available through that cutoff.

{inferred: separation guard} This makes outcome-free discovery mechanically testable rather than a
promise in analysis prose. It also prevents an analyst from repeatedly adjusting a card-distance
threshold after seeing which adjustment produces an attractive matchup result.

## Feature representation

### Subject archetype configuration

Build separate main-deck and sideboard representations. For each deck, retain fixed-vocabulary card
count vectors plus explicit structural fields already available without match results: companion,
deck size, main/side boundary, and parser-confidence or unknown-card indicators. Do not collapse
main and side into one bag; two eras can share a maindeck while encoding different post-board plans.

For each time bucket, retain both:

- the deck-level vectors, so a method can distinguish one coherent configuration from a 50/50 mix
  of two configurations; and
- smoothed normalized card-slot distributions for an inexpensive segment summary.

Equal-weight Jensen–Shannon divergence is suitable for comparing normalized card-slot or archetype-share
distributions because it is symmetric, nonnegative, and does not have the same
zero-support failure as directed Kullback divergence.[recurrent-lin-jensen-shannon]{1}
[recurrent-lin-jensen-shannon]{2}[recurrent-lin-jensen-shannon]{4} The generalized weighted construction can summarize more than two
distributions, but pairwise distances should remain the inspectable primitive here.
[recurrent-lin-jensen-shannon]{3}

{inferred: representation limit} A normalized card-slot distribution discards multimodality. It
should therefore be a screening distance, not the sole evidence that two segments are the same.
Deck-level energy distance or an equivalent two-sample distribution measure should challenge the
summary distance before nomination.

### External metagame context

For each bucket, create an opponent-archetype share distribution excluding the subject archetype,
plus source mix and event-size summaries. Compare the normalized archetype shares with
Jensen–Shannon divergence. Keep format-rule and legality changes as explicit categorical facts rather
than attempting to infer them from decklists.

{inferred: scope boundary} External composition is a discovery feature, not permission to combine
matches. A subject configuration can recur in a different field; such a segment may still be worth
certifying, but it should be labeled `context-shifted` and face a stricter later gate.

### Time unit and support

Use a fixed calendar bucket for the trace, while retaining raw event/deck membership underneath it.
Empty or low-support buckets must be marked missing rather than filled by matchup outcomes. Append
deck count, event count, and source mix as diagnostics so a shift caused by coverage can be
distinguished from a shift in deck construction.

The energy-change-point source assumes observations are independent over time and have a finite
absolute moment.[recurrent-ecp-james-matteson]{1} Legacy events and adjacent calendar buckets can
violate independence through repeated pilots, copied lists, source schedules, and persistent trends.
Consequently, permutation significance from the off-the-shelf procedure is not calibrated evidence
unless the dependence problem is separately addressed.

## Candidate algorithm A — segment, then reunite

### A1. Segment adjacent history

For each subject archetype and each `as_of` cutoff:

1. Order outcome-free observations by event date and bucket them on the chosen calendar grid.
2. Run a multivariate change-point procedure on configuration features. E-Divisive is an
   implementable reference: it searches for multiple joint-distribution changes by hierarchical
   bisection and uses an energy divergence rather than limiting detection to a mean shift.
   [recurrent-ecp-james-matteson]{1}[recurrent-ecp-james-matteson]{2}
3. Enforce a predeclared minimum segment duration and minimum numbers of decks and independent
   events. Keep a change-point uncertainty band rather than treating one estimated date as exact.
4. Split at hard observation-contract boundaries such as a parser taxonomy change unless features
   have been backfilled under one version.

{inferred: implementation guard} Because event dependence weakens the off-the-shelf permutation
test, use the change-point score initially as a deterministic nomination device and select its
penalty or threshold only from deck-configuration stability tests. Do not describe its p-values as
valid until block-aware calibration has been demonstrated.

E-Agglo is useful when known candidate boundaries—ban dates, taxonomy migrations, or source outages—
provide an initial segmentation, because it starts from supplied segments and greedily merges
adjacent ones.[recurrent-ecp-james-matteson]{3} It should not, however, make every ban a permanent
barrier: an unaffected configuration can later be nominated across the ban after the affectedness
and context gates evaluate it. `{inferred: project mapping from supplied boundaries}`

### A2. Describe each segment

Persist a segment fingerprint containing:

- date interval and `as_of` cutoff;
- deck count, event count, pilots when identifiable, and source mix;
- main-deck and sideboard card-slot distributions;
- deck-level configuration sample or a reproducible sketch of it;
- opponent-archetype share distribution;
- legality/ban facts and archetype-parser version; and
- missingness and unknown-card rates.

No field in the fingerprint may be derived from wins, losses, games, standings, or conversion.

### A3. Nominate recurrent segments

Compare every completed historical segment with the current reference segment on independently
named distance channels:

- `d_main`: main-deck configuration distance;
- `d_side`: sideboard configuration distance;
- `d_mix`: distance between deck-level distributions, preserving multimodality;
- `d_field`: external archetype-share distance; and
- exact compatibility flags for legality, taxonomy, and structural deck facts.

{inferred: anti-chaining design} Form recurrent candidate groups with a complete-link rule: every
pair of segments in a group must satisfy the predeclared discovery thresholds. Do not use
single-link connected components, where a chain of intermediate segments can reunite endpoints that
are not similar to one another. The current segment must be a member of every candidate set emitted
for current reporting.

Emit rejected-nearby segments with reason codes, not just accepted candidates. Examples are
`main_shift`, `sideboard_shift`, `mixed_configuration`, `field_shift`, `insufficient_events`,
`taxonomy_incompatible`, and `future_of_as_of`. This makes later disagreement diagnosable.

## Challenger B — sticky recurrent-state model

An HDP-HMM can learn an unknown number of states and assign the same latent state to separated time
intervals.[recurrent-fox-sticky-hdphmm]{1}[recurrent-fox-sticky-hdphmm]{3} That is a direct formal
model of recurrence. The ordinary HDP-HMM, however, can rapidly alternate among redundant states;
the sticky extension adds explicit self-transition bias to favor persistence.
[recurrent-fox-sticky-hdphmm]{2}[recurrent-fox-sticky-hdphmm]{3}

An implementable challenger would use the same outcome-free feature matrix as algorithm A, fit a
finite sticky HMM with a predeclared state-count search before attempting an HDP-HMM, and return
posterior state probabilities rather than only a Viterbi label. A segment is nominated only if its
state posterior is concentrated on the current state's label after label alignment across refits.
`{extends}`

{inferred: failure mode} This challenger is sensitive to emission specification, state persistence,
label switching, initialization or posterior mixing, and the amount of history included. Multimodal
emissions can represent heterogeneous configurations, but the source notes extra posterior
uncertainty when flexible emissions coexist with rapid switching.[recurrent-fox-sticky-hdphmm]{4}
Every historical `as_of` report would require a cutoff-specific refit; a state assignment learned
with future observations is retrospective and leaks information into an as-known-then snapshot.

## Challenger C — joint segmentation and clustering with TICC

TICC simultaneously segments and clusters a multivariate time series into recurring states, with a
switching penalty that favors temporal persistence.[recurrent-hallac-ticc]{1}
[recurrent-hallac-ticc]{2} It can therefore challenge the two-stage segmentation decision by asking
whether a joint objective finds the same reunions.

The model assumes each state has a sparse Gaussian inverse-covariance structure over short windows,
and requires choices for window size, state count, sparsity, and switching penalty.
[recurrent-hallac-ticc]{3} Its full objective is non-convex and alternating optimization is not
globally guaranteed.[recurrent-hallac-ticc]{4} Its published real-data case has far denser sampling
than a weekly metagame trace.[recurrent-hallac-ticc]{5} `{inferred: compares the source dataset with
the project trace}`

{inferred: use condition} Do not promote TICC beyond a challenger unless dimensionality is reduced
without outcome information, stability across restarts is shown, and the recovered states remain
stable under cutoff-specific refits. Otherwise its additional structure can create apparent precision
without enough segment observations to estimate the state covariances.

## Algorithm comparison

| Method | Recurrence representation | Inspectability | Load-bearing assumptions | Initial role |
|---|---|---|---|---|
| Change points + segment similarity | Explicit union of separately detected intervals | High: boundaries, fingerprints, distances, and reasons persist | Segmentation stability; predeclared similarity channels; dependence-aware calibration | Production candidate generator `{inferred: project role}` |
| Sticky HMM / HDP-HMM | Same latent state can return after intervening states | Medium: state emissions and transition matrix are inspectable, but fit uncertainty matters | Markov state process; appropriate emissions; persistence prior; cutoff-specific fitting | Challenger `{inferred: project role}` |
| TICC | Joint recurrent cluster labels with switching penalty | Medium: state dependency graphs are interpretable | Gaussian sparse inverse covariance; time-invariant window structure; local optimization; enough observations | Challenger after dimension reduction `{inferred: project role}` |
| Direct moving-window matching | Every old window independently compared with the current window | High per comparison, low globally | Window-width choice and large candidate-search space | Diagnostic only `{inferred: project role}` |

{inferred: comparison conclusion} Direct historical-window matching is useful for finding missed
segments, but it should not define eras: overlapping windows multiply nearly duplicate candidates,
make endpoints unstable, and move multiplicity into an opaque search over widths and dates.

## Failure modes and required diagnostics

- **False reunion through summary averages.** Two metagames can have the same mean card shares but
  different mixtures of deck variants. Require a deck-level distribution check.
- **False reunion through chaining.** Complete-link grouping and direct comparison with the current
  segment prevent a sequence of small changes from joining distant endpoints.
- **Source-composition artifact.** Report online/paper and provider mix per segment; do not let a
  provider entering or leaving the corpus masquerade as deck evolution.
- **Sparse-segment volatility.** Require duration, decks, and distinct-event support independently;
  a large deck count from one event is not broad temporal support.
- **Parser drift.** Backfill one taxonomy/version or force a boundary. Never compare fingerprints
  produced under incompatible archetype or card normalization rules.
- **Ban overreach.** Record legality and confirmed affectedness as explicit guards. A ban is not
  itself proof that every archetype changed, and visual deck similarity is not proof that an affected
  archetype remained transportable.
- **Historical leakage.** Recompute segmentation, thresholds, and clusters with `date <= as_of` for
  as-known-then reports. A full-history model may be exposed only as a retrospective view.
- **Outcome leakage.** Persist a machine-readable feature allowlist and assert that candidate outputs
  are byte-identical when outcome columns are permuted or removed.

## Disconfirming analysis

The search actively tested the recommendation against methods that encode recurrence directly.
Sticky HDP-HMMs learn unknown state cardinality and recurring persistent states, so they can avoid a
separate clustering stage.[recurrent-fox-sticky-hdphmm]{1}[recurrent-fox-sticky-hdphmm]{3} TICC
also solves segmentation and recurrence jointly.[recurrent-hallac-ticc]{1} These sources disconfirm
any claim that segmentation-then-similarity is uniquely capable.

They do not displace it as the initial method because both add assumptions and fit instability that
must be audited at each historical cutoff. The HMM source demonstrates redundant rapid switching in
the non-sticky model.[recurrent-fox-sticky-hdphmm]{2} TICC declares a highly non-convex full
objective and only local optimization.[recurrent-hallac-ticc]{4} The simple method remains the
recommended first candidate generator because its intermediate artifacts can be inspected and
replayed; that is a project-facing inference, not a superiority result from the papers.

The change-point source also cuts against overconfidence in algorithm A: its stated guarantees assume
independent observations.[recurrent-ecp-james-matteson]{1}[recurrent-ecp-james-matteson]{2}
Legacy sampling is plausibly dependent. The brief therefore withholds inferential status from
off-the-shelf permutation p-values and treats segmentation as nomination until dependence-aware
calibration is demonstrated.

## Contradictions

| Relationship | Position A | Position B | Consequence |
|---|---|---|---|
| tension | E-Divisive provides a general multivariate change-point procedure with consistency under independent observations.[recurrent-ecp-james-matteson]{1}[recurrent-ecp-james-matteson]{2} | Event-derived metagame observations are not assured independent because lists, pilots, sources, and adjacent buckets can be related. | Use the method for candidate boundaries; do not present its default permutation significance as calibrated for this corpus. |
| qualifies | Sticky HDP-HMMs represent recurring persistent latent states with unknown cardinality.[recurrent-fox-sticky-hdphmm]{1}[recurrent-fox-sticky-hdphmm]{3} | The same source shows that insufficient persistence structure yields redundant rapid switching.[recurrent-fox-sticky-hdphmm]{2} | Any HMM challenger needs explicit persistence, posterior diagnostics, and cutoff refits. |
| tension | TICC jointly models temporal consistency and recurring dependency states.[recurrent-hallac-ticc]{1}[recurrent-hallac-ticc]{2} | Its objective is non-convex, and its demonstrated data density is unlike the intended weekly trace.[recurrent-hallac-ticc]{4}[recurrent-hallac-ticc]{5} | Treat agreement with TICC as sensitivity evidence, not an automatic replacement for the simpler method. |

## Revisit if

- Decklist coverage becomes dense enough to estimate state-specific covariance structures reliably.
- Pilot identity or event-family metadata makes dependence-aware resampling implementable.
- Parser versions cannot be backfilled consistently across the historical corpus.
- The certification stage finds that field-context distance contributes no forward transport signal,
  or that another outcome-free feature repeatedly predicts false reunion.
- Sticky-HMM and segment-similarity candidates disagree systematically in cutoff-based validation.
- A rules or card-data source permits exact historical legality reconstruction for every `as_of`
  date.

## Acquisition candidates

No additional source is blocking this discovery decision, and this pass produced no source-bound
enriching acquisition candidate.
