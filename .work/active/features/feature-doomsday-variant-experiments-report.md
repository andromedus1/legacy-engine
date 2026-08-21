---
id: feature-doomsday-variant-experiments-report
kind: feature
stage: done
tags: [research, advisory, analytics, ui]
parent: null
depends_on:
  - feature-doomsday-pivot-performance
release_binding: null
gate_origin: null
research_origin: doomsday-variant-experiments
research_refs:
  - doomsday-splash-variants
  - doomsday-pivot-performance
  - doomsday-variant-experiments
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
- BUG, Esper, Turbo Dimir, and Dimir Creature Juke receive clean Moxfield-ready 60/15 exports with
  exact-vs-reconstructed provenance kept explicit and contract-tested against their canonical lists.

## Simplification opportunity

Reuse the registered candidate manifest, exact-list files, local DuckDB, prior source-direct
attestations, ranking report patterns, and playtest protocol. Do not create another deck registry,
duplicate the ranking generator, or imply a complete game simulator exists.

## Mockups

- Screens: `.mockups/screens/feature-doomsday-variant-experiments-report/index.html`
- Selected: option-4, **Pilot's Field Manual** (2026-08-20)
- Rationale: book-like navigation and play-style-first comparison, with compact numeric density
  borrowed from option-2 for at-a-glance decisions.

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

## Engagement record

- Regenerated `decks/best-deck-best-call-ranking.html` from the local DuckDB: 386 field decks
  since 2026-08-10, corpus maximum 2026-08-19, 95 archetype rows, and 106 camp rows.
- Dispatched three independent facets: observed outcomes and bias controls, exact-list
  construction/access experiments, and strategic break-even plus prospective playtest design.
- Synthesized the completed facets into
  `.research/analysis/campaigns/doomsday-variant-experiments/parent.md` and the report-facing
  `report-content.json`; all 14 unique registered/reconstructed candidates remain accounted for.
- Preserved the main tension instead of flattening it into a power ranking: current category
  standings are B 7-5, C 4-2, and D 7-9, while the exact Wasteland/Murktide lineage is 21-8 after
  duplicate collapse but comes from one pilot. No causal tempo penalty is claimed.
- Recorded deterministic opening-resource/access differences and the metagame break-even surface;
  none is represented as a played-game win rate. The preregistered physical program remains 260
  candidate matches plus 260 matched Dimir-control matches.
- Full verification completed: adversarial and isolated-evaluator revision findings were resolved;
  the second isolated evaluation approved the campaign; citation lint reports 250 resolved
  citations with zero broken, thin, or pattern flags.
- Implemented the selected Pilot's Field Manual as a generated, self-contained, responsive HTML
  surface backed by a tracked template and renderer. The final output contains 14 candidates and
  reports the 2026-08-19 corpus cutoff.
- Published four clean Moxfield imports under `decks/doomsday-variants/moxfield/`; BUG is explicitly
  an inferred post-ban reconstruction, while Esper, Turbo Dimir, and Creature Juke preserve exact
  observed artifacts/registrations.
- Verification: 87 focused tests pass; Ruff check and format check pass; HTML structure,
  self-containment, responsive behavior, reduced-motion handling, and embedded-data escaping are
  covered.

## Completion

Completed 2026-08-20. The result is a bounded build-and-test priority guide, not a causal matchup
ranking. The local operations projection remains stale at 2026-08-18 with legality pending; the
research corpus itself reaches 2026-08-19, and no network refresh was triggered to clear the
banner. Exact published legal BUG, Moonshadow, and Cutter registrations remain optional acquisition
candidates rather than silently promoted work.
