---
id: feature-engine-geo-dimension
kind: feature
stage: drafting
tags: [ingestion, analytics, needs-research, hold-for-review, deferred]
parent: epic-local-meta-support
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-14
updated: 2026-06-15
---

> **DEFERRED 2026-06-15** — parked by decision; not in scope for the current cycle. Local-meta
> Phase 1 already ships the paper-prep workflow; geo stays parked until a location data source is
> chosen. Revisit by lifting `deferred`/`hold-for-review` and running the location-data research.


# Native geographic/region dimension — DEFERRED (needs data source + foundation roll)

## Brief
Tournaments carry no geographic/location field (the `tournaments` table is id/name/date/uri/format/
source/provenance — no location). Natively filtering by region (the headline Boulder use case) requires
a LOCATION DATA SOURCE that does not exist yet: the fbettega cache doesn't structure location, and
parsing it from event names/URIs is unreliable. This phase therefore needs RESEARCH (where does
trustworthy location data come from?) before design, and it ROLLS FOUNDATION DOCS (new geo entity +
ingestion/schema boundary + region filtering across reports/advise) per the epic's strategic decision.

When it lands, add `local:<region>` (and, with an event-tier dimension, `regional`) Venue members to
`analytics/venue.py::resolve_venues` — the `feature-three-venue-meta-frame` comparison/divergence/CLI
layers consume `list[Venue]` and need no change (forward seam already in place).

DEFERRED pending: (1) a location data-source decision (research), (2) confirmation to roll foundation
docs. Not built in this pass. Tagged needs-research.
