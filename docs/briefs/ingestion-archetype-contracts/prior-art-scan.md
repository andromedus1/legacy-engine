---
description: Prior-art scan for the legacy-engine ingestion + archetype-classification pipeline — what already exists (ports, scrapers, classifiers, analytics platforms, card libs) and the reuse verdict for each. Read before deciding adopt-vs-build on the MTGOArchetypeParser port.
type: brief
kind: research
research_method: /deep-research
status: draft
updated: 2026-05-29
summary: |
  Maps the existing tooling around the Badaro/fbettega Legacy decklist ecosystem to decide what
  legacy-engine should reuse vs. build. Headline: NO maintained, standalone Python port of
  MTGOArchetypeParser's rules engine exists — the canonical archetype matcher is still Badaro's
  C# tool (MIT, archived Sept 2025), and the community's de facto pipeline is "C# parser →
  Aliquanto3/Jiliac R reports." fbettega ported only the SCRAPER to Python (mtg_decklist_scrapper)
  and still labels archetypes with the C# parser before feeding R. The two non-rules alternatives
  are videre-project/nbac-worker (Python multinomial Naive Bayes classifier, Apache-2.0, not
  rules-based) and j6e/mtg-meta-analyzer (TypeScript, signature-card + KNN, not Python). For card
  resolution / decklist parsing, mature Python libs exist and should be adopted (Scrython, mtg_parser).
key_findings:
  - "HEADLINE / PORT VERDICT: there is no maintained standalone Python port of the MTGOArchetypeParser RULES engine (InMainboard / OneOrMore / Fallback-pile logic). legacy-engine is genuinely building the Python rules-matcher. Adopt the RULE DATA (MTGOFormatData JSON, MIT), port the ALGORITHM."
  - "Canonical matcher = Badaro/MTGOArchetypeParser — C#, MIT, ARCHIVED 2025-09-24 (read-only). Still authoritative as a spec/reference, not a runtime dependency."
  - "De facto community standard pipeline = MTGODecklistCache (JSON) → MTGOArchetypeParser (C#, labels decks) → Aliquanto3/Jiliac R-Meta-Analysis (R, produces meta share + matchup matrices). This is the workflow legacy-engine re-implements in Python."
  - "fbettega is the LIVE data source: mtg_decklist_scrapper (Python, 'adapt badaro work in python' — SCRAPER ONLY, MTG_decklistcache as git submodule) + Magic_data_analysis (R fork of Aliquanto). It still uses the C# parser for labeling — no Python classifier inside."
  - "videre-project/nbac-worker — Python, Apache-2.0, multinomial Naive Bayes archetype classifier covering legacy among 6 formats. NOT rules-based (no MTGOFormatData), architected as a Cloudflare Worker. LEARN-FROM (ML fallback idea); core src/nbac/ extractable but don't adopt wholesale."
  - "j6e/mtg-meta-analyzer — TypeScript/Svelte, MIT, actively maintained (v0.3.1, Mar 2026). Signature-card rules + KNN fallback, melee.gg ingestion, produces matchup matrices + scatter plots. LEARN-FROM (classifier design + viz), wrong language to reuse."
  - "CARD-CONTRACT libs to ADOPT: Scrython (Scryfall wrapper, Py, built-in rate limiting in 2.x); mtg_parser (EUPL-1.2, parses 11+ decklist sources incl. MTGO/Moxfield/MTGGoldfish, active Apr 2026) — but mtg_parser does NOT resolve cards or classify archetypes."
  - "edh-engine (our sibling) used NONE of these — hand-rolled httpx + BeautifulSoup + pydantic. Legacy's archetype-parser layer is net-new; the scrython/mtg_parser adopt decision is the one place to break from edh-engine's hand-roll habit."
related:
  - {slug: docs/briefs/ingestion-archetype-contracts/parent.md, relationship: refines}
  - {slug: docs/briefs/ingestion-archetype-contracts/csharp-python-port-strategy.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/mtgoformatdata-rule-schema.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/archetype-matching-algorithm.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/scryfall-card-contract.md, relationship: parallel-to}
  - {slug: docs/briefs/ingestion-archetype-contracts/ingestion-ops-and-metashare.md, relationship: parallel-to}
---

# Brief: Prior-Art Scan — Ingestion & Archetype Classification

## Purpose
Before legacy-engine builds a Python ingestion + archetype-classification pipeline over the fbettega
decklist cache and Badaro's MTGOFormatData/MTGOArchetypeParser, this brief answers the load-bearing
question: **does a maintained Python path already exist, or are we genuinely building the Python port?**

**Answer up front:** We are genuinely building the rules-engine port. No maintained standalone Python
implementation of MTGOArchetypeParser's rule-matching logic exists. What *does* exist and should be
reused: the **rule data** (MTGOFormatData JSON), the **scraper** (fbettega's Python scraper), and
**card-resolution libraries** (Scrython, mtg_parser). What we should learn from but not adopt: two
*non-rules* classifiers (videre's Naive-Bayes worker; j6e's TypeScript signature+KNN analyzer).

---

## 1. The de facto community pipeline (the standard we re-implement)

The canonical community metagame workflow is a three-stage chain, all by the same lineage:

```
Badaro/MTGODecklistCache  ──►  Badaro/MTGOArchetypeParser  ──►  Aliquanto3/R-Meta-Analysis
   (JSON tournament cache)        (C# rules engine: labels        (R: meta share %, matchup
                                   each deck with an archetype)     matrices, tier reports)
```

- **Stage 1 — Data:** `Badaro/MTGODecklistCache` — JSON cache of tournaments from MTGO, Manatraders,
  Melee, Topdeck. Each file is a tournament object: array of decks + standings + bracket. The schema
  entity is `CacheItem`. **ARCHIVED — last update 2025-06-10** when the mtgo.com scraper broke; README
  now points users to "alternative data sources." No license stated on the repo page.
  <https://github.com/Badaro/MTGODecklistCache>
- **Stage 2 — Classify:** `Badaro/MTGOArchetypeParser` — C#, **MIT**, **ARCHIVED 2025-09-24** (read-only).
  Rules-based engine; reads `MTGOFormatData` rules + the cache, emits `mtgo_data_YYYY_MM_DD.csv/json`
  with one archetype label per deck. <https://github.com/Badaro/MTGOArchetypeParser>
  - Rule vocabulary (the spec the PORT team must replicate): `InMainboard` / `InSideboard` /
    `InMainOrSideboard` (card required), `OneOrMoreInMainboard` (≥1 of a list), `TwoOrMoreInMainboard`
    (≥2), `DoesNotContain`. All conditions in an archetype must hold (AND). Archetypes have **variants**
    (match "main" rules first, then variant rules). Unmatched decks fall through to **Fallbacks/Piles**
    (a "Common Cards" set; tag by the fallback sharing the most cards) to handle "goodstuff" decks.
- **Stage 3 — Report:** `Aliquanto3/R-Meta-Analysis` — R, "analyse MTG tournament results in all the
  imaginable ways." Consumes the parser's JSON, writes meta reports to `/Results`. ~51 commits, no
  releases, no license stated. Aliquanto3 has largely handed off; **Jiliac** is the active community
  publisher of Eternal/Legacy/Pioneer meta updates built on this stack.
  <https://github.com/Aliquanto3/R-Meta-Analysis>

**Implication for legacy-engine:** our INGEST + RULES + CLASSIFY + SERVE modules collapse this entire
C#-plus-R chain into one Python pipeline. The rule *data* and the rule *vocabulary* above are the
contract to honor; everything else is ours to redesign.

---

## 2. The live data source — fbettega (the cache the brief named)

Because Badaro's repos are archived, **fbettega is the maintained continuation** of the data side:

| Repo | Lang | What it does | Status |
|---|---|---|---|
| `fbettega/mtg_decklist_scrapper` | Python | "Trying to adapt badaro work in python." **Scraper only** — pulls MTGO, Melee, Topdeck, Cards Realm (Manatraders standings partial). Pip deps (unpinned), includes `MTG_decklistcache` as a **git submodule**. | Active (pushed 2026-05-29 per source brief); 8★/6 forks |
| `fbettega/MTG_decklistcache` | (cache data) | The JSON decklist cache itself — fbettega's continuation of Badaro/MTGODecklistCache. | Active (2026-05-29) |
| `fbettega/Magic_data_analysis` | R | "Version personnel de l'analyse du metagame modern" — fbettega's fork/continuation of Aliquanto's R analysis. | Active |
| `fbettega/MTG_FB_tools` | — | Helper sub-project of the R `Modern_data_analysis`. Not a classifier. | — |

**Critical detail for the PORT team:** fbettega ported the **scraper** to Python but **did NOT port
the archetype classifier** — the pipeline still relies on Badaro's C# `MTGOArchetypeParser` to label
decks before the R analysis. So even in the most-Python community pipeline available today, **archetype
classification is still C#**. This confirms the port gap is real and unfilled.

---

## 3. Non-rules archetype classifiers (alternatives — learn-from, not adopt)

These exist and classify Legacy decks, but neither implements the MTGOFormatData rules engine:

- **`videre-project/nbac-worker`** — Python, **Apache-2.0**. Multinomial **Naive Bayes** archetype
  classifier ("NBAC"), formats `standard|modern|pioneer|vintage|legacy|pauper`. Pure ML trained on
  labeled card-frequency data — **no rules, no MTGOFormatData**. Architected as a **Cloudflare Worker**
  (low-latency inference service), modular `src/nbac/` (train/score/model). ~21 commits, active (Feb 2026).
  **VERDICT: LEARN-FROM.** A statistical classifier is exactly the kind of *fallback* you'd want when
  rules don't match (better than Badaro's "most-shared-cards" pile heuristic). Core lib is extractable,
  but it's worker-shaped; treat as a design reference for a CLASSIFY fallback tier, not a dependency.
  <https://github.com/videre-project/nbac-worker>
  - Broader context: `videre-project` is an active org (Apache-2.0) — `MTGOSDK` (C#, MTGO client
    inspection), `Tracker` (TS), `mtgo-db`, `monorepo` API. It is the *modern* MTGO-data ecosystem but
    is MTGO-client-centric, not a drop-in decklist-cache analytics platform.

- **`j6e/mtg-meta-analyzer`** — TypeScript (74%) + Svelte, **MIT** (code) / CC-BY-4.0 (content),
  actively maintained (**v0.3.1, 2026-03-19**). Tournament metagame analysis: **matchup matrices**,
  metagame **scatter plots** (share vs. win rate), tournament browser. Classification = **signature-card
  rules with KNN fallback**. Ingests **melee.gg directly** (`fetch-tournament.ts`) — does **NOT** use
  MTGODecklistCache / MTGOFormatData / fbettega. **VERDICT: LEARN-FROM.** Best available reference for
  (a) the rules+KNN hybrid classification pattern and (b) the meta-share/matchup-matrix output design.
  Wrong language to reuse; the architecture and visualizations are worth studying for our SERVE layer.
  <https://github.com/j6e/mtg-meta-analyzer>

---

## 4. Card-resolution & decklist-parsing libraries (ADOPT)

These solve problems we should NOT hand-roll (note: edh-engine hand-rolled httpx+BS4 — this is the
place to break that habit). They feed the sibling **CARD-CONTRACT** subdomain.

- **`NandaScott/Scrython`** — Python Scryfall API wrapper, on PyPI. 2.x adds **built-in rate limiting**
  (auto-enforces Scryfall's ~10 req/s), no extra deps. **VERDICT: ADOPT** for card resolution /
  Scryfall lookups. <https://github.com/NandaScott/Scrython> · <https://pypi.org/project/scrython/>
- **`lheyberger/mtg-parser`** (PyPI `mtg_parser`) — Python, **EUPL-1.2**, **active** (v0.0.1a54,
  2026-04-28). Parses decklists from 11+ sources (MTGO/MTGA text, Moxfield, Archidekt, Scryfall,
  MTGJSON, MTGGoldfish, TappedOut, TCGPlayer; some need Cloudflare-bypass). **Does NOT resolve cards or
  classify archetypes** — pure decklist→structured-list. **VERDICT: ADOPT (scoped)** for parsing
  arbitrary decklist text; we still own card resolution (via Scrython) and classification.
  Note EUPL-1.2 is a weak-copyleft license — fine as a library dependency; confirm compatibility before
  vendoring source. <https://pypi.org/project/mtg_parser/>
- **Other Python card libs (lower priority):** `mtgtools` (EskoSalaka — Scryfall/mtgio data into a ZODB
  object DB; heavyweight, **IGNORE** unless we want an object store), `mtgsdk`/magicthegathering.io
  (older, less maintained than Scryfall — **IGNORE**, Scryfall is the live source), `mtgjson` tooling
  (bulk card data; useful only if we want offline bulk card sets rather than API — **defer**).

---

## 5. Other scrapers / analytics seen (mostly ignore)

- `gabriel-ballesteros/mtg-metagame-scraper` (Python web scraper for decklists) — generic, less
  maintained than fbettega; **IGNORE** (fbettega's cache is the richer, live source).
- `Warlord1986pl/MTG-Metagame-Analyzer`, `lirianom/mtg-analytics` (price modeling),
  `lheyberger/mtg-deckstats`, `mia-0032/mtgo-decklist-scraper`, `ElLorans/GoldfishScrape` — small /
  niche / unmaintained or off-target (prices, single-source). **IGNORE.**
- `mtgdecks.net`, `MTGGoldfish`, `MTGTop8` — aggregator *sites*, HTML-only, bot-blocking; already
  covered as data-source caveats in `docs/briefs/legacy-metagame.md`. Not reusable code.

---

## 6. Consolidated verdict table

| Project | Lang | License | Maint. | What it is | Verdict |
|---|---|---|---|---|---|
| Badaro/MTGOArchetypeParser | C# | MIT | Archived 2025-09 | The rules-engine spec | **REFERENCE / port the algorithm** |
| Badaro/MTGOFormatData | JSON | MIT | (archived stack) | Archetype rule data | **ADOPT the data** |
| Badaro/MTGODecklistCache | JSON | n/a | Archived 2025-06 | Original cache | Reference schema; use fbettega's instead |
| fbettega/mtg_decklist_scrapper | Python | n/a | Active | Python scraper (no classifier) | **ADOPT / fork** for INGEST |
| fbettega/MTG_decklistcache | data | n/a | Active | Live decklist cache | **ADOPT** as data source |
| Aliquanto3/R-Meta-Analysis | R | n/a | Handoff→Jiliac | Meta reports | **LEARN-FROM** (report design) |
| videre-project/nbac-worker | Python | Apache-2.0 | Active | NB ML classifier (no rules) | **LEARN-FROM** (fallback tier) |
| j6e/mtg-meta-analyzer | TS/Svelte | MIT | Active 2026-03 | sig+KNN, matchup matrices | **LEARN-FROM** (classify + viz) |
| Scrython | Python | (MIT-ish) | Active | Scryfall wrapper | **ADOPT** (CARD-CONTRACT) |
| mtg_parser | Python | EUPL-1.2 | Active 2026-04 | Decklist text parser | **ADOPT (scoped)** |
| mtgtools / mtgsdk / mtgjson | Python | various | mixed | card data alt sources | **IGNORE / defer** |

**Bottom line:** Adopt the **rule data** (MTGOFormatData) and the **scraper + cache** (fbettega);
**port the rules algorithm** (no Python equivalent exists); **learn from** the two non-rules classifiers
for a fallback tier and from j6e for output design; **adopt** Scrython (+ optionally mtg_parser) for
card/decklist handling rather than hand-rolling as edh-engine did.

---

## Suggested cross-references to sibling subdomains

- **PORT** (adopt-vs-build): This brief is your input. **Build** the rules matcher — no maintained
  Python port exists. fbettega proves even the most-Python community pipeline still shells out to the
  C# parser. Closest reference impls: Badaro's C# source (the spec) and j6e's TS signature+KNN matcher.
- **RULES** (rule schema): The MTGOFormatData rule vocabulary in §1 (InMainboard / OneOrMore /
  TwoOrMore / DoesNotContain / variants / Fallback-piles) is the schema you formalize. Data is MIT.
- **CLASSIFY** (the algorithm): Primary = port Badaro's deterministic AND-of-conditions + variant +
  most-shared-cards-pile fallback. Strongly consider videre's Naive-Bayes (§3) as a *statistical
  fallback tier* above the pile heuristic; study j6e's KNN fallback as a third reference.
- **INGEST** (cache schema): fbettega/mtg_decklist_scrapper + MTG_decklistcache (§2) is the live source;
  Badaro's archived `CacheItem` JSON (§1) is the schema of record. Adopt/fork the Python scraper.
- **CARD-CONTRACT** (Scryfall): Adopt **Scrython** (rate-limited Scryfall wrapper) for card resolution;
  **mtg_parser** for parsing arbitrary decklist text formats (§4). Both Python, both maintained.
- **SERVE/OPS**: j6e/mtg-meta-analyzer (§3) and the Aliquanto/Jiliac R reports (§1) are the reference
  designs for meta-share %, matchup matrices, and share-vs-winrate scatter outputs.
