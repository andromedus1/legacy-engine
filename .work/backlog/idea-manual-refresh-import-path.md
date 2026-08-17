---
id: idea-manual-refresh-import-path
created: 2026-08-16
updated: 2026-08-16
tags: [bug, ops]
---

The documented one-command manual refresh, `.venv/bin/python scripts/refresh_decision_data.py`,
successfully refreshes sources, card coverage, labels, camps, and eras but fails at the final ranking
step with `No module named 'scripts'` unless the repository root is supplied through `PYTHONPATH`.
The last-good HTML is preserved and running the ranking generator with `PYTHONPATH=.` succeeds.
