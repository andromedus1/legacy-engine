---
source_handle: data-autonomy-mtgo-client
fetched: 2026-07-31
source_url: https://github.com/fbettega/mtg_decklist_scrapper/blob/main/Client/MTGOclient.py
provenance: source-direct
source_class: source-code
---

# mtg_decklist_scrapper/Client/MTGOclient.py — MTGO source client

## Summary

The MTGO client scrapes public, unauthenticated pages on mtgo.com: the monthly decklist
index at `https://www.mtgo.com/decklists/{year}/{month}` (parsed with BeautifulSoup,
selecting `li.decklists-item` nodes), then each event page, whose decklist payload is
embedded in the HTML as a JavaScript assignment `window.MTGO.decklists.data = {…}` that
the client extracts and parses as JSON. No API key, no login, plain `requests.get`.
This is the lowest-friction source to run as a hot spare — and MTGO is legacy-engine's
primary Legacy source (Challenges + Leagues).

## Key passages

> LIST_URL = "https://www.mtgo.com/decklists/{year}/{month}" / ROOT_URL = "https://www.mtgo.com" — MTGOSettings, lines 26-27

> response = requests.get(tournament_list_url) — line 58 (no auth headers)

> tournament_nodes = soup.select("li.decklists-item") — line 64

> (line for line in html_rows if line.startswith("window.MTGO.decklists.data = ")) — line 110 (embedded-JSON extraction)

> if "decklists" not in event_json: — line 187 (event JSON contract)

## Structural metadata

Python source at HEAD of `main`, fetched 2026-07-31 via GitHub REST (base64-decoded);
line numbers from grep over the decoded file.
