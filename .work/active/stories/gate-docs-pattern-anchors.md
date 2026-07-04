---
id: gate-docs-pattern-anchors
kind: story
stage: done
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

## Resolution
Located current anchors directly: `load_hoser_catalog` now at sideboard.py:912, `_load_default_hoser_catalog` at :1044 (bound to `HOSER_CATALOG` at :1056) — updated curated-json-resource-loader.md's table row. The degraded-`MatchupPlan` construct (previously cited 1451-1472) is now at sideboard.py:2447-2470 — updated honest-degrade-marker.md's anchor and its quoted snippet to match the current field order and note-construction logic (two branches: pooled-adaptive-window note vs. plain thin-data note, both feeding the same `note` variable).

Confirmed but NOT fixed (out of scope for batch C — `advisory-window-resolution-block.md` is not among this batch's owned files): `advise_refresh` in that pattern's anchors is indeed stale at cli.py:3053, now actually at cli.py:3613. Flagging for the patterns gate/next drain to pick up.
