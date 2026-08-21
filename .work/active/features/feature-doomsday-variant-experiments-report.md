---
id: feature-doomsday-variant-experiments-report
kind: feature
stage: implementing
tags: [research, advisory, analytics, ui]
parent: null
depends_on:
  - feature-doomsday-pivot-performance
release_binding: null
gate_origin: null
research_origin: null
research_refs:
  - doomsday-splash-variants
  - doomsday-pivot-performance
research_dials:
  scope_authority: mixed
  verification_rigor: full
  intent: decision-support
  output_kind: adoption-recommendations
created: 2026-08-20
updated: 2026-08-20
---

# Experiment across Doomsday variants and publish the field guide

## Brief

Run every honest experiment the refreshed local corpus and exact registered decklists support,
then commission a fresh-context synthesis that identifies the best-supported Doomsday versions,
their play-style differences, trade-offs, pros and cons, and the metagame conditions that change
the recommendation. Publish the result as a concise, visually striking, self-contained HTML field
guide designed for at-a-glance use.

This work must keep three evidence classes separate: observed tournament outcomes, reproducible
deck-construction or draw/access experiments, and prospective physical-playtest requirements.
Incomplete matchup rows and the unfinished rules-aware goldfish engine cannot be converted into
invented win rates. Where an experiment cannot currently run, record the missing primitive and the
exact future protocol instead.

## Strategic decisions

- **Decision relevance:** choose which Doomsday versions deserve acquisition, construction, and
  testing priority; explain when a pilot should prefer focused Dimir, a sideboard-led juke,
  Esper/value, BUG/green protection, Grixis/Squelcher, or deep denial-tempo.
- **Research authority:** mixed — preserve exact registered lists and observed data contracts while
  allowing experiment design and comparison dimensions to emerge from the evidence.
- **Verification:** full — citation lint, fresh adversarial review, isolated evaluator, and lead
  source/experiment spot checks.
- **Visual direction:** dark academia fused with a data-dense trading terminal; concise hierarchy,
  Dimir-toned palette, accessible contrast, responsive offline HTML, and no framework dependency.
- **Experimental boundary:** execute all supported retrospective, structural, access, and scenario
  analyses; emit rather than fabricate physical-match or rules-engine results that the repository
  cannot presently produce.

## Acceptance

- The refreshed Best Deck / Best Call HTML is regenerated from `data/legacy.duckdb` and its corpus
  cutoff and row counts are recorded.
- Outcome comparisons expose selection, event, pilot, sample-size, and taxonomy sensitivity.
- Exact candidate lists receive reproducible construction, mana-pressure, opening-hand/access, and
  sideboard-cost comparisons wherever current primitives permit them.
- Matchup economics and metagame scenarios identify what each pivot must gain to repay its costs.
- A fresh synthesizer consumes completed experimental outputs and produces bounded recommendations,
  play-style portraits, pros/cons, trade-offs, and uncertainty.
- Full ARD verification passes without laundering prior campaign synthesis as source substrate.
- Four distinct report-layout mocks are produced inside the confirmed visual world, one direction
  is selected, and the final self-contained HTML report is checked for responsive, accessible,
  at-a-glance interpretation.

## Simplification opportunity

Reuse the registered candidate manifest, exact-list files, local DuckDB, prior source-direct
attestations, ranking report patterns, and playtest protocol. Do not create another deck registry,
duplicate the ranking generator, or imply a complete game simulator exists.

## Mockups

- Screens: `.mockups/screens/feature-doomsday-variant-experiments-report/index.html`
- Selected: pending layout exploration inside the confirmed dark-academia/trading-terminal world

## Decomposition rationale

Checkpoint A compared three shapes:

1. **Color-by-color:** intuitive for deckbuilding, but it repeats splash/chassis confounding and
   encourages unsupported winner labels from tiny cohorts.
2. **Simulator-first:** attractive for a decisive answer, but the rules-aware goldfish and matchup
   simulator remains an unfinished project arc; treating a draw checker as game simulation would
   be misleading.
3. **Evidence-axis:** independently test observed outcomes, exact-list construction/access costs,
   and matchup/metagame economics, then cross-synthesize them.

The evidence-axis shape is selected. Three parallel facets cover:

- **Outcome experiment:** refreshed census, event/pilot/publication controls, bootstrap or exact
  uncertainty where support permits, taxonomy sensitivity, recurrence, and current/historical
  boundaries.
- **Construction/access experiment:** exact 75 verification, color and land pressure, opening-hand
  resource/access distributions, post-board exchange costs, and explicit abstention where card
  sequencing would require the unfinished rules engine.
- **Strategic experiment:** matchup-rescue break-even surfaces, metagame scenarios, play-style and
  skill-burden comparison, boarding-plan implications, and a concrete paired physical-test matrix.

Self-flag: no computational result in this campaign may be described as a played-game win rate.
The synthesis must preserve observed, simulated-draw, inferred-scenario, and prospective-test
labels as separate evidence types.
