---
id: feature-standalone-field-read
kind: feature
stage: drafting
tags: [advisory]
parent: epic-local-meta-support
depends_on: [feature-advise-provenance-flag]
release_binding: null
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Standalone field-read (no deck required)

## Brief
The most insightful advisory output — field composition + field-vulnerability / hate-equity profile —
is currently gated behind supplying a full `--deck`. Expose a standalone field-read that takes just a
field (global, `--provenance`, or custom `--field`) and prints the composition + vulnerability/hate-equity
profile with no deck. Likely a new `advise field` leaf (or `--no-deck` mode). Reuse the existing
field-vulnerability/hate-equity computation from the report path; just decouple it from the deck input.
