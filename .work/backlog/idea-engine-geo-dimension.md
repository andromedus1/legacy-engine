---
id: idea-engine-geo-dimension
created: 2026-06-04
tags: [ingestion, analytics]
---

Tournaments carry no geographic/location field, so the engine cannot answer its headline use case — preparing for a *local* metagame (e.g. "the meta around Boulder"). This session we proxied with provenance=paper. Add a location dimension where source data allows (Melee/SCG events often expose venue/region), expose --region / --venue filters on meta/tiers/matchups/advise, and gracefully degrade to provenance when unavailable.
