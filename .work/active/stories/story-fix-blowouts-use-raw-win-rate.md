---
id: story-fix-blowouts-use-raw-win-rate
kind: story
stage: done
tags: [bug, analytics]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-08-02
updated: 2026-08-02
---

# Restore raw-win-rate blowout classification

## Symptom

The Best Deck / Best Call HTML does not flag blowouts according to the intended raw matchup win
rate definition.

## Root cause

Commit `9b060be` changed both `blowouts()` and the expanded-ledger tint from serialized `c.raw` to
the empirical-Bayes estimate `c.p`. That noise-control change altered the established meaning of
the blowout indicator instead of relying on the existing measured-cell evidence gate.

## Fix approach

Classify full and half blowouts from `c.raw` again, retaining the `c.measured` (`n >= ground_n`,
normally 8) gate and keeping adjusted/shrunk values unchanged for the page's other metrics.
Synchronize the methodology and ledger-key copy, then regenerate the production HTML.

## Regression test

`tests/test_refresh_best_call_ranking.py` asserts that both the aggregate tally and expanded-ledger
highlight branches compare `c.raw`, not `c.p`, at the locked 40%/45% thresholds.

## Implementation notes

- **Execution capability**: direct focused repair; the regression was isolated to one HTML
  template and its owned runbook, so broader implementation fanout was unnecessary.
- **Files changed**: `scripts/best_call_ranking_template.html`,
  `tests/test_refresh_best_call_ranking.py`, and `docs/analysis/best-call-ranking.md`; generated
  knowledge indexes were regenerated normally.
- **Confirmation**: the regression test first failed on the existing `c.p` comparisons, then
  passed after both tally and ledger branches moved to `c.raw`. All 26 page-generator tests and
  the complete 3,531-test suite passed; the production HTML was regenerated and inspected for
  raw-WR comparisons and copy.
- **Adjacent work**: positive inverse bands are tracked separately as
  `story-positive-matchup-edge-highlights`.

## Review (2026-08-02)

**Verdict: approve.** Bounded inline review confirmed that the change is limited to the intended
classification and presentation paths, preserves the measured-cell gate, leaves every ranking
metric unchanged, keeps source and generated HTML copy aligned, and has a regression guard for
both affected branches. No independent or cross-model review was used for this standalone story.
