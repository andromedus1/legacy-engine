# Documentation Review Report

**Project:** legacy-engine

**Date:** 2026-09-05

**Scope:** Doomsday Variant Rankings implementation, README pointer, SPEC capability row,
ARCHITECTURE module entry, and `docs/analysis/doomsday-variant-rankings.md`.

**Review:** one balanced, fresh, same-harness standard feature-review pass.

**Result:** two documentation/code contradictions found, accepted, and addressed; no other scoped
documentation findings.

The integrated pass compared the feature contract, implementation, tests, report template, CLI
surface, and all four changed documentation surfaces. It checked the report's manual refresh
boundary, exclusive cohort definitions, global external-field inheritance, evidence ledgers,
date windows, uncertainty disclosures, exact-list selection, generated-output location, and links.

## Accepted corrections

1. **Ledger list completeness.** The earlier wording allowed any nonempty card fragment to look like
   a compatible list. Standings now require the subject registration to have known board labels,
   positive counts, at least 60 main-deck cards, no more than 15 sideboard cards, and no
   card banned at the cutoff. Resolved rounds apply the same filter to both participants. Larger
   main decks and short sideboards remain evidence; the recent exact-list selector separately
   requires 60 main plus 15 side cards.
2. **Public date parsing.** The earlier parser could truncate malformed strings into plausible dates.
   The public `--since`, inherited `field.since`, and exclusive `field.until` values now require real
   canonical `YYYY-MM-DD` dates, and field start must precede field end. Database dates continue to
   use the canonical SQL date path.

The runbook now states both boundaries directly. README, SPEC, and ARCHITECTURE remain consistent
with the corrected implementation and need no further expansion.

## Verification boundary

The host is verifying the accepted fixes through the focused checks and final delivery workflow.
The standard review contract calls for one fresh independent pass, so these accepted corrections do
not trigger a second reviewer pass. This report does not assert a final test count or completed CI.
