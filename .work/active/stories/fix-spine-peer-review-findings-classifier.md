---
id: fix-spine-peer-review-findings-classifier
kind: story
stage: implementing
tags: [ingestion, archetype, bug]
parent: fix-spine-peer-review-findings
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Matcher contract fidelity (findings 1-4)

## Brief
Align `archetype/matcher.py` to the Badaro/rule-schema contract: variant uses its own color flag (#1);
Conflict label built from each match's final color-prefixed `_label(...)` in matcher order, no sort/dedupe
(#2); fallback weights main+side copies divided by the number of distinct entries/rows (#3); condition
semantics use `Cards[0]` for single-card types, treat empty `Cards` as non-constraining, and make
`TwoOrMoreInMainOrSideboard` double-count a card present in both zones (#4). Decisions locked in the parent.

## Implementation
Parent `fix-spine-peer-review-findings` → **Unit 1: Matcher contract fidelity**. Regression tests in
`tests/test_matcher.py` with synthetic `RuleSet`s grounded in the rule-schema brief. See parent
`## Design decisions` (fixed inputs) and `## Implementation Units` Unit 1 for exact signatures + acceptance
criteria. Trickiest part = the fallback denominator (#3) — implement and test it first.
