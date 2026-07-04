---
id: idea-hoser-catalog-new-card-gap
created: 2026-07-04
tags: [advisory, sideboard, curated-data]
---

# Hoser-catalog new-card gap — sweep's unclassified cluster is rank-1 (24 archetypes)

Sweep finding (2026-07-04, validation-gated harness, global current-regime field): the
`unclassified` winners-only cluster is the top-ranked divergence — 24 archetypes, led by
cards the catalog/tag derivation can't attribute:

- **Disruptor Flute — winners-only in 10 archetypes** (Eldrazi 100%, Golgari Landfall 100%,
  Lands 87%, Painter 75%, Show and Tell 70%, Blue Artifacts 63%, …) — the exact
  "systematic gap, not per-deck noise" shape the sweep was built to catch.
- Wrath of the Skies (4 archetypes), Dismember (4), Barrowgoyf (5, tag-missed), Meltdown
  (3), Deafening Silence (3), Magus of the Moon, Price of Progress, …

Likely one root cause: recently-printed cards absent from the curated hoser catalog AND
missed by `_derive_attacks_for_promoted`'s text heuristics. Candidate fixes: catalog refresh
sweep for post-cutoff sets (data-driven: mine the sweep JSON's unclassified members by
adoption), plus derivation-rule gaps (e.g. "each opponent" tax effects, X-damage board
sweeps). Related: [[idea-catalog-lint-vs-db]], [[idea-card-semantics-rules-layer]] (the
error map this feeds). The unclassified cluster size is the tracking metric — re-run
`advise sweep` after any fix.
