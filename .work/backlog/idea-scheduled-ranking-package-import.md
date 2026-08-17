---
id: idea-scheduled-ranking-package-import
created: 2026-08-16
updated: 2026-08-16
tags: [infra]
---

The installed `legacy-engine ops scheduled-refresh` entrypoint completes refresh, labeling, camps,
and eras but fails at ranking publication with `No module named 'scripts'` because
`DefaultDecisionRefreshPorts.write_ranking` imports the repository-only
`scripts.refresh_best_call_ranking` module. The production ranking generator must be importable from
the installed package without relying on repository-root `sys.path`, while preserving direct script
compatibility and last-good atomic publication.
