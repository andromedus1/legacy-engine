---
id: epic-gap-discovery-discovery-tuning
kind: feature
stage: drafting
tags: [generation, discovery]
parent: epic-gap-discovery
depends_on: [epic-gap-discovery-adjacency]
release_binding: null
gate_origin: null
created: 2026-06-01
updated: 2026-06-01
---

# Discovery Tuning (value transfer + gated suggestion surface)

## Brief

The evidence + honesty layer on top of the adjacency model: takes the nominated candidates
from `epic-gap-discovery-adjacency` and decides which to surface as exploratory swap-in
suggestions, with explicit uncertainty. This is the **key unlock** — a candidate is by
definition under-played in the shell, so its in-shell per-card signal is thin; the fix is
**cross-archetype value transfer**. `analytics/card_value` already pools per-`(card, board,
opponent)` lift across ALL decks (not conditioned on the running deck's archetype), so
`card_values_vs([X], board, opponent=M)` gives `X`'s lift vs threat `M` over every deck that
ran it. Transfer that lift, shrunk toward no-edge by the cross-field `n`
(`matchup.beta_binomial_shrink_to`, the two-level-empirical-Bayes pattern).

**Transfer is role-gated** (a new small, curated `TRANSFERABLE_ROLES` allow-list, mirroring
how `sideboard.HOSER_CATALOG` treats answers as archetype-independent): transfer the matchup
lift for answer/hoser/generic-cantrip roles where it is honest; for **synergy/engine roles**
(combo enablers, payoffs, build-arounds) the pooled lift is meaningless out of context, so
those candidates are still nominated but must clear the **normal un-transferred in-shell
confidence gate** (no transfer credit) to surface — per the inherited decision below.

Surfaces via a new **`--discover` flag on `generate tune`**: when set, the command appends a
**distinct, clearly-flagged exploratory-suggestion section** after the proven in-pool swap log
— never silently mixed in. Discovery suggestions NEVER drive the greedy swap objective (that
preserves the existing no-gameplan-hollowing guarantee); they are suggest-and-label only.
Every suggestion is gated at the **established tier (≥100 cross-field n)** by default and
labeled `presence-correlational, transferred from cross-field data, NOT goldfish-validated`
(reuse the `report cards` / `advise sideboard` disclaimer wording). Exploration is capped at a
few candidates.

Does NOT cover the adjacency/nomination logic (that's the dependency) nor goldfish validation
(the deferred `epic-goldfish-simulation` pillar slots in later as a candidate → goldfish-passes?
→ promote-from-suggestion filter; design the output so that filter drops in without a rewrite).

## Epic context

- Parent epic: `epic-gap-discovery`
- Position in epic: consumer of `epic-gap-discovery-adjacency` — the riskiest feature in the
  epic (it is where exploration could fabricate edges), so the confidence gating is load-bearing.

## Inherited design decisions

- **Card-discovery CLI surface = `--discover` flag on `generate tune`** (not a separate
  `generate discover` command) — one command, two clearly-flagged output blocks; proven swaps
  first, exploratory suggestions in a distinct labeled section after.
- **Synergy/engine-piece candidates = include, but require in-shell evidence (option b)** —
  they are nominated by the adjacency model but get NO cross-field transfer credit; they must
  clear the normal un-transferred in-shell confidence gate to surface (in practice they rarely
  will, since they are under-played in the shell by definition — but the path is general).
- **Transfer is role-gated** via a new curated `TRANSFERABLE_ROLES` allow-list (answers / hosers
  / generic cantrips), mirroring `sideboard.HOSER_CATALOG`.
- **Shrinkage**: transferred lift is a prior shrunk toward 0 (no-edge) by cross-field `n` via
  `beta_binomial_shrink_to`.
- **Confidence bar = established tier (≥100 cross-field n)** for a discovery suggestion to
  surface by default — a HIGHER bar than in-pool tuning (which accepts evolving), because the
  candidate is unproven in this shell. Do not relax for coverage.
- **Honesty invariants** (load-bearing, non-negotiable): distinct flagged section, never in the
  proven swap log; never drives the greedy objective; explicit correlational + not-goldfish
  labels; capped exploration count.
- **Windowing / reuse**: thread the tuner's latest-ban-regime window; reuse ONE `CardWinRates`
  aggregate across tune + discovery (per `fix-tuning-sideboard-winrate-reuse`, and the open
  backlog perf note `idea-tuning-sideboard-winrate-reuse`).

## Research briefs

- `docs/briefs/card-adjacency-and-discovery.md` §2 (cross-archetype value transfer — the role
  decomposition + shrinkage), §3 (risk & validation — confidence gating, what v1 can/cannot
  claim, where goldfish fits later), §Implementation Notes.

## Foundation references

- `src/legacy_engine/analytics/card_value.py` — `card_values_vs` / `CardValue` (the transferable
  per-card×matchup quantity).
- `src/legacy_engine/analytics/matchup.py` — `beta_binomial_shrink_to` (shrinkage primitive).
- `src/legacy_engine/advisory/sideboard.py` — `HOSER_CATALOG` (the archetype-independent-answers
  precedent `TRANSFERABLE_ROLES` mirrors).
- `src/legacy_engine/generation/tuning.py` — `tune_deck` / `TunedDeck` (the command this flag
  extends; discovery composes alongside, does not enter, the greedy objective).
- `src/legacy_engine/cli.py` — `@generate.command("tune")` (~line 1232).
