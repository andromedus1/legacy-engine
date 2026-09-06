# legacy-engine

A **Magic: The Gathering Legacy-format analytics & advisory engine**. It answers, with data: *"What is the meta, how do I attack it, and how do I tune my deck?"*

The default refreshed analysis is [Deck Rankings](decks/deck-rankings.html), a generated local
page with independent performance and matchup-floor rankings.

The separate [Doomsday Variant Rankings runbook](docs/analysis/doomsday-variant-rankings.md)
documents the manually generated Esper/Teferi, Sultai/Veil, Grixis/Squelcher, Dimir, and residual
comparison. After refreshing its existing database and global-field inputs, build it with
`.venv/bin/python scripts/refresh_doomsday_variant_rankings.py`.

legacy-engine ingests tournament results, labels decks with a three-level taxonomy
(**superarchetype → parent archetype → camp**), and tracks changes caused by bans, releases,
and deck evolution. Deck Rankings combines current observations with compatible history;
thin evidence and prior estimates stay visible with their uncertainty and sources.

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
   meta-positioning score (expected win rate vs the weighted field), the Deck Rankings landing page
   (full-field performance plus highest worst-matchup floor), a sideboard recommender with an
   impact-decomposed, explainable, slot-ROI-aware scoring model, and a what-to-play advisor
   (proactive/reactive, best-deck vs best-call).

See [`docs/VISION.md`](docs/VISION.md) for the full vision and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
for how it's built.

## Status

The **observed-data spine, meta analytics, three-level taxonomy, stable-era detection, deck
generation, advisory differentiator, and local visualization layer** are built and covered by the
repository's current checks. Only the goldfish-simulation
pillar remains deferred:

| Capability | State |
|---|---|
| Scryfall card dimension + derivations | ✅ built |
| Card prices (per-printing USD; `seed prices`) | ✅ built |
| fbettega tournament ingestion (DuckDB) | ✅ built |
| Archetype classifier (ported MTGOArchetypeParser) | ✅ built |
| Sub-archetype variant tagging (`report meta --by-variant`, `generate consensus --variant`) | ✅ built |
| Superarchetype strategy-cluster registry (`superarchetype run|list|explain`; reviewed `--promote`) | ✅ built |
| Meta-share (3 definitions, online/paper; venue split `--venues`; sub-archetype split `report subgroup`) | ✅ built |
| Matchup matrix (Wilson/Jeffreys CI + Beta-Binomial shrinkage + confidence tiers) | ✅ built |
| Meta trends across ban-list regimes (version-stamped; `--movers N` biggest-movers digest) | ✅ built |
| Ban-affectedness report (`report affectedness` — which bans drove an archetype's valid_since) | ✅ built |
| Head-to-head matchup lookup (`report matchups --a/--b` — single directed cell + Wilson CI) | ✅ built |
| Per-entity stable-era detection (`eras run|list|explain|confirm` — change-point ensemble, fleet FDR, ban/release attribution, BOCPD drift alarm) | ✅ built |
| Era-aware analytics & advisory (stable_since is the DEFAULT per-cell window; detection-derived global field era; ban-only fallback, loudly labeled) | ✅ built |
| Hierarchical + cross-era cell shrinkage (camp → leave-camp-out parent → superarchetype → marginal priors; thin new-era cells anchor to their own pre-disturbance value, labeled) | ✅ built |
| Legacy meta-positioning score (Bayesian Monte-Carlo, custom field, best-call vs best-deck; `--list-granular` S_granular overlay) | ✅ built |
| Deck Rankings landing page (`decks/deck-rankings.html`; performance/floor, refresh changes, build diagnostics, Pareto tradeoffs) | ✅ built |
| Sideboard recommender (weighted max-coverage: PuLP/CBC ILP + greedy + anti-hate; collection-aware; considering/bubble pool) | ✅ built |
| Two-stage core+hedge sideboard (`advise sideboard --smart`) — natural-budget dedicated core (no padding, may return <15) + diversity-preferring hedge in the flex slots; commit/insurance labels + coverage curve + uncovered-field tail | ✅ built |
| Impact-decomposed sideboard scoring (centrality × symmetry × castability × draw-probability vs derived/curated archetype linchpins; per-card breakdown, coverage% diagnostic, slot-ROI/punt table) | ✅ built |
| Sideboard-scorer backtest (`advise backtest` — recommended vs top-finisher boards) | ✅ built |
| Archetype-sweep backtest (`advise sweep` — batch divergence mining across all archetypes) | ✅ built |
| Future-only recurrent evidence validation (`advise recurrent-validation plan|freeze|evaluate|aggregate|proposal` — cutoff-safe, evaluation-only, no auto-apply) | ✅ built |
| Data-driven subarchetype discovery (`discover run|list|apply|promote` — HDBSCAN camps, three-gate validated incl. temporal Gate C, era-default pools, staged→promoted) | ✅ built |
| Variant overlays, opt-in (`report matchups --split-variant` · `report cards --conditioned [--variant]` · `report subgroup --winrates`) | ✅ built |
| What-to-play (proactivity, vulnerability tags incl. ramp, hate-equity, best-deck/best-call) | ✅ built |
| Standalone field read (`advise field` — field composition + vulnerability/hate-equity; no deck required) | ✅ built |
| Provenance-filtered serving advice and meta/matchup reports (`--provenance online|paper`) | ✅ built |
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
is fetched once and mirrored. Derived stats carry an evidence basis: confidence tier where the
surface defines one, and otherwise sample size, interval, prior, or provenance; meta-% is never
emitted unlabeled.

## Install

Requires **Python 3.11–3.13**; maintainer checkouts use Python **3.13**.

```bash
git clone https://github.com/andromedus1/legacy-engine.git
cd legacy-engine
python3.13 -m venv .venv
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

# Local decision-data operations (the scheduler wraps the same composed refresh)
legacy-engine ops scheduler install   # install/update the 07:30 local user LaunchAgent
legacy-engine ops scheduler inspect   # loaded state, exact plist, schedule, and log paths
legacy-engine ops scheduler run-now   # launch now; never kills an already-running refresh
legacy-engine ops status              # last outcome, phase/reason, artifact identity, pending actions
legacy-engine ops status --brief      # one local-only session-orientation line
legacy-engine ops monitor acknowledge CANDIDATE_ID  # suppress unchanged evidence after review
legacy-engine ops scheduler uninstall # unload, then remove only legacy-engine's plist

# Label every ingested deck with an archetype
legacy-engine label

# Stable-era ledger — detect per-archetype/per-camp era boundaries from the corpus itself
legacy-engine eras run          # detect + attribute + persist (also raises the drift alarm)
legacy-engine eras list         # every entity's stable_since + triggering disturbance
legacy-engine eras explain "Doomsday"   # walk one entity's boundary derivations (signals, p, verdicts)
legacy-engine eras confirm 2026-06-29 "Candelabra of Tawnos" "Tron growth engine"  # register a confirmed ban → regime table heals

# Superarchetype lifecycle — preview first, then explicitly replace the serving registry
legacy-engine superarchetype run          # preview a candidate; does not alter serving data
legacy-engine superarchetype list         # inspect serving clusters and member provenance
legacy-engine superarchetype explain "Aluren"  # explain one parent archetype's assignment
legacy-engine superarchetype run --promote # after review: replace serving JSON registry + DuckDB cache

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
# report/advise commands take explicit windowing (--since / --until / --regime / --all-time);
# by DEFAULT they window per-entity at each archetype's detected stable era (ban-only fallback,
# loudly labeled) — every windowed figure names its window and trigger in // audit lines

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
legacy-engine advise backtest --archetype "Dimir Tempo" --field field.txt  # scorer's board vs top-finisher boards (empirical anchor, never pass/fail)
legacy-engine advise sweep --field field.txt                    # batch backtest EVERY archetype; ranked scorer-vs-winners divergence clusters
legacy-engine advise benchmark plan --db data/legacy.duckdb --protocol-id recurrent-parent-future-v1 --created-at 2026-08-16T00:00:00Z --first-cutoff 2025-01-01 --until 2026-08-01 --out benchmark.json
legacy-engine advise recurrent-validation plan --protocol src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json --base-protocol benchmark.json --artifact-root data/recurrent-validation
legacy-engine advise recurrent-validation freeze --protocol src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json --base-protocol benchmark.json --fold fold-001 --snapshot-db artifacts/fold-001.duckdb --snapshot-manifest artifacts/fold-001.manifest.json --stages artifacts/fold-001.stages.json --forecast artifacts/fold-001.forecast.json --code-commit $(git rev-parse HEAD) --artifact-root data/recurrent-validation
legacy-engine advise recurrent-validation evaluate --protocol src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json --base-protocol benchmark.json --origin data/recurrent-validation/origins/<digest>/origin.json --cases artifacts/fold-001.cases.json --field-counts artifacts/fold-001.field-counts.json --artifact-root data/recurrent-validation
legacy-engine advise recurrent-validation aggregate --protocol src/legacy_engine/data/amplification/recurrent-evidence-future-v1.json --base-protocol benchmark.json --origin data/recurrent-validation/origins/<digest>/origin.json --evaluation data/recurrent-validation/evaluations/<digest>.json --artifact-root data/recurrent-validation
legacy-engine advise recurrent-validation proposal --assessment assessment.json --target-config-version recurrent-expanded-v1 --artifact-root data/recurrent-validation
legacy-engine discover run --archetype "Doomsday"               # cluster a parent into camps within its stable era (HDBSCAN, three-gate validated incl. temporal Gate C), stage as candidate
legacy-engine discover run --archetype "Doomsday" --all-pool    # cluster the full corpus instead; %current stays anchored to the era
legacy-engine discover apply --archetype "Doomsday"             # apply a staged split to decks.variant (labeled-speculative overlay)
legacy-engine discover promote --archetype "Doomsday" --variant "Tamiyo, Inquisitive Student"  # curate a confirmed camp into the registry
legacy-engine report matchups --split-variant "Doomsday" --a "Doomsday [Tamiyo, Inquisitive Student]" --b "Izzet Delver"  # camp-level matchup cells
legacy-engine report cards --archetype "Dimir Tempo" --conditioned  # archetype-scoped card win-rate beside the marginal + sign-conflict warnings
legacy-engine report subgroup --archetype "Doomsday" --signature "Murktide Regent" --winrates  # per-camp W/L + win% + tier
# --field-scope/--no-field-scope (default ON) restricts top-finisher tournaments to those whose own
#   metagame overlaps --field's archetypes; --no-field-scope reproduces the prior global sample
# --my-deck NAME loads a saved UserDeck; --field FILE supplies a custom field
# --collection FILE enables owned/acquire annotations; --budget N caps the acquire plan
# --provenance online|paper filters serving advice (listed below) and report matchups/meta
# recurrent validation is evaluation-only: no `run`, no `latest`, and no auto-apply/promote command

# Player identity and strength
legacy-engine identify suggest          # candidate alias clusters (identity dedup)
legacy-engine identify strong           # players clearing the strength gate in the current regime
legacy-engine identify track "example42"  # per-regime archetype history for a player

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
legacy-engine deck save --name "my Dimir Tempo" --deck my.txt  # save / version a deck
legacy-engine deck load --name "my Dimir Tempo"                # load current version
legacy-engine deck buildable --name "my Dimir Tempo"           # check what you can build

# Visualization — render dashboards & charts (Vega-Lite → interactive HTML or static PNG; no Chrome/Node)
legacy-engine viz deck "Dimir Tempo" --out dash.html   # per-deck attack-focused dashboard
legacy-engine viz meta --out meta.html           # also: viz matchups | viz trends | viz tiers (.html or .png)
```

### Local scheduled refresh

`legacy-engine ops scheduler install` creates the user agent
`~/Library/LaunchAgents/com.legacy-engine.refresh.plist`. It runs the existing typed
decision-data composition daily at **07:30 local time** through the repository's absolute
`.venv/bin/python`; `RunAtLoad` is deliberately absent. `StartCalendarInterval` means a run missed
while the Mac sleeps is coalesced and started after wake. The job writes stdout/stderr to
`data/ops/logs/refresh.out.log` and `refresh.err.log`.

Every scheduled or manual attempt targeting the same database/ranking pair uses the same
artifact-derived non-blocking kernel lock. An overlapping invocation does no refresh work and
leaves its own immutable evidence without overwriting the active run's canonical status. Canonical
status lives at `data/ops/status/decision-refresh.json`; missing, malformed, failed, degraded,
running, and more-than-36-hour-old records are distinct `ops status` results. A successful ranking
records its exact path and SHA-256. A failed refresh preserves the prior ranking without claiming
that artifact as newly written.

The same locked run also checks format currency. Scryfall's oracle bulk detects changes in
`legalities.legacy`; WotC announcement pages supply attributable actions/effective dates; the
existing `/sets` scan plus the actual card-ingest diff surfaces new-release evidence. Each signal
is separately labeled `clear`, `pending`, `not_due`, or `unavailable`, and an upstream/parser
failure retains last-good evidence and degrades the job rather than reporting false calm. Machine
state lives at `data/ops/state/format-monitor.json` (or beside an explicit test/status override).

Monitoring is deliberately **not authority**. `ops monitor acknowledge CANDIDATE_ID` suppresses
only that candidate's unchanged evidence hash; materially new evidence resurfaces it. A reviewed
Legacy ban becomes accepted engine truth only through the existing explicit
`eras confirm DATE CARD REASON` command. Unbans or unexpected restriction transitions remain loud
as unsupported pending actions because the cumulative ban ledger cannot honestly represent them.

The lifecycle is reversible: install is an identical-config no-op, refuses to boot out an active
refresh, and restores/reloads the previous plist after any post-bootout failure; uninstall likewise
refuses active-run bootout and retains the plist when bootout fails.
Use `ops scheduler inspect`, `ops status`, and the two log files before intervening. Format
monitoring runs inside this job; there is no second LaunchAgent or daemon. The scheduler does **not**
install an upstream hot spare, vendor-price refresh, or a Modern deployment.

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

```bash
# Refresh the standalone Deck Rankings review page (generated and git-ignored).
.venv/bin/python scripts/refresh_best_call_ranking.py
# writes decks/deck-rankings.html

# Score a private expected field with the same model and a separate output.
.venv/bin/python scripts/refresh_best_call_ranking.py \
  --field decks/local-field-saved-post-may18-107.txt \
  --field-label "Saved post-May 18 field (107 players)" \
  --out decks/deck-rankings-local-saved.html

# Audit parent-versus-build decision units from the generated page and source DB.
.venv/bin/python scripts/analyze_decision_units.py \
  --db data/legacy.duckdb --report decks/deck-rankings.html --format markdown
```

The full refresh uses `scripts/refresh_decision_data.py`; the focused script name is retained for
callers and scheduler wiring. `scripts/evaluate_deck_rankings.py` retains its default retrospective
field-half-life diagnostic and optional adaptive matchup baseline. Its separate `--served-model`
mode freezes cutoff-refitted, retrospective fixed-parent snapshots and the shared production Deck
Rankings projection before it reads later outcomes:

```bash
.venv/bin/python scripts/evaluate_deck_rankings.py --db data/legacy.duckdb \
  --served-model --output-dir data/benchmarks/deck-rankings-evaluation-v1
```

The optional `--phase` separates artifact freezing, development scoring, and confirmation scoring
(or runs both scoring phases with `all`); it defaults to `development`, which seals predictions for
all six declared origins before scoring the first three. Run confirmation later with
`--phase confirmation --selected-method <method>`.
Confirmation reuses the sealed predictions only after validating their requested configuration and
seals the development decision before it opens the final three horizons.

The served-model evaluation compares the production prior scale `1` with fixed `.5` and `2`
sensitivities and the conditional `opponent-plan-prior-v1` challenger on one prediction grid. It
reports log loss, Brier score, calibration, support strata, reciprocity, paired event differences,
and later evidence for the named floor pairings. The run is parent-only and uses observed-by-cutoff
card availability where release dates are unavailable. The hash-pinned parent taxonomy includes the
production Energy color split into Boros Energy and Mardu Energy; camps remain disabled. Each frozen
cell retains its selected view, match-id digest, and admitted windows. The outcome-blind card-metadata
quarantine applies the same fixed ceilings to every method (at most `.5%` of decks and `2%` of rounds),
records raw and retained ledgers, and does not repair metadata. Development selected scale `2`, but
confirmation slightly favored the current scale `1` on both proper scores, so production retains
scale `1`. The generated page can disclose the dated scores and call sensitivity; the evaluator has
no publication or deployment gate.

`meta_view.py` is the **meta view** (where the field is, how it's moving, what's
best-positioned over time); `deck_vs_cohort_viz.py` is the **my-deck view** (how one
75 compares to the field). Both render to self-contained inline SVG (no Chrome / Node /
CDN) and carry confidence tiers honestly. `meta_view.py` knobs: `--bands-top`,
`--pos-top`, `--ema-span`, `--last-months`.

The cohort tool renders, per card, your count vs the cohort's 0x/1x/2x/3x/4x histogram with
inclusion%, on-mode / off-distribution / missing tags, grouped by card type, plus a
confidence-tier banner. `--require "Card=N"`/`"Card>=N"` carves a sub-cohort; the
window defaults to the current ban regime (override with `--since`).

### Deck Rankings method

Deck Rankings keeps field composition and matchup evidence separate. The current field is an
exponentially weighted view of published deck lists in the observed ban-regime slice, using a
provisional 28-day half-life. It is a distribution of published lists, not a census of tournament
entrants. Integer sightings, decay-weighted counts, effective sample size, and bounded transition
prior support remain distinct in the output.

Each directed matchup cell draws on compatible history selected for that pairing. Its estimate is
the mean of a Beta posterior formed from wins, total matches, prior mean, and the cell's retained
prior strength; an absent cell receives the weak Beta(1, 1) fallback. Clean interval evidence can
replace a cell once without being pooled again with overlapping fallback evidence. Thin and
prior-only cells stay visible with their 95% interval, W-L/n, prior provenance, and source window.

Performance and floor are independent views of those cells. Performance is the current-field
weighted mean of all cell posterior means, including a structural 50% mirror. Floor is the minimum
posterior mean over non-mirror opponents with positive field share. Their leaders and table sorts
are independent; the floor range beside a row belongs to its named toughest pairing, while the
posterior interval for the minimum across all opponents remains in Evidence details.

The page presents the calls through sortable archetype and camp columns, an agency map, and a
strategic-plan table whose five headers are sortable. Coverage/n filters narrow the shared view,
and compact row dropdowns expose matchup records, intervals, and evidence support. The current
production prior scale remains `1` after the sealed development/confirmation comparison: development
selected scale `2`, while confirmation slightly favored scale `1` on both proper scores. This is a
descriptive projection; the evaluator supplies evidence and does not act as a publication gate. See
the [Deck Rankings refresh and interpretation runbook](docs/analysis/best-call-ranking.md) for the
full evidence boundaries and reproducible commands.

Passing `--field` reweights the same selected matchup cells for a private expected field while
keeping candidate eligibility tied to the current global corpus. Counted rows are supplied scenario
observations, `# effective_n` is concentration evidence, and share-only rows stay fixed weights.
Unknown opponents retain their positive mass as weak-prior cells. The command requires a separate
`--out`, labels global observations separately, and reports global-versus-scenario performance and
floor calls; the scheduled global page remains unchanged. Local strategic-plan shares remain visible,
but their projections are unavailable until composition-specific plan aggregates exist.

Each refresh also compares the previous compatible published page and shows up to three observations:
the largest field-share movement, the largest modeled beneficiary, and any changed performance or
floor call. Performance changes are split arithmetically into field-weight and matchup-estimate
contributions; missing forecasts, new baselines, and incompatible scenarios remain explicit.
Expanded archetype rows add a parent-versus-build diagnostic with camp floors, common-opponent coverage,
pooling uplift, separate main/side slot distances, card-record coverage, and source-scoped normalized
pilot overlap. These disclosures do not alter the page's parent ranking or taxonomy.

The mature `advise positioning` command remains a separate legacy estimator with its established
Agency/P(best), evidence strata, adaptive windowing, and `--provenance` behavior. Historical
matchup bands on that surface use raw win rate: **Blowout** <40%, **Half** 40–45%, **Edge** 55–60%
inclusive, and **Dominant** >60%.

Each leaf takes `-v/--verbose`. `advise positioning|sideboard|whattoplay|field|report|refresh|acquire|compare`
and `report matchups|meta` take `--provenance online|paper` and a `--db` path.
Omitting `--provenance` combines evidence for serving advice, except `advise refresh`, which
defaults to separate online and paper packages. Meta/matchup reports also accept `all`.
Statistics identify their basis and evidence support; advisory output carries a heuristic-vs-data-driven
audit trail. Absent/thin signal is always labeled (never a silent zero). Commands not yet implemented
fail loudly rather than returning empty results.

## Development

```bash
.venv/bin/python -m pytest -q     # run the test suite
```

This project is built with a research-grounded, substrate-driven workflow:

- **`docs/`** — the knowledge layer: `VISION.md`, `SPEC.md`, `ARCHITECTURE.md`, `PRINCIPLES.md`, and
  domain briefs under `docs/briefs/`. A three-layer knowledge index (`docs/knowledge-index-nav.yaml`,
  `docs/knowledge-index.yaml`, and `docs/knowledge-index-detail.yaml`) is generated from doc
  frontmatter.
- **`.work/`** — the work substrate: epics → features → stories as markdown items with YAML
  frontmatter, queried via `.work/bin/work-view`. Work flows design → implement → review per item.
- Every feature ships with tests; docs describe present intent (rolling-foundation).

## Layout

```
src/legacy_engine/
  ingestion/   # Scryfall JSONL bulk, fbettega cache, rules, banlist + WotC monitor, releases, DuckDB
  archetype/   # rules loader, matcher (ported Detect), colors, labeler, variants
  analytics/   # match_results, matchup (era-aware windows + hierarchical priors), metashare,
               #   trends, card_value, affectedness, discovery, subgroup, venue, speculation
               #   eras/     (stable-era detection: series, bocpd, detect, ensemble, store,
               #              attribution, run, consume)
               #   players/  (identity, strength, history)
               #   superarchetype/ (strategy clustering, registry, aggregation, consumption)
  advisory/    # field, positioning, sideboard, whattoplay, report, gaps, window,
               #   collection, acquire, primer, refresh, deck_ranking, doomsday_variants
  generation/  # consensus, export, tuning, discovery (modes 1+2+3), card_distribution, models
               #   (generate doctor lives in tuning/models)
  collection/  # persist (JSON SSOT), store (DuckDB), inventory, decks, allocation
  ops/         # locked refresh, typed status, launchd controls, detection-only format monitor
  viz/         # Vega-Lite specs + theme + render (HTML/PNG) + 12-col layout + per-deck dashboard
  models/      # shared Pydantic types (Card, TournamentResult, MatchupCell, Variant,
               #   Inventory, UserDeck, ...)
  cli.py · config.py · confidence.py · card_tags.py · colors.py · interaction_facts.py
scripts/       # knowledge-index generation; visualizations; Deck and Doomsday Variant Rankings
docs/          # vision, spec, architecture, principles, briefs, knowledge index
tests/         # hermetic pytest suite; CI/current checks are authoritative
```

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for a working checkout, the
house rules (every number labeled; tests ship with the change; hermetic CLI tests), and where
things live. The test suite is hermetic and needs no seeded corpus, so `pip install -e ".[dev]"`
followed by `python -m pytest -q` works on a fresh clone.

## Privacy

This repository ships no personal data. `src/legacy_engine/data/players/aliases.json` — the
cross-source player-identity map — is intentionally **empty**: linking one person's handles
across MTGO, Melee, and paper is identifying information about a third party. Add your own
entries locally and keep them out of commits.

## License

[MIT](LICENSE).
