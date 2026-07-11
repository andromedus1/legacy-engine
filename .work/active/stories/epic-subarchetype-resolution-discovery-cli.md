---
id: epic-subarchetype-resolution-discovery-cli
kind: story
stage: implementing
tags: [analytics, archetype]
parent: epic-subarchetype-resolution-discovery
depends_on: [epic-subarchetype-resolution-discovery-cluster]
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Discovery: staging registry + discover/promote CLI

## Brief
Units 5-6 — the human-confirm surface. Staging-registry models (`DiscoveredSplitRecord` etc.) +
loader/promotion in `archetype/discovered.py` (curated-json-resource-loader pattern; new
`DISCOVERED_VARIANTS_PATH` config const), and the `discover run|list|promote` CLI group (nested-group +
fail-loud-stub, audit-echo `// ...` provenance, honest report even on FAIL). `promote` appends
`VariantRule`s to the curated `legacy.json` + sets `defaults` for the complement.

## Implementation
Parent feature `## Implementation Units` → Unit 5 (models + `archetype/discovered.py`) + Unit 6
(`discover` CLI group in `cli.py`). Tests: `tests/archetype/test_discovered.py` load/stage/promote
round-trip + fail-fast; hermetic CLI `discover run/promote --db <tmp>` (never default DB); FAIL split
still prints the honest report.
