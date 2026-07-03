---
id: feature-sb-effect-tagging-model
kind: feature
stage: drafting
tags: [advisory]
parent: epic-sideboard-scoring-model
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Effect-tagging + hoser catalog: linchpin, symmetry, color-contingent, castability

## Brief

Foundation feature (A) of `epic-sideboard-scoring-model`. The scorer (Feature B) is only as
good as the card→effect model it reads, and that model — `data/hosers/legacy.json` + the
vulnerability-tag system — is coarse and has known errors. This feature fixes and deepens it.
It folds two backlog ideas (`idea-sb-color-contingent-hate`, `idea-granular-effect-tagging`)
and adds the two new factors the epic's impact decomposition needs: **centrality (linchpin)**
and **castability**.

Scope:
- **Quick data fixes** (low-risk, independently useful): correct Hydroblast's tag (it targets
  *red*, not manabases); add Blue Elemental Blast + Red Elemental Blast to the catalog with
  correct attribution; dedupe functionally-identical hosers so they aren't counted as distinct
  coverage.
- **Color-contingent hate** — a model concept for "anti-red / anti-blue" rather than shoehorning
  color blasts into archetype tags.
- **Symmetry flag** — asymmetric (opponent-only) vs symmetric (affects me too), so the scorer can
  catch self-hosing (Grafdigger's Cage vs the deck's own graveyard).
- **Finer graveyard tags** — replace monolithic "graveyard hate" with tags that capture how a card
  interacts with the graveyard (synergy/anti-synergy).
- **Archetype linchpin model** — per-archetype critical points of failure, so impact can score
  "hits a linchpin" (Painter's Grindstone) vs "hits a redundant piece" (a Mox).
- **Castability attributes** — the conditions/cost to actually cast a hoser in a given matchup
  (color requirements, conditional free-cast like Massacre needing an opponent's Plains).

<!-- Design input below preserved from the folded backlog ideas. -->

## Design input — granular effect tagging (from idea-granular-effect-tagging)

Improve decision-making by making card effect tagging more granular — finer tags give the engine
nuance (especially graveyard interactions) and better advice.

1. **More granular graveyard tagging.** Current tags are too coarse to capture how a card
   interacts with the graveyard and other cards. Finer tags let the engine reason about graveyard
   synergies/anti-synergies instead of treating "graveyard hate" as a monolith.
2. **Symmetry flag for game-wide effects.** Asymmetric (opponent-only) vs symmetric (everyone,
   including the controller) — lets the engine catch self-hosing recommendations.

Motivating example (Flow State / Dimir Tempo dive, 2026-06-22): Grafdigger's Cage was treated as
fine SB for Dimir Tempo, but post-Flow-State the deck leans on its *own* graveyard (Nethergoyf +
Flow State's "instant AND sorcery in graveyard → draw 2"). Cage is symmetric graveyard hate, so it
hoses the deck's own plan. Real data backs it: as Flow State hit ~100%, Cage dropped ~47%→~20% SB
inclusion, shifting to Nihil Spellbomb. Today's tagging lacked the nuance to flag Cage as
self-hosing.

## Design input — color-contingent hate (from idea-sb-color-contingent-hate)

Represent color-contingent hate and de-duplicate functionally-identical hosers. Found in a
test-drive: the engine recommended 3 Hydroblast + 1 Blue Elemental Blast as distinct coverage — but
oracle text confirms both target RED (the anti-*blue* blasts are Red Elemental Blast / Pyroblast,
uncastable in U/B). Root cause is data + modeling:
- `data/hosers/legacy.json`: Hydroblast mis-tagged `attacks: ['greedy-manabase','low-interaction']`
  (it counters/destroys red). Blue/Red Elemental Blast aren't in the catalog at all — BEB only
  appeared via empirical promotion with the generic `'combo'` fallback tag.
- The vulnerability-tag system has no concept of color-contingent hate ("anti-red", "anti-blue"),
  so color blasts get shoehorned into archetype tags and stacked as if distinct.

Fix: (a) add BEB + REB with correct attribution and fix Hydroblast's tag (~one-line catalog edit,
low-risk); (b) give the model a notion of color-contingent hate and/or de-duplicate
functionally-identical hosers.
