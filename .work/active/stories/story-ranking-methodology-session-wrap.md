---
id: story-ranking-methodology-session-wrap
kind: story
stage: done
tags: [analytics, docs, ui]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-09-05
updated: 2026-09-05
---

# Explain ranking methodology and finish repository handoff

Verify current source/report freshness; expand the existing bottom Method disclosure
with readable data-selection and estimation explanations. Cover recent field versus
historical matchups, published-list denominator, decisive-match inclusion, pair-specific
history, priors, uncertainty, archetype/camp/plan interpretation, local scenarios and
the sealed method comparison. Keep the main report concise and use current payload
dates/counts where useful. Update README/runbook and remove verified stale README claims.

One cohesive standalone story, host-owned implementation and bounded review; a doc
worker owns README/runbook. Existing disclosure prose needs no new mock. Verify against
source code, existing report tests, and browser rendering; regenerate both outputs
without changing analytical payloads. Synchronize the task branch and ready PR, preserve
unrelated uv.lock/Hogaak work, and leave main's older integration history separate.

## Freshness evidence
2026-09-05: upstream fbettega cache HEAD and local HEAD both
`d345273553b3140a14c4561d081cd29d183623e8` (September 3). Today's scheduled refresh
succeeded at 21:20:28 UTC; report corpus_max is September 3, with 1,105 published lists
since August 10. Two existing era alarms remain pending confirmation data. UI-only
rerenders preserve that analytical snapshot; saved local shares are historical.

## Completion and bounded inline review
Expanded the existing Method disclosure with source selection, decisive-round inclusion,
recent field versus pair-specific historical windows, retained Beta priors, field and
matchup uncertainty, plan/build interpretation, local scenarios and the sealed evaluation.
Its dates, list/source counts and effective sample size come from the report payload.
README/runbook now describe the current UI and methodology; stale test-count and two-layer
index claims are removed. Index regeneration: zero errors, six pre-existing warnings.

48 report tests pass. A test's exact old explanatory sentence failed after the prose edit;
removed that low-value copy assertion, retaining its typed-evidence/publication checks.
Chromium checks passed for both regenerated pages at 1440px/390px, including source counts,
evaluation rows, sorting, no removed controls, no page overflow or JS errors. Screenshot
inspected; analytical payloads unchanged. No new research or model change was needed.

Bounded host review approves: methodology claims checked against recent_field,
match_results, best_call_evidence, deck_ranking_projection and deck_ranking code and the
sealed experiment. README edits received targeted doc-worker verification. No independent
code reviewer was used for this standalone story. Repository synchronization uses the
existing task PR; main's older baseline history and unrelated local work remain separate.
