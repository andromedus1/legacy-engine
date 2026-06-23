# legacy-engine

A **Magic: The Gathering Legacy-format analytics & advisory engine**. It answers, with data: *"What is the meta, how do I attack it, and how do I tune my deck?"*

legacy-engine is rigorous and reproducible: it ingests real tournament results, labels every
deck under a consistent archetype taxonomy, and computes the metagame, matchup matrix, and field-aware
advice on top — every number labeled, sample-gated, and traceable to its source.

It is the sibling of **edh-engine** (which does the same for cEDH), reusing that platform's
three-data-layer architecture adapted to a 1v1, best-of-3, sideboarded, 60-card eternal format.

## The four pillars

All four draw from the same data layers; they answer different questions.

1. **Meta & Performance** — what's being played and how it performs. Meta-share computed three labeled
   ways (raw entry / top-cut presence / win-rate-weighted), matchup matrices with confidence intervals,
   archetype trends across banned-list regimes, online-vs-paper splits.
2. **Deck Mechanics** *(planned)* — how a deck functions internally: goldfish speed, consistency,
   London-mulligan modeling, and a format meta-speed distribution.
3. **Deck Generation** — consensus baseline (mode 1) + field-tuning (mode 2) + gap-discovery (mode 3)
   + export are built; only goldfish-validated candidate-validation is deferred pending the `goldfish/` pillar.
4. **Meta Attack / Advisory** *(the Legacy-specific differentiator)* — *how to attack the field*: a
   meta-positioning score (expected win rate vs the weighted field), a sideboard recommender, and a
   what-to-play advisor (proactive/reactive, best-deck vs best-call).

See [`docs/VISION.md`](docs/VISION.md) for the full vision and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
for how it's built.

## Status

The **observed-data spine, meta analytics, deck generation, the advisory differentiator, and a
local visualization layer** are built and tested (2242 passing tests). Only the goldfish-simulation
pillar remains deferred:

| Capability | State |
|---|---|
| Scryfall card dimension + derivations | ✅ built |
| Card prices (per-printing USD; `seed prices`) | ✅ built |
| fbettega tournament ingestion (DuckDB) | ✅ built |
| Archetype classifier (ported MTGOArchetypeParser) | ✅ built |
| Sub-archetype variant tagging (`report meta --by-variant`, `generate consensus --variant`) | ✅ built |
| Meta-share (3 definitions, online/paper; venue split `--venues`; sub-archetype split `report subgroup`) | ✅ built |
| Matchup matrix (Wilson/Jeffreys CI + Beta-Binomial shrinkage + confidence tiers) | ✅ built |
| Meta trends across ban-list regimes (version-stamped; `--movers N` biggest-movers digest) | ✅ built |
| Ban-affectedness report (`report affectedness` — which bans drove an archetype's valid_since) | ✅ built |
| Head-to-head matchup lookup (`report matchups --a/--b` — single directed cell + Wilson CI) | ✅ built |
| Regime-aware analytics & advisory (adaptive per-cell ban windowing) | ✅ built |
| Meta-positioning score (Bayesian Monte-Carlo, custom field, best-call vs best-deck; `--list-granular` S_granular overlay) | ✅ built |
| Sideboard recommender (weighted max-coverage: PuLP/CBC ILP + greedy + anti-hate; collection-aware; considering/bubble pool) | ✅ built |
| Two-stage core+hedge sideboard (`advise sideboard --smart`) — natural-budget dedicated core (no padding, may return <15) + diversity-preferring hedge in the flex slots; commit/insurance labels + coverage curve + uncovered-field tail | ✅ built |
| What-to-play (proactivity, vulnerability tags incl. ramp, hate-equity, best-deck/best-call) | ✅ built |
| Standalone field read (`advise field` — field composition + vulnerability/hate-equity; no deck required) | ✅ built |
| Provenance-filtered advisory (`--provenance online|paper` on all advise leaves + report matchups/meta) | ✅ built |
| Field Read & Deck Recommendation report (the `advise report` surface; `--venues` cross-venue) | ✅ built |
| Deck refresh (`advise refresh` — per-venue tuned maindeck + sideboard + primer) | ✅ built |
| Acquisition plan (`advise acquire` — ranked priced buy list) | ✅ built |
| Per-card win-rate analytics (`report cards`) | ✅ built |
| New-card speculation (`report new-cards`, `report speculate` — PRE-DATA FORECAST) | ✅ built |
| Prices report (`report prices`) | ✅ built |
| Player-strength scoring + archetype history (`identify suggest|strong|track`) | ✅ built |
| Gap discovery — under-explored archetypes (`report gaps`) + adjacent-card discovery (`generate tune --discover`) | ✅ built |
| Consensus baseline decklist (`generate consensus`; `--variant/--players/--strong` pool filters) | ✅ built |
| Field-tuned decklist (`generate tune`) + Deck doctor (`generate doctor`) | ✅ built |
| Decklist export (`export deck`) | ✅ built |
| Visualization — per-deck HTML dashboards + meta/matchup/trends/tier charts (Vega-Lite → HTML + PNG) | ✅ built |
| Personal collection + deck inventory (`collection` + `deck` groups; `--my-deck`) | ✅ built |
| Goldfish simulation + goldfish-validated candidate-validation | 📋 deferred pillar |

## Architecture in one breath

Three data layers feed the analytical pillars:

- **Observed** — fbettega tournament cache, Scryfall cards, banned-list snapshots, archetype labels.
- **Synthetic** *(deferred)* — goldfish simulation (speed, consistency).
- **Generated** — positioning, sideboard packages, eventual deck candidates.

Raw mirrored JSON (under `data/`, git-ignored) is the **reproducible source of truth**; an embedded,
rebuildable **DuckDB** (`data/legacy.duckdb`) is the analytical layer for the matchup-matrix and
meta-share join workloads. The engine makes **no network calls at analysis time** — all external data
is fetched once and mirrored. Every derived stat carries a confidence tier (`established` / `evolving` /
`speculative`) and a sample size, and meta-% is never emitted unlabeled.

## Install

Requires **Python 3.11+**.

```bash
git clone git@github.com:andromedus1/legacy-engine.git
cd legacy-engine
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Usage

The CLI is `legacy-engine`, organized into nested command groups.

```bash
# Seed the local data layer (fetch + mirror, then load DuckDB)
legacy-engine seed cards        # Scryfall oracle bulk → card index
legacy-engine seed cache        # mirror + ingest the fbettega tournament cache
legacy-engine seed rules        # vendor the MTGOFormatData archetype rules
legacy-engine seed banlist      # banned-list snapshots
legacy-engine seed prices       # Scryfall default_cards bulk → per-printing prices

# Incremental refresh (release-aware)
legacy-engine refresh all       # tournament cache + rules (+ --prices to include prices bulk)
legacy-engine refresh cards     # release-aware diff refresh of the card universe

# Label every ingested deck with an archetype
legacy-engine label

# Meta & performance reports
legacy-engine report meta       # meta-share (raw / top-cut / win-rate-weighted; online vs paper)
legacy-engine report meta --venues online,paper   # cross-venue divergence comparison
legacy-engine report meta --by-variant            # split by sub-archetype variant tag
legacy-engine report matchups   # archetype matchup matrix with confidence intervals
legacy-engine report tiers      # S/A/B tier list over meta-share
legacy-engine report trends     # meta-share evolution across ban-list regimes
legacy-engine report trends     --movers 5       # + biggest-movers digest between the two latest regimes
legacy-engine report matchups   --a "Dimir Tempo" --b "Sneak & Show"  # single directed cell + CI
legacy-engine report affectedness --archetype "Dimir Tempo"  # which bans drove valid_since
legacy-engine report gaps       # under-explored archetypes (high positioning S, low meta-share)
legacy-engine report subgroup --archetype "Dimir Tempo"  # sub-archetype split + matchup deltas
legacy-engine report variants --archetype "Dimir Tempo"  # registered variants + meta share within the parent archetype
legacy-engine report new-cards  # card names added in the latest refresh-cards ingest diff
legacy-engine report speculate "Psychic Frog"     # PRE-DATA FORECAST for a specific card
legacy-engine report prices "Force of Will"       # per-printing USD prices for a card
# report/advise commands take ban-regime windowing: --since / --until / --regime / --all-time

# Per-card win-rate report
legacy-engine report cards                       # per-card presence-correlational win-rate (vs field)

# Meta attack / advisory — "how to attack the field"
legacy-engine advise positioning --deck my.txt   # expected WR vs the weighted field (P(best) ranking)
legacy-engine advise positioning --deck my.txt --list-granular  # + list-granular S_granular overlay
legacy-engine advise positioning --deck my.txt --provenance paper  # paper-only field + matrix
legacy-engine advise sideboard   --deck my.txt   # recommended 15-card sideboard (ILP + greedy "why")
legacy-engine advise sideboard   --deck my.txt --smart  # core+hedge: dedicated core (no 4/4/4 padding) + diversity hedge
legacy-engine advise whattoplay  --deck my.txt   # proactivity, vulnerability tags, best-deck/best-call
legacy-engine advise field                        # field composition + vulnerability profile (no deck)
legacy-engine advise field --provenance online    # online-only field read
legacy-engine advise report      --deck my.txt   # full Field Read & Deck Recommendation + audit trail
legacy-engine advise report      --deck my.txt --venues online,paper  # cross-venue report
legacy-engine advise refresh     --deck my.txt   # per-venue tuned maindeck + sideboard + primer
legacy-engine advise acquire     --collection binder.txt --archetype "Dimir Tempo"  # priced buy list
# --my-deck NAME loads a saved UserDeck; --field FILE supplies a custom field
# --collection FILE enables owned/acquire annotations; --budget N caps the acquire plan
# --provenance online|paper is available on all advise leaves (and report matchups/meta)

# Player identity and strength
legacy-engine identify suggest          # candidate alias clusters (identity dedup)
legacy-engine identify strong           # players clearing the strength gate in the current regime
legacy-engine identify track "bosh95"  # per-regime archetype history for a player

# Deck generation
legacy-engine generate consensus --archetype "Dimir Tempo"           # consensus baseline (mode 1)
legacy-engine generate consensus --archetype "Dimir Tempo" --variant "Bauble"  # variant-scoped pool
legacy-engine generate consensus --archetype "Dimir Tempo" --strong  # strong-player pool only
legacy-engine generate tune      --archetype "Dimir Tempo" --deck my.txt  # field-tuned list (mode 2)
legacy-engine generate tune      --deck my.txt --discover    # + adjacent swap-in candidates (mode 3)
legacy-engine generate doctor    --deck my.txt               # diagnose stale/coverage gaps

# Decklist export
legacy-engine export deck --deck my.txt          # format for Moxfield / Archidekt / MTGGoldfish import

# Personal collection + deck management
legacy-engine collection import --file binder.txt  # import card inventory
legacy-engine collection show                       # show inventory (--free-only / --card NAME)
legacy-engine collection status                     # allocation summary
legacy-engine collection rebuild                    # rebuild DuckDB from JSON SSOT
legacy-engine deck save --name "my Dimir Tempo" --file my.txt  # save / version a deck
legacy-engine deck load --name "my Dimir Tempo"                # load current version
legacy-engine deck buildable --name "my Dimir Tempo"           # check what you can build

# Visualization — render dashboards & charts (Vega-Lite → interactive HTML or static PNG; no Chrome/Node)
legacy-engine viz deck "Dimir Tempo" --out dash.html   # per-deck attack-focused dashboard
legacy-engine viz meta --out meta.html           # also: viz matchups | viz trends | viz tiers (.html or .png)
```

### Deck-prep tooling (`scripts/`)

Standalone analysis helpers that sit alongside the CLI:

```bash
# Overlay a decklist against a cohort's per-card copy-count distribution (HTML).
# Prototype for the planned deck-doctor visualization (see .work/ feature-deck-doctor-viz).
.venv/bin/python scripts/deck_vs_cohort_viz.py \
  --deck decks/dimir-tempo-current.txt --archetype "Dimir Tempo" \
  --require "Flow State>=1" --require "Nethergoyf=3" \
  --out decks/dimir-tempo-vs-cohort.html
```

```bash
# Render the meta-landscape report (deck-agnostic): composition + trends + movers,
# and best-deck/best-call positioning over time. Optionally also emit a deck's matchups.
.venv/bin/python scripts/meta_view.py --out decks/meta.html \
  --deck "Dimir Tempo" --matchups-out decks/dimir-tempo-matchups.html
```

`meta_view.py` is the **meta view** (where the field is, how it's moving, what's
best-positioned over time); `deck_vs_cohort_viz.py` is the **my-deck view** (how one
75 compares to the field). Both render to self-contained inline SVG (no Chrome / Node /
CDN) and carry confidence tiers honestly. `meta_view.py` knobs: `--bands-top`,
`--pos-top`, `--ema-span`, `--last-months`.

The cohort tool renders, per card, your count vs the cohort's 0x/1x/2x/3x/4x histogram with
inclusion%, on-mode / off-distribution / missing tags, grouped by card type, plus a
confidence-tier banner. `--require "Card=N"`/`"Card>=N"` carves a sub-cohort; the
window defaults to the current ban regime (override with `--since`).

Each leaf takes `-v/--verbose`; all `advise` leaves and `report matchups|meta` take
`--provenance [online|paper|all]` and a `--db` path. Every emitted number is labeled with its
definition/basis, sample size, and confidence tier; advisory output carries a heuristic-vs-data-driven
audit trail. Absent/thin signal is always labeled (never a silent zero). Commands not yet implemented
fail loudly rather than returning empty results.

## Development

```bash
.venv/bin/python -m pytest -q     # run the test suite
```

This project is built with a research-grounded, substrate-driven workflow:

- **`docs/`** — the knowledge layer: `VISION.md`, `SPEC.md`, `ARCHITECTURE.md`, `PRINCIPLES.md`, and
  domain briefs under `docs/briefs/`. A two-layer knowledge index (`docs/knowledge-index*.yaml`) is
  generated from doc frontmatter.
- **`.work/`** — the work substrate: epics → features → stories as markdown items with YAML
  frontmatter, queried via `.work/bin/work-view`. Work flows design → implement → review per item.
- Every feature ships with tests; docs describe present intent (rolling-foundation).

## Layout

```
src/legacy_engine/
  ingestion/   # Scryfall (oracle + prices bulk), fbettega cache, rules, banlist, releases, DuckDB store
  archetype/   # rules loader, matcher (ported Detect), colors, labeler, variants
  analytics/   # match_results, matchup (adaptive ban-windowing), metashare, trends, card_value,
               #   affectedness, subgroup, venue, speculation
               #   players/  (identity, strength, history)
  advisory/    # field, positioning, sideboard, whattoplay, report, gaps, window,
               #   collection, acquire, primer, refresh
  generation/  # consensus, export, tuning, discovery (modes 1+2+3), card_distribution, models
               #   (generate doctor lives in tuning/models)
  collection/  # persist (JSON SSOT), store (DuckDB), inventory, decks, allocation
  viz/         # Vega-Lite specs + theme + render (HTML/PNG) + 12-col layout + per-deck dashboard
  models/      # shared Pydantic types (Card, TournamentResult, MatchupCell, Variant,
               #   Inventory, UserDeck, ...)
  cli.py · config.py · confidence.py · card_tags.py · colors.py · interaction_facts.py
scripts/       # standalone helpers: knowledge-index gen; viz prototypes (meta_view.py, deck_vs_cohort_viz.py)
docs/          # vision, spec, architecture, principles, briefs, knowledge index
tests/         # pytest suite (2242 tests)
```

## License

Private project — all rights reserved.
