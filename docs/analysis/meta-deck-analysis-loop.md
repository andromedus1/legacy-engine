---
description: Read before running deck-prep analysis on any archetype — the codified repeatable loop (stages, tools, honesty gates) and the simulation-engine feed spec it produces.
type: design
kind: planning
status: active
updated: 2026-07-04
summary: |
  Codifies the five-stage meta-deck analysis loop proven on Dimir Tempo + Doomsday Tempo
  (2026-07-04) into a repeatable per-archetype procedure, and specifies the knowledge feed
  it produces for the simulation engine / synthetic data generator (epic-goldfish-simulation
  input spec, not implementation).
decisions:
  - "The loop is per-archetype and composable: any meta archetype runs stages 1-4 with the same shipped surfaces (consensus → boards A/B → per-meta variants → comparison); stage order is fixed, stages are skippable only with a stated reason."
  - "Two boards always: A unconstrained (acquisition targets fall out for free), B owned-constrained (catalog-filter + labeled repairs — never presented as a native solver mode)."
  - "Sweep-confirmed overrides (Defense Grid, Damping Sphere) apply mechanically to every board until the scorer mechanisms are fixed; every override and refill is labeled in the deck file header."
  - "Venue divergence is first-class output — per-meta verdicts are never blended; each verdict ships with its composition trigger (what field drift would flip it)."
  - "Subarchetype splits are conservative marker rules persisted to decks.variant; neither/both residue stays unlabeled; camp n and tier are stated on every downstream claim."
  - "Engine-raw reference lists keep known scorer biases VISIBLE (e.g. pitch-counter 1-ofs) so before/after remains measurable; only the pilot's personal board gets judgment fills."
  - "The loop's outputs are the simulation feed: nothing new is computed for the sim engine — it consumes what the loop already produces."
---

# The meta-deck analysis loop

Proven end-to-end on 2026-07-04 (Dimir Tempo stages 1-2, Doomsday Tempo stage 3, cross-meta
comparison stage 4). Runs per archetype; composes only shipped engine surfaces.

## Preconditions (every run)

1. `refresh all` + `label` — corpus current, zero unlabeled regime decks (echo currency in
   every deliverable header).
2. Collection file current (`decks/binder.txt`); reconcile known gaps first (open item:
   dual-land accounting — plays 4 Underground Sea, binder lists none).
3. Field files regime-scoped (`local-field-since-518.txt` pattern); online =
   `provenance='online'` current regime.

## The stages

| # | Stage | Surfaces | Deliverables |
|---|---|---|---|
| 1 | Boards A/B for the pilot deck | `advise sideboard --smart --collection` + owned-catalog re-solve + `advise backtest --field-scope` | optimized .txt + owned .txt + analysis .md (copy histograms 0x-4x, paired swaps, overrides, acquisition list) |
| 2 | Per-meta reference lists + best-picks | `generate consensus [--provenance]` + `advise positioning --candidates --seed` | meta-<venue>-<arch>.txt files + rankings note |
| 3 | Subarchetype split (when camps exist) | marker-rule SQL → `decks.variant` → `build_consensus(variant=)` | camp lists + split rule + camp contrast |
| 4 | Cross-deck comparison | `advise compare --field` per venue + positioning | comparison .md with per-venue verdict + flip trigger |
| 5 | Reflection | this doc + substrate items | new findings → backlog/features; study artifact |

## Honesty gates (inherited from analysis-statistical-context-gates; non-negotiable)

- Winner-sample tier on every backtest claim; camp n on every subarchetype claim.
- Imputed matchup cells (`*`) named when they carry field mass; MC CIs quoted, P(A>B) is the
  summary statistic, EV deltas are not.
- Copy-count claims cite the observed histogram, never inclusion% alone.
- Divergence (scorer-vs-winners, venue-vs-venue, camp-vs-camp) is diagnostic output — it
  never back-propagates into scores.

## Automation path (relates: idea-dogfood-loop-as-autonomous-process, idea-study-loop-other-archetype-lenses)

The loop is deliberately mechanical enough to drive from a batch driver like the archetype
sweep: stages 1-2 are already scriptable per archetype (the sweep's `run_sweep` is stage 1's
backtest half); stage 3 needs a marker-rule registry per archetype (curated JSON, same
pattern as the hoser catalog); stage 4 is a pairwise driver over the loop's outputs. The
payoff the maintainer named: non-Dimir lenses (combo/prison/creature archetypes) stress different
scorer mechanics and will mine different engine-improvement clusters — the loop IS the
idea-processing machine.

## Simulation-engine feed spec (input contract for epic-goldfish-simulation; produces, not implements)

The loop already emits everything the synthetic data generator needs — the sim epic should
consume these artifacts, not recompute them:

1. **Deck population**: per-archetype consensus lists + camp variants (+ copy-count
   distributions per card for list-sampling around the consensus, from
   `observed_copy_distribution`).
2. **Field composition**: regime-scoped field files per venue (share + effective-N counts →
   Dirichlet-samplable).
3. **Matchup priors**: the adaptive matrix cells with tier labels (established/evolving/
   speculative/imputed) — the sim's game-outcome priors, with honesty flags to propagate.
4. **Board plans**: per-matchup OUT/IN swap plans (`matchup_plans`) — the sim's post-board
   state transitions.
5. **Divergence clusters**: the sweep's ranked clusters as scenario weights — where the
   engine's model is known-weak, the sim should sample adversarially, not confirm bias.
6. **Goldfish-speed inputs** (the epic's own domain): consensus manabases + curve profiles
   fall out of the same consensus artifacts.

Each feed item exists today as a file or a queryable surface; the missing piece is only a
manifest that binds one loop-run's artifacts into a versioned bundle (a feature for the sim
epic's design pass, after its [needs-brief] is written).
