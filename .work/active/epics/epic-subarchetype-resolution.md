---
id: epic-subarchetype-resolution
kind: epic
stage: drafting
tags: [analytics, archetype]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-29
updated: 2026-07-11
brief: docs/briefs/subarchetype-discovery.md
---

# Subarchetype resolution

## Brief

The engine carries a **flat archetype label per deck**. Subarchetypes that play completely
differently collapse onto one parent label, so they pool into a single matchup row and a single
card-win-rate denominator — which distorts every downstream stat. This wall has been hit in three
consecutive dogfooding sessions:

- **Doomsday** (2026-06-29 / 07-05): the Legacy one-card rule labels every maindeck-Doomsday deck
  "Doomsday", but `report subgroup --archetype Doomsday --signature "Murktide Regent"` shows a clean
  **292/878 split, both established tier** — a tempo/mana-denial camp (Tamiyo +2.7, Wasteland +2.1,
  Bowmasters +1.0) vs an all-in mana camp (Personal Tutor, Lotus Petal, Cabal Ritual). ~25% of the
  archetype is a different deck.
- **WU Phelia / Quantum Riddler** (2026-07-11): the real deck is split three ways by the parser
  (Azorius Midrange + White Beanstalk + Azorius Stoneblade, by engine package) and had to be
  **hand-merged into one cohort** to recover matchup sample — the inverse problem (one deck read as
  three labels).
- **Dimir Tempo card keep/cut** (2026-06-27): `report cards --archetype "Dimir Tempo"` showed
  Mishra's Bauble at −0.040 marginal lift (a "cut" signal), while `report subgroup` showed
  Goyf+Bauble was the *best* cell (59.7%, n=159) — the marginal number is cross-archetype
  contaminated and pointed backwards.

**Why it matters:** matchup accuracy, card keep/cut calls, and field composition are all only as
honest as the partition they condition on. Today that partition is a single flat label. Same risk
lurks in every broad bucket — Eldrazi, Painter, the *Delver family, the Midrange labels.

**Known integration constraint (from prior investigation):** `analytics/match_results.py` keys on
`decks.archetype` only, so persisting `decks.variant` labels alone does **not** split the matchup
matrix — the matrix builder must gain a variant dimension. Existing primitives are a starting point,
not a solution: `archetype/variants.py` (hand-authored card-presence registry, `data/variants/legacy.json`),
`report subgroup` (manual single-card split), `report variants` / `report meta --by-variant` /
`generate consensus --variant`.

## Strategic decisions

- **Epic membership**: discovery + variant-conditioned matchup cells + archetype-conditioned card
  win-rate. — One analytics-infrastructure arc. `idea-archetype-id-trainer` stays in the backlog: it
  is a separate in-game coaching product surface that consumes flat archetype knowledge and does not
  depend on subarchetype resolution.
- **Discovery method: full unsupervised, statistically self-validating**: the pilot lacks the subject
  expertise to reliably hand-confirm a hybrid registry today, so discovery cannot lean on human
  judgment as its correctness gate — clusters must earn their split via statistical validation
  (cohesion/separation, both-camp sample tiers, card-inclusion divergence like the Doomsday case).
  Preserve a **human-confirm hook** so camps can be promoted/renamed into the curated registry as the
  pilot's expertise grows. — The core of the research/scout brief.
- **Sequencing: discovery-first**: the data-driven discovery engine ships before the analytics
  conditioning consumes it; the conditioning features `depends_on` discovery. (Note: the matchup-cell
  and card-win-rate slices are technically computable off the *existing curated* variants today —
  discovery-first is a deliberate choice to build the real classifier before wiring analytics to it,
  not a technical constraint.)
- **Honesty bar: surface labeled, never hide**: splitting a parent shrinks per-cell n, often into
  speculative tier (e.g. Dimir Tempo Tempo/Turbo was n=47/49). Variant-conditioned cells surface at
  whatever tier they land with mandatory honesty labels — consistent with the project's
  honest-degrade policy. No split is hidden for being thin, and none is silently blended away.

## Intended arc (for /epic-design to realize post-brief)

Sketch only — decomposition, interfaces, and the discovery mechanism are `epic-design`'s job once the
brief exists. Dependency order reflects discovery-first:

1. **Subarchetype discovery engine** (research-gated core) — cluster/validate/name splits within a
   parent at corpus scale, persist to `decks.variant`, with a human-confirm promotion hook. Absorbs
   `idea-subarchetype-discovery` (this item).
2. **Variant-conditioned matchup cells** — extend `match_results.py` / `matchup.py` with an optional
   variant dimension on one side; speculative-tier honesty labels mandatory. `depends_on` #1.
   Absorbs `idea-variant-conditioned-matchup-cells`.
3. **Archetype/variant-conditioned card win-rate** — restrict the `compute_card_winrates` W/L
   denominator to the archetype's (or camp's) own decks; emit an honest-degrade warning when a card's
   marginal lift conflicts in sign with its within-archetype subgroup win-rate; surface subgroup win%
   directly in `report subgroup`. `depends_on` #1. Absorbs `idea-archetype-conditioned-card-winrate`.

## Foundation-doc status

VISION rolled forward (two-level taxonomy intent — method-independent). ARCHITECTURE / SPEC
roll-forward is **deferred to post-brief `/epic-design`**: the discovery mechanism is research-pending,
and per "research before design" the architecture must not commit to an unresearched clustering
approach.

## Next

Brief **written** and attested: `docs/briefs/subarchetype-discovery.md` (ARD citation chain clean;
15 source-direct attestations under `.research/attestation/`, corpus
`.research/reference/subarchetype-discovery/`). It locks the method — flex-band representation,
TF-IDF/count + cosine/Bray-Curtis, HDBSCAN-primary (self-determines k, labels noise) on a
reduced embedding, two-gate validation (resampling stability >0.9 / prediction strength >0.8 **and**
both-camp evolving tier + signature divergence), the double-dipping guard, and the optional
`(archetype, variant) × opponent` matchup-cell key that reuses the existing tier gates unchanged.

Ready for `/epic-design` to decompose into the three features (discovery engine → variant-conditioned
matchup cells → archetype/variant-conditioned card win-rate).
