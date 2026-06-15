---
id: fix-venues-regime-default
kind: story
stage: done
tags: [advisory, analytics]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: docs
created: 2026-06-13
updated: 2026-06-14
---

# `report meta --venues` should default to current regime (gate-tests / test-drive)

The new venue comparison surface inherits `report meta`'s full-corpus default, so it shows regime-blended
data (Tron 1%!) unless `--regime current` is added — undercutting the ban-regime honesty the engine is
built around. Default the `--venues` comparison to the current regime (or loudly warn it's full-corpus).
Supersedes idea-test-drive-findings #1.

## Resolution

**Changed:** `src/legacy_engine/cli.py` — in `report_meta`'s `--venues` branch, detect when no explicit window flag was given (`regime is None and since is None and until is None and not all_time`) and set `effective_regime = "current"` before calling `resolve_advisory_window`. The non-venues path is completely unchanged (byte-identical, `adaptive_default=False`, full-corpus default preserved).

**Tests added:** `tests/test_cli_venues.py` — two new tests in `TestReportMetaVenues`:
- `test_venues_default_window_is_current_regime_not_full_corpus`: asserts that `report meta --venues online,paper` with no window flag echoes `regime: current` in the window line (not `full-corpus`), and that venue tables still render (test DB dates are inside the current regime).
- `test_non_venues_default_remains_full_corpus`: asserts that plain `report meta` (no `--venues`) still echoes `// window: full-corpus` — gated-additive contract.

**Suite:** 1884 passed (was 1882; +2 new tests). No regressions.

