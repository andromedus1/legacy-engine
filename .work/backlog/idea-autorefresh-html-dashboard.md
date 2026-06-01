---
id: idea-autorefresh-html-dashboard
created: 2026-06-01
tags: [analytics, infra]
---

A live HTML dashboard for the engine's analysis surfaces that stays current on its own. Two coupled pieces:
(1) a scheduled/autonomous data-refresh pipeline (cron-like) that re-pulls tournaments + cards from the
upstream sources and re-labels archetypes so the corpus stays fresh without manual `seed` runs; and (2) a
static HTML report bundle — meta, matchups, tiers, trends, cards, gaps, positioning — regenerated on every
refresh so the dashboard always reflects the latest pull. The interesting design questions (where the
schedule runs, how to detect a successful upstream pull, static-render vs served, how it composes with the
existing `--chart-dir` matplotlib output and the `report` command family) are deferred to `/agile-workflow:scope`.
