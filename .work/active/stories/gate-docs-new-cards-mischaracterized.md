---
id: gate-docs-new-cards-mischaracterized
kind: story
stage: done
tags: [documentation]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: docs
created: 2026-06-14
updated: 2026-06-14
---

# SPEC + README mischaracterize `report new-cards` as a speculative forecaster

## Drift category
foundation-doc-assertion + readme-staleness (High)

## Location
- Doc: `docs/SPEC.md:49`, `README.md:127`
- Code: `src/legacy_engine/cli.py:1857-1903` (report_new_cards); forecasting is `report_speculate`
  at `cli.py:1906` + `analytics/speculation.py`

## Current doc text
SPEC.md:49 — "**[Built] New-card speculation** — `report new-cards` + `report speculate` forecast
new/pre-data cards … always labeled `PRE-DATA FORECAST`."
README.md:127 — "`legacy-engine report new-cards  # new/pre-data cards with speculative fitness forecast`"

## Reality
`report new-cards` does NOT forecast. It reads the persisted ingest diff written by `refresh cards`
and lists the actual new card *names* ("what's new to test this week"). Only `report speculate`
(and `--new`) produces the `interaction_facts` + role-filtered-analogue forecast labeled
`PRE-DATA FORECAST`.

## Required edit
- SPEC.md:49 — split the two surfaces: "**[Built] New-card surfacing + speculation** — `report
  new-cards` lists card names added in the most recent `refresh cards` diff-ingest run; `report
  speculate` (and `--new`) forecasts a pre-data card's fitness using `interaction_facts` +
  role-filtered analogues, always labeled `PRE-DATA FORECAST`."
- README.md:127 — comment becomes `# card names added in the latest refresh-cards ingest diff`.
Rolling-foundation: replace in place, no historical prose.
