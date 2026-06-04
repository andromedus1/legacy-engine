---
id: idea-report-data-freshness
created: 2026-06-04
tags: [analytics, ingestion]
---

No report surfaces how current the underlying data is, so a stale DB produces confident-looking but outdated output with no warning. Print a 'data current as of <max event date>' (and corpus size) header on every report, and optionally warn when the newest event is older than N days.
