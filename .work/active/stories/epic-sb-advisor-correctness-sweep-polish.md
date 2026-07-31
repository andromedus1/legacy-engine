---
id: epic-sb-advisor-correctness-sweep-polish
kind: story
stage: implementing
tags: [advisory, cli]
parent: epic-sb-advisor-correctness
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-31
---

# Sweep report polish: near-duplicate clusters + Σ-adoption formatting


# Sweep report polish — near-duplicate clusters + Σ-adoption formatting

Two cosmetic findings from the first validated `advise sweep` runs (2026-07-04):

1. **Near-duplicate clusters**: `combo` and `storm-reliant` winners-only clusters share
   almost identical membership (cards tagged with both), so one root cause renders twice.
   Consider merging clusters whose member sets are (near-)identical, or reporting the tag
   pair as one cluster key.
2. **Σ adoption formatting**: summed adoption renders as e.g. "Σ adoption 5904%" (59.04
   summed fractions × 100). Display as a unitless sum or average instead.

Diagnostic-surface behavior is correct; this is readability only.
