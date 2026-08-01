---
source_handle: data-autonomy-cache-repo-meta
fetched: 2026-07-31
source_url: https://api.github.com/repos/fbettega/MTG_decklistcache
provenance: source-direct
source_class: api-response
---

# GitHub API — fbettega/MTG_decklistcache repository metadata

## Summary

GitHub REST API metadata for the tournament-data cache repo legacy-engine mirrors
(`FBETTEGA_CACHE_REPO` in `config.py`). Confirms the repo is live (pushed 2026-07-30),
GPL-3.0 licensed, default branch `main`, ~153 MB (`size` is in KB), and had zero open
issues at fetch time. The size figure bounds the hot-spare storage question: a full
mirror of every format/source since the repo's origin is ~153 MB of JSON, so a
Legacy-only spare tree is far smaller.

## Key passages

> {"default_branch":"main","license":"GPL-3.0","open_issues":0,"pushed_at":"2026-07-30T18:33:50Z","size":156287} — response fields `default_branch`, `license.spdx_id`, `open_issues`, `pushed_at`, `size` (KB)

## Structural metadata

GitHub REST v3 `GET /repos/{owner}/{repo}`; fetched via authenticated `gh api` on
2026-07-31. Fields quoted verbatim from the JSON response (jq-projected).
