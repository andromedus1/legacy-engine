---
id: epic-deck-generation
kind: epic
stage: implementing
tags: [generation]
parent: null
depends_on: [epic-advisory]
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

## Decomposition

Split by capability into 3 child features, scoped per the `## Design decisions` to **consensus + field-tuning
+ export** (gap-discovery / candidate-validation deferred to a follow-up epic — the former needs a per-card
win-rate data extension, the latter needs the goldfish pillar). `consensus` and `export` are independent
(parallel wave 1); `tuning` depends on `consensus` because consensus establishes the `generation/` module and
the `generate` CLI group, and tuning optimizes a consensus (or user) shell.

### Child features
- `epic-deck-generation-consensus` — mode 1: modal-card aggregation → legal exactly-60 + ≤15 de-duped list; establishes `generation/` + `generate` CLI group — depends on: `[]`
- `epic-deck-generation-export` — portable multi-target import-text exporter (Moxfield/Archidekt/MTGGoldfish/.dec) + deep-link; pure/offline — depends on: `[]`
- `epic-deck-generation-tuning` — mode 2: optimize 60+15 vs the windowed field (matchup×field-share + sideboard recommender), before/after positioning `S`, bimodal fallback — depends on: `[epic-deck-generation-consensus]`

### Deferred to a follow-up epic
- **Gap discovery (mode 3)** — archetype-gaps (high `S`, low share) + card-gaps; the card-gap half needs a new per-card win-rate match-results extension.
- **Goldfish-validated candidate validation** — depends on the `epic-goldfish-simulation` pillar (cross-pillar enhancement).

### Decomposition risks
- **Tuning is the largest feature** (~8–10 units: flex-slot ID, field-weighted equity, swap search, sideboard integration, before/after `S`, regime windowing, bimodal fallback). Its `/feature-design` pass should spawn child stories.
- **Consensus mode-1 reconciliation** (exactly-60 + main/side de-dupe from greedy modal fill) is the trickiest single unit — design it first in the consensus feature's pass.

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
