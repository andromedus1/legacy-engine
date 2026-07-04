---
id: gate-docs-vocab-12-tags
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

## Resolution
Verified against whattoplay.py:417 (VulnerabilityTag vocabulary comment), :628-632 (`_vulnerability_from_composition` docstring), :479 (`_NONCREATURE_RELIANT_MAX = 0.15`), :492 (`_COLORLESS_RELIANT_DENSITY = 0.15`), :745-755 (tag-add logic), and `data/hosers/legacy.json` (Force of Negation/Spell Pierce attack `noncreature-reliant`; Consign to Memory attacks `colorless-reliant`). Added both tags to ARCHITECTURE.md:190's whattoplay.py row with derivation + attachment-point notes. Added both to advisory-methods.md's key_findings seed list (frontmatter, line 23) and as two new tag-table rows with Derivation/Exposes columns. Frontmatter key_findings changed → re-ran `scripts/gen_knowledge_index.py`; regenerated `docs/knowledge-index.yaml`, `docs/knowledge-index-detail.yaml`, `docs/knowledge-index-nav.yaml` included in this commit.
