---
id: feature-advise-provenance-flag
kind: feature
stage: drafting
tags: [advisory]
parent: epic-local-meta-support
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Thread `--provenance` through the advise commands

## Brief
`report meta/matchups` expose `--provenance online|paper` but the `advise` commands
(positioning/whattoplay/report/sideboard/refresh/acquire) don't — so a user can't run advisory against
a paper-only (or online-only) field. Thread `--provenance` through the advise command surfaces so the
expected field is built from the chosen provenance. Reuse the existing provenance-aware
`build_global_field`/`compute_metashare`/`build_advisory_inputs` plumbing (already accepts provenance).
Gated-additive: absent → current global behavior byte-identical. This is the discoverable, supported
version of the hand-rolled `--field` + paper workflow from the 2026-06-13 dogfood session.
