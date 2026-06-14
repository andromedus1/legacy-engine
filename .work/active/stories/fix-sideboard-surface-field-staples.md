---
id: fix-sideboard-surface-field-staples
kind: story
stage: done
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

## Implementation notes

### Promotion policy
When `archetype` is set and the empirical pool is non-empty, pool cards NOT already in `HOSER_CATALOG`
are PROMOTED into the candidate universe via `_build_promoted_candidates`. Promotion is fully gated:
no archetype → no pool → no promotion → byte-identical to pre-fix catalog-only behavior.

### Coverage attribution (`_derive_attacks_for_promoted`)
Pure oracle_text heuristic, priority order:
1. "counter target" / "counter that spell" → `{combo, storm-reliant}`
2. "exile" + "graveyard" → `{graveyard-reliant}`
3. "destroy target creature" / "exile target creature" → `{creature-based}`
4. `staple_role(name) == "free_interaction"` (card_tags) → `{combo, storm-reliant}`
5. "destroy/exile target artifact/enchantment" → `{greedy-manabase}`
6. Fallback: `{combo}` (conservative; warns in `SideboardPackage.warnings`)

### max_copies
Derived from the archetype's `modal_count` for that card in `card_frequencies(board="side")`,
capped at 4. Avoids a second DB call by reusing the freq data already fetched for the pool.

### swing
`_SWING_SOFT` (0.10) for all promoted cards — conservative because attribution is heuristic.

### Colors
Read from the `cards` table VARCHAR column (concatenated WUBRG string, e.g. `"UB"`).
`castable_any_color` derived from `_FREE_SPELL_RE` match on oracle_text.

### Gated-additive proof
- `promoted_candidates=None` → `_build_coverage_model` Step 4b is a no-op.
- `archetype=None` → `recommend_sideboard` never calls `_build_promoted_candidates`.
- All 1842 pre-fix tests pass unchanged; 23 new tests added (181 total sideboard tests).

### Failing-then-passing core test
`TestEmpiricalPromotion.test_fon_and_consign_surfaced_by_recommend_sideboard`:
seeds 10 Dimir Tempo decks all running FoN(2) + Consign(1) in the sideboard → 100% adoption.
Before fix: both absent from `HOSER_CATALOG` → structurally unsurfaceable → test FAILS.
After fix: both promoted → appear in `pkg.cards` → test PASSES.

