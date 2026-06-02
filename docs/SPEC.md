---
name: spec-legacy-engine
description: Read when scoping what to build — the capabilities, domain entities, and non-functional requirements of legacy-engine. Pairs with VISION (why) and ARCHITECTURE (how).
type: spec
kind: planning
summary: |
  Capability spec for legacy-engine. Defines the system's capabilities across four pillars, the core
  domain entities (Card, Decklist, Archetype, TournamentResult, MatchupCell, DeckDefinition,
  SideboardPackage), the MVP slice (ingestion + meta analytics + advisory), and non-functional
  requirements (reproducibility, version-stamped legality, sample-size confidence gating).
decisions:
  - "MVP capability set = card-data ingestion, tournament-results ingestion, archetype parsing, meta analytics (tier list / meta-% / matchup matrix / per-card win-rate), the advisory layer (positioning score + maindeck-aware sideboard recommender + what-to-play), and deck generation modes 1+2+export (consensus baseline, field-tuned decklist, Moxfield/Archidekt export)."
  - "Deferred capabilities = goldfish simulation (Deck Mechanics pillar); deck generation gap-discovery (mode 3) and goldfish-validated candidate-validation remain deferred until goldfish/ ships."
  - "Core entities: Card, Decklist (75-card maindeck+sideboard), Archetype, TournamentResult, MatchupCell, DeckDefinition (deck-as-data for sim), SideboardPackage, BanListSnapshot."
  - "Meta-% is computed under multiple definitions (raw entry count, top-cut presence, win-rate-weighted) and every report is labeled online/paper/blend — never a single unlabeled number."
  - "Matchup cells and any derived stat carry sample-size + confidence metadata; low-n cells (n<100) are flagged, reusing edh-engine's confidence-metadata pattern."
  - "Reproducibility is an NFR: deterministic given inputs+seed; all external data pre-fetched and cached; legality validated against a dated BanListSnapshot."
  - "Visualization is a cross-cutting Vega-Lite presentation layer (interactive HTML via vega-embed + static PNG via vl-convert), superseding the matplotlib charts; headline deliverable is a reusable per-deck dashboard composing meta-share/matchups/trends/positioning/consensus. Self-contained + offline; no server, no editing GUI."
created: 2026-05-29
updated: 2026-06-01
related:
  - {slug: docs/VISION.md, relationship: depends-on}
  - {slug: docs/ARCHITECTURE.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/parent.md, relationship: depends-on}
---

# Spec: legacy-engine

> *Why* this exists → [VISION.md](VISION.md). *How* it's built → [ARCHITECTURE.md](ARCHITECTURE.md).

## Capabilities

Grouped by pillar. **MVP** = built in the first arc; **Later** = deferred to a subsequent pillar.

### Pillar 1 — Meta & Performance
- **[MVP] Ingest card data** from Scryfall (oracle text, types, mana cost, CMC, colors, legality) — the card dimension, shared shape with edh-engine.
- **[MVP] Ingest tournament results** from the fbettega decklist cache (MTGO Challenges + Melee paper events) — the edhtop16 analog.
- **[MVP] Parse archetypes** — label each decklist into the community taxonomy via ported MTGOFormatData rules.
- **[MVP] Compute the metagame** — tier list, meta-% under multiple definitions (raw count / top-cut presence / win-rate-weighted), with explicit online/paper/blend labeling.
- **[MVP] Matchup matrix** — N×N archetype win-rate table computed from cache standings, with sample-size + confidence per cell.
- **[Later] Trends & regime shifts** — meta evolution across banned-list announcements (the Entomb-ban-style step change as a first-class view).

### Pillar 2 — Deck Mechanics (goldfish)
- **[Later] Deck-as-data model** + **mana solver** (port edh-engine's bipartite-matching `can_pay`) + **London-mulligan Monte Carlo** (straight London, NO free mull — the Legacy delta).
- **[Later] Goldfish clock** — per-deck turn-to-kill PMF; calibrate against published anchors (Oops All Spells 66% T1 / 76% T2 / 83% T3).
- **[Later] Meta-speed distribution** — per-archetype clock weighted by meta share, monthly; goldfish (upper bound) vs effective (⊗ Force-of-Will/Daze survival) clocks.
- **[Later] Cross-deck comparison** + engines-vs-payoffs role tagging (per-deck, not global).

### Pillar 3 — Deck Generation
- **[MVP] Consensus baseline** — modal-card aggregation over an archetype's in-window decks → legal exactly-60 + ≤15 de-duped list; `card_frequencies` primitive.
- **[MVP] Field-tuning (mode 2)** — greedy maindeck-flex swaps driven by field-weighted per-card×matchup value; no-signal fallback; maindeck-aware sideboard + per-matchup OUT/IN plans.
- **[MVP] Export** — portable multi-target import text (Moxfield/Archidekt/MTGGoldfish/`.dec`); pure offline.
- **[Later] Gap discovery (mode 3)** — data-driven identification of under-explored cards/shells; depends on `card_value` (now unblocked) + goldfish validation.
- **[Later] Goldfish-validated candidate validation** — simulate candidates against projected field; depends on `goldfish/` pillar.

### Pillar 4 — Meta Attack / Advisory *(differentiator)*
- **[MVP] Meta-positioning score** — `Σ field_share(arch) × winrate(deck vs arch)` = expected WR vs the weighted field; user can supply a custom expected local field.
- **[MVP] Sideboard recommender** — hoser→target bipartite graph solved as weighted set-cover over the expected field; models the anti-hate second order (Veil/Defense Grid/Force of Vigor point at hate cards).
- **[MVP] "What to play" advisor** — proactive-vs-reactive and best-deck-vs-best-metagame-call framing over the current field.

### Cross-cutting — Visualization & Reporting
- **Per-deck dashboard** — one self-contained page composing meta-share, the matchup spread (adaptive per-cell ban-aware matrix), trends across ban-regimes, positioning (best-call vs best-deck), and the consensus 60+15 list + primer, for any archetype.
- **Composable viz platform** — a Vega-Lite spec layer (curated sub-schema + structural validator + canonical theme + 12-col tile/layout); any command emits composable tiles. Supersedes the matplotlib chart export.
- **Dual output** — interactive self-contained HTML (vega-embed from CDN) + static PNG (vl-convert, no browser). Every chart carries the same confidence/labels as the text reports.

## Domain Entities (the key nouns)

| Entity | What it is | Notes |
|--------|-----------|-------|
| **Card** | A Magic card | Scryfall-resolved: name, cost, CMC, colors, types, oracle text, legality. Tagged with `staple_role` and `is_free_spell` (Legacy-specific). |
| **Decklist** | A tournament 75 | 60+ maindeck, 0–15 sideboard; from a TournamentResult. Validated against a BanListSnapshot. |
| **Archetype** | A named deck strategy | e.g. "Dimir Tempo", "Sneak & Show". Assigned by the archetype parser; carries pillar/cluster, fair-axis ordinal. |
| **TournamentResult** | One event's records | Event metadata (online/paper, date, size), per-deck finish position, standings/rounds where available. |
| **MatchupCell** | (archetype_a, archetype_b) → record | `{winrate, sample_n, ci, window}`; confidence-gated. |
| **BanListSnapshot** | Legality as of a date | Blacklist of banned names + `banned_date` + `ban_reason` + category predicates; enables historical validation. |
| **DeckDefinition** | Deck-as-data for sim | *(Later)* card list + tagged roles (payoff/enabler/engine) + combo line + goldfish clock + confidence metadata. Mirrors edh-engine's YAML model. |
| **SideboardPackage** | A recommended 15 | *(Advisory)* set of hosers with edges to the archetypes/hate-cards they attack, plus coverage score vs a field. |
| **DeckDashboard** | A composed per-deck page | *(Viz)* a set of Vega-Lite tiles (meta-share, matchup spread, trends, positioning, consensus + primer) laid out on a 12-col grid and rendered to self-contained HTML + PNG. |

## Non-Functional Requirements

- **Reproducibility** — deterministic given inputs + seed; all external data pre-fetched and cached; the engine makes no network calls at analysis time (mirrors edh-engine).
- **Version-stamped legality** — every legality check resolves against a dated `BanListSnapshot`, so a 2024 deck that legally ran Psychic Frog validates correctly. Banned-list data refreshed ~quarterly.
- **Confidence-gated stats** — matchup cells and derived metrics carry sample size + confidence; low-n (n<100) flagged by default. Reuses edh-engine's confidence-metadata pattern.
- **Source transparency** — every meta-% and matchup figure is labeled with its source, window, and online/paper/blend basis. No unlabeled headline numbers.
- **Resilience** — ingestion tolerates a single bad deck/event (catch, log, continue); mirror the community cache locally (it's fragile / community-run).
- **Portability** — local file storage, no DB or server required for MVP (storage revisited at /architecture if query patterns demand it).
- **Self-contained, offline viz output** — visualization output is local and needs no server: interactive HTML embeds `vega-embed` from CDN and opens directly in a browser; static PNG via `vl-convert` needs no browser/Chrome at all.

## What's explicitly out of scope (MVP)
Goldfish simulation, deck generation gap-discovery (mode 3) and goldfish-validated candidate-validation, full rules-correct game engine, real-time event tooling, non-Legacy formats, and any interactive deck-building / web-app GUI (read-only self-contained HTML dashboards from the `viz/` layer are in scope; an editing UI is not). See VISION non-goals. Note: deck generation modes 1+2+export are built; only the simulation-dependent modes remain deferred.
