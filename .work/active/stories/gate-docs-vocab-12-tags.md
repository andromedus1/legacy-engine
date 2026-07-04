---
id: gate-docs-vocab-12-tags
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

# Vulnerability-tag vocabulary omits noncreature-reliant + colorless-reliant (10 -> 12)

## Drift category
foundation-doc-assertion

## Location
Docs: docs/ARCHITECTURE.md:190 + docs/briefs/advisory-methods.md:23 and :217-228 · Code: whattoplay.py:746,:755 (docstring 628-632; _NONCREATURE_RELIANT_MAX @479, _COLORLESS_RELIANT_DENSITY @494)

## Current doc text
> vulnerability tags (graveyard-recursion/graveyard-fuel/plays-<color>/combo/low-curve/greedy-manabase/creature-based/low-interaction/storm-reliant/ramp)

## Reality
Epic-2 added noncreature-reliant (creature density < 0.15 — exposes control/combo to broad anti-noncreature counters) and colorless-reliant (colorless nonland-spell density >= 0.15 — exposes to colorless/trigger answers like Consign).

## Required edit
Add both tags to ARCHITECTURE:190's list; add seed-list entries at advisory-methods.md:23 and two tag-table rows (derivation + exposed-hate columns). If advisory-methods frontmatter key_findings changes, re-run scripts/gen_knowledge_index.py.
