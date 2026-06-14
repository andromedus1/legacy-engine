---
id: fix-sideboard-surface-field-staples
kind: story
stage: implementing
tags: [advisory, quality]
parent: null
depends_on: []
release_binding: null
gate_origin: tests
created: 2026-06-13
updated: 2026-06-13
---

# Sideboard recommender structurally can't surface field staples (ROOT CAUSE)

## Finding (gate-tests, High) — the test-drive root cause
`advisory/sideboard.py::recommend_sideboard` is a coverage solver over a hand-curated ~23-card
`HOSER_CATALOG` that does NOT contain Force of Negation or Consign to Memory. The empirical-pool filter
(feature-archetype-empirical-recommendations) only INTERSECTS the candidate set with the catalog
(`_build_coverage_model` ~line 838 drops catalog cards not in the pool) — it can never ADD a
high-adoption field staple the catalog lacks. So a modal-2 staple at >5% archetype adoption is
structurally unsurfaceable; the recommender produced a graveyard-heavy board (4 Grafdigger's + 3 Nihil)
while the outlier check flagged the missing FoN/Consign.

## Fix
Make the empirical pool ADDITIVE to the candidate universe, not just an intersection filter: high-adoption
archetype sideboard cards should be promotable into the coverage candidate set even if absent from the
hand-curated catalog (with role/coverage attribution derived from card data + interaction_facts where
possible). Encode a failing-then-passing test: seed a corpus where the archetype runs Force of Negation /
Consign at >5% adoption, assert `recommend_sideboard(...).cards` surfaces (or a sanity warning accounts
for) those staples. Supersedes idea-test-drive-findings #3.

