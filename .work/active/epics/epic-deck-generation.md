---
id: epic-deck-generation
kind: epic
stage: done
tags: [generation]
parent: null
depends_on: [epic-advisory]
release_binding: v0.1.0
gate_origin: null
created: 2026-05-29
updated: 2026-06-14
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

Realized as **5 child features** (decomposed into 3 initially; the tuning #4 fork — see below — un-deferred the
per-card win-rate data and added a maindeck-aware sideboard rework as prerequisites, per Andrew's 2026-05-31
decision). `consensus` and `export` were independent (parallel wave 1); the tuning arc is a strict dependency
chain `per-card-value → sideboard-maindeck → tuning`, with `tuning` also depending on `consensus` (which
establishes the `generation/` module + `generate` CLI group).

### Child features (all done 2026-05-31)
- `epic-deck-generation-consensus` — mode 1: modal-card aggregation → legal exactly-60 + ≤15 de-duped list; establishes `generation/` + `generate` CLI group — depends on: `[]`
- `epic-deck-generation-export` — portable multi-target import-text exporter (Moxfield/Archidekt/MTGGoldfish/.dec) + deep-link; pure/offline — depends on: `[]`
- `epic-deck-generation-per-card-value` — **(net-new, un-deferred)** per-card + per-card×matchup win-rate analytics (`analytics/match_results.compute_card_winrates` + `analytics/card_value.py`), confidence-tiered, presence-correlational; `report cards` CLI; the rounds-bearing test fixture — depends on: `[]`
- `epic-deck-generation-sideboard-maindeck` — **(net-new)** reworked `advisory/sideboard.py` to be maindeck-aware: per-matchup OUT/IN plans + value-aware weighting, additive/gated (coverage preserved as the data-absent fallback) — depends on: `[epic-deck-generation-per-card-value]`
- `epic-deck-generation-tuning` — mode 2: optimize 60+15 vs the windowed field; reworked so per-card×matchup value is the **sole** maindeck-swap driver (no gameplan hollowing), coverage is audit-only; re-runs the maindeck-aware sideboard for the 15 + per-matchup plans; combined-legality guaranteed — depends on: `[epic-deck-generation-consensus, epic-deck-generation-sideboard-maindeck]`

### Deferred to a follow-up epic
- **Gap discovery (mode 3)** — archetype-gaps (high `S`, low share) + card-gaps. The card-gap half is now **unblocked** by `epic-deck-generation-per-card-value` (the per-card win-rate extension shipped); archetype-gaps + the discovery surface remain for a follow-up epic.
- **Goldfish-validated candidate validation** — depends on the `epic-goldfish-simulation` pillar (cross-pillar enhancement).
- **Joint main+sideboard ILP co-optimization** + **tuning adjacent-card discovery** ([[idea-tuning-adjacent-card-discovery]]) — deferred enhancements.

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


## Epic completion (2026-05-31)

All 5 child features are `stage: done`. The Deck Generation pillar (consensus + export + maindeck-aware
field-tuning) ships; only gap-discovery (mode 3) + goldfish-validated candidate-validation remain deferred.

**Arc summary** (resolves the held tuning #4 fork — Andrew chose to un-defer per-card win-rate data + make the
sideboard maindeck-aware): `per-card-value` (new per-card×matchup win-rate analytics + `card_value` +
`report cards`) → `sideboard-maindeck` (advisory SSOT rework: per-matchup OUT/IN plans, value-aware, additive
+ gated so rounds-less behavior is byte-identical) → `tuning` rework (per-card value the sole maindeck-swap
driver — no gameplan hollowing; coverage audit-only; combined legality; fixes the prior vacuous-test gap).

**Verification:** 961 tests green. Each feature got a fresh-context deep review (all Approve); a Phase-8
holistic completion review verified cross-feature contracts + ran the full chain end-to-end on the real
seeded DB (Dimir Tempo + Dimir Reanimator → legal 60/15, honest thin-data degradation, no fabricated edges).
Foundation-doc drift fixed (ARCHITECTURE.md generation/analytics/sideboard). Perf nit parked:
[[idea-tuning-sideboard-winrate-reuse]].

**OWED before this epic is *fully* signed off:** a true **cross-model** review of `src/legacy_engine/`
(generation/ + advisory/sideboard.py + analytics/card_value.py + match_results per-card). All reviews this
arc were same-model fresh-context Claude because **Codex was out of credits**. Re-run cross-model when credits
return.