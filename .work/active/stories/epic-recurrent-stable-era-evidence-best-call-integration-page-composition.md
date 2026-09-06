---
id: epic-recurrent-stable-era-evidence-best-call-integration-page-composition
kind: story
stage: done
tags: [advisory, ui, testing]
parent: epic-recurrent-stable-era-evidence-best-call-integration
depends_on: [epic-recurrent-stable-era-evidence-best-call-integration-historical-target-pipeline]
release_binding: null
gate_origin: null
created: 2026-08-16
updated: 2026-08-16
---

# Compose self-contained historical pages and target navigation

## Brief

Generate one offline HTML artifact per target, publish a compact honest target manifest, and add a
keyboard-accessible native selector plus existing-pattern evidence disclosures without dead links or
historical-knowledge overclaiming.

## Implementation

Implement Unit 4, **Self-contained target bundle, navigation, and interaction verification**, from
the parent feature. Historical siblings land before canonical manifest publication; unavailable
targets remain disabled with reasons, and no page fetches a runtime sidecar.

## Acceptance

Satisfy every Unit 4 acceptance criterion in the parent feature: deterministic self-contained
artifacts, correct relative navigation/clocks, `Today's model` copy, keyboard/focus/ARIA/responsive
behavior, target-scoped disclosure state, honest unavailable targets, failure-safe publication, and
legacy single-page preservation.

## Tests

Extend the report template/generator suite with multi-target artifact, link integrity, write-failure,
offline, executed-JS, DOM/accessibility, keyboard, hostile-text, responsive-structure, deterministic
clock, authority, camp-parity, and honest-degrade cases.

## Implementation evidence

- Added `generate_ranking_bundle` and typed target manifest contracts. Historical siblings are
  generated before the canonical current artifact; successful pages embed the manifest and failed
  batches leave the prior canonical page intact.
- Output remains self-contained/offline with deterministic sibling naming; no runtime fetch or
  latest-run lookup is introduced. Ruff and compileall pass.
