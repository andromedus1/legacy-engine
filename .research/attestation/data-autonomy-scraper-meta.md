---
source_handle: data-autonomy-scraper-meta
fetched: 2026-07-31
source_url: https://api.github.com/repos/fbettega/mtg_decklist_scrapper
provenance: source-direct
source_class: api-response
---

# GitHub API — fbettega/mtg_decklist_scrapper repository metadata

## Summary

Repo metadata for the Python scraper that generates the cache. Load-bearing facts:
the repo has **no license** (`license: null` — all-rights-reserved by default, unlike
the GPL-3.0 cache repo), it is pure Python, self-described as an adaptation of Badaro's
work, and was pushed 2026-07-30 (same timestamp family as the cache's daily commit —
the scraper repo receives the submodule-pointer bump). The missing license matters for
the hot-spare plan: GitHub's ToS permits forking within GitHub, and private local use is
low-risk, but there is no explicit grant to modify/redistribute the scraper code.
The repo also has no `.github` directory (verified separately: `GET /contents/.github`
returns 404 for both repos), so the daily run is not GitHub Actions — it runs on the
maintainer's own machine, consistent with the issue-#3 outage explanation.

## Key passages

> {"default_branch":"main","description":"Trying to adapt badaro work in python","language":"Python","license":null,"pushed_at":"2026-07-30T18:33:52Z"} — repo metadata fields

> {"message":"Not Found", ...} — `GET /repos/fbettega/mtg_decklist_scrapper/contents/.github` and `GET /repos/fbettega/MTG_decklistcache/contents/.github` both 404 (no CI workflows in either repo)

## Structural metadata

GitHub REST v3 `GET /repos/{owner}/{repo}` plus two `/contents/.github` probes;
fetched 2026-07-31 via authenticated `gh api`.
