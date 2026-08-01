---
source_handle: data-autonomy-melee-client
fetched: 2026-07-31
source_url: https://github.com/fbettega/mtg_decklist_scrapper/blob/main/Client/MtgMeleeClientV2.py
provenance: source-direct
source_class: source-code
---

# mtg_decklist_scrapper/Client/MtgMeleeClientV2.py — Melee.gg source client

## Summary

The Melee client authenticates as a regular user: it GETs `melee.gg/Account/SignIn` to
extract the `__RequestVerificationToken` CSRF token, POSTs email+password (read from
`melee_login.json`) to `melee.gg/Account/SignInPassword`, and caches session cookies,
re-logging-in when they expire. Data comes from a mix of endpoints: a decklist search
POST at `melee.gg/Decklist/SearchDecklists`, a per-decklist JSON API at
`melee.gg/Decklist/GetTournamentViewData/{decklist_guid}`, and round/standings pages —
with `time.sleep(DELAY_SECONDS)` politeness delays between requests. The client also
builds its card-name normalization map live from `api.scryfall.com/cards/search` with
pagination. Net: a Melee hot-spare leg requires a Melee account whose credentials sit
in a local file, uses undocumented internal endpoints (no official public API), and is
the most ToS-sensitive part of the pipeline.

## Key passages

> login_page = session.get("https://melee.gg/Account/SignIn", headers=classic_headers) — line 94 (CSRF token fetch)

> raise FileNotFoundError("Missing login file: melee_login.json") — line 107

> "https://melee.gg/Account/SignInPassword", — line 129 (credential POST)

> api_url = f"https://melee.gg/Decklist/GetTournamentViewData/{decklist_guid}" — line 342

> tournament_list_url = 'https://melee.gg/Decklist/SearchDecklists' — line 428

> time.sleep(DELAY_SECONDS) — lines 191, 458 (politeness delay)

> url = f"https://api.scryfall.com/cards/search" — line 590 (runtime name-normalizer build)

## Structural metadata

Python source at HEAD of `main`, fetched 2026-07-31 via GitHub REST (base64-decoded);
line numbers from grep over the decoded file.
