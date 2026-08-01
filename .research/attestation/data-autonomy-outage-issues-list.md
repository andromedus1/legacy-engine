---
source_handle: data-autonomy-outage-issues-list
fetched: 2026-07-31
source_url: https://api.github.com/repos/fbettega/MTG_decklistcache/issues?state=all&per_page=10
provenance: source-direct
source_class: api-response
---

# GitHub API — MTG_decklistcache full issue list (outage history)

## Summary

The complete issue list of the cache repo (3 issues total, all closed, all
outage reports). Establishes that the July 2026 outage was not the first: issue #1,
"Automatic Update has stopped", was filed 2026-04-14 and closed 2026-04-17 — a second,
earlier 2026 stall of the automated updater. Issue #2 is a duplicate of #3 filed from
the wrong account and closed within a minute. Two independent multi-day outages within
four months is the empirical fragility baseline for the hot-spare decision.

## Key passages

> {"closed_at":"2026-07-29T03:58:42Z","created_at":"2026-07-23T17:22:02Z","number":3,"state":"closed","title":"Daily auto updates stopped after July 1"} — issues[0]

> {"closed_at":"2026-07-23T17:21:51Z","created_at":"2026-07-23T17:20:56Z","number":2,"state":"closed","title":"Automatic updates seem to have stopped again (last run July 1)"} — issues[1]

> {"closed_at":"2026-04-17T07:33:49Z","created_at":"2026-04-14T02:02:09Z","number":1,"state":"closed","title":"Automatic Update has stopped"} — issues[2]

## Structural metadata

GitHub REST v3 `GET /repos/{owner}/{repo}/issues?state=all&per_page=10`, jq-projected;
fetched 2026-07-31. The repo has exactly these three issues.
