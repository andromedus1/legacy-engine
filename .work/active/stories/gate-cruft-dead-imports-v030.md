---
id: gate-cruft-dead-imports-v030
kind: story
stage: done
tags: [cleanup]
parent: null
depends_on: []
release_binding: v0.3.0
gate_origin: cruft
created: 2026-07-11
updated: 2026-07-11
---

# Dead noqa-suppressed import in _print_discovery_report + 3 pre-existing test F401s

## Confidence
Medium (ruff-verifiable; zero runtime use confirmed)

## Findings
1. `src/legacy_engine/cli.py:6582` — `from legacy_engine.analytics.discovery import DiscoveredSplit  # noqa: F401`
   inside `_print_discovery_report`: the only other use is the quoted forward-ref annotation (never
   evaluated); a function-body import doesn't serve the checker. Delete the line.
2. `tests/test_card_winrates.py:14,19,20` — `pytest`, `CardWinRates`, `MatchCoverage` unused (F401,
   pre-existing debt surfaced because the bundle touched the file; bundle actually reduced 6→3).
   `ruff --fix` removes.

## Removal
Delete cli.py:6582; `ruff check --select F401 --fix tests/test_card_winrates.py`. Surgical only.

## Implementation notes (2026-07-11)
Both removals applied: cli.py dead noqa'd import deleted; 3 test F401s ruff-fixed. ruff clean; scoped tests green.
