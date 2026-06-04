---
id: idea-curated-price-source
created: 2026-06-04
tags: [ingestion, generation]
---

Cost/overlap/pivot-budget analysis was unreliable because the Scryfall oracle bulk has usd:null for exactly the expensive cards — reserved-list duals (Underground Sea), and even Null Rod. Add a curated/secondary price source (e.g. Scryfall per-printing prices, TCGplayer, or a maintained override table for reserved-list staples) so deck-cost and pivot-cost features are trustworthy.
