---
id: bug-knowledge-index-omits-research-analysis
created: 2026-08-20
updated: 2026-08-20
tags: [docs, infra]
---

`scripts/gen_knowledge_index.py` currently discovers only `docs/**/*.md`, despite the active
knowledge-index contract requiring current Agentic Research artifacts under `.research/analysis/`
to be indexed. A successful regeneration after creating
`.research/analysis/campaigns/doomsday-splash-variants/parent.md` remained at 32 documents and did
not include the new campaign. Fix the generator's discovery and exclusion behavior without
hand-editing the generated YAML layers, then add a regression test proving a conformant
`.research/analysis/` artifact is discoverable while attestation/reference tiers remain excluded.
