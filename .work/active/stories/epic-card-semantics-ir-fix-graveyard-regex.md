---
id: epic-card-semantics-ir-fix-graveyard-regex
kind: story
stage: implementing
tags: [advisory, bug]
parent: epic-card-semantics-ir
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-04
updated: 2026-07-31
---

# Fix _RE_GRAVEYARD to match the "their graveyard" oracle template (Exhume)


# `_RE_GRAVEYARD` misses the "their graveyard" oracle template (Exhume gets no graveyard role)

Surfaced by gate-tests drain v0.2.0 (batch B): restoring a dropped assertion revealed
`whattoplay._RE_GRAVEYARD` doesn't match "their graveyard" — Exhume's actual symmetric template
("each player puts a creature card from their graveyard onto the battlefield") — so
`_card_roles(Exhume)` returns empty and reanimator composition under-counts recursion density.
Honest state: `tests/test_whattoplay.py` carries a strict xfail with full explanation
(test_exhume_has_graveyard_recursion); Animate Dead split into its own passing test.

Fix: extend the regex to the their/each-player possessive templates; re-check which archetype
densities shift (reanimator shells) and whether any vulnerability-tag thresholds need re-pinning.
Card-semantics incident #11 for [[idea-card-semantics-rules-layer]] — another regex-tier miss of a
standard oracle template, strengthening the semantic-IR case.
