---
id: gate-docs-pattern-anchors
kind: story
stage: implementing
tags: [documentation]
parent: null
depends_on: []
release_binding: v0.2.0
gate_origin: docs
created: 2026-07-04
updated: 2026-07-04
---

# Pattern-skill file:line anchors into sideboard.py shifted

## Drift category
pattern-skill-staleness

## Location
Docs: .agents/skills/patterns/curated-json-resource-loader.md:67 (cites sideboard.py:469/574; actual 912/1044) + .agents/skills/patterns/honest-degrade-marker.md:49 (cites sideboard.py:1451-1472; actual ~2456-2465)

## Current doc text
> (stale line anchors)

## Reality
~600 lines were added to sideboard.py across the two epics; the cited constructs moved.

## Required edit
Update the two sideboard.py anchors to current lines (verify at edit time). NOTE for the patterns gate: cli.py anchors in advisory-window-resolution-block.md are long-stale too (advise_refresh cited at cli.py:3053, now 3613) — sweep there.
