---
id: bug-eras-run-bypasses-refresh-lock
created: 2026-08-12
updated: 2026-08-12
tags: [bug, analytics, infra]
---

# `eras run` bypasses the shared decision-data execution lock

Live operations reproduction after confirming the 2026-08-10 Fantasticar ban:

1. `legacy-engine eras run` opened `data/legacy.duckdb` for a full recompute.
2. `legacy-engine ops scheduler run-now` correctly acquired the scheduled-refresh file lock, but
   then failed at the DuckDB boundary because the era process (PID 74489) still held the database.
3. The scheduled attempt failed safely before ranking publication and recorded the exact conflict,
   but this proves the lock is not yet authoritative across every supported production mutation
   entrypoint.

Fix through `/agile-workflow:fix`: make `eras run` acquire the same artifact-identity execution
lock used by scheduled/manual decision refresh, with a hermetic contention regression in both
directions. Preserve the existing DuckDB lock as defense in depth and keep read-only era commands
unlocked. Do not broaden this into a general job queue.
