---
id: story-fix-best-call-methodology-and-warning-placement
kind: story
stage: review
created: 2026-08-17
updated: 2026-08-17
tags: [bug, ux]
parent: null
depends_on: []
release_binding: null
gate_origin: null
---

# Correct Best Call methodology copy and demote row-level warnings

## Symptom

The two methodology disclosures predate transition-stabilized field shares and localized interval
recovery, so they can imply that the displayed meta share is raw post-ban share and do not explain
why clean-history direct estimates remain separate from Agency grounding. Per-subject `P(best)=n/a`
warnings also fill the first-read audit header even though they are row-level diagnostics.

## Root cause

The report template renders the entire `meta.audit` list into the header and its explanatory prose
was not updated when the decision-field and diagnostic interval-evidence layers shipped.

## Fix approach

Keep the audit payload unchanged, partition row-level ranking warnings at render time, and place them
in one collapsed diagnostics disclosure after the result tables. Correct the existing methodology
copy to name observed versus transition-stabilized field shares, exact clean-interval recovery, and
the diagnostic/authoritative boundary. This reuses the page's existing disclosure pattern, so the
project's mockup convention classifies it as a copy/content correction with no mock required.

## Regression test

`tests/test_refresh_best_call_ranking.py` asserts that the methodology names both field layers and
localized direct evidence, and that ranking-subject warnings are filtered from the header and
rendered in a disclosure below the Subarchetypes section.

## Implementation notes

- Execution capability: focused local repair; the issue is confined to one generated-page template
  and its existing browser-executed regression harness.
- Changed `scripts/best_call_ranking_template.html` to separate observed and effective field
  semantics, explain localized exact-interval estimates and their authority boundary, and partition
  row-level ranking warnings into a collapsed disclosure after the result tables.
- Extended `tests/test_refresh_best_call_ranking.py` with copy-contract assertions and an executed
  DOM regression proving summary audit lines remain in the header while subject warnings move to
  the bottom disclosure.
- Confirmation: the initial two regressions failed before the template change; the report-focused
  ranking/decision/scheduler set passes 74 tests; the live report regenerated successfully with
  197 observed decks, 95 archetype rows, 106 camp rows, and 38,640,366 output bytes.
- Documentation: `docs/analysis/best-call-ranking.md` was independently audited and corrected in
  commit `3da6246`; knowledge-index regeneration and the required planning-doc consistency review
  are handled before story closure.
- Adjacent issues parked: none.

## Review findings

- **Blocker — camp-share exception omitted from page prose.** The first consistency pass found that
  the template said every camp fraction came from current-window decks, while production correctly
  uses the preceding-regime camp fraction for a parent represented only by transition-prior decks.
  The runbook already names the exception. Bounced to implementing to correct both page references,
  extend the copy regression, regenerate the artifact, and re-verify.

## Review correction

- Corrected both camp-share references to distinguish current-window camp fractions from the
  preceding-regime fraction used for a transition-prior-only parent.
- Corrected the count-location wording: the field-basis line, not the compact audit header, reports
  both observed and effective field counts.
- Added both claims to the methodology-copy regression, reran the 74-test focused suite, and
  regenerated the live 38,640,596-byte report successfully.
