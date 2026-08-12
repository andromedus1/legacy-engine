---
id: feature-ranking-credible-window-utility-review-fixes
kind: story
stage: implementing
tags: [bug, analytics, advisory, ui, testing]
parent: feature-ranking-credible-window-utility
depends_on: [feature-ranking-credible-window-utility-usefulness-contract]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Credible-window utility standard-review fixes

## Brief

Close every receiver-confirmed finding from the feature's single standard review before publication:

- exclude prior mass only for archetypes affected at the current boundary, not any historical ban;
- record explicit-null stored horizons as real confirmed-ban clamps with both candidates;
- use preceding-regime camp composition for prior-only supported parents;
- serialize exact observed count, prior contribution, and decision share per row, make
  `transition-prior` presence outrank imputation quality, and align first-read/field-basis copy;
- record degraded written artifacts as written and make unavailable utility operationally degraded;
- add hermetic affected/unaffected/new/prior-only, August-10-shaped zero-grounded-but-supported,
  first-read/JS, refresh/status, and compatibility regressions;
- return `observed-thin` when no preceding confirmed regime exists;
- reject a practical call outside the rendered ranked prefix and inconsistent useful/degraded status.

The fix keeps proof-grade production ordering and benchmark authority unchanged, does not rerun the
future-only benchmark, and requires receiver verification rather than a second independent review.
