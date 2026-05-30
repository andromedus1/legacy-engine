---
description: The operational + downstream-computation contract for the data layer — source-layer fragility, the mirror-and-decouple resilience strategy, the three meta-% definitions (raw / top-cut / win-rate-weighted), online-vs-paper splitting, and whether we can compute our own matchup matrix from the cache (we can — the JSON carries Rounds with pairings). Read before designing the ingestion boundary, the meta-share computation, or the matchup-matrix module.
type: brief
kind: research
research_method: /deep-research
status: draft
updated: 2026-05-29
summary: |
  The data layer legacy-engine depends on is one community-maintained scrape (fbettega) sitting on top
  of an upstream (mtgo.com / Melee) that WotC actively destabilizes — Badaro's predecessor cache died
  2025-06-10, MTGO has restricted decklist visibility since 2024-06-20, and a Feb-2026 visibility cut was
  rolled back days later. This brief specifies the operational contract: mirror both the fbettega cache and
  MTGOFormatData rules as versioned local inputs behind an `ingestion/` port so a replacement source swaps in
  without touching analytics; compute meta-% three labeled ways (raw entry count, top-cut presence,
  win-rate-weighted) because MTGO data is success-filtered and online/paper diverge; and — the load-bearing
  finding — the cache JSON includes a `Rounds` object with per-match pairings (`player1`/`player2`/`result`),
  so we CAN compute our own matchup matrix from raw rounds when present, with no dependence on the bot-blocked
  mtgdecks.net matrix.
key_findings:
  - "Source layer is single-point-of-failure: fbettega is the live successor to Badaro's MTGODecklistCache (archived 2025-06-10, reason 'mtgo.com scraper is no longer working'); it is one maintainer scraping an upstream WotC actively restricts."
  - "Upstream is hostile-by-policy, not just fragile: MTGO publishes only Top-32 of scheduled events + a SELECTION of 5-0 league lists since 2024-06-20; a further Feb-2026 visibility cut was announced and ROLLED BACK within days (mtgo.com 2026-02-20) — visibility is a live, mutable variable."
  - "LOAD-BEARING: the cache JSON carries a Rounds object (matches: player1, player2, result, id) AND Standings (rank, points, wins/losses/draws, omwp/gwp/ogwp). We CAN compute our own matchup matrix from raw rounds — no dependence on mtgdecks.net's 403-blocked matrix. BUT both are emitted 'when available'."
  - "Coverage is structurally bimodal: paper (Melee) and MTGO Challenges typically ship Rounds+Standings → matchups computable; MTGO 5-0 League dumps ship decklists only (no pairings, no standings) → contribute to raw-count meta-% but NOT to matchup cells or win-rate weighting."
  - "Meta-% has three non-comparable definitions: (a) raw entry share, (b) top-cut presence (success-filtered, inflates winners), (c) win-rate-weighted. Published MTGO data is itself success-filtered, so naive raw-count over a challenge-only corpus already double-counts success. MTGGoldfish uses a 5%-inclusion floor by design."
  - "Online and paper diverge materially (online: cheap tuned tempo; paper: dual-heavy diverse). Derive the split from the cache Tournament name/uri/source field; LABEL each separately and offer a weighted blend — never emit an unlabeled blended number (PRINCIPLES #6)."
  - "Resilience plan: vendor both repos as pinned git submodules/snapshots under data/upstream/ with a captured commit SHA + fetch date; analytics reads only the local mirror; a staleness health-check flags upstream dead if newest tournament date or repo HEAD age exceeds a threshold."
  - "Confidence-gate everything (PRINCIPLES #7): archetypes <2% share and matchup cells n<100 are flagged, not silently shown; attach edh-engine's established/evolving/speculative tier as metadata on every emitted stat."
related:
  - {slug: docs/briefs/ingestion-archetype-contracts/parent.md, relationship: refines}
  - {slug: docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/archetype-matching-algorithm.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/mtgoformatdata-rule-schema.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/csharp-python-port-strategy.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/prior-art-scan.md, relationship: parallel-to}
---

# Brief: Ingestion Operations & Meta-Share Computation

## Purpose
This brief owns the **operational contract** for the data layer and the **downstream computation** that
sits directly on it. It goes deeper than the data-sources table in
[`docs/briefs/legacy-metagame.md`](../legacy-metagame.md) §5 (which catalogues *what* the sources are) and
makes that catalogue *operational*: how the layer fails, how we insulate against it, and exactly how the
numbers built on top of it must be computed. It assumes the JSON shape itself is owned by the sibling INGEST
brief — here we *use* that shape to decide what's computable. It directly implements PRINCIPLES
[#5 legality-is-live-data], [#6 never-an-unlabeled-meta-%], and [#7 confidence-gate-every-stat].

---

## 1. Source-layer fragility — the failure modes

The platform's entire fact base is **one community scrape of an upstream that Wizards actively
destabilizes**. This is not hypothetical fragility; it has already failed once and is mutated by policy.

### 1.1 The history (a chain of single points of failure)
- **Badaro/MTGODecklistCache — archived 2025-06-10.** The README states the reason verbatim: *"mtgo.com
  scraper is no longer working, so this project will be officially shut down."* The scrape had been
  progressively failing for months before that (melee.gg 2025-03-19, manatraders 2025-03-20). This was the
  community-standard cache and the data source the C# `MTGOArchetypeParser` was built against. It is dead.
  ([github.com/Badaro/MTGODecklistCache](https://github.com/Badaro/MTGODecklistCache))
- **MTGO visibility cut — 2024-06-20.** WotC reduced what mtgo.com publishes: going forward only the
  **Top 32 decks of scheduled events and a *selection* of 5-0 League lists**. Badaro's README explicitly
  flags that "MTGO.com data from 2024-06-20 onwards is significantly more limited." This is the root cause of
  the eventual scraper death — the page structure and the data behind it changed.
  ([Magic Online on X, 2024-07-05](https://x.com/MagicOnline/status/1809258773070098646))
- **WotC reformatted decklist pages ~mid-2025** breaking the HTML scrapers that the whole ecosystem
  (mtgo-decklist-scraper, mtg-metagame-scraper, Badaro's updater) relied on.
- **fbettega is the live successor — and it is one maintainer.** `fbettega/mtg_decklist_scrapper` (the
  scraper) + `fbettega/MTG_decklistcache` (the output) are the live pipeline, last pushed 2026-05-29. The
  cache README states its entities were "initially inspired by" Badaro's C# model and "follows a similar
  structure" — i.e. it is a deliberate drop-in successor. But it is a single unpaid maintainer with no SLA,
  no redundancy, and the same hostile upstream.
- **The upstream is mutable by policy, not just by accident.** On **2026-02-20** WotC announced *another*
  decklist-visibility cut, then **rolled it back within days** — mtgo.com: *"We're going to pull back on the
  decklist change we asked the Magic Online team to make earlier this week... return you to your originally
  scheduled Magic Online decklists,"* explaining they were trying to reduce MTGO's overrepresentation in
  aggregators but "moved too fast." ([mtgo.com 2026-02-20](https://www.mtgo.com/news/reversing-decklist-changes-02202026))

### 1.2 What this means for the platform
**Treat the source layer as a hostile, mutable, single-maintainer dependency, not a stable API.** Concrete
failure modes to design against:

| Failure mode | Trigger | Symptom in our pipeline | Blast radius |
|---|---|---|---|
| **Upstream death** | WotC reformat again; maintainer burns out | fbettega repo stops updating (HEAD age grows) | Total — no new facts |
| **Silent coverage shrink** | WotC publishes fewer lists (the 2024 cut, the aborted 2026 cut) | Tournament files thinner; Rounds/Standings vanish | Matchups + win-rate weighting degrade silently |
| **Schema drift** | fbettega changes field names to match a new scrape | Parse errors or, worse, silent field misread | Quiet data corruption |
| **Source-mix shift** | More Melee, less MTGO (or vice versa) | Online/paper blend changes underneath us | Meta-% drifts for non-format reasons |

The non-negotiable design consequence: **never read the live upstream at analysis time.** Pin it, mirror
it, version it, and put a boundary between it and everything downstream (§2).

---

## 2. Mirroring & resilience strategy

### 2.1 Mirror both inputs as versioned local artifacts
Two upstream repos are inputs; both get vendored and pinned:

1. **`fbettega/MTG_decklistcache`** — the tournament-fact corpus.
2. **`Badaro/MTGOFormatData`** — the archetype-detection rules (the CLASSIFY/RULES siblings own *how* these
   are applied; ops owns that they are **mirrored and pinned**, since a rules change silently re-labels the
   entire historical meta).

Recommended layout (analytics never reaches past the mirror):
```
data/
  upstream/
    decklistcache/        # git submodule or rsync snapshot of fbettega cache
    mtgoformatdata/       # git submodule or snapshot of Badaro rules
    MANIFEST.yaml         # { repo, commit_sha, fetched_at, newest_tournament_date } per mirror
  curated/                # OUR normalized parquet/jsonl, derived from upstream/ only
```
`MANIFEST.yaml` is the provenance record: every curated artifact is reproducible from a known upstream
commit. This is the same "knowledge compiled, not re-derived" discipline as PRINCIPLES #4 — the curated
layer is a pure function of a pinned input.

### 2.2 The `ingestion/` boundary (ports & adapters)
Design the boundary so the source is swappable without touching analytics or advisory:
- **Port (the contract analytics depends on):** a normalized internal record — `TournamentRecord` with
  `event_id, source, online_or_paper, date, format, decks[], rounds[]?, standings[]?` and
  `DeckRecord{player, finish, mainboard, sideboard, archetype?}`. This is OUR shape, not fbettega's.
- **Adapter (the only code that knows fbettega's JSON):** `FbettegaCacheAdapter` reads the mirrored JSON and
  emits the port type. A replacement source (a new scraper, Topdeck API, a revived Badaro fork) is a *new
  adapter* implementing the same port — analytics is untouched.
- **Rule:** nothing above `ingestion/` may import the raw cache schema. Matchup, meta-%, and advisory code
  see only the port type. (Mirrors edh-engine's Scryfall-adapter boundary.)

### 2.3 Refresh cadence
- Cache: **refresh daily**, off-peak. Badaro's pipeline updated ~17:00 UTC; fbettega is daily. Daily is
  ample — Legacy events are weekly-cadence, paper majors are monthly.
- MTGOFormatData rules: **refresh weekly + on every B&R announcement** (a ban can spawn/kill an archetype;
  PRINCIPLES #5 version-stamping depends on catching rule changes at the right date).
- Every refresh **bumps the manifest SHA and re-runs the curated build**, so the curated layer and the
  pinned upstream never drift apart.

### 2.4 "Is upstream stale/dead?" health check
Run on every refresh; emit a status, never crash the pipeline:
- **GREEN** — fbettega HEAD pushed within N days (suggest N=4; weekly events + scrape lag) AND newest
  `tournament.date` in the cache within N days.
- **YELLOW (stale)** — HEAD or newest-tournament age in [N, 2N]. Surface a banner on every meta report:
  "data may be incomplete — newest event {date}."
- **RED (dead)** — age > 2N, OR adapter parse-failure rate spikes (schema drift signal). Freeze the curated
  layer at the last-good manifest and alert. **Analytics keeps serving the last-good snapshot** rather than
  serving nothing — degradation, not outage.
- **Coverage-shrink alarm** — track the rolling fraction of tournaments that carry `rounds`/`standings`.
  A sudden drop is the 2024-style policy cut happening again; it silently kills matchup data, so it must be
  alarmed independently of the dead/stale check.

---

## 3. Meta-% computation — the three definitions

There is no single "metagame share." There are three genuinely different numbers, and the published source
data is itself biased, so the choice of definition is load-bearing. **Per PRINCIPLES #6, every emitted share
states (definition, online/paper basis, window).**

Let the corpus be a set of decks `D`, each with an `archetype a`, a `finish`, an `event`, and (when the
event has standings) a derived win-rate. Let `top_cut(d)` be true if `d` finished in the event's published
top cut (top 8 / top 32).

### (a) Raw entry share — "what people brought"
```
share_raw(a) = count(d in D : archetype(d) == a) / |D|
```
The denominator is every collected deck. **Caveat that makes this subtle:** published MTGO data is *already
success-filtered* (only Top-32 + selected 5-0 lists survive to the page — §1.1). So a "raw count" over an
MTGO-heavy corpus is **not** a neutral field sample; it over-weights decks that did well enough to be
published. Raw share is only a clean field sample for events where *all* entries are published (most paper
Melee events, full MTGO challenge entry lists when available).

### (b) Top-cut presence share — "what won" (success-filtered, inflates winners)
```
share_topcut(a) = count(d : archetype(d)==a AND top_cut(d)) / count(d : top_cut(d))
```
Share among top finishers only. **Inflates decks that convert** (high top-8 conversion) and deflates
high-volume-but-grindy decks. This is the number most "tier list" articles implicitly use. It answers "what
is winning," not "what is being played." MTGO Challenge data, being top-32-only, is structurally a top-cut
sample even before we filter.

### (c) Win-rate-weighted share — "expected field strength"
Requires per-deck match results (from `rounds`/`standings`):
```
wr(a)      = wins(a) / (wins(a) + losses(a))          # over all matches by archetype-a decks
weight(a)  = share_raw(a) * wr(a)
share_wrw(a) = weight(a) / Σ_b weight(b)
```
Down-weights popular-but-mediocre decks; up-weights efficient performers. Only computable where match data
exists (§4). This is the input to the advisory "positioning score" in the metagame brief §7.

### MTGGoldfish's methodology (the canonical external anchor)
MTGGoldfish applies a **5% inclusion floor**: a deck must be ≥5% of the scraped lists to appear in the
metagame breakdown — *"so in events with 40 decklists, 3 entries would be enough."* Stated rationale: low
enough to include "Tier 1.5" decks, high enough that a "Tier 2" deck "would have to do more work to make it
in." Their corpus is MTGO Daily-Event / Challenge / League results — i.e. **success-filtered MTGO data**, so
their headline share is closest to a *raw count over a top-cut-biased sample* (a blend of (a) and (b)), not a
neutral field sample. ([mtggoldfish.com/articles/the-metagame-1](https://www.mtggoldfish.com/articles/the-metagame-1))

**Our rule:** compute all three ourselves from the mirrored raw finishes, label each, and treat aggregator
headline numbers as validation only — never as our source of truth.

---

## 4. Matchup-matrix computation from the cache — feasibility (LOAD-BEARING)

**Verdict: YES, we can compute our own matchup matrix from the cache — when the event publishes rounds.** We
do NOT need the bot-blocked mtgdecks.net matrix as a hard dependency.

### 4.1 What the JSON actually contains (confirmed)
The fbettega cache file carries four top-level objects ([fbettega README](https://github.com/fbettega/MTG_decklistcache),
schema "initially inspired by" [Badaro's C# model](https://github.com/Badaro/MTGODecklistCache.Tools/tree/main/MTGODecklistCache.Updater.Model)):
- **Tournament** — `date, name, uri, formats, json_file`
- **Deck** — `date, player, result, anchor_uri, mainboard[{count, card_name}], sideboard[...]`
- **Rounds** — `round_name` + `matches[]`, where each match has **`player1`, `player2`, `result`, `id`**
- **Standings** — `rank, player, points, wins, losses, draws, omwp, gwp, ogwp`

The README qualifies both with **"when available"** — Rounds = "match pairings and results, when available";
Standings = "final standings, when available." Coverage is therefore conditional, not guaranteed.

### 4.2 How to build the matrix
1. Label every deck in the event with an archetype (CLASSIFY sibling).
2. Join `rounds[].matches[]` on `player1`/`player2` → each side's archetype (player name is the join key
   between the Deck object and the match object — both carry `player`).
3. `result` is an aggregate match score string (e.g. `"2-1"`), **not** per-game winners — so we get
   match-level W/L, which is exactly what a matchup matrix needs.
4. Accumulate a directed `(arch_a, arch_b) → {wins, losses, n}` table; the diagonal is the mirror (drop or
   force 50%).

### 4.3 The structural catch — coverage is bimodal
The "when available" qualifier is decisive:
- **Paper (Melee) + MTGO Challenges** → typically ship Rounds + Standings → **matchups computable.**
- **MTGO 5-0 League dumps** → publish **decklists only**, no pairings, no standings (Leagues record only
  the 5-0 finish, not the path). These decks **contribute to raw-count meta-% (3a) but NOT to matchup cells
  or win-rate weighting (3c).**

So the matchup matrix is built **only from the subset of events with `rounds` present**, and that subset is
smaller and more challenge/paper-skewed than the meta-% corpus. This must be tracked: the matrix's effective
sample is a different (smaller) population than the play-rate sample.

### 4.4 Reconciling with the join-name fragility
Player-name string-matching across `Deck.player` and `match.player1/2` is the weak link — handles, casing,
and bye/forfeit rows ("player2" empty) need normalization. Byes and intentional draws (a match `result` with
no clear winner) are dropped from win-rate accumulation. This is a known, bounded data-cleaning task, not a
blocker.

### 4.5 Relationship to external matrices
mtgdecks.net publishes a winrate matrix (30,926 matches Nov 2025–May 2026 per the metagame brief) but
**403-blocks bots**. Use it as a **validation cross-check** against our computed matrix, not a source. Our
computed matrix is the source of truth because it is reproducible from pinned inputs and carries our own
confidence metadata (§6); the external matrix is opaque and unversioned.

---

## 5. Online vs paper — splitting and labeling

The two metagames diverge materially: **online skews cheap, tuned, tempo-heavy** (MTGO economics + iteration
speed); **paper is more dual-land-heavy and diverse** (collection inertia, higher-variance fields). A blended
number hides this and violates PRINCIPLES #6.

### 5.1 Deriving the split from the cache
There is no explicit `online`/`paper` boolean field. Derive it from the **source / Tournament metadata**:
- The cache is organized **by website** in its directory tree (`Tournaments/<website>/<date>/...`). The
  website folder (`mtgo`, `melee`, `manatraders`, `topdeck`) is the primary signal.
- `Tournament.uri` / `Tournament.name` corroborate (mtgo.com URIs and "Challenge"/"League" naming → online;
  Melee event pages + paper-major names like "Eternal Weekend" → paper).
- Adapter responsibility: set `online_or_paper` on the `TournamentRecord` from website + uri, with a small
  override table for ambiguous Melee events (Melee hosts both paper majors *and* online qualifiers).

### 5.2 The product rule
Compute and **display each separately by default**; offer a **weighted blend** as an explicit opt-in where the
weights are stated (e.g. 70/30 online/paper if the user's local field is online-leaning). The blend is never
the default and never unlabeled. Track the online:paper *ratio of the corpus itself* over time — a shift in
the ratio moves blended numbers for non-format reasons (the §1.2 "source-mix shift" failure mode).

---

## 6. Confidence / sample-size gating

Every derived stat carries confidence metadata reusing edh-engine's **`established | evolving | speculative`**
tiering (the goldfish-track pattern referenced in the metagame brief §7).

### Recommended thresholds
| Stat | Gate | Action below gate |
|---|---|---|
| **Archetype share** | < 2% of corpus | Flag as "fringe / low-sample"; group into "Other" in headline views; never tier it |
| **Matchup cell** | n < 100 matches | Show with explicit `[low-n: {n}]` flag + wide CI; never present as settled |
| **Win-rate (any)** | n < ~30 | `speculative`; suppress from advisory positioning score |
| **Corpus window** | < ~4 events or < 2 weeks | Whole report flagged `evolving`; banner the window |

### Tier mapping
- **established** — share ≥2%, matchup n≥100, multi-window stable → eligible for tier lists and advisory.
- **evolving** — meets sample but window is short or trend is moving → shown with a trend caveat.
- **speculative** — below sample gate → shown only on explicit drill-down, never in headlines, never fed to
  the positioning score.

Attach the tier + raw `n` + CI as **metadata on the stat object itself**, so every surface (CLI, report)
can render the gate without re-deriving it. Confidence is a property of the number, not of the view.

Wilson score interval (not normal approximation) for win-rate CIs — it behaves at the small-n and
near-0/near-1 cells that dominate a sparse matchup matrix.

---

## Suggested cross-references to sibling subdomains

- **INGEST (JSON schema):** This brief consumes the schema to assess matchup feasibility (§4.1). INGEST owns
  the authoritative field-by-field shape, the "when available" optionality semantics, and byes/forfeit
  edge-cases in `rounds[].matches[]`. Cross-ref: my §4.1 field list should be reconciled against their
  canonical schema; my §4.4 name-join fragility is a shared concern.
- **CLASSIFY:** §3/§4 depend on every deck being archetype-labeled before share/matchup accumulation.
  My matrix is only as good as their labels; my <2% gating (§6) interacts with their "Unknown/Other" bucket.
- **RULES:** §2.1 mirroring + §2.3 weekly/on-B&R refresh of MTGOFormatData is the operational counterpart to
  their rules semantics; a rules change silently re-labels history (provenance via my MANIFEST.yaml).
- **PORT:** the `MTGOArchetypeParser` port target; my `ingestion/` port (§2.2) is the upstream boundary their
  ported classifier plugs into.
- **CARD-CONTRACT:** Scryfall card dimension is the other half of normalization; `mainboard[].card_name`
  strings (§4.1) must resolve against their card contract.
- **PRIOR-ART:** Badaro's archived cache + the abandoned HTML scrapers (§1.1) are prior art for what breaks
  and why; the C# CacheItem model is the schema ancestor.
