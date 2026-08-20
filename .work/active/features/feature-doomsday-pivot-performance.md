---
id: feature-doomsday-pivot-performance
kind: feature
stage: done
tags: [research, advisory, analytics]
parent: null
depends_on:
  - research-handoff-doomsday-splash-variants-5
release_binding: null
gate_origin: null
research_origin: doomsday-pivot-performance
research_refs:
  - doomsday-splash-variants
  - doomsday-pivot-performance
research_dials:
  scope_authority: mixed
  verification_rigor: standard
  intent: decision-support
  output_kind: adoption-recommendations
created: 2026-08-20
updated: 2026-08-20
---

# Assess Doomsday pivot intensity and performance

## Brief

Determine whether Doomsday performs better when it remains focused on turbo combo, adopts a
sideboard-only transformational juke, incorporates a value-combo layer, or commits maindeck slots
and lands to a deep tempo hybrid. The current published surface suggests Personal Tutor turbo and
Esper/value configurations outperform Wasteland/Murktide tempo, but League publication selection,
event mix, overlapping categories, repeated pilots, and tiny post-ban samples make that comparison
non-causal.

Use the existing 14-list candidate registry and the refreshed tournament corpus to distinguish
published viability, recurrence, event-normalized results, and matchup-specific evidence. Define a
reproducible pivot-intensity classification for exact 75s, test whether the apparent tempo penalty
survives reasonable controls and sensitivity checks, and refine the paired local playtest program
around the matchups capable of justifying a pivot cost. Do not manufacture a win-rate or package
effect where failed-League or match-level denominators are unavailable.

## Strategic decisions

- **Decision relevance:** choose which of pure turbo, sideboard-only transformation, value-combo,
  or deep tempo hybridization should receive build and playtest priority, and identify the hostile
  matchups that could justify paying a pivot cost.
- **Scope authority:** mixed — preserve the registered candidate corpus while allowing evidence-led
  pivot categories and sensitivity groupings to emerge.
- **Verification rigor:** standard — run citation lint, an adversarial read, and lead spot checks.
- **Output posture:** recommendations must keep event-publication evidence, controlled local
  results, and mechanistic measurements separate.

## Research registration

- consumer: the operator's Doomsday build and paired-playtest program
- temporal_contract: snapshot as of the refreshed 2026-08-20 research cutoff
- primitives_extends: the existing Doomsday candidate manifest, tournament corpus, and playtest
  protocol
- primitives_opts_out: causal package win rates and unpublished League denominators
- decision_relevance: testing priority and the location/intensity of a fair or tempo pivot change
  if the apparent performance penalty survives bias and overlap checks
- analytical_artifact_type: multi-facet campaign

## Simplification opportunity

Reuse the existing manifest, source attestations, and paired-log contract. Do not create another
deck registry or collapse the distinction between published results and local controlled outcomes.
If a simpler pivot-intensity axis explains the current color/chassis labels, prefer it as the
comparison vocabulary without deleting the source-facing labels.

## Acceptance

- Quantifies available post-ban and historical evidence with explicit coverage and selection-bias
  limits.
- Separates sideboard-only transformation, value overlap, and maindeck tempo commitment.
- Tests the apparent tempo penalty against event type, pilot/list dependence, category overlap, and
  reasonable alternative classifications.
- Identifies which matchup-specific gains would repay aggregate consistency costs.
- Produces a concrete prioritized testing matrix without claiming unsupported causal superiority.
- Passes the standard agentic-research verification stack and records any unresolved evidence gaps.

## Decomposition rationale

Autopilot Checkpoint A considered three shapes:

1. **Construction-first:** quantify outcome bias, define pivot intensity, then model matchup payoff.
2. **Color-first:** compare Dimir, Esper, BUG, Grixis, and green-white directly.
3. **Evidence-layer-first:** separate published, local-controlled, and mechanistic evidence before
   considering deck construction.

The construction-first shape is selected. Color-first would reproduce the known chassis/splash
confounding, while evidence-layer-first would not independently test whether maindeck commitment
or sideboard transformation explains the apparent penalty. Three parallel facets will cover:

- **Outcome surface and bias:** published records, event/League selection, pilot and exact-list
  dependence, standings/round coverage, and sensitivity analyses.
- **Pivot-intensity taxonomy:** reproducible classification of maindeck tempo commitment,
  value-combo overlap, and sideboard-only transformation across the registered and wider corpus.
- **Matchup economics and test design:** which hostile-matchup improvements could repay the broad
  consistency cost, what existing match data can support, and the next paired-test matrix.

Self-flag: the 12-list post-ban window is too small for an adjusted causal model. The engagement
must be willing to return “directional signal only” and express break-even requirements rather than
convert a selected published surface into a package win rate.

## Engagement record

- **Campaign:** `.research/analysis/campaigns/doomsday-pivot-performance/parent.md`
- **Fan-out:** three independent facets covering outcome/bias, pivot taxonomy, and matchup
  economics/test design.
- **Population contract:** twelve exact-archetype Doomsday registrations dated 2026-08-10 through
  2026-08-18; the conflict-labelled row is reported separately and excluded from comparisons.
- **Finding:** the Personal Tutor/Wasteland published-record gap falls from 37.7 percentage points
  raw to 14.6 points without selected League 5-0s and 8.3 points in Challenges only. The direction
  remains descriptive, but the sample cannot identify a causal tempo penalty and is materially
  pilot-dependent.
- **Decision:** prioritize a matched-main Dimir no-juke versus literal sideboard-only-juke test;
  retain Esper/value as the next distinct rung and treat Wasteland/Murktide as a deeper, separately
  costed hybrid. Use hostile-metagame break-even math before promoting any pivot.
- **Verification:** the single standard adversarial pass returned `NEEDS-REVISION`; all five gates
  were corrected and directly checked. Citation lint resolved 141 citations with zero broken, thin,
  or pattern flags; `git diff --check` passed. No second independent research review was run.
- **Evidence gaps:** no failed-League denominator, incomplete direct player rounds, and no controlled
  matched-main local logs. No source-grounded acquisition candidate was available.
- **Operations caveat:** the local scheduled-refresh projection remained stale at 2026-08-18 with
  legality pending; the campaign used the already-refreshed local corpus through 2026-08-19 and did
  not trigger a network refresh merely to clear the banner.

## Completion

All acceptance criteria are satisfied at the evidence-supported level. The campaign separates
publication, construction, and prospective local evidence; defines a reproducible intensity axis;
tests the apparent penalty under available controls; and emits a prioritized paired-playtest matrix
without claiming causal superiority.
