# Doc Review Report

**Project:** legacy-engine  
**Date:** 2026-09-05  
**Scope:** Deck Rankings delivery; system foundations plus the rankings runbook and README.  
**Passes:** two fresh read-only passes: system consistency, and system + Deck Rankings.  
**Exit gate:** PASS — 0 Critical / 0 High. Two pre-existing Medium findings remain.

Both passes checked the current code, CLI help, scoped cross-references, and sealed evaluation
artifacts. The five indexable planning documents have the required frontmatter. No missing
scoped code/document references or blocking research artifacts were found.

## Corrected during delivery

The module pass found that docs promised local strategic-plan shares while the implementation
neither attached nor rendered them. The independent feature review found the same contract bug.
The publisher now assigns local plan shares; the page shows those shares while leaving plan
performance/floor unavailable and stating the mapped-field coverage. This is a product fix
covered by the local-field feature's accepted review corrections, not a change to the intended
contract. The template regression verifies visible shares and the accompanying explanation.

## Remaining Medium findings

- README lines 40 and 432 retain the old exact claim “3,540 passing.” The suite has grown;
  collection alone is not evidence of a new passing total. This pre-existing count is outside
  the revised Deck Rankings instructions. CI is the authoritative current verification.
- README line 402 says “two-layer knowledge index.” The current generated navigator, full
  catalog, and detail files form three layers, correctly described in AGENTS and CLAUDE.

## Verified decisions

- Performance and minimum-matchup floor are independent priorities; performance breaks floor ties.
- Historical evaluation freezes forecasts before outcomes, separates development and confirmation,
  preserves missing support, and does not gate publication. The sealed development selection was
  doubled prior strength; its small confirmation reversal supports retaining the current default.
- The comparison uses 347.5 development and 92 confirmation directed half-match weights.
  Separate phase Markdown/JSON artifacts preserve both periods.
- Local scenarios preserve supplied evidence semantics, unknown opponent mass, global candidate
  presence, and a separate output destination. The saved historical example contains 107 players,
  including four unclassified Affinity Combo players; its end date is unspecified.
- Build diagnostics compare two or more current camps on the same external field, keep missing
  evidence distinct from disagreement, and expose separate main/side record denominators.

## Validation and limits

System reviewer: 75 focused tests passed, page JavaScript parsed, diff check clean. Module reviewer:
CLI help, source paths, actual saved sample, and sealed evidence values verified. Host presentation
and report verification: 53 tests passed after the accepted local display fixes. Knowledge-index
regeneration reports zero errors and six existing warnings (decision-list length and four orphan
README entry files). Final full CI and generated-page browser results are recorded in the delivery
items and PR. Unrelated research and worktree files were excluded from this review.
