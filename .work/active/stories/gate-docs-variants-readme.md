---
id: gate-docs-variants-readme
kind: story
stage: implementing
tags: [documentation]
parent: null
depends_on: []
release_binding: v0.1.0
gate_origin: docs
created: 2026-06-14
updated: 2026-06-14
---

# README mislabels `report variants` as "per-variant card inclusion divergence"

## Drift category
readme-staleness (High)

## Location
- Doc: `README.md:126`
- Code: `src/legacy_engine/cli.py:1646-1725` (report_variants)

## Current doc text
> `legacy-engine report variants --archetype "Dimir Tempo"  # per-variant card inclusion divergence`

## Reality
`report variants` lists registered variants and their meta share within each parent archetype
(per-variant deck count + share of the parent's decks in the latest ban-regime window; zero-match
parents flagged). Card-inclusion divergence is `report subgroup`'s job, not this.

## Required edit
README.md:126 comment becomes: `# registered variants + meta share within the parent archetype`.
