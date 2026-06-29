---
id: epic-sb-config-evaluation
kind: epic
stage: drafting
tags: [advisory, analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-29
updated: 2026-06-29
---

# Sideboard & Configuration Evaluation

## Brief

The engine is **single-deck** today: every advisory surface (`advise positioning`,
`whattoplay`, `sideboard`) scores one 75 against a field. It cannot answer two questions a
real operator faces constantly:

1. **Is a given sideboard slot actually pulling weight in its target matchup?** — "Does
   Toxic Deluge in my SB actually help vs Death & Taxes, or am I just running it on faith?"
2. **Is configuration A better than configuration B against this field?** — and the sharp
   special case that motivated this epic: **is transforming into a second deck worth more
   than dedicating the sideboard to silver bullets?**

This epic adds an empirical evaluation arc for both: a matchup-conditioned sideboard-slot
test (the measurement primitive) and a configuration comparator (the decision tool) that
compares two whole 75s — including **transform-alternates** (one deck that sideboards into a
different deck) — against the field, with a **break-even** readout.

**Motivating real-world use (Andrew, paper Boulder meta):** evaluating "Doomsday-tempo that
transforms into Dimir Tempo" vs "Dimir Tempo + a silver-bullet SB (Massacre / Toxic Deluge /
Hurkyl's Recall / Null Rod)." Session analysis (2026-06-29) found the transform option wins
net field EV (~56% vs ~53% over the n≥30 Boulder field), but the decision hinges on the
both-modes-underwater matchups (Blue Artifacts, Eldrazi) where only the SB can help — exactly
what these tools would quantify. The two reliable matchup inversions driving the result:
Death & Taxes (Dimir 34.6% → Doomsday 71.8%) and Energy (37.9% → 59.6%).

## Strategic decisions
- **Scope of the comparator (general vs transform-specific)**: General engine + transform
  layer, delivered transform-first. — The internal engine is general either way (you can't
  compute the transform envelope `max(mode_A, mode_B)` per matchup without computing each
  config's full per-matchup vector — which *is* the general two-config comparison). So we
  build the general engine, design its "config" abstraction grounded in **both** real uses
  (transform-alternate AND build-A-vs-build-B, so generality is pinned by ≥2 uses, not
  speculative), but **sequence delivery transform-first** (the validated need, robust to thin
  data via break-even), general-comparison surface second. Avoids both the wrong-abstraction
  risk of designing off one use and the slow-to-value risk of shipping nothing until a
  polished general surface exists.
- **Structure**: One epic, two features (slot-test → comparator). — Real capability arc with a
  dependency; the comparator wants its own design pass to carve the transform-first /
  general-second child stories.
- **Foundation roll-forward**: deferred to design. — Both features are additive (extend
  `analytics/subgroup.py` and `advisory/positioning.py`; no new model entity, boundary, or
  data-flow change). Per the rolling-foundation principle and the `epic-local-meta-support`
  precedent, SPEC/VISION/ARCHITECTURE roll forward at `feature-design` when the actual command
  surface is decided, not now.

## Known constraint — the data ceiling (applies to both features)

The engine has **no game-level or sideboarding-action data** — only the registered 75 and an
aggregate match score (`"2-1"`), with no game order or board-state. So every sideboard-lift
number is a **presence-correlational proxy over the decklist**, with selection confounds (the
decks that choose to run a card may differ systematically) and thin per-matchup samples;
Boulder-specific SB data is ~nil. The deliverable is **decision support with explicit
assumptions + break-even sensitivity, NOT "the data proves it."** Both features must wear this
honestly (honest-degrade marker pattern: Wilson CIs, significance tests, loud thin-n /
presence-correlational banners).

## Features
- **epic-sb-config-evaluation-matchup-slot-test** — the measurement primitive (Piece 1).
- **epic-sb-config-evaluation-config-comparator** — the decision tool (Piece 2); depends on
  the slot-test. Subsumes the backlog idea `idea-sb-transformational-sideboarding`.

## Reusable machinery (from code investigation, 2026-06-29)
- `analytics/subgroup.py` (`SubgroupSplit`) — already partitions an archetype's decks by a
  card-presence signature and computes matchup deltas; Piece 1 conditions this on a specific
  opponent + `board=side` and adds the stats.
- `analytics/match_results.py::compute_card_winrates` — per-`(card, board, opponent)` win/loss
  with engine dedup (the `dup`/`uniq_decks` cardinality guards).
- `analytics/card_value.py::card_value_matchup` — two-level empirical-Bayes per
  `(card, board, opponent)`; note it measures *lift-vs-prior*, NOT the *with-vs-without-in-
  matchup* contrast Piece 1 needs (different, more decision-relevant statistic).
- `advisory/positioning.py::score(deck, field)` — the field-weighted EV / Bayesian-MC engine
  Piece 2 generalizes to two configs.
- `advisory/sideboard.py` (`--smart` core+hedge) — the existing recommender Piece 2's
  transform/threat-swap modeling complements.
