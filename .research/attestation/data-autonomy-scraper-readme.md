---
source_handle: data-autonomy-scraper-readme
fetched: 2026-07-31
source_url: https://github.com/fbettega/mtg_decklist_scrapper
provenance: source-direct
source_class: readme
---

# fbettega/mtg_decklist_scrapper — README ("MTG Tournament Fetcher")

## Summary

The scraper's README documents everything needed to run it: sources covered (MTGO,
Melee, Topdeck, Cards Realm, plus partially-functional Manatraders), the credential
files it expects (a Topdeck API key file and a Melee email+password JSON), the CLI
contract (`python fetch_tournament.py <cache_folder> <start_date> <end_date> <source>
<leagues>` with defaults of 7-days-ago → today), Python ≥3.8, a pip requirements
install, logging to `log_scraping.txt`, retry-on-error, and the output layout
`<cache_folder>/<source>/<year>/<month>/<day>/<tournament>.json` — the exact tree
legacy-engine's `discover_legacy_events` already walks. Repo tree (fetched alongside):
`Api_token_and_login/`, `Client/`, `MTG_decklistcache` (submodule), `comon_tools/`,
`models/`, `fetch_tournament.py`, `requirements.txt`, `tests/`. `requirements.txt`
contains exactly: beautifulsoup4, numpy, pytest, python_dateutil, Requests.

## Key passages

> This script fetches tournament data from various Magic: The Gathering platforms, including MTGO, Melee, Topdeck and Cards Realm. — Overview

> [Manatraders] is not fully functional in order to recover standings. The script tries to de-anonymize the masks that replace player names, but this is not always possible — Note

> Add your **API key** to the following file: "Api_token_and_login/api_topdeck.txt" — Topdeck API

> Add your **login credentials** to this file: "Api_token_and_login/melee_login.json" … {"login": "your MTG Melee email", "mdp": "your MTG Melee password"} — MTG Melee Login

> python fetch_tournament.py <cache_folder> <start_date> <end_date> <source> <leagues> — Usage

> `<start_date>`: Start date in `YYYY-MM-DD` format (default: 7 days ago). … `<source>`: … `mtgo` `melee` `topdeck` `manatrader` `cardsrealm` `all` — Arguments

> Make sure you are using Python 3.8 or later. — Python Version

> If an error occurs while fetching tournament data, the script will automatically retry up to five times before failing. — Error Handling & Retry Mechanism (note: the code's `run_with_retry` is actually called with max_attempts=10; README is stale here)

> Tournaments are stored in: `<cache_folder>/<source>/<year>/<month>/<day>/<tournament>.json` — File Storage Structure

## Structural metadata

README.md at HEAD of `main`, fetched 2026-07-31 via GitHub REST `GET /readme`
(base64-decoded). requirements.txt and top-level tree fetched via `GET /contents`.
