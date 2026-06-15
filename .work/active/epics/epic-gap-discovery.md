---
id: epic-gap-discovery
kind: epic
stage: done
tags: [generation, discovery]
parent: null
depends_on: [epic-deck-generation]
release_binding: v0.1.0
gate_origin: null
created: 2026-05-31
updated: 2026-06-14
---

# Gap Discovery (deck generation mode 3)

## Brief

The deferred **mode 3** of the Deck Generation pillar (split out of `epic-deck-generation`, which shipped
consensus + export + field-tuning). Two halves:

- **Archetype-gaps** — surface archetypes with high positioning `S` (well-positioned vs the field) but low
  meta-share: under-explored shells the field is sleeping on. Consumes `advisory/positioning` + `metashare`.
- **Card-gaps / adjacent-card discovery** — let the tuner consider cards the deck does NOT already run:
  role/color/CMC/synergy-**adjacent** candidates that are under- or un-played in this shell but have proven
  value. This turns "tuning" (bounded to the archetype's observed pool) toward "discovery" — the
  differentiator. Promoted from `idea-tuning-adjacent-card-discovery` (2026-05-30).

**What this session unblocked:** the per-card×matchup win-rate extension (`analytics/card_value`,
`compute_card_winrates`) shipped in `epic-deck-generation`, removing the hard data blocker the original idea
cited. Adjacent candidates can now be scored by **cross-archetype** per-card value (a card proven vs threat M
in *other* decks → transfer it here), confidence-gated. The remaining unknowns are an **adjacency model**
(what makes a card a candidate) and **validating exploratory candidates** (where the eventual
`epic-goldfish-simulation` pillar adds a confidence layer — not a hard blocker for a confidence-gated v1).

## Design decisions
- **Card-discovery CLI surface**: `--discover` flag on `generate tune` (not a separate command) — one
  command, two clearly-flagged output blocks: proven in-pool swaps first, exploratory suggestions in a
  distinct labeled section after.
- **Synergy/engine-piece candidates**: include, but require in-shell evidence (option b) — nominated by the
  adjacency model, get NO cross-field transfer credit, must clear the normal un-transferred in-shell
  confidence gate to surface (general path; rarely fires since they're under-played in shell by definition).
- **Archetype-gap surface**: new `report gaps` command in the existing `report` family (not a column folded
  into `report tiers`) — keeps the two distinct reads uncoupled.

## Decomposition

Split by capability into the two halves of mode 3, with the card-gap half further split along the
nominate-then-score seam. The **archetype-gap** half is mechanical and fully independent
(`report gaps` over positioning × metashare) → its own parallelizable feature. The **card-gap** half splits
into nomination (`adjacency`: which cards are even candidates) and evidence+honesty (`discovery-tuning`:
cross-archetype value transfer, role-gated, confidence-gated, suggest-and-label). This shape isolates the
load-bearing safety logic (transfer gating, honesty invariants) into one feature and keeps the corpus-query
adjacency work separable, while letting the archetype-gap read ship in parallel.

### Child features

- `epic-gap-discovery-archetype-gaps` — `report gaps`: high-S / low-share archetype surfacing (positioning ×
  metashare), confidence-gated — depends on: `[]`
- `epic-gap-discovery-adjacency` — `generation/discovery.py` candidate nomination: not-in-deck ∩ color-legal
  ∩ role-relevant ∩ CMC-band, ranked by `deck_cards` co-occurrence PMI — depends on: `[]`
- `epic-gap-discovery-discovery-tuning` — `--discover` flag on `generate tune`: role-gated cross-archetype
  value transfer (shrunk), established-tier gate, distinct labeled suggest-and-label surface — depends on:
  `[epic-gap-discovery-adjacency]`

### Decomposition risks

- **discovery-tuning is the riskiest feature** — it is where exploration could fabricate edges. The honesty
  invariants (distinct flagged section, never drives the greedy objective, established-tier bar, explicit
  correlational/not-goldfish labels, capped count) are load-bearing and must not be relaxed for coverage.
- **Synergy-include (option b) adds a second gate path** in discovery-tuning (transferred vs un-transferred
  in-shell), slightly more branching than omit-entirely would have. Acceptable for generality; covered by the
  inherited decision.
- **archetype-gaps is the smallest feature** (reuses two shipped surfaces) — borderline tiny, but a distinct
  capability with its own CLI + gap-score design, so it stays its own feature rather than folding into report.
- **(later) goldfish-validated candidates** — deferred to `epic-goldfish-simulation`; discovery-tuning's
  output is designed so a goldfish-passes? filter slots in as a promote-from-suggestion step without a rewrite.

## Foundation references
- `docs/briefs/deck-generation-and-moxfield.md` §2.2 (mode 3 card-gaps).
- `epic-deck-generation` (the shipped consensus/export/tuning + per-card-value + maindeck-aware sideboard it
  builds on), `epic-goldfish-simulation` (later validation layer).
- Related backlog/notes: this epic supersedes `idea-tuning-adjacent-card-discovery`.
