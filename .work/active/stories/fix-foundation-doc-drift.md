---
id: fix-foundation-doc-drift
kind: story
stage: implementing
tags: [documentation]
parent: null
depends_on: []
release_binding: null
gate_origin: docs
created: 2026-06-13
updated: 2026-06-13
---

# Foundation-doc drift: ARCHITECTURE + SPEC (gate-docs, High)

- ARCHITECTURE.md Module Map missing ~10 new modules (interaction_facts, analytics/{subgroup,venue,
  speculation,players/*}, archetype/variants, generation/card_distribution, advisory/{collection,acquire,
  primer,refresh}, ingestion/{prices,releases}, models/{collection,variant}). Add them.
- ARCHITECTURE.md CLI diagram + Conventions stale: missing report subgroup|variants|new-cards|speculate|
  prices, report meta --venues/--by-variant, generate doctor, generate consensus --variant/--players/
  --strong, identify group, advise refresh|acquire, seed prices, --my-deck; `refresh` is now a group.
- SPEC.md Domain Entities missing Variant, Player, Venue, InteractionFacts; Capabilities still mark mode-3
  gap-discovery [Later] though README/code mark it built (SPEC vs README contradiction).
- Strip rolling-foundation violations in ARCHITECTURE (the "previously private"/"replaces matplotlib"
  migration prose).
Supersedes idea-build-group-doc-drift-and-polish (docs portion).

