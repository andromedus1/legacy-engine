---
id: epic-data-autonomy-format-monitoring-review-corrections
kind: story
stage: done
tags: [bug, ingestion, infra]
parent: epic-data-autonomy-format-monitoring
depends_on: [epic-data-autonomy-format-monitoring-ops-integration]
release_binding: null
gate_origin: null
created: 2026-08-12
updated: 2026-08-12
---

# Close format-monitor review gaps

## Brief

Resolve the receiver-confirmed standard-review findings across bulk truncation safety, monitor-state
concurrency, dated confirmation, monitor SIGTERM lifecycle, attributable redirect handling, typed
candidate status, and the corresponding architecture assertion. Preserve detection-only authority
and verify the corrected aggregate without commissioning another independent pass.

## Implementation

- Rejects any oracle or prices bulk whose fully streamed row count differs from Scryfall's positive
  `object_count`, preserving both prior mirror and metadata.
- Uses one state-derived `flock` around both monitor and acknowledgement read/transition/write
  transactions; hermetic concurrency coverage proves acknowledgement waits for the active writer.
- Requires normalized card plus WotC effective date for confirmation and retains a typed
  `confirmed` disposition without further pending action.
- Holds catchable SIGTERM behavior across the complete locked refresh/monitor/status lifecycle.
- Persists candidate id, kind, disposition, and name in job status and full audit output.
- Validates each WotC redirect and final URL against HTTPS `magic.wizards.com`, then attributes the
  resolved URL.
- Corrects the architecture integration table to distinguish scheduled detection from manual
  curated acceptance.

Focused correction verification: `85 passed`; changed-module Ruff: clean; knowledge index: 0
errors and the same 6 existing structural warnings.
