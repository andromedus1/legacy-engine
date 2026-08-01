# Bibliography — data-autonomy-upstream corpus

Append-only. `N` is the human-readable index; the citation lint resolves by `handle`.

| N | handle | source | url |
|---|--------|--------|-----|
| 1 | data-autonomy-cache-repo-meta | GitHub API — fbettega/MTG_decklistcache repo metadata | https://api.github.com/repos/fbettega/MTG_decklistcache |
| 2 | data-autonomy-cache-commits | GitHub API — MTG_decklistcache recent commit log (cadence + outage window) | https://api.github.com/repos/fbettega/MTG_decklistcache/commits?per_page=15 |
| 3 | data-autonomy-outage-issue3 | MTG_decklistcache issue #3 — "Daily auto updates stopped after July 1" (+ maintainer comments) | https://github.com/fbettega/MTG_decklistcache/issues/3 |
| 4 | data-autonomy-outage-issues-list | GitHub API — MTG_decklistcache full issue list (April + July 2026 outages) | https://api.github.com/repos/fbettega/MTG_decklistcache/issues?state=all&per_page=10 |
| 5 | data-autonomy-scraper-meta | GitHub API — fbettega/mtg_decklist_scrapper repo metadata (no license, no CI) | https://api.github.com/repos/fbettega/mtg_decklist_scrapper |
| 6 | data-autonomy-scraper-readme | mtg_decklist_scrapper README — sources, credentials, CLI, layout | https://github.com/fbettega/mtg_decklist_scrapper |
| 7 | data-autonomy-scraper-fetch | fetch_tournament.py — orchestration, sleeps, retries, idempotent writes | https://github.com/fbettega/mtg_decklist_scrapper/blob/main/fetch_tournament.py |
| 8 | data-autonomy-mtgo-client | Client/MTGOclient.py — mtgo.com decklist pages, embedded JSON, no auth | https://github.com/fbettega/mtg_decklist_scrapper/blob/main/Client/MTGOclient.py |
| 9 | data-autonomy-melee-client | Client/MtgMeleeClientV2.py — Melee login flow + internal endpoints | https://github.com/fbettega/mtg_decklist_scrapper/blob/main/Client/MtgMeleeClientV2.py |
| 10 | data-autonomy-badaro-cache-meta | GitHub API — Badaro/MTGODecklistCache (+Tools, +MTGOFormatData) archived/active state | https://api.github.com/repos/Badaro/MTGODecklistCache |
| 11 | data-autonomy-scryfall-bulk-docs | Scryfall docs — Bulk Data Files (daily, JSONL, 12-24h collection) | https://scryfall.com/docs/api/bulk-data |
| 12 | data-autonomy-scryfall-bulk-api | Scryfall live GET /bulk-data — jsonl_download_uri only (no download_uri) | https://api.scryfall.com/bulk-data |
| 13 | data-autonomy-scryfall-cards-docs | Scryfall docs — Card object legalities field | https://scryfall.com/docs/api/cards |
| 14 | data-autonomy-scryfall-rate-limits | Scryfall docs — Rate Limits (10/s API; *.scryfall.io unlimited) | https://scryfall.com/docs/api/rate-limits |
| 15 | data-autonomy-wotc-br-announcement | WotC B&R announcement June 29 2026 — page structure, next-date line | https://magic.wizards.com/en/news/announcements/banned-and-restricted-june-29-2026 |
| 16 | data-autonomy-wotc-br-list | WotC standing Banned & Restricted list page — server-rendered check | https://magic.wizards.com/en/banned-restricted-list |
| 17 | data-autonomy-mtgjson-price-model | MTGJSON docs — Price List model (providers incl. cardkingdom; buylist+retail) | https://mtgjson.com/data-models/price/price-list/ |
| 18 | data-autonomy-mtgjson-allprices | MTGJSON docs — AllPrices (90-day history) / AllPricesToday | https://mtgjson.com/downloads/all-files/ |
| 19 | data-autonomy-mtgjson-faq | MTGJSON FAQ — daily build schedule | https://mtgjson.com/faq/ |
| 20 | data-autonomy-ck-pricelist | Card Kingdom live GET /api/v2/pricelist — schema, row count, LED spot check | https://api.cardkingdom.com/api/v2/pricelist |
| 21 | data-autonomy-ck-gopkg | go-cardkingdom (mtgban) — CK API endpoints + field semantics | https://pkg.go.dev/github.com/mtgban/go-cardkingdom |
| 22 | data-autonomy-topdeck-api-docs | TopDeck.gg Tournaments V2 API — free keys, 100 req/min, endpoints | https://topdeck.gg/docs/tournaments-v2 |
| 23 | data-autonomy-launchd-plist-man | launchd.plist(5) man page (Darwin 25.3.0) — saved copy | .research/reference/data-autonomy-upstream/launchd-plist-man.txt |
| 24 | data-autonomy-launchctl-man | launchctl(1) man page (Darwin 25.3.0) — saved copy | .research/reference/data-autonomy-upstream/launchctl-man.txt |
| 25 | data-autonomy-melee-terms | melee.gg/Terms fetch attempt — error page; ToS unverifiable | https://melee.gg/Terms |
