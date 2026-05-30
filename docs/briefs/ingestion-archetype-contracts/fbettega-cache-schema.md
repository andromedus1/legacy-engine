---
description: Read before designing the ingestion/ module — the exact JSON schema, repo layout, source/provenance encoding, update cadence, and consumption strategy for the fbettega tournament-data cache.
type: brief
kind: research
research_method: /deep-research
status: draft
updated: 2026-05-29
summary: |
  Pins down the data contract for the fbettega tournament-data sources (fbettega/MTG_decklistcache +
  fbettega/mtg_decklist_scrapper), the Legacy analog to cEDH's edhtop16. Every JSON file is a CacheItem
  with four parts — Tournament, Decks[], Rounds[], Standings[] — written by the scraper's to_dict() methods
  in PascalCase keys; the real committed schema differs from the (stale) README example. Provenance
  (online MTGO vs paper Melee) is encoded by the source DIRECTORY and the Uri host, not a field. Card names
  are already normalized to Scryfall canonical forms by the scraper, which de-risks the card-data join.
key_findings:
  - "Schema (verified against live files): each .json = CacheItem with PascalCase top-level keys Tournament, Decks, Rounds, Standings. Tournament = {Date, Name, Uri, Formats}; Deck = {Date, Player, Result, AnchorUri, Mainboard[], Sideboard[]} with cards as {Count, CardName}; Standing = {Rank, Player, Points, Wins, Losses, Draws, OMWP, GWP, OGWP}; RoundItem = {Player1, Player2, Result}."
  - "The README's JSON example (lowercase keys, Formats as a list) is STALE/illustrative — real files use PascalCase and Formats is a bare string 'Legacy' (the Python model types it List[str] but to_dict emits the raw value). Build the parser against the to_dict() output, not the README."
  - "Layout: Tournaments/<Source>/<YYYY>/<MM>/<DD>/<slug>.json. Source dirs: MTGO, MTGmelee, Topdeck, CardsRealm, Manatrader (+ Tournaments-Archive for dead sources). Legacy events found via filename slug (legacy-challenge-32-…, legacy-showcase-challenge-…, legacy-league-…) AND Tournament.Formats=='Legacy'; paper-Melee slugs are free-text so filter on Formats, not the name."
  - "Provenance is NOT a field: online vs paper is the source directory (MTGO = online; MTGmelee/Topdeck/CardsRealm = mostly paper) plus the Uri host (mtgo.com vs melee.gg vs topdeck.gg). Player names corroborate (MTGO handles vs paper real names). The engine must derive a provenance label at ingest from dir+host."
  - "Leagues vs Challenges differ structurally: MTGO leagues are 5-0 dumps — Rounds=[] and Standings=[], Deck.Result is a record like '5-0'. Challenges carry full Rounds (Quarterfinals…/Round N) + 32 Standings with tiebreakers, Deck.Result is '1st Place'. Code MUST treat empty Rounds/Standings as normal, not an error."
  - "Card names are already Scryfall-canonical: the scraper's CardNameNormalizer strips whitespace, removes the Alchemy 'A-' prefix, and maps via a dict built at runtime from Scryfall (is:split/is:dfc/adventure/flip) plus a hardcoded MTGO/Melee mismatch table. Split cards use ' // ' (e.g. 'Dead // Gone'). This means a near-direct join to Scryfall, but it's runtime-built (drifts), so keep a fallback fuzzy/unmatched bucket."
  - "Cadence: MTGO/Melee/Topdeck auto-update daily ~17:00 UTC (commits land ~18:32 UTC); Manatraders ~Monday after the event. One automated commit/day ('Mise à jour automatique : YYYY-MM-DD'). MTGO.com data from 2024-06-20 onward is degraded (website change) and lives in a separate folder."
  - "Consumption: clone (cache is a git submodule of the scraper) or sparse-checkout Tournaments/MTGO + Tournaments/MTGmelee; git pull is the incremental signal. Detect new events by diffing the day-folder file list (scraper itself dedups via 'if os.path.exists(target_file): continue'). Raw GitHub (raw.githubusercontent.com/…/master/…) works per-file; GitHub contents API lists day folders."
related:
  - {slug: docs/briefs/ingestion-archetype-contracts/parent.md, relationship: refines}
  - {slug: docs/briefs/ingestion-archetype-contracts/mtgoformatdata-rule-schema.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/archetype-matching-algorithm.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/csharp-python-port-strategy.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/prior-art-scan.md, relationship: parallel-to}
---

# Brief: fbettega Tournament-Data Cache — Schema & Ingestion Contract

## Purpose
This brief pins the **exact data contract** of the fbettega sources so the `ingestion/` module can be
designed without guessing, and so the `archetype/` classifier knows precisely what deck shape it receives.
The Legacy-metagame brief (`docs/briefs/legacy-metagame.md`, §5 data-sources) already *named* these sources
and the edhtop16-analogy; this brief gives them **shape**.

Two repos:
- **`fbettega/MTG_decklistcache`** — the populated data repo (the fact source). ~446 commits, GPL-3.0, pushed daily; live as of 2026-05-29.
- **`fbettega/mtg_decklist_scrapper`** — the Python scraper that produces it ("adapts badaro work in python"). Successor to the now-dead `Badaro/MTGODecklistCache` C# pipeline.

Where a claim comes from the scraper source rather than a published spec, it's marked **[inferred from code]**;
where it's verified against a live committed file, it's marked **[verified <path>]**.

---

## 1. The JSON schema — a tournament file

Every file is one **`CacheItem`** serialized via the scraper's `to_dict()` methods
(`models/base_model.py`). **Top-level keys are PascalCase** and there are exactly four:

```jsonc
{
  "Tournament": { ... },     // event metadata (single object)
  "Decks":      [ ... ],     // submitted decklists
  "Rounds":     [ ... ],     // match pairings (may be empty)
  "Standings":  [ ... ]      // final standings (may be empty)
}
```

### 1.1 Tournament (object)
| Field | Type | Notes |
|---|---|---|
| `Date` | string | ISO; date-only for MTGO (`"2026-05-24"`), full ISO+tz for Melee (`"2026-05-23T13:30:00+00:00"`) |
| `Name` | string | e.g. `"Legacy Challenge 32"`, `"Legacy Showcase Challenge"`; paper names are free-text and may be non-Latin (Japanese seen) |
| `Uri` | string | canonical event URL — **the provenance host** (`mtgo.com` / `melee.gg` / `topdeck.gg`) |
| `Formats` | **string** | `"Legacy"`. The model types this `List[str]` and the README shows a list, but live files emit a bare string. **Treat as `str \| list[str]`.** |

> The model also has `json_file` and `force_redownload` fields, but `Tournament.to_dict()` **omits them** — they are scraper-internal and never appear in committed files. [inferred from `base_model.py`]

### 1.2 Deck (array element)
| Field | Type | Notes |
|---|---|---|
| `Date` | string \| null | MTGO sets it (`"2026-05-24T03:00:00+00:00"`); **Melee leaves it `null`** |
| `Player` | string | MTGO handle (`"Cirxi"`) or paper real name (`"Yanagi Toya"`) |
| `Result` | string | `"1st Place"`/`"2nd Place"` (bracketed events) OR a record `"5-0"`/`"4-1"` (leagues) OR match record for swiss |
| `AnchorUri` | string | deck permalink; MTGO appends `#deck_<Player>`, Melee is a `Decklist/View/<guid>` URL |
| `Mainboard` | array | `[{ "Count": int, "CardName": str }, …]` |
| `Sideboard` | array | same shape; **can be empty `[]`** |

### 1.3 Round (array element) — pairings/brackets
```jsonc
{ "RoundName": "Quarterfinals",
  "Matches": [ { "Player1": "kyataoka", "Player2": "musasabi", "Result": "2-1-0" }, … ] }
```
- `RoundName` is `"Round N"` (swiss) or bracket labels (`"Quarterfinals"`, `"Semifinals"`, `"Finals"`).
- `Result` is `"p1-p2"` or `"p1-p2-draws"`. (The model also derives `scores`/`numeric_score`/`id` in memory, but `RoundItem.to_dict()` emits only `Player1/Player2/Result` — **`id` is not in the file**.) [inferred from `base_model.py`]
- **`Rounds` is `[]` for leagues** (no bracket).

### 1.4 Standing (array element)
```jsonc
{ "Rank": 1, "Player": "Cirxi", "Points": 18, "Wins": 9, "Losses": 0, "Draws": 0,
  "OMWP": 0.5278, "GWP": 0.75, "OGWP": 0.4757 }
```
- `OMWP`/`GWP`/`OGWP` = opponent-match-win%, game-win%, opponent-game-win% (the standard MTG tiebreakers), floats.
- **`Standings` is `[]` for leagues.** Challenges carry one Standing per player (32 for a Challenge 32).

> **Real verified examples:**
> [verified `Tournaments/MTGO/2026/05/24/legacy-challenge-32-2026-05-2412842926.json`] — 32 decks, 3 Rounds (QF/SF/F), 32 Standings, Result `"1st Place"`.
> [verified `Tournaments/MTGmelee/2026/05/23/189-…-the-189th-legacy-at-home-430609-2026-05-23.json`] — 16 decks, 3 swiss Rounds, 16 Standings, Deck.Date `null`.
> [verified `Tournaments/MTGO/2026/05/25/legacy-league-2026-05-2510612.json`] — 15 decks, Rounds `[]`, Standings `[]`, Result `"5-0"`.

---

## 2. Repo layout / directory convention

```
MTG_decklistcache/
├── Tournaments/                 # live sources
│   ├── MTGO/<YYYY>/<MM>/<DD>/<slug>.json
│   ├── MTGmelee/<YYYY>/<MM>/<DD>/<slug>.json
│   ├── Topdeck/<YYYY>/...
│   ├── CardsRealm/<YYYY>/...
│   └── Manatrader/<YYYY>/...
├── Tournaments-Archive/         # dead/discontinued sources, same layout
├── LICENSE  (GPL-3.0)
└── README.md
```
Path template (from the scraper): `cache_folder/<SourceName>/<year>/<month>/<day>/<filename>.json`,
zero-padded month/day. [inferred from `fetch_tournament.py`; verified against live tree]

**Finding Legacy events:**
- MTGO slugs are deterministic: `legacy-challenge-32-<date><id>.json`, `legacy-showcase-challenge-<date><id>.json`, `legacy-league-<date><leagueid>.json`. You *can* prefilter MTGO by the `legacy-` filename prefix.
- **Paper (MTGmelee) slugs are free-text** (e.g. `189-the-189th-legacy-at-home-430609-…`, `clc-2026-etapa-04-legacy-…`) — do **not** rely on the filename. **Filter on `Tournament.Formats == "Legacy"`** (normalize to handle the `str`-vs-`list` ambiguity). A single Melee file is single-format in practice, but the field exists to allow multi-format containers, so check membership.

---

## 3. Sources covered & how provenance is encoded

| Source dir | Provider | Online/Paper | Uri host | Player field | Legacy relevance |
|---|---|---|---|---|---|
| `MTGO` | mtgo.com | **Online** | `mtgo.com` | screen names | **Primary** — Challenges, Showcase Challenges, 5-0 Leagues |
| `MTGmelee` | melee.gg | **Paper** (mostly) | `melee.gg` | real names | Eternal Weekend EU/BMO + regional paper events |
| `Topdeck` | topdeck.gg | Paper | `topdeck.gg` | real names | Sparse for Legacy (Topdeck/2026 had no Legacy at check time) |
| `CardsRealm` | cardsrealm.com | mixed | `cardsrealm.com` | mixed | minor |
| `Manatrader` | manatraders.com | Online | manatraders | online monthly; de-anon issues |

**Provenance is not an explicit field.** It is encoded by **(a) the source directory** the file lives in and
**(b) the `Tournament.Uri` host**. The ingestion layer must *synthesize* a provenance label at parse time
(e.g. `provenance = "online" if source in {MTGO, Manatrader} else "paper"`), and may corroborate with the
Uri host. Player-name style (handle vs real name) is a weak secondary signal, not a contract. This matters
because online and paper metagames diverge materially (per the metagame brief) — the engine should keep the
provenance tag on every deck row for split meta-% reporting.

---

## 4. Update cadence

- **MTGO, Melee, Topdeck:** automatically updated **daily ~17:00 UTC**; the actual git commit lands ~18:32 UTC.
- **Manatraders:** ~the **Monday** after the event.
- Commits are **one automated push per day**, message `"Mise à jour automatique : YYYY-MM-DD"` (verified: 2026-05-29, -28, -26, -25 commits). The scraper runs headless (credentials in `Api_token_and_login/`); the cache repo is a **git submodule** of the scraper repo (`.gitmodules`).
- **Degradation note (carry into ops/fragility planning):** MTGO.com data from **2024-06-20 onward is significantly more limited** due to an MTGO website change and is stored separately. Expect thinner Rounds/Standings on newer MTGO events than on pre-2024 ones.

---

## 5. How to consume it from Python

**Mirroring options (pick based on backfill needs):**
1. **Full clone + `git pull`** — simplest; `git pull` is the incremental refresh. The diff of new files since last pull = new events.
2. **Sparse checkout** of just `Tournaments/MTGO` + `Tournaments/MTGmelee` (Legacy lives almost entirely there) — smaller working tree.
3. **Raw GitHub per-file** — `https://raw.githubusercontent.com/fbettega/MTG_decklistcache/master/Tournaments/MTGO/<Y>/<M>/<D>/<slug>.json`. Use the **GitHub contents API** to list a day folder, then fetch raw files. Good for targeted pulls; subject to API rate limits, so prefer clone for bulk. (Default branch is `master`.)

**Parsing strategy:** load JSON → read PascalCase keys → normalize `Formats` to a set → keep only Legacy →
map each `Deck` to `{player, result, provenance, mainboard:[(count,name)], sideboard:[(count,name)]}`.
The classifier (sibling CLASSIFY/RULES) keys on `CardName` counts, so the contract that matters downstream is
`Mainboard`/`Sideboard` arrays of `{Count, CardName}`.

**Incremental new-event detection:** persist the set of ingested `(source, Uri)` (or file path); on each refresh,
diff the day-folder listing against that set. The scraper guarantees idempotent file paths and dedups on its
side (`if os.path.exists(target_file): continue`), so a path-level diff is reliable. Use `Tournament.Uri` as the
**stable event key** (it's the canonical URL and survives re-scrapes); use `AnchorUri` as the deck key.

---

## 6. Data-quality caveats

- **Empty Rounds/Standings is NORMAL** for leagues — do not raise. Branch on event type: presence of `Standings`/`Rounds` ⇒ bracketed event; absence ⇒ league (and `Result` is a `W-L` record).
- **`Deck.Date` is `null` on Melee** — fall back to `Tournament.Date`.
- **`Formats` type drift** (`str` in live files vs `List[str]` in the model/README) — normalize defensively.
- **README example is stale** (lowercase keys, list Formats, a `json_file`/`id` field) — it does **not** match committed files. Trust `to_dict()` / live files.
- **Card-name normalization is largely already done by the scraper** — `CardNameNormalizer.normalize()` strips
  whitespace, removes the Alchemy `A-` prefix, and maps via a dict **built at runtime from Scryfall** (`is:split`,
  `is:dfc`, adventure, flip) plus a hardcoded MTGO/Melee mismatch table (e.g. `"Altar Of Dementia"→"Altar of Dementia"`,
  `"Full Art Plains"→"Plains"`). Net effect: **CardName is effectively Scryfall-canonical**, split cards use ` // `
  (e.g. `"Dead // Gone"`). BUT the mapping is runtime-built so it can drift / miss new sets — the engine should
  still validate every CardName against its own Scryfall mirror and route misses to an `unmatched` bucket rather
  than dropping the deck.
- **Sideboard may be `[]`** (paper events sometimes omit it; MTGO leagues sometimes thin). The classifier must tolerate sideboard-blind input.
- **Dedup across sources:** the same paper event can appear on multiple providers, and MTGO Challenges occasionally re-fire IDs. Dedup on `Tournament.Uri`; for cross-source dedup, fall back to `(Name, Date, sorted player set)`.
- **Player de-anonymization** on Manatraders is unreliable (noted by the scraper) — treat Manatraders player identity as low-confidence.
- **Non-Latin / free-text tournament names** (e.g. Japanese) — store `Name` as UTF-8, never key archetypes off it.

---

## Suggested cross-references to sibling subdomains

- **RULES (MTGOFormatData rule schema)** — *depends-on*: the rules consume exactly the `Mainboard`/`Sideboard` `{Count, CardName}` arrays this brief documents; rule authoring assumes the CardName is Scryfall-canonical, which §6 confirms the scraper already provides.
- **CLASSIFY (MTGOArchetypeParser algorithm)** — *depends-on*: the classifier's input contract is the per-`Deck` card list here; it must tolerate empty `Sideboard` (§6) and the `str`-vs-`list` `Formats` ambiguity (§1.1).
- **CARD-CONTRACT (Scryfall fields the rules key on)** — *parallel-to*: §6's normalization finding (scraper builds its map from Scryfall `is:split`/`is:dfc`/adventure/flip) directly informs which Scryfall name fields the join must cover; the ` // ` split convention is shared.
- **SERVE/OPS (fragility/mirroring + meta-% computation)** — *depends-on*: §4 cadence/degradation and §5 mirroring/incremental-detection are the raw inputs to the fragility plan; the provenance label synthesized in §3 is what meta-% must split online vs paper on; the 2024-06-20 MTGO degradation is a load-bearing fragility fact.
- **PORT (C#→Python port strategy)** — *parallel-to*: the schema here is the Python re-derivation of Badaro's original C# `CacheItem`; the port effort should preserve these exact PascalCase keys for compatibility.
- **PRIOR-ART (existing tools consuming these sources)** — *parallel-to*: other consumers (e.g. MTGODecklistCache downstreams) rely on the same `to_dict()` contract; their parsing choices are evidence for the defensive normalizations recommended in §6.
