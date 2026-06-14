---
name: spec-legacy-engine
description: Read when scoping what to build — the capabilities, domain entities, and non-functional requirements of legacy-engine. Pairs with VISION (why) and ARCHITECTURE (how).
type: spec
kind: planning
summary: |
  Capability spec for legacy-engine. Defines the system's capabilities across four pillars, the core
  domain entities (Card, Decklist, Archetype, Variant, TournamentResult, MatchupCell, InteractionFacts,
  Player, Venue, SideboardPackage, Inventory, UserDeck), the built capability set (ingestion + meta
  analytics + advisory + collection/prices/players/variant/venue/speculation subsystems + all deck
  generation modes), and non-functional requirements (reproducibility, version-stamped legality,
  sample-size confidence gating, honest-degrade policy).
decisions:
  - "Built capability set = card-data ingestion, prices ingestion, tournament-results ingestion, archetype parsing + variant tagging, meta analytics (tier list / meta-% / matchup matrix / per-card win-rate / subgroup split / venue divergence / new-card speculation), the advisory layer (positioning + maindeck-aware sideboard + what-to-play + field-read report + collection-aware acquire + refresh + primer), player-strength + history, and all deck generation modes 1+2+3+export (consensus baseline with --variant/--players/--strong, field-tuned decklist, gap-discovery, deck doctor)."
  - "Deferred capabilities = goldfish simulation (Deck Mechanics pillar); goldfish-validated candidate-validation remains deferred until goldfish/ ships. Gap-discovery (mode 3) itself is built."
  - "Core entities: Card, Decklist (75-card maindeck+sideboard), Archetype, Variant (sub-archetype tag), TournamentResult, MatchupCell, InteractionFacts (pure card interaction classifier), Player (resolved identity + strength record), Venue (online/paper), DeckDefinition (deck-as-data for sim — later), SideboardPackage, BanListSnapshot, Inventory, UserDeck."
  - "Meta-% is computed under multiple definitions (raw entry count, top-cut presence, win-rate-weighted) and every report is labeled online/paper/blend — never a single unlabeled number."
  - "Matchup cells and any derived stat carry sample-size + confidence metadata; low-n cells (n<100) are flagged, reusing edh-engine's confidence-metadata pattern."
  - "Reproducibility is an NFR: deterministic given inputs+seed; all external data pre-fetched and cached; legality validated against a dated BanListSnapshot."
  - "Visualization is a cross-cutting Vega-Lite presentation layer (interactive HTML via vega-embed + static PNG via vl-convert); headline deliverable is a reusable per-deck dashboard composing meta-share/matchups/trends/positioning/consensus. Self-contained + offline; no server, no editing GUI."
  - "HONEST-DEGRADE NFR: thin/absent signal surfaces a labeled banner or degraded flag with a named reason. No silent zeros, no fabricated numbers. Applies in the advisory window (thin-regime banner), sideboard/primer (degraded=True note), speculation (PRE-DATA FORECAST label), prices (all_null flag), venue divergence (labeled)."
  - "PRICES + ACQUISITION: seed prices + report prices + advise acquire give the user a priced buy list ranked by field-relevance × archetype-relevance; PriceQuote.all_null is the honest-null signal."
created: 2026-05-29
updated: 2026-06-13
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
- **[Built] Ingest card data** from Scryfall (oracle text, types, mana cost, CMC, colors, legality) — the card dimension, shared shape with edh-engine.
- **[Built] Ingest card prices** from Scryfall default_cards bulk (per-printing USD prices → `card_prices` DuckDB table; `PriceQuote.all_null` is the honest-null signal).
- **[Built] Ingest tournament results** from the fbettega decklist cache (MTGO Challenges + Melee paper events) — the edhtop16 analog.
- **[Built] Parse archetypes** — label each decklist into the community taxonomy via ported MTGOFormatData rules.
- **[Built] Sub-archetype variant tagging** — classify each deck's variant (e.g. "Bauble") by card-presence registry; drives `report meta --by-variant` and `generate consensus --variant`.
- **[Built] Compute the metagame** — tier list, meta-% under multiple definitions (raw count / top-cut presence / win-rate-weighted), with explicit online/paper/blend labeling; venue divergence (online vs paper share spread via `report meta --venues`).
- **[Built] Matchup matrix** — N×N archetype win-rate table computed from cache standings, with sample-size + confidence per cell.
- **[Built] Trends & regime shifts** — meta evolution across banned-list announcements (the Entomb-ban-style step change as a first-class view).
- **[Built] Sub-archetype split** — `report subgroup` partitions an archetype's pool by card-presence signature and shows per-subgroup matchup deltas and card divergence.
- **[Built] New-card speculation** — `report new-cards` + `report speculate` forecast new/pre-data cards using `interaction_facts` + role-filtered analogues; always labeled `PRE-DATA FORECAST`.
- **[Built] Player-strength scoring** — `identify suggest|strong|track`: alias resolution, confidence-gated strength records (min events + tier + win-rate), per-regime archetype history.

### Pillar 2 — Deck Mechanics (goldfish)
- **[Later] Deck-as-data model** + **mana solver** (port edh-engine's bipartite-matching `can_pay`) + **London-mulligan Monte Carlo** (straight London, NO free mull — the Legacy delta).
- **[Later] Goldfish clock** — per-deck turn-to-kill PMF; calibrate against published anchors (Oops All Spells 66% T1 / 76% T2 / 83% T3).
- **[Later] Meta-speed distribution** — per-archetype clock weighted by meta share, monthly; goldfish (upper bound) vs effective (⊗ Force-of-Will/Daze survival) clocks.
- **[Later] Cross-deck comparison** + engines-vs-payoffs role tagging (per-deck, not global).

### Pillar 3 — Deck Generation
- **[Built] Consensus baseline** — modal-card aggregation over an archetype's in-window decks → legal exactly-60 + ≤15 de-duped list; `card_frequencies` primitive; `--variant/--players/--strong` pool filters.
- **[Built] Field-tuning (mode 2)** — greedy maindeck-flex swaps driven by field-weighted per-card×matchup value; no-signal fallback; maindeck-aware sideboard + per-matchup OUT/IN plans.
- **[Built] Export** — portable multi-target import text (Moxfield/Archidekt/MTGGoldfish/`.dec`); pure offline.
- **[Built] Gap discovery (mode 3)** — data-driven identification of under-explored cards/shells via `generate tune --discover` + adjacent-card PMI scoring.
- **[Built] Deck doctor** — `generate doctor` diagnoses a deck against the current field: flags stale includes, coverage gaps, and suggests targeted swaps.
- **[Later] Goldfish-validated candidate validation** — simulate candidates against projected field; depends on `goldfish/` pillar.

### Pillar 4 — Meta Attack / Advisory *(differentiator)*
- **[Built] Meta-positioning score** — `Σ field_share(arch) × winrate(deck vs arch)` = expected WR vs the weighted field; user can supply a custom expected local field.
- **[Built] Sideboard recommender** — hoser→target bipartite graph solved as weighted set-cover over the expected field; models the anti-hate second order; collection-aware (`--collection`, `--owned-only`).
- **[Built] "What to play" advisor** — proactive-vs-reactive and best-deck-vs-best-metagame-call framing over the current field.
- **[Built] Collection-aware acquire plan** — `advise acquire` ranks priced buys by field-relevance × archetype-relevance; budget filter; redundancy/over-quantity flags.
- **[Built] Deck refresh** — `advise refresh` runs a full per-venue tuning pass (field-tuned maindeck + sideboard + primer); loudly labels thin/no-data matchups.
- **[Built] Matchup primer** — plain-speak per-matchup OUT/IN guide generated from the sideboard plan; `degraded=True` matchups are labeled reasoning-based, never fabricate numbers.

### Cross-cutting — Visualization & Reporting
- **Per-deck dashboard** — one self-contained page composing meta-share, the matchup spread (adaptive per-cell ban-aware matrix), trends across ban-regimes, positioning (best-call vs best-deck), and the consensus 60+15 list + primer, for any archetype.
- **Composable viz platform** — a Vega-Lite spec layer (hand-built spec builders + canonical theme via strip-and-inject + 12-col tile/layout; spec validity checked test-time via the real Vega-Lite compiler); any command emits composable tiles. Replaces the matplotlib chart export.
- **Dual output** — interactive self-contained HTML (vega-embed from CDN) + static PNG (vl-convert, no browser). Every chart carries the same confidence/labels as the text reports.

## Domain Entities (the key nouns)

| Entity | What it is | Notes |
|--------|-----------|-------|
| **Card** | A Magic card | Scryfall-resolved: name, cost, CMC, colors, types, oracle text, legality. Tagged with `staple_role` and `is_free_spell` (Legacy-specific). |
| **Decklist** | A tournament 75 | 60+ maindeck, 0–15 sideboard; from a TournamentResult. Validated against a BanListSnapshot. |
| **Archetype** | A named deck strategy | e.g. "Dimir Tempo", "Sneak & Show". Assigned by the archetype parser; carries pillar/cluster, fair-axis ordinal. |
| **Variant** | A sub-archetype tag | e.g. "Bauble" for Dimir Tempo builds running Asmoranomardicadaistinaculdacar. Assigned by the variant registry; drives pool filters and report splits. |
| **TournamentResult** | One event's records | Event metadata (online/paper, date, size), per-deck finish position, standings/rounds where available. |
| **MatchupCell** | (archetype_a, archetype_b) → record | `{winrate, sample_n, ci, window}`; confidence-gated. |
| **BanListSnapshot** | Legality as of a date | Blacklist of banned names + `banned_date` + `ban_reason` + category predicates; enables historical validation. |
| **InteractionFacts** | A card's interaction classification | Pure function of card oracle text: graveyard reliance, counter-magic density, speed signals, free-spell flag. Consumed by speculation and vulnerability tagger; no DB dependency. |
| **Player** | A resolved player identity | Canonical `player_id` after alias resolution; carries strength record (`events`, `win_rate_shrunk`, confidence `tier`) over a window. |
| **Venue** | Online / paper provenance | Derived from fbettega source dir + URI host; used for per-venue meta-share splits and cross-venue divergence. |
| **DeckDefinition** | Deck-as-data for sim | *(Later)* card list + tagged roles (payoff/enabler/engine) + combo line + goldfish clock + confidence metadata. Mirrors edh-engine's YAML model. |
| **SideboardPackage** | A recommended 15 | *(Advisory)* set of hosers with edges to the archetypes/hate-cards they attack, plus coverage score vs a field; carries per-matchup `MatchupPlan` (OUT/IN swaps). |
| **DeckDashboard** | A composed per-deck page | *(Viz)* a set of Vega-Lite tiles (meta-share, matchup spread, trends, positioning, consensus + primer) laid out on a 12-col grid and rendered to self-contained HTML + PNG. |
| **Inventory** | The user's owned cards | *(Personal)* owned card → quantity (+ printing/condition). Local, single-user now; schema designed cloud-ready for a later hosted surface. Makes advice buildable from what you actually own. |
| **UserDeck** | The user's own deck (a variant) | *(Personal)* a named, **versioned** 75 the user owns and plays — distinct from the inferred `Archetype`; cards may be allocated from `Inventory` (a deck vs the free binder). |

## Non-Functional Requirements

- **Reproducibility** — deterministic given inputs + seed; all external data pre-fetched and cached; the engine makes no network calls at analysis time (mirrors edh-engine).
- **Version-stamped legality** — every legality check resolves against a dated `BanListSnapshot`, so a 2024 deck that legally ran Psychic Frog validates correctly. Banned-list data refreshed ~quarterly.
- **Confidence-gated stats** — matchup cells and derived metrics carry sample size + confidence; low-n (n<100) flagged by default. Reuses edh-engine's confidence-metadata pattern.
- **Source transparency** — every meta-% and matchup figure is labeled with its source, window, and online/paper/blend basis. No unlabeled headline numbers.
- **Resilience** — ingestion tolerates a single bad deck/event (catch, log, continue); mirror the community cache locally (it's fragile / community-run).
- **Portability** — local file storage, no DB or server required for MVP (storage revisited at /architecture if query patterns demand it).
- **Self-contained, offline viz output** — visualization output is local and needs no server: interactive HTML embeds `vega-embed` from CDN and opens directly in a browser; static PNG via `vl-convert` needs no browser/Chrome at all.

## What's explicitly out of scope
Goldfish simulation and goldfish-validated candidate-validation (the `goldfish/` deferred pillar), full rules-correct game engine, real-time event tooling, non-Legacy formats, and an interactive deck-building *editor* GUI (read-only self-contained HTML dashboards from the `viz/` layer are in scope; an editing UI is not). A **hosted web-app GUI is deferred pending its own research**. The user's personal collection + deck inventory is in scope as a local, single-user capability (schema designed cloud-ready for a later hosted surface). See VISION non-goals. Note: gap-discovery (mode 3) is built; only goldfish-validated candidate-validation remains deferred.
