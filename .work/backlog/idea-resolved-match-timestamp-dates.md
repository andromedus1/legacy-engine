---
id: idea-resolved-match-timestamp-dates
created: 2026-08-16
updated: 2026-08-16
tags: [analytics]
---

The localized-evidence live refresh failed in `resolve_match_records` because the production
`tournaments.date` column includes timezone-aware ISO timestamps such as
`2025-07-20T09:00:00+00:00`, while the resolved-match path passes the whole value to
`date.fromisoformat`. The evidence selector must accept the corpus' supported date/timestamp storage
shapes without changing the physical-match identity or cutoff semantics.
