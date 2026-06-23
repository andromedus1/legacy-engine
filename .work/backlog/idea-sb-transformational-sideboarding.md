---
id: idea-sb-transformational-sideboarding
created: 2026-06-15
tags: [advisory, sideboard]
---

Sideboard recommender: credit **transformational sideboarding** (threats, not just answers).

The coverage model values a card only as an ANSWER to an opponent vulnerability tag. It is
structurally blind to transformational sideboarding — bringing in **threats** (e.g. Barrowgoyf,
swapped with Nethergoyf) that dodge removal and grind better vs control/midrange, a standard, strong
Legacy plan. In the test-drive the engine dismissed 2 Barrowgoyf entirely and even mis-tagged it
`'combo'` via the promoted-card fallback.

Fix direction: a way to represent and value a threat-swap / transformational package in the SB
recommender — board out reactive cards, bring in threats vs removal-heavy matchups — so the solver
doesn't ignore or penalize threats that real lists board in. This is exactly the slice of operator
judgment the current coverage objective cannot see (and that the operator-hedge philosophy of
epic-sideboard-core-and-hedge already acknowledges). Scope under/alongside that epic later.
