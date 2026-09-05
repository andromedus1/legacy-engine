---
id: story-ranking-methodology-session-wrap
kind: story
stage: implementing
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
