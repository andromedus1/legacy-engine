---
id: feature-custom-field-counts-normalization
kind: feature
stage: drafting
tags: [advisory]
parent: epic-local-meta-support
depends_on: [feature-advise-provenance-flag]
release_binding: null
gate_origin: null
created: 2026-06-14
updated: 2026-06-14
---

# Custom fields carry counts + tightened normalization

## Brief
A custom `--field` file is share-only (`counts=None`), so positioning can't model field-share confidence
(Dirichlet backing) for a user-supplied local field — it falls back to point shares. Let custom fields
optionally carry counts (or a confidence proxy / effective-N), feeding the Dirichlet posterior so a
hand-built Boulder field can express uncertainty. Also tighten the custom-field normalization edge cases
(zero-sum, renormalization warnings, Unknown/Conflict handling). Gated-additive: share-only fields keep
working exactly as today.
