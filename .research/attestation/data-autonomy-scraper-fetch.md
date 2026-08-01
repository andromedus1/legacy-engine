---
source_handle: data-autonomy-scraper-fetch
fetched: 2026-07-31
source_url: https://github.com/fbettega/mtg_decklist_scrapper/blob/main/fetch_tournament.py
provenance: source-direct
source_class: source-code
---

# mtg_decklist_scrapper/fetch_tournament.py — orchestration source

## Summary

The scraper's single entry point. Per source it downloads the tournament list for the
date window, then fetches each tournament's details with retry and writes one JSON file
atomically (temp file + `os.replace`). Load-bearing operational facts: per-request
politeness sleep is 60s for Topdeck ("to avoid rate limits") and 5s for all other
sources; retries go through `run_with_retry(action, sleep_time, max_attempts)` invoked
with 10 attempts; a file that already exists on disk is skipped (`os.path.exists` →
`continue`) — which is why the daily run over a trailing 7-day window is idempotent and
self-backfilling; tournaments with no data, no decks, or all-empty mainboards are
skipped and their empty day-folders removed; all output is teed to `log_scraping.txt`.

## Key passages

> if source_name == "Topdeck": sleep_time = 60  # Longer sleep time for Topdeck to avoid rate limits / else: sleep_time = 5  # Default sleep time for other sources — update_folder

> if os.path.exists(target_file): continue — update_folder (idempotent dedup)

> details = run_with_retry(lambda: source.TournamentList().get_tournament_details(tournament), sleep_time, 10) — update_folder (10 attempts)

> with open(temp_file, 'w', encoding="utf-8") as f: json.dump(details.to_dict(), f, ensure_ascii=False, indent=2) / os.replace(temp_file, target_file) — atomic write

> default=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d") — argparse start_date default (trailing 7-day window)

> configure_logging("log_scraping.txt") — main()

## Structural metadata

Python source at HEAD of `main`, fetched 2026-07-31 via GitHub REST `GET /contents/fetch_tournament.py`
(base64-decoded). ~160 lines reviewed (imports, update_folder, run_with_retry, main argparse).
