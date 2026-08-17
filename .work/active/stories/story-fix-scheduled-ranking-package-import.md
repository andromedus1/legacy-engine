---
id: story-fix-scheduled-ranking-package-import
kind: story
stage: implementing
created: 2026-08-16
updated: 2026-08-16
tags: [infra, bug]
parent: null
depends_on: []
release_binding: null
gate_origin: null
---

# Make scheduled ranking generation independent of repository import paths

## Brief

Make `legacy-engine ops scheduled-refresh` load the production ranking generator through a
package-owned boundary so an installed console entrypoint can publish the ranking without the
repository root on `sys.path`. Preserve direct `scripts/refresh_best_call_ranking.py` compatibility
and the existing last-good atomic publication behavior.

## Simplification opportunity

Centralize the existing absolute-path script loading pattern behind one small package adapter and
reuse it from scheduled and bundle publication; do not relocate or rewrite the mature generator in
this focused repair.
