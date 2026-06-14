---
id: fix-venues-regime-default
kind: story
stage: drafting
tags: [advisory, analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: docs
created: 2026-06-13
updated: 2026-06-13
---

# `report meta --venues` should default to current regime (gate-tests / test-drive)

The new venue comparison surface inherits `report meta`'s full-corpus default, so it shows regime-blended
data (Tron 1%!) unless `--regime current` is added — undercutting the ban-regime honesty the engine is
built around. Default the `--venues` comparison to the current regime (or loudly warn it's full-corpus).
Supersedes idea-test-drive-findings #1.

