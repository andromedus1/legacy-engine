---
source_handle: data-autonomy-outage-issue3
fetched: 2026-07-31
source_url: https://github.com/fbettega/MTG_decklistcache/issues/3
provenance: source-direct
source_class: issue-thread
---

# MTG_decklistcache issue #3 — "Daily auto updates stopped after July 1"

## Summary

The issue that reported the July 2026 outage of the fbettega cache (filed 2026-07-23 by
`andromedus1`, closed 2026-07-29 with state_reason "completed"). The maintainer's reply
gives the outage's root cause: the automated scrape runs on his personal server, and a
home move plus hardware changes to that server environment took the script offline. No
monitoring caught it on his side; the report came from a downstream consumer three weeks
in. He restored it manually on 2026-07-28 ("manual fix automatic commit coming soon").
Establishes: the entire upstream pipeline is one person's home server with no failover
and no automated alerting — the single point of failure the hot-spare epic targets.

## Key passages

> Noticed the daily update commits stopped after July 1 (last thing in the repo is a manual commit on July 2). Possibly the same kind of upstream hiccup as in March, but wanted to flag it in case the updater died quietly. — issue body, andromedus1, 2026-07-23

> I've recently been through a home move and made several hardware upgrades/changes to my server environment, which put the automated script on hold. I haven't had the chance to look into it yet, but I'll be getting it back up and running shortly. — comment, fbettega, 2026-07-24

> manual fix automatic commit coming soon — comment, fbettega, 2026-07-28

> "state":"closed","state_reason":"completed","created_at":"2026-07-23T17:22:02Z","closed_at":"2026-07-29T03:58:42Z" — issue metadata

## Structural metadata

Fetched via GitHub REST v3 (`GET /repos/.../issues/3` + `/comments`) on 2026-07-31;
quotes are verbatim from the issue body and the two maintainer comments.
