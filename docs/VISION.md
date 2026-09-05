---
name: vision-legacy-engine
description: Read first — the why and what of legacy-engine. Vision, problem, principles pointer, and the four-pillar domain model for the Legacy analytics platform.
type: north-star
kind: planning
summary: |
  legacy-engine is a Magic: The Gathering Legacy-format analytics platform — sibling to edh-engine
  (cEDH). It answers "what's the meta, how do I attack it, and how do I tune my deck?" via three
  reinforcing data layers (observed tournament data, synthetic goldfish simulation, generated insight)
  powering four analytical pillars: Meta & Performance, Deck Mechanics, Deck Generation, and Meta Attack/Advisory.
decisions:
  - "Four analytical pillars — Meta & Performance, Deck Mechanics (goldfish), Deck Generation, and Meta Attack/Advisory (the Legacy-specific differentiator: matchup positioning, sideboard recommender, what-to-play)."
  - "Sibling-of-edh-engine: reuse its 3-data-layer → pillar architecture, deck-as-data model, goldfish/mana/mulligan engines wherever the domain overlaps; diverge only where Legacy demands it."
  - "Key architectural delta: an explicit archetype-parser layer (no commander to key on) — labels decklists into the community taxonomy."
  - "Current shipped arc = ingestion + meta analytics + advisory + deck generation (consensus, field tuning, export, gap discovery, and deck doctor); goldfish simulation and goldfish-validated candidate evaluation remain deferred Deck Mechanics work."
  - "Legacy is a 1v1, best-of-3, 60-card-with-sideboard format — sideboarding and matchups are first-class, unlike edh-engine's 4-player goldfish framing."
  - "Banned-list legality is a live blacklist (changes ~quarterly) and must be version-stamped by date for historical analysis."
  - "Per-entity stable eras: every per-archetype/per-camp statistic uses the entity's own detected and certified set of compatible time intervals, not just one global ban regime or monotone suffix; bans and releases nominate disturbances, confirmed affectedness remains a hard boundary, and every windowed figure names the admitted intervals and evidence provenance."
  - "Three-level taxonomy: superarchetype (data-driven strategy cluster over archetypes, curated overrides) → parent archetype → camp. Superarchetypes support internal context and strategic-plan navigation; the Deck Rankings page makes performance and worst-matchup floor equally visible while the mature Agency/P(best) projection and benchmark remain frozen reference surfaces."
  - "Deck Rankings is a current descriptive decision projection: full-field posterior mean performance and the minimum non-mirror posterior matchup mean are shown with intervals, provenance, and Pareto tradeoffs. Performance and floor have independent leaders, with performance breaking floor ties."
  - "Persistent-coach layer (cross-cutting): engine-generated knowledge — meta reads, per-deck findings, consensus decklists with primers — persists across sessions and is surfaced automatically; advice is grounded in a user profile (decks played, collection, local meta). maintainer-first now, multi-user-ready by design: the profile is data, not code."
created: 2026-05-29
updated: 2026-09-05
related:
  - {slug: docs/SPEC.md, relationship: refines}
  - {slug: docs/ARCHITECTURE.md, relationship: refines}
  - {slug: docs/PRINCIPLES.md, relationship: parallel-to}
  - {slug: docs/briefs/legacy-metagame.md, relationship: depends-on}
  - {slug: docs/briefs/legacy-foundations.md, relationship: depends-on}
---

# Vision: legacy-engine

## Vision
A **Magic: The Gathering Legacy-format analytics platform** that answers, with data rather than
vibes: *"What is the meta, how do I attack it, and how do I tune my deck?"* It is the sibling of
**edh-engine** (which does the same for cEDH) and deliberately reuses that platform's architecture as
its schema — three data layers feeding analytical pillars, a deck-as-data model, goldfish simulation,
and a compiled knowledge layer — adapted to the realities of a 1v1, best-of-3, sideboarded, 60-card
eternal format.

## Problem
Legacy deckbuilding and metagaming are largely experience- and forum-driven. Tier lists live in
scattered "This Week in Legacy" articles; matchup knowledge lives in Discord and individual reps;
"what should I play this weekend?" is answered by feel. There is no rigorous, reproducible way to:

- Track the metagame from raw tournament results under a *consistent, auditable* **three-level** archetype taxonomy — superarchetype (strategy cluster) above, parent archetype in the middle, data-driven subarchetype (camp) below — so decks that share a label but play differently are not pooled into one matchup row or one card-win-rate denominator, while strategy families provide explicitly exploratory pooled context where specific labels are too thin to speak on their own
- Window every per-entity statistic to that entity's own **certified stable-era intervals** — bans *and* new-card releases rebuild decks mid-regime, so pooling across an incompatible disturbance mixes generations of the same label into one number; compatible historical pockets may be recovered across excluded gaps, but each figure must name the admitted intervals, their certification, and the disturbance or evidence rule that excludes each gap
- Compute matchup matrices, a deck's **expected win rate against the weighted field**, and its
  highest defensible worst-matchup floor
- Recommend a sideboard package that maximally covers the expected field (hosers → targets)
- Measure how fast and consistently a deck executes its plan (goldfish clock) and aggregate that into a **meta-speed distribution**
- Separate **online vs paper** metagames, which diverge materially
- Discover under-explored shells or tune an existing list against where the meta is heading

legacy-engine solves this with three reinforcing data layers:

1. **Observed data** — tournament results, decklists, banned-list state (what's actually happening)
2. **Synthetic data** — goldfish simulation: speed, consistency, mulligan/hand quality (what *should* happen by the rules)
3. **Generated insight** — matchup positioning, sideboard recommendation, card-impact, eventual deck candidates (what to do about it)

Tournament data tells us what to simulate and what the matchups are; simulation tells us *why* decks
win (speed, consistency, disruption density); and that understanding drives the advisory and
generation layers. Crucially for Legacy, the advisory layer — **how to attack the field** — is a
first-class product surface, not an afterthought.

## Principles
See [PRINCIPLES.md](PRINCIPLES.md) for the full set. The load-bearing ones: *analytics is the product*,
*data-driven over vibes*, *rules-correct at the fidelity claimed*, *knowledge is compiled not
re-derived*, *legality is live data*, and *always label online-vs-paper and the meta-% definition*.

## Domain Model — the four pillars

All four pillars draw from the same three data layers and the compiled knowledge layer; they answer
different questions.

**1. Meta & Performance** — what's being played, how it performs, how it shifts. Tier lists, meta-%
breakdowns (computed under multiple definitions — raw count, top-cut presence, win-rate-weighted),
matchup matrices, archetype trends across banned-list regime shifts, online-vs-paper splits. Built on
observed tournament data, supplemented by simulation.

**2. Deck Mechanics** — how a deck functions internally. Goldfish speed (turn-to-kill PMF),
consistency, hand quality, London-mulligan modeling, mana-curve and sequencing analysis, the engines-
vs-payoffs distinction (deck-context-dependent card roles). The headline output is **cross-deck
comparison** and a format **meta-speed distribution** (per-archetype goldfish clock weighted by meta
share, tracked monthly). Models *both* a goldfish clock (upper bound) and an effective clock (convolved
with Force-of-Will/Daze survival); the gap is a format-health signal.

**3. Deck Generation** — finding under-explored shells and tuning builds against the (current or
projected) meta. Analytically guided: the knowledge layer finds gaps, deck-mechanics knowledge
constrains the build, simulation and matchup data validate candidates.

**4. Meta Attack / Advisory** *(the Legacy-specific differentiator)* — *how to attack the field.*
The `decks/deck-rankings.html` landing page puts full-field posterior performance and the minimum
non-mirror matchup floor side by side, with conditional intervals, source provenance, and Pareto
tradeoffs. Its performance and floor calls are independent, with performance breaking floor ties.
The existing meta-positioning score, sideboard recommender (hoser→target weighted set-cover), and
"what to play" advisor remain available for deck-specific and local-field questions.

**Cross-cutting: the persistent coach.** The pillars' outputs do not evaporate at the end of a
session. Meta knowledge (tier reads, matchup insight, field trends), per-deck critical findings,
and the curated consensus-deck corpus with primers persist as maintained engine state, surfaced
automatically when relevant — a session starts from accumulated knowledge, not from scratch. Advice
is grounded in a **user profile** (decks owned and played, collection, local meta, preferences).
Built maintainer-first; multi-user-ready by design — the profile is data, so serving another player is
a config swap, not a rewrite.

## Non-goals (for now)
- Not an interactive deck-building *editor* GUI, and not a web app yet — a hosted web UI is deferred pending its own research. The engine **does** model the user's personal collection and own decks as a first-class *local* layer (so advice is buildable and actionable from what you actually own), but it stays CLI-first analytics, not a deckbuilding editor.
- Not a full rules-correct game engine — Legacy is 1v1, and goldfish simulation remains a deferred
  Deck Mechanics track while the observed-data generation and advisory surfaces are already built.
- Not Vintage, Modern, or other formats (though the card/data layer is largely format-agnostic).
- Not live/real-time during events — all external data is pre-fetched and cached.

## Related Documents
| Document | Purpose |
|----------|---------|
| [SPEC.md](SPEC.md) | What the system does — capabilities, domain entities, NFRs |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Current detailed module map, data flow, and implementation boundaries |
| [PRINCIPLES.md](PRINCIPLES.md) | Decision heuristics specific to this project |
| [research-plan.md](research-plan.md) | Current research posture, completed grounding, and deferred refresh work |
| [briefs/legacy-foundations.md](briefs/legacy-foundations.md) | Rules, London mulligan, format constraints |
| [briefs/legacy-metagame.md](briefs/legacy-metagame.md) | 2026 meta, archetypes, data sources, how-to-attack |
