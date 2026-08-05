---
description: "What does it take to own the fbettega tournament-data generation as a hot-spare pipeline, and to put B&R/release/price monitoring on a launchd schedule that surfaces at session start? Read before designing epic-data-autonomy's upstream-ownership and monitoring arcs."
type: brief
kind: research
slug: data-autonomy-upstream
research_method: /brief
verification_status: attested
provenance: agent-synthesis
updated: 2026-07-31
blocks_phase: epic-data-autonomy
summary: |
  Reverse-engineers the upstream tournament-data pipeline legacy-engine consumes (fbettega's
  mtg_decklist_scrapper → MTG_decklistcache), diagnoses the July 2026 outage (one person's home
  server, no CI, no alerting — the second multi-day stall of 2026), and assesses the epic's fixed
  hot-spare ambition: run the same scraper ourselves on a schedule, verify spare output against
  the existing cache parser, and flip CACHE_DIR only when upstream is down. Also pins the
  machine-readable sources and polling designs for B&R + set-release monitoring, launchd
  scheduling patterns for the maintainer's Mac, and a feasibility verdict on Card Kingdom prices.
key_findings:
  - "The entire upstream is one person's home server: no GitHub Actions in either fbettega repo, and the July 2026 outage (26 days of missed daily updates, 07-02→07-28) was caused by a house move + server hardware changes; April 2026 had a second multi-day stall — hot-spare is justified by observed base rate, not paranoia."
  - "Running the scraper ourselves is LOW effort: pure Python (beautifulsoup4/requests/dateutil/numpy), one CLI entry point defaulting to a self-backfilling trailing 7-day window, idempotent file writes; MTGO — the engine's primary Legacy source — needs no credentials at all (public pages with embedded JSON). Melee needs a real account login (undocumented endpoints, unverifiable ToS — the one gray zone); Topdeck has an official free-key API at 100 req/min."
  - "The scraper repo has NO license (cache repo is GPL-3.0) — fork it on GitHub and run it privately rather than vendoring/modifying/redistributing its code; treat our spare's output tree as private infrastructure, never republish."
  - "Hot-spare verification is nearly free: our cache.py parse_cache_item + ingest_cache already define the schema contract, so spare-vs-upstream divergence checking is 'run both trees through the existing parser and diff tournaments/decks on overlap days' — no new contract machinery."
  - "P0 side-finding: Scryfall bulk data is now JSONL-only (every /bulk-data entry has jsonl_download_uri and no download_uri), and ingestion/scryfall.py reads meta['download_uri'] — the engine's next cold `seed cards`/refresh will KeyError; fix before (or as part of) the scheduled-refresh feature."
  - "B&R monitoring should be two-signal: (a) detection = daily oracle_cards bulk diff of legalities.legacy transitions (values are legal/not_legal/restricted/banned; bulk collected every 12-24h, *.scryfall.io downloads unlimited); (b) attribution = polling the WotC announcement page family, which is server-rendered, uses fixed phrasing ('<Card> is banned.', 'Changes effective as of <date>', 'Next announcement: <date>') and pre-announces the next B&R date — both feed the existing eras-confirm/append_ban_event registration loop, with the eras drift alarm as backstop."
  - "launchd: use StartCalendarInterval (jobs missed while the Mac sleeps fire once on wake, coalesced — unlike StartInterval, which silently misses); gui/<uid> LaunchAgents with absolute .venv paths, StandardOut/ErrPath logs, and a status JSON the session-start surface reads; launchctl kickstart is the manual catch-up verb."
  - "Card Kingdom is OPEN: api.cardkingdom.com/api/v2/pricelist is a public unauthenticated ~67 MB JSON (149,977 rows, scryfall_id join key, retail + buylist + per-condition), regenerated at least daily; LED spot check $949.99 retail confirms the CK-vs-Scryfall divergence that motivated the idea. MTGJSON (cardkingdom provider, retail+buylist, 90-day history) is the sanctioned-aggregator fallback; TCGplayer direct API is moot."
related:
  - {slug: docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md, relationship: depends-on}
  - {slug: docs/briefs/ingestion-archetype-contracts/parent.md, relationship: depends-on}
  - {slug: docs/briefs/change-point-detection.md, relationship: parallel-to}
---

# Brief: Owning the Upstream — Hot-Spare Tournament Data + Scheduled Format Monitoring

## Purpose

Unblocks `epic-data-autonomy`. The epic's design decisions are **fixed inputs**: (a) the
upstream-ownership ambition is a **hot spare** — build and periodically exercise our own
tournament-data generation, keep consuming upstream normally, flip to ours only when upstream is
down (not full replication, not archive-only); (b) the scheduling substrate is **local launchd on
the maintainer's Mac** against local `data/` + DuckDB, with session-start surfacing of results. This brief
answers what the builder needs: how the upstream actually runs and fails, what running it
ourselves takes, how to verify the spare, which sources the B&R/release monitors should poll and
how, the launchd mechanics, and whether Card Kingdom prices are ingestible.

The data *contract* (CacheItem JSON schema, provenance encoding, discovery) is already pinned by
`docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md` — this brief does not repeat
it. Read that brief alongside this one.

---

## 1. The upstream as it actually runs

Two repos, one maintainer (François Bettega):

- **`fbettega/MTG_decklistcache`** — the data repo the engine mirrors (`FBETTEGA_CACHE_REPO`).
  GPL-3.0, default branch `main`, ~153 MB (`size: 156287` KB), live as of 2026-07-30
  `[data-autonomy-cache-repo-meta]{1}`.
- **`fbettega/mtg_decklist_scrapper`** — the Python scraper that generates it ("Trying to adapt
  badaro work in python"). **No license.** `[data-autonomy-scraper-meta]{5}` The cache repo is a
  git submodule of the scraper `[data-autonomy-scraper-readme]{6}`.

**Where it runs: one person's home server.** Neither repo has a `.github` directory — there are no
CI workflows; the daily job is self-hosted `[data-autonomy-scraper-meta]{5}`. Normal cadence is
exactly one automated commit per day, message `"Mise à jour automatique : YYYY-MM-DD"`, landing
~18:18–18:48 UTC `[data-autonomy-cache-commits]{2}`.

**The July 2026 outage, precisely.** Last automated commit 2026-07-01T18:33Z; a "manual commit"
on 07-02; then nothing until "first fix manual"/"second fix" and a resumed automatic commit on
2026-07-28 — 26 days of missed daily updates, recovered by backfill on resume
`[data-autonomy-cache-commits]{2}`. Root cause, from the maintainer on issue #3: "I've recently
been through a home move and made several hardware upgrades/changes to my server environment,
which put the automated script on hold" `[data-autonomy-outage-issue3]{3}`. Nobody's monitoring
caught it — the report came from a downstream consumer (the maintainer, as `andromedus1`) three weeks in,
and the issue closed as completed 2026-07-29 `[data-autonomy-outage-issue3]{3}`.

**Not the first stall.** The repo's entire issue history is outage reports: issue #1 "Automatic
Update has stopped" (2026-04-14 → closed 04-17) preceded July's issues #2/#3
`[data-autonomy-outage-issues-list]{4}`. Two independent multi-day stalls within four months is
the empirical fragility base rate the hot-spare decision rests on.

**Heritage.** Badaro's original C# pipeline is dead: `MTGODecklistCache` archived (last push
2025-06-10) and `MTGODecklistCache.Tools` archived (2025-09-24). But `MTGOFormatData` — the
archetype rules the engine vendors — is still actively maintained (pushed 2026-07-21)
`[data-autonomy-badaro-cache-meta]{10}`. The rules supply chain and the tournament-data supply
chain have different life expectancies; this epic only needs to own the second.

---

## 2. Scraper anatomy — what we'd actually be running

Entry point: `python fetch_tournament.py <cache_folder> <start_date> <end_date> <source>
<leagues>`, sources `mtgo | melee | topdeck | manatrader | cardsrealm | all`; `start_date`
defaults to 7 days ago, `end_date` to today `[data-autonomy-scraper-readme]{6}`. Python ≥3.8;
`requirements.txt` is exactly beautifulsoup4, numpy, pytest, python_dateutil, Requests — no
Selenium, no headless browser `[data-autonomy-scraper-readme]{6}`.

Operational behavior (from `fetch_tournament.py` source `[data-autonomy-scraper-fetch]{7}`):

- **Idempotent + self-backfilling.** Existing files are skipped (`if os.path.exists(target_file):
  continue`), so the default trailing 7-day window re-run daily fills any gap up to a week without
  duplicating work. Writes are atomic (temp file + `os.replace`).
- **Politeness.** `sleep_time = 60` seconds between tournaments for Topdeck ("to avoid rate
  limits"), 5 seconds for every other source; failures retry via `run_with_retry(..., 10)`
  attempts. (The README's "retry up to five times" is stale versus the code.)
- **Hygiene.** Events with no data / no decks / all-empty mainboards are skipped; output tees to
  `log_scraping.txt`.

Per-source reality:

| Source | Endpoint style | Auth | Notes |
|---|---|---|---|
| MTGO | `https://www.mtgo.com/decklists/{year}/{month}` index (BeautifulSoup, `li.decklists-item`), event pages carry `window.MTGO.decklists.data = {…}` embedded JSON | **none** — plain `requests.get` | `[data-autonomy-mtgo-client]{8}` — the engine's primary Legacy source (Challenges + Leagues) is the easiest leg |
| Melee | login flow: GET `/Account/SignIn` (CSRF) → POST `/Account/SignInPassword` with email+password from `melee_login.json`; data via `/Decklist/SearchDecklists` + `/Decklist/GetTournamentViewData/{guid}`; `time.sleep(DELAY_SECONDS)` between calls | **real user account** | `[data-autonomy-melee-client]{9}` — undocumented internal endpoints; also rebuilds its card-name normalizer live from `api.scryfall.com/cards/search` |
| Topdeck | official Tournaments V2 API | **free API key** in `Authorization` header (file `Api_token_and_login/api_topdeck.txt`) | 100 req/min on most endpoints, 429 on excess `[data-autonomy-topdeck-api-docs]{22}` `[data-autonomy-scraper-readme]{6}` — sparse for Legacy but fully sanctioned |
| Manatraders | scrape + de-anonymization | account-ish | "not fully functional in order to recover standings" `[data-autonomy-scraper-readme]{6}` — skip in the spare |
| CardsRealm | scrape (bot-detection workaround was needed upstream in June 2026) | none | minor for Legacy — skip in the spare |

---

## 3. Hot-spare design

### 3.1 Run it, don't rewrite it — but fork, don't vendor

The scraper is unlicensed (`license: null` `[data-autonomy-scraper-meta]{5}`), unlike the GPL-3.0
cache repo `[data-autonomy-cache-repo-meta]{1}`. No license = no explicit grant to copy, modify,
or redistribute the code. The pragmatic, low-risk posture:

- **Fork `mtg_decklist_scrapper` on GitHub** (GitHub's ToS permits forking public repos within
  GitHub) and pin our fork's SHA. Run it **as-is, privately, unmodified** — a subprocess, not a
  library import. Do not vendor its code into `src/`, do not publish our generated tree, do not
  serve it to anyone else. If we ever need code changes, prefer upstream PRs (fbettega merges
  community fixes — e.g. the June 2026 Cardsrealm header fix) over divergence.
- The spare's job is **currency during upstream outages**, not history: upstream's git history
  remains the archive; our spare only ever generates the trailing window.

### 3.2 Moving parts (the full inventory)

1. **Fork pin** — our GitHub fork of the scraper + recorded SHA (same pattern as
   `MTGOFORMATDATA_SHA` in `config.py`).
2. **Spare venv** — separate from the engine's `.venv`; deps are the five packages above
   `[data-autonomy-scraper-readme]{6}` (pin them in a lockfile at fork time).
3. **Credentials** — Topdeck API key (free, developer portal
   `[data-autonomy-topdeck-api-docs]{22}`) in `Api_token_and_login/api_topdeck.txt`; a dedicated
   Melee account's email+password in `Api_token_and_login/melee_login.json`
   `[data-autonomy-scraper-readme]{6}`. Keep both OUT of the engine repo (they live in the spare's
   working tree, which is gitignored or outside the repo entirely). MTGO needs nothing
   `[data-autonomy-mtgo-client]{8}`.
4. **Spare output tree** — `data/spare_cache/Tournaments/<Source>/<Y>/<M>/<D>/*.json`, exactly
   the upstream layout so `discover_legacy_events`/`ingest_cache` work on it unmodified.
5. **Exercise job** (launchd, weekly) — run the scraper over the default trailing 7-day window
   (`mtgo` at minimum; `melee` if the account is set up), then run the divergence check (§3.3),
   then write the status file (§5.3). Weekly is enough to prove the spare works while staying a
   polite, low-volume consumer; the 7-day window means even weekly runs have full coverage.
6. **Failover flip** — a config/CLI switch (`refresh all --cache-dir data/spare_cache`, or a
   `CACHE_SOURCE` pointer file) that makes `ingest_cache` consume the spare tree instead of the
   upstream mirror. `ingest_cache` is already content-hash keyed, so mixed provenance is safe:
   re-ingesting the same event from either tree is a no-op unless bytes changed.
7. **Staleness detector** — the thing that tells us to flip: upstream mirror's newest
   tournament date (or last `git pull` delta) vs today. >3 days with zero new files across all
   sources = YELLOW; >7 = RED, surface "flip to spare" at session start. (Upstream's own cadence
   is one commit/day `[data-autonomy-cache-commits]{2}`, so 3 missed days is already anomalous.)

Estimate: the spare itself is genuinely small — a fork pin, a venv, one launchd plist, one
divergence script, one flip flag. The MTGO-only spare has **zero** credential/ToS friction and
covers the engine's primary source; Melee is an optional second leg behind a real account.

### 3.3 Verification: schema-identity + divergence, using what we already have

The engine already owns the contract: `parse_cache_item`/`ingest_cache`
(`src/legacy_engine/ingestion/cache.py`) parse upstream files into typed models with resilience
counters, and `_db_matches_parsed` proves DB-vs-file equivalence. So:

- **Contract test (schema identity):** run `discover_legacy_events` + `parse_cache_item` over the
  spare tree; assert zero `bad` events and that every parsed `TournamentResult` field the engine
  consumes (name/date/uri/format/source/provenance, deck boards, rounds, standings) is populated
  with the same shapes as upstream. This is a pytest over real spare output — no mocks.
- **Divergence check (overlap days):** for each day both trees cover, join events on
  `Tournament.Uri` (the stable event key) and diff: events present in one tree only; per-event
  deck counts; per-deck (player, result, sorted card multiset). Report as a labeled partition
  (upstream-only / spare-only / content-mismatch) — a divergence-as-diagnostic surface, never
  auto-reconciled. Expected steady-state: spare-only ≈ 0, upstream-only ≈ 0 for MTGO;
  content-mismatch only when upstream hand-edited files.
- **Ledger honesty:** ingesting the spare tree goes through the same `ingest_ledger` content-hash
  path, so labels survive and re-runs are cheap — no special-casing.

### 3.4 Licensing / ToS honesty table

| Surface | Status | Posture |
|---|---|---|
| Cache repo (data) | GPL-3.0 `[data-autonomy-cache-repo-meta]{1}` | mirroring/consuming is what it's for |
| Scraper code | **no license** `[data-autonomy-scraper-meta]{5}` | fork on GitHub, run privately, don't vendor/redistribute |
| mtgo.com decklist pages | public, unauthenticated `[data-autonomy-mtgo-client]{8}` | low risk; identify with a UA; 5s politeness sleeps as upstream does `[data-autonomy-scraper-fetch]{7}` |
| melee.gg | credentialed access to undocumented endpoints `[data-autonomy-melee-client]{9}`; Terms page currently serves an error page, so ToS is **unverified** `[data-autonomy-melee-terms]{25}` | gray zone: dedicated account, keep volume minimal, accept the leg may die; upstream repo stays primary |
| topdeck.gg | official API, free keys, 100 req/min `[data-autonomy-topdeck-api-docs]{22}` | fully sanctioned |
| Card Kingdom pricelist | public endpoint, no auth, no embedded usage policy `[data-autonomy-ck-pricelist]{20}`; established third-party use `[data-autonomy-ck-gopkg]{21}` | one fetch/day with descriptive UA; MTGJSON as sanctioned fallback `[data-autonomy-mtgjson-price-model]{17}` |

---

## 4. B&R + release monitoring

The engine's regime layer already self-heals: the eras drift alarm flags unattributed
disturbances, and `eras confirm` → `append_ban_event` registers a dated event in the curated
`data/banlist/events.json`, healing every downstream consumer (`banlist_as_of`, regime windows,
affectedness) on next read (`src/legacy_engine/ingestion/banlist.py`). The monitor's job is
**registration latency**: catch the event in ~a day instead of waiting for the corpus fingerprint
(the Candelabra ban took ~6 weeks to be noticed under rules-pin staleness — see
`docs/briefs/change-point-detection.md`).

### 4.1 B&R: two signals, detection + attribution

**Signal 1 — Scryfall legalities diff (detection, machine-precise).** Card objects carry a
`legalities` object whose values are exactly `legal`, `not_legal`, `restricted`, `banned`
`[data-autonomy-scryfall-cards-docs]{13}`. Daily job: download the `oracle_cards` bulk, extract
`{oracle_id: legalities.legacy}`, diff against yesterday's snapshot; any `legal→banned` (or
reverse) transition is a detected B&R event with the card named. Freshness bound: "Bulk data is
only collected once every 12-24 hours" `[data-autonomy-scryfall-bulk-docs]{11}`, and bulk
downloads from `*.scryfall.io` "do not have rate limits" `[data-autonomy-scryfall-rate-limits]{14}`
— one API call + one ~24 MB `oracle_cards` download per day `[data-autonomy-scryfall-bulk-api]{12}`
is fully within budget. This piggybacks on the refresh job's existing bulk download — the diff is
nearly free.

**Signal 2 — WotC announcement page (attribution + calendar).** The announcement pages are
server-rendered and formulaic: a per-format block in fixed phrasing ("Legacy Candelabra of Tawnos
is banned." / "No changes"), an effective-date line ("Changes effective as of June 29, 2026."),
and — the gift — a pre-announced calendar: "Next announcement: August 10, 2026", with commentary
confirming a fixed yearly schedule ("our fourth of seven banned and restricted announcements for
the year") `[data-autonomy-wotc-br-announcement]{15}`. URL pattern:
`/en/news/announcements/banned-and-restricted-<month>-<day>-<year>`. Polling design: store the
next-announcement date; on and after that date, probe the predicted URL (plus a small date
window for slips) until it exists; parse the Legacy block; carry the effective date and the
announcement URL as the `reason` provenance for registration. Between announcements, poll cheaply
(the stored date tells you when checking daily actually matters).

**Cross-check (optional, slow):** the standing banned-restricted list page is also
server-rendered (a raw-HTML grep finds "Candelabra of Tawnos") `[data-autonomy-wotc-br-list]{16}`
— usable as a weekly belt-and-suspenders diff, but it is a Nuxt app and brittler to parse; don't
build the primary on it.

**Registration flow:** either signal fires → emit a PENDING event into the status file (§5.3)
with card, date, source URL → surface at session start → human confirms via `eras confirm`
(which calls `append_ban_event`; duplicates raise, so double-detection is harmless). Auto-append
without confirmation is NOT recommended: `BAN_EVENTS` is deliberately fail-loud curated data, and
a scraping false positive would silently corrupt every regime window. The drift alarm remains the
backstop for anything both signals miss.

**MTGJSON as tertiary:** MTGJSON rebuilds daily ("Builds kick off at 1:00AM EST and go live at
9:00AM EST" `[data-autonomy-mtgjson-faq]{19}`) and its card models carry legalities too — but it
adds nothing over Scryfall for detection latency; skip it for B&R.

### 4.2 Set releases: the engine already has the right primitive

`ingestion/releases.py` already scans Scryfall `/sets` into `upcoming` (30-day horizon) and
`recently_released` (14-day lookback) buckets, advisory-only, with the cards-table diff as the
authoritative what's-new signal. The monitoring feature just needs to (a) run `fetch_sets` +
`upcoming_and_recent` on the schedule, (b) put the result in the status file, and (c) trigger the
bulk re-pull + `load_cards_diff` when a set flips into `recently_released`. New-card catalog
currency (hosers/linchpins sweep, `report new-cards`) then keys off the persisted ingest diff as
today. No new external source is needed — one `/sets` GET/day sits far under the "10/second"
general API limit `[data-autonomy-scryfall-rate-limits]{14}`.

### 4.3 P0 side-finding: the Scryfall JSONL migration already broke the refresh leg

The live `/bulk-data` listing exposes **only** `jsonl_download_uri` (gzipped JSON Lines); the
plain-JSON `download_uri` field is gone from every bulk type
`[data-autonomy-scryfall-bulk-api]{12}`, matching the docs' current format statement ("Each bulk
file is a gzipped JSONL (JSON Lines) archive") `[data-autonomy-scryfall-bulk-docs]{11}`. But
`ingestion/scryfall.py` line 107 does `_validate_scryfall_uri(meta["download_uri"])` — a KeyError
on the next non-cached bulk download, for both the oracle and the prices (`default_cards`) paths.
**Fix in the first feature of this epic** (read `jsonl_download_uri`, stream-decompress, parse
JSONL lines; oracle_cards is ~24 MB compressed, default_cards ~77 MB
`[data-autonomy-scryfall-bulk-api]{12}`). This is also the epic's thesis in miniature: upstream
contracts drift silently; scheduled jobs must treat "upstream changed shape" as a first-class,
loudly-surfaced failure mode, not a stack trace in a log nobody reads.

---

## 5. launchd scheduling on the maintainer's Mac

### 5.1 The load-bearing semantics

- **Use `StartCalendarInterval`, not `StartInterval`.** Calendar jobs missed while the machine
  sleeps run once on wake: "Unlike cron which skips job invocations when the computer is asleep,
  launchd will start the job the next time the computer wakes up. If multiple intervals transpire
  before the computer is woken, those events will be coalesced into one event upon wake"
  `[data-autonomy-launchd-plist-man]{23}`. `StartInterval` (every-N-seconds) intervals that fire
  during sleep "will be missed" `[data-autonomy-launchd-plist-man]{23}` — wrong tool for a
  personal machine.
- **Jobs are user LaunchAgents** in `~/Library/LaunchAgents/`, targeted at the `gui/<uid>` domain
  ("targets the domain based on which user it is associated with and is generally more
  convenient") `[data-autonomy-launchctl-man]{24}`.
- **`RunAtLoad` stays false** (default; "should be avoided" per the man page)
  `[data-autonomy-launchd-plist-man]{23}` — the wake-coalescing already covers catch-up.
- **Logs via `StandardOutPath`/`StandardErrorPath`** (files auto-created)
  `[data-autonomy-launchd-plist-man]{23}`.
- **Manual verbs:** `launchctl kickstart gui/$UID/<label>` runs a job immediately "regardless of
  its configured launch conditions" (`-k` restarts a running instance); `launchctl print
  gui/$UID/<label>` shows state incl. last exit status `[data-autonomy-launchctl-man]{24}`.
  Load/unload with `launchctl bootstrap gui/$UID <plist>` / `bootout`.

### 5.2 Concrete plist pattern

One plist per job, `com.legacy-engine.<job>` labels. Daily refresh example:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.legacy-engine.refresh</string>
  <key>ProgramArguments</key><array>
    <string>/Users/andrewclark/dev/legacy-engine/.venv/bin/python</string>
    <string>-m</string><string>legacy_engine.cli</string>
    <string>ops</string><string>scheduled-refresh</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/andrewclark/dev/legacy-engine</string>
  <key>StartCalendarInterval</key><dict>
    <key>Hour</key><integer>7</integer><key>Minute</key><integer>30</integer>
  </dict>
  <key>StandardOutPath</key><string>/Users/andrewclark/dev/legacy-engine/data/ops/logs/refresh.out.log</string>
  <key>StandardErrorPath</key><string>/Users/andrewclark/dev/legacy-engine/data/ops/logs/refresh.err.log</string>
</dict></plist>
```

Key choices: absolute `.venv` interpreter path (launchd inherits no shell env — and the venv is
Python 3.13, not system Python); `WorkingDirectory` = repo root so `PROJECT_ROOT`-relative paths
resolve; timing after ~07:30 local puts the run after upstream's ~18:30 UTC previous-day commit
`[data-autonomy-cache-commits]{2}` and after MTGJSON's 9:00 AM EST publish when a price job needs
it `[data-autonomy-mtgjson-faq]{19}`. Suggested schedule: **daily** upstream pull + ingest +
Scryfall bulk/legalities diff + `/sets` scan + CK prices; **weekly** spare-pipeline exercise +
divergence check. `ThrottleInterval` matters only for respawn storms (default: no more than one
spawn per 10 seconds `[data-autonomy-launchd-plist-man]{23}`) — irrelevant at daily cadence,
leave it unset.

### 5.3 Failure alerting that fits session-start surfacing

launchd has no built-in notification; the right fit for this project is a **status file the
session surface reads** (same shape as the substrate snapshot):

- Every scheduled job's last act — success OR failure — is writing
  `data/ops/status/<job>.json`: `{job, started_at, finished_at, ok, summary, pending_actions[]}`.
  Wrap the job in a runner that catches all exceptions so the status file is written even on
  crash (exit-code-only failures would otherwise be visible only via `launchctl print`).
- `pending_actions` carries the human loop: detected-but-unregistered B&R events (→ `eras
  confirm`), upstream staleness RED (→ flip to spare), spare divergence findings, JSONL-style
  contract breaks.
- A tiny `legacy ops status` CLI leaf prints the aggregate with `// `-prefixed audit lines
  (audit-echo pattern); the SessionStart hook (or a one-line addition to it) cats the same
  aggregate. A job that hasn't written its status within its expected period + grace is itself a
  finding ("job silent since <date>") — that catches the fbettega failure mode (updater dies
  quietly) on our own infrastructure.

---

## 6. Card Kingdom price source — verdict: OPEN, ingest directly

**`https://api.cardkingdom.com/api/v2/pricelist` is a public, unauthenticated JSON endpoint.**
Verified live 2026-07-31: one GET returned 66,775,641 bytes; `meta.created_at` "2026-07-31
14:10:35" (same-day → regenerated at least daily); `data` = 149,977 product rows; each row has
`sku`, **`scryfall_id`**, `name`, `edition`, `is_foil`, `price_retail`, `qty_retail`, `price_buy`,
`qty_buying`, and per-condition (`nm/ex/vg/g`) buy prices/quantities
`[data-autonomy-ck-pricelist]{20}`. The dogfooding pain case validates end-to-end: Lion's Eye
Diamond (Mirage) shows `price_retail` 949.99 / NM buylist 535.00 `[data-autonomy-ck-pricelist]{20}`
— versus the stale ~$55 memory-quote that motivated the idea. Field semantics corroborated by the
established mtgban client: `PriceBuy … 0 = not purchasing`; `ScryfallID … for cross-referencing
with Scryfall API` `[data-autonomy-ck-gopkg]{21}`; a sealed-product endpoint also exists
(`/api/sealed_pricelist`) `[data-autonomy-ck-gopkg]{21}` — not needed.

**Honesty caveats:** there are no published official docs or ToS for the endpoint, and the
response embeds no usage policy `[data-autonomy-ck-pricelist]{20}`; third-party consumption
(mtgban, MTGJSON's cardkingdom provider) is established practice
`[data-autonomy-ck-gopkg]{21}` `[data-autonomy-mtgjson-price-model]{17}` but that is convention,
not a grant. Posture: one fetch/day from the scheduled job, descriptive User-Agent, treat as
revocable — and the fallback is already aggregated: **MTGJSON carries a `cardkingdom` provider
with optional `buylist` and `retail` price points** (`buylist` = "selling cards to this
provider", `retail` = "buying cards from this provider")
`[data-autonomy-mtgjson-price-model]{17}`, with AllPricesToday for current-day pulls and
AllPrices holding "the past 90 days" of history `[data-autonomy-mtgjson-allprices]{18}`, rebuilt
daily `[data-autonomy-mtgjson-faq]{19}`. The MTGJSON route costs an extra uuid→scryfall_id
mapping hop; the direct route joins on `scryfall_id` natively — prefer direct, fall back to
MTGJSON if CK ever closes the endpoint.

**Build shape** (per the parked idea, unchanged by research): CK price table keyed by
`scryfall_id`+printing via the JSON-SSOT/rebuildable-DuckDB pattern; vendor dimension on the
price layer; buylist-vs-retail kept distinct; honest-degrade to Scryfall/TCG with a labeled
source tag when a printing is missing. **TCGplayer direct API: moot** — CK is open, and MTGJSON's
`tcgplayer` provider already supplies TCG retail+buylist `[data-autonomy-mtgjson-price-model]{17}`;
docs.tcgplayer.com documents no public application path for new API keys (checked 2026-07-31).

---

## 7. Implementation notes (for epic-design)

**Suggested feature seams** (not a decomposition — epic-design owns that):

1. **Scryfall JSONL fix** — unblocks everything downstream; smallest possible PR; regression test
   against a recorded `/bulk-data` response (§4.3).
2. **Scheduled refresh + status files** — the `ops scheduled-refresh` runner (mirror → ingest →
   bulk diff → sets scan), status JSON contract, `legacy ops status`, session-start line, plists
   + a `docs/` runbook for `launchctl bootstrap`/`kickstart`.
3. **B&R monitor** — legalities-diff detector + WotC announcement poller + pending-registration
   flow into `eras confirm` (§4.1).
4. **Hot spare** — fork pin, spare venv, weekly exercise plist, divergence check, staleness
   detector + flip flag (§3.2–3.3). MTGO-only first; Melee leg optional behind its account.
5. **CK prices** — ingest + vendor dimension (§6).

**Pre-mortem, the three ways this goes wrong:**

- *The spare silently rots.* A spare that isn't exercised is theater — the weekly run + divergence
  check IS the feature; its status file must go RED when it hasn't run or hasn't matched.
- *Auto-registration corrupts the regime table.* Keep the human in the `eras confirm` loop; the
  monitors PROPOSE, `append_ban_event` disposes (it already raises on duplicates).
- *Scheduled jobs fail invisibly.* Every job writes its status file on failure too; "silent since
  <date>" is itself a surfaced finding (§5.3) — we must not reproduce upstream's failure mode
  (dead updater, nobody notices for three weeks `[data-autonomy-outage-issue3]{3}`).

**Out of scope for the hot spare:** full history replication (upstream git is the archive);
Manatraders/CardsRealm legs ("not fully functional" / minor for Legacy
`[data-autonomy-scraper-readme]{6}`); publishing or serving our generated data (license posture,
§3.4); any cloud scheduling substrate (epic decision: local launchd only).

---

## Sources

1. GitHub API — fbettega/MTG_decklistcache repo metadata — https://api.github.com/repos/fbettega/MTG_decklistcache
2. GitHub API — MTG_decklistcache commit log — https://api.github.com/repos/fbettega/MTG_decklistcache/commits?per_page=15
3. MTG_decklistcache issue #3 (July outage + root cause) — https://github.com/fbettega/MTG_decklistcache/issues/3
4. GitHub API — MTG_decklistcache issue list (outage history) — https://api.github.com/repos/fbettega/MTG_decklistcache/issues?state=all&per_page=10
5. GitHub API — mtg_decklist_scrapper repo metadata — https://api.github.com/repos/fbettega/mtg_decklist_scrapper
6. mtg_decklist_scrapper README — https://github.com/fbettega/mtg_decklist_scrapper
7. fetch_tournament.py — https://github.com/fbettega/mtg_decklist_scrapper/blob/main/fetch_tournament.py
8. Client/MTGOclient.py — https://github.com/fbettega/mtg_decklist_scrapper/blob/main/Client/MTGOclient.py
9. Client/MtgMeleeClientV2.py — https://github.com/fbettega/mtg_decklist_scrapper/blob/main/Client/MtgMeleeClientV2.py
10. GitHub API — Badaro/MTGODecklistCache (+Tools, +MTGOFormatData) — https://api.github.com/repos/Badaro/MTGODecklistCache
11. Scryfall docs — Bulk Data Files — https://scryfall.com/docs/api/bulk-data
12. Scryfall live GET /bulk-data (2026-07-31) — https://api.scryfall.com/bulk-data
13. Scryfall docs — Card objects (legalities) — https://scryfall.com/docs/api/cards
14. Scryfall docs — Rate Limits — https://scryfall.com/docs/api/rate-limits
15. WotC B&R announcement, June 29 2026 — https://magic.wizards.com/en/news/announcements/banned-and-restricted-june-29-2026
16. WotC standing Banned & Restricted list — https://magic.wizards.com/en/banned-restricted-list
17. MTGJSON — Price List data model — https://mtgjson.com/data-models/price/price-list/
18. MTGJSON — AllPrices / AllPricesToday — https://mtgjson.com/downloads/all-files/
19. MTGJSON — FAQ (build schedule) — https://mtgjson.com/faq/
20. Card Kingdom live GET /api/v2/pricelist (2026-07-31) — https://api.cardkingdom.com/api/v2/pricelist
21. go-cardkingdom (mtgban) docs — https://pkg.go.dev/github.com/mtgban/go-cardkingdom
22. TopDeck.gg Tournaments V2 API docs — https://topdeck.gg/docs/tournaments-v2
23. launchd.plist(5) man page (Darwin 25.3.0, saved copy) — .research/reference/data-autonomy-upstream/launchd-plist-man.txt
24. launchctl(1) man page (Darwin 25.3.0, saved copy) — .research/reference/data-autonomy-upstream/launchctl-man.txt
25. melee.gg/Terms fetch attempt (error page; ToS unverifiable) — https://melee.gg/Terms

Local grounding (no attestation needed — in-repo): `src/legacy_engine/ingestion/cache.py`,
`banlist.py`, `releases.py`, `scryfall.py`, `config.py`;
`docs/briefs/ingestion-archetype-contracts/fbettega-cache-schema.md` (the CacheItem contract);
`docs/briefs/change-point-detection.md` (the Candelabra detection-latency ground truth).
