---
id: idea-tune-transparency
created: 2026-06-04
tags: [generation]
---

generate tune is opaque and conservative: it reports Value/Coverage numbers with no sense of scale (is 0.0633 good?), converges with "0 swaps" in a way that reads as "optimal" when it really means "no flex-slot improvement", only optimizes flex slots (never suggests *adding* a consensus staple the deck lacks, like Flow State), and discovery mode says "3 candidates below the gate" without naming them. Add scale/interpretation to the metrics, name discovery candidates, and offer add-not-just-swap suggestions.
