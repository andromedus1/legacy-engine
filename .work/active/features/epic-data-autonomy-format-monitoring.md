---
id: epic-data-autonomy-format-monitoring
kind: feature
stage: drafting
tags: [ingestion, infra]
parent: epic-data-autonomy
depends_on: [epic-data-autonomy-local-refresh-operations]
release_binding: null
gate_origin: null
created: 2026-08-11
updated: 2026-08-11
---

# Ban/restricted and new-release change monitoring

## Brief

Add a local monitoring step around the scheduled decision-data refresh so format-changing events
do not depend on memory or an ad hoc manual check. Detect candidate Legacy legality changes and new
card releases from attributable upstream evidence, compare them with the engine's last accepted
state, and surface durable pending/clear/unavailable status.

Monitoring is detection, not authority: it must never silently rewrite the B&R ledger, taxonomy,
ranking regime, or card truth. A human must confirm format changes before they become accepted
engine state. Preserve last-good evidence through upstream failures and distinguish “no change”
from “could not check.” This feature does not implement the deferred hot-spare data pipeline,
vendor pricing, rules IR, sideboard modeling, or Modern deployment.

## Acceptance boundary

- Candidate changes retain source, observed-at time, effective/release date when available, and a
  stable identity suitable for acknowledgement.
- Repeated checks are idempotent and do not re-alert acknowledged unchanged evidence.
- Upstream ambiguity or failure produces a loud unavailable/pending state, never a false clear.
- Status integrates with the local refresh operator surface and is covered by hermetic adapters.
