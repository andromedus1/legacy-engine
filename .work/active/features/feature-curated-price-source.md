---
id: feature-curated-price-source
kind: feature
stage: drafting
tags: [ingestion, generation, hold-for-review]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-04
updated: 2026-06-13
---

Cost/overlap/pivot-budget analysis was unreliable because the Scryfall oracle bulk has usd:null for exactly the expensive cards — reserved-list duals (Underground Sea), and even Null Rod. Add a curated/secondary price source (e.g. Scryfall per-printing prices, TCGplayer, or a maintained override table for reserved-list staples) so deck-cost and pivot-cost features are trustworthy.
