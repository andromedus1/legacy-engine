---
id: epic-deck-generation
kind: epic
stage: drafting
tags: [generation]
parent: null
depends_on: [epic-advisory, epic-goldfish-simulation]
release_binding: null
gate_origin: null
created: 2026-05-29
updated: 2026-05-30
---

# Deck Generation (deferred pillar)

## Brief

The Deck Generation pillar — **deferred**, the furthest-out capability. Find under-explored shells and
tune existing builds against the (current or projected) meta: the knowledge layer identifies structural
gaps, deck-mechanics knowledge constrains the build (mana, roles, consistency floor), and the matchup +
goldfish layers validate candidates. Analytically guided, not brute force.

Brief gate satisfied (2026-05-30): `docs/briefs/deck-generation-and-moxfield.md` now covers both the
Moxfield surfacing path and the generation/tuning approach over our existing advisory layers. Note the
brief's finding that the **consensus-baseline + Moxfield export sub-arc can ship independently** (pure data
aggregation, no goldfish, no advisory-heuristic dependency), while the **tune/discover modes depend_on** the
three advisory-improvement items filed this session — `/epic-design` should likely split the epic along that
line and may relax the hard `epic-goldfish-simulation` dependency (goldfish-validation is a later cross-pillar
enhancement, not a blocker for consensus+export+field-tuning).

## Research briefs
- `docs/briefs/deck-generation-and-moxfield.md` — **(written 2026-05-30)** Moxfield integration (no official
  API → export-as-import, support@moxfield.com for sanctioned reads) + generation modes (consensus baseline →
  field-tuning → gap discovery) consuming meta-share / matchup / positioning / sideboard, with the advisory
  heuristic gaps as hard prerequisites for the tuning modes.
- `docs/briefs/advisory-methods.md` — the positioning / matchup / sideboard methods the generator orchestrates.

## Foundation references
- `docs/ARCHITECTURE.md` — the deferred `generation/` module (consumes advisory + goldfish outputs).
- `docs/VISION.md` — Deck Generation pillar.

## Anticipated child features
(provisional — real decomposition after the generation brief + `/epic-design`)
- Meta-gap discovery (structural gaps in the archetype/card space)
- Constrained build search (mana/role/consistency constraints)
- Candidate validation (positioning + goldfish clock + consistency floor)

## Design decisions
Captured via `/epic-design --only-questions` (interactive, 2026-05-30). Fixed inputs for the full
decomposition + per-feature design passes — autopilot and `/feature-design` inherit these and should not
re-decide.

- **Goldfish dependency → RELAX.** Rewrite `depends_on` to drop `epic-goldfish-simulation`; keep only
  `epic-advisory` (done). The advisory-heuristic prerequisites from the brief
  (`improve-whattoplay-proactivity-threat-signal`, `improve-positioning-pbest-uneven-sample`,
  `improve-sideboard-realdata-quality`) all landed in `epic-advisory-hardening` (done), so modes 1–2 are
  unblocked now. Goldfish-validation of candidates is a later cross-pillar enhancement, not a blocker
  (per brief §2.5).
- **Mode scope → Consensus + field-tuning + export; DEFER gap-discovery.** This epic decomposes into
  (1) consensus baseline (mode 1, pure aggregation, reconciles to a legal exactly-60 + de-duped list),
  (2) field-tuning (mode 2, the core — optimize 60+15 vs the windowed field via matchup×field-share, run
  the sideboard recommender, report before/after positioning `S`), and (3) the portable export surface.
  **Gap discovery (mode 3) is deferred to a follow-up epic** — its card-gap half needs a new per-card
  win-rate match-results extension that doesn't exist yet, and its output is the most speculative. (Update
  the "Anticipated child features" sketch accordingly during decomposition: gap-discovery / candidate-
  validation move out of this epic's realized scope.)
- **Export breadth → Portable multi-target text.** One exporter emitting the standard
  `<qty> <Card Name>` + `Sideboard` text that imports into Moxfield, Archidekt, MTGGoldfish, `.dec`, etc.,
  plus an optional Moxfield deep-link/copy block. Pure, offline, **zero network calls**, reuses the existing
  decklist representation. **No native push, no sanctioned Moxfield read in this epic** (both post-MVP /
  product decisions per brief §1.2).
- **Generation field default → Windowed latest ban-regime.** Default the generation corpus to the current
  post-latest-ban regime window (reuse the `trends` regime windowing); the user may override the window.
  Bimodal-coverage fallback applies: where matchup-n < 30 the tuner falls back to consensus + legality and
  says so (no fabricated tuned edge). Always `validate_deck` against the as-of-date ban snapshot.
