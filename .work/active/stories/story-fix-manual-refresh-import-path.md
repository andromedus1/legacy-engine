---
id: story-fix-manual-refresh-import-path
kind: story
stage: implementing
created: 2026-08-16
updated: 2026-08-16
tags: [bug, ops]
parent: null
depends_on: []
release_binding: null
gate_origin: null
---

# Make the documented manual decision refresh executable directly

## Brief

The documented one-command manual refresh, `.venv/bin/python scripts/refresh_decision_data.py`,
successfully refreshes sources, card coverage, labels, camps, and eras but fails at the final ranking
step with `No module named 'scripts'` unless the repository root is supplied through `PYTHONPATH`.
The last-good HTML is preserved and running the ranking generator with `PYTHONPATH=.` succeeds.

## Simplification opportunity

Make the documented direct script entry point establish one consistent repository import context;
do not require operators to know or supply an undocumented environment override.
