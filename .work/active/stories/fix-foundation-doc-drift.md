---
id: fix-foundation-doc-drift
kind: story
stage: done
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

## Resolution

ARCHITECTURE.md: added Module Map rows for `interaction_facts.py`, `analytics/{subgroup,venue,speculation}`,
`analytics/players/{identity,strength,history}`, `archetype/variants.py`, `generation/card_distribution.py`
and `generation/models.py`, `advisory/{collection,acquire,primer,refresh,window}.py`,
`ingestion/{prices,releases}.py`, `models/{collection,variant}.py`, and top-level support modules
(`card_tags.py`, `colors.py`). Updated CLI diagram to show the full command surface including
`seed prices`, `refresh all|cards`, `report subgroup|variants|new-cards|speculate|prices`,
`advise refresh|acquire`, `identify suggest|strong|track`, `generate doctor`,
`generate consensus --variant/--players/--strong`, `report meta --venues/--by-variant`, and `--my-deck`.
Updated Conventions section to enumerate all CLI groups with accurate leaf commands. Stripped rolling-foundation
violations ("previously private in advisory/report.py" and the "migrated from the former charts.py" prose).
Bumped frontmatter `updated: 2026-06-13` and refreshed summary/decisions to reflect collection/prices/
players/variant/venue/speculation subsystems and the honest-degrade policy.

SPEC.md: added Domain Entities rows for Variant, Player, Venue, InteractionFacts. Moved mode-3 gap-discovery
from [Later] to [Built] throughout Pillar 3 (consistent with README and code). Added capability bullets for
prices/acquisition, player-strength, venue split, variant tagging, new-card speculation, deck doctor,
collection-aware acquire, deck refresh, and matchup primer. Updated frontmatter summary/decisions.

