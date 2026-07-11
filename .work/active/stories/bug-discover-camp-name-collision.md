---
id: bug-discover-camp-name-collision
kind: story
stage: implementing
tags: [analytics, bug]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-11
updated: 2026-07-11
---

# Bug: discover auto-naming can assign the SAME name to two camps

## Brief
Found in the top-meta discover sweep (2026-07-11): the Lands split produced two distinct camps
BOTH auto-named "Sphere of Resistance" (n=144 with StP/Rishadan Port and n=158 with Ancient Tomb —
genuinely different prison builds sharing the same top signature card). Name collision breaks
`discover apply` semantics: both camps' member decks would get the same `decks.variant` value,
silently merging two clusters the validator just certified as distinct. Also ambiguous in
`discover list`/`promote --variant NAME`.

## Fix sketch
In the naming step (analytics/discovery.py), on collision disambiguate with the next
distinguishing signature card (e.g. "Sphere of Resistance / Swords to Plowshares" vs
"Sphere of Resistance / Ancient Tomb") or a deterministic suffix; add a uniqueness guard +
regression test (two camps sharing a top signature card must get distinct names).
