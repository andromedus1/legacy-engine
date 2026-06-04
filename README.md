# legacy-engine

A **Magic: The Gathering Legacy-format analytics & advisory engine**. It answers, with data rather
than vibes: *"What is the meta, how do I attack it, and how do I tune my deck?"*

Legacy metagaming today is experience- and forum-driven — tier lists scattered across articles,
matchup knowledge living in Discord and reps, "what should I play this weekend?" answered by feel.
legacy-engine makes it rigorous and reproducible: it ingests real tournament results, labels every
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

MVP — the **observed-data spine, meta analytics, deck generation, the advisory differentiator, and a
local visualization layer** are built and tested (1176 passing tests). Only the goldfish-simulation
pillar remains deferred:

| Capability | State |
|---|---|
| Scryfall card dimension + derivations | ✅ built |
| fbettega tournament ingestion (DuckDB) | ✅ built |
| Archetype classifier (ported MTGOArchetypeParser) | ✅ built |
| Meta-share (3 definitions, online/paper) | ✅ built |
| Matchup matrix (Wilson/Jeffreys CI + Beta-Binomial shrinkage + confidence tiers) | ✅ built |
| Meta trends across ban-list regimes (version-stamped) | ✅ built |
| Regime-aware analytics & advisory (adaptive per-cell ban windowing) | ✅ built |
| Meta-positioning score (Bayesian Monte-Carlo, custom field, best-call vs best-deck) | ✅ built |
| Sideboard recommender (weighted max-coverage: PuLP/CBC ILP + greedy + anti-hate) | ✅ built |
| What-to-play (proactivity, vulnerability tags, hate-equity, best-deck/best-call) | ✅ built |
| Field Read & Deck Recommendation report (the `advise` surface) | ✅ built |
| Per-card win-rate analytics (`report cards`) | ✅ built |
| Gap discovery — under-explored archetypes (`report gaps`) + adjacent-card discovery (`generate tune --discover`) | ✅ built |
| Consensus baseline decklist (`generate consensus`) | ✅ built |
| Field-tuned decklist (`generate tune`) | ✅ built |
| Decklist export (`export deck`) | ✅ built |
| Visualization — per-deck HTML dashboards + meta/matchup/trends/tier charts (Vega-Lite → HTML + PNG) | ✅ built |
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

# Label every ingested deck with an archetype
legacy-engine label

# Meta & performance reports
legacy-engine report meta       # meta-share (raw / top-cut / win-rate-weighted; online vs paper)
legacy-engine report matchups   # archetype matchup matrix with confidence intervals
legacy-engine report tiers      # S/A/B tier list over meta-share
legacy-engine report trends     # meta-share evolution across ban-list regimes
legacy-engine report gaps       # under-explored archetypes (high positioning S, low meta-share)
# report/advise commands take ban-regime windowing: --since / --until / --regime / --all-time

# Per-card win-rate report
legacy-engine report cards                       # per-card presence-correlational win-rate (vs field)

# Meta attack / advisory — "how to attack the field"
legacy-engine advise positioning --deck my.txt   # expected WR vs the weighted field (P(best) ranking)
legacy-engine advise sideboard   --deck my.txt   # recommended 15-card sideboard (ILP + greedy "why")
legacy-engine advise whattoplay  --deck my.txt   # proactivity, vulnerability tags, best-deck/best-call
legacy-engine advise report      --deck my.txt   # the full Field Read & Deck Recommendation + audit trail
# advise commands take --field FILE (a custom "<share> <archetype>" field) and --db

# Deck generation
legacy-engine generate consensus --archetype "Dimir Tempo"  # consensus baseline decklist (mode 1)
legacy-engine generate tune      --archetype "Dimir Tempo" --deck my.txt  # field-tuned list (mode 2)
legacy-engine generate tune      --deck my.txt --discover    # + suggest adjacent swap-in candidates (mode 3)

# Decklist export
legacy-engine export deck --deck my.txt          # format for Moxfield / Archidekt / MTGGoldfish import

# Visualization — render dashboards & charts (Vega-Lite → interactive HTML or static PNG; no Chrome/Node)
legacy-engine viz deck "Dimir Tempo" --out dash.html   # per-deck attack-focused dashboard
legacy-engine viz meta --out meta.html           # also: viz matchups | viz trends | viz tiers (.html or .png)
```

Each leaf takes `-v/--verbose`; `report` commands take `--provenance [online|paper|all]` and a `--db`
path. Every emitted number is labeled with its definition/basis, sample size, and confidence
tier; advisory output carries a heuristic-vs-data-driven audit trail. Commands not yet implemented fail
loudly rather than returning empty results.

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
  ingestion/   # Scryfall, fbettega cache, MTGOFormatData rules, banlist, DuckDB store
  archetype/   # rules loader, matcher (ported Detect), colors, labeler
  analytics/   # match_results, matchup (adaptive ban-windowing), metashare, trends, card_value, affectedness
  advisory/    # field, positioning, sideboard, whattoplay, report, gaps, window
  generation/  # consensus, export, tuning, discovery (modes 1+2+3)
  viz/         # Vega-Lite specs + theme + render (HTML/PNG) + 12-col layout + per-deck dashboard
  models/      # shared Pydantic types (Card, TournamentResult, MatchupCell, ...)
  cli.py · config.py · confidence.py · card_tags.py · colors.py
docs/          # vision, spec, architecture, principles, briefs, knowledge index
tests/         # pytest suite
```

## License

Private project — all rights reserved.
