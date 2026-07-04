---
id: gate-docs-backtest-field-scope
kind: story
stage: drafting
tags: [documentation]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: docs
created: 2026-07-04
updated: 2026-07-04
---

# advise backtest --field-scope flag undocumented

## Drift category
foundation-doc-assertion

## Location
Docs: docs/ARCHITECTURE.md:197 (backtest row) + :315 (CLI flag enumeration) + README.md:152 (usage, optional) · Code: cli.py:3038-3105, backtest.py:238,:317

## Current doc text
> 'advise backtest ... has its own --since/--until ...'

## Reality
backtest gained --field-scope/--no-field-scope (default ON): tournament-level filter dropping events where < _FIELD_OVERLAP_MIN of labeled decks belong to a --field archetype, with honest-degrade banner at zero candidates.

## Required edit
Add field-scoping to the ARCHITECTURE backtest row + the :315 flag list; optionally the README example.
