---
id: fix-spine-peer-review-findings-correctness
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

# Rules SHA pinning + validate_deck enforcement (findings 5, 7)

## Brief
True rules pinning (#5): `refresh_rules` checks out a configured `MTGOFORMATDATA_SHA` and fails if the
post-checkout HEAD doesn't match, instead of recording whatever HEAD was cloned/pulled. Deck validation
(#7): `validate_deck` rejects nonpositive counts and enforces category bans — ante/offensive via a
name-enumerated `CATEGORY_BANNED_NAMES` set, plus an optional injected `type_line_of` resolver for
Conspiracy/Attraction/Sticker types (skipped when absent, per Ports & Adapters).

## Implementation
Parent `fix-spine-peer-review-findings` → **Unit 2 (rules_vendor.py + config.py)** and **Unit 3
(banlist.py + models/banlist.py)**. Pin SHA = `e056bc7d63c0138091986ce1696c705bc7dee296`. Tests in
`tests/test_rules_vendor.py` (fake runner asserts fetch/checkout/verify; mismatch raises) and
`tests/test_banlist.py` (nonpositive counts, category-banned names, injected type_line_of, None path).
See parent `## Implementation Units` Units 2-3 for signatures + acceptance criteria.
