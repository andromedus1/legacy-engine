---
id: new-set-ingestion-and-speculation-analogous-matcher
kind: story
stage: review
tags: [analytics, methodology]
parent: feature-new-set-ingestion-and-speculation
depends_on: []
release_binding: null
gate_origin: null
created: 2026-06-13
updated: 2026-06-13
---

## Design

Carved out of `feature-new-set-ingestion-and-speculation` (Unit 1) because the analogous-card
nearest-neighbour matcher is the one piece with real algorithmic risk, is independently testable from
hand-built `Card`s with no DB, and is reusable (gap-discovery adjacency could consume it later).

### Scope

A pure similarity function over typed card features — **no oracle-text embedding, no learned model**
(we have neither, and the project posture is data-driven, auditable similarity).

```python
@dataclass(frozen=True)
class Analogue:
    card: str
    similarity: float   # [0,1], transparent feature distance
    # the borrowed empirical signal is attached by the fusion unit (Unit 3), not here

def analogous_cards(target: Card, pool: Iterable[Card], *, k: int = 5) -> list[Analogue]:
    """k nearest existing cards to `target` by a transparent weighted feature distance."""
```

Lives in `src/legacy_engine/analytics/speculation.py` (the module Unit 1 establishes; Units 2-3 of the
parent feature extend it).

### Similarity components (transparent, weighted, summed → [0,1])

- **Card-type bucket** — hard filter: creature / instant / sorcery / enchantment / artifact / land /
  planeswalker. A new creature's analogues are creatures, never sorceries. Cross-bucket pairs are
  excluded, not merely down-weighted.
- **Color-set Jaccard** over `Card.colors`.
- **CMC proximity** — `1 / (1 + |cmc_a − cmc_b|)`; "free" spells (`card_tags.is_free_spell`) treated as
  effective CMC 0.
- **Shared role tags** — overlap of `card_tags` roles (`staple_role`, `mana_base_tags`) and
  `interaction_facts` `affects`/`permanence`/`free_cast` (consumed read-only from the sibling feature;
  degrades to `card_tags`-only overlap when interaction facts unavailable — gated-additive).
- **Shared keywords** — Jaccard over keyword cues parsed from oracle_text/type_line.

Weights are explicit module constants (auditable, not magic numbers inline). Result is bounded `[0,1]`,
deterministic, with a stable tie-break (sort by `(−similarity, name)`).

### Test plan (behaviour-derived, no DB)

- A new "Brainstorm-like" cantrip's nearest analogues are the cantrip staples (Ponder/Preordain), not
  creatures (card-type hard filter holds).
- A new dual land's analogues are dual lands, not spells.
- A new free counterspell finds Force-of-Will/Daze-shaped cards via the `free_cast` + role overlap.
- Empty pool ⇒ `[]`; `k` larger than the eligible pool ⇒ returns all eligible, no error.
- Similarity is bounded `[0,1]`; identical card ⇒ similarity 1.0; ordering deterministic on ties.
- `interaction_facts` absent ⇒ matcher still works on `card_tags` signal alone (gated-additive).

### Risks

- **Wrong neighbours ⇒ wrong borrowed prior** (the whole point of carving this out for its own test
  suite). Mitigated by the card-type hard filter, explicit auditable weights, and the parent feature's
  guarantee that the analogues + similarities are *shown* to the human, never hidden behind one number.
- **Over-fitting the weights to a handful of test cards.** Keep components few and justified by the
  Legacy briefs; resist adding more until a concrete forecast needs one.

## Hold

Design complete; held for human review before implementation (parent feature is `hold-for-review`).

## Implementation notes

Implemented 2026-06-13 as part of `feature-new-set-ingestion-and-speculation`.

**Module:** `src/legacy_engine/analytics/speculation.py` — `Analogue` dataclass and `analogous_cards(target, pool, k)`.

**Similarity components (all weights are auditable module constants):**
- Card-type bucket: hard filter — cross-bucket pairs excluded (not down-weighted). Buckets: creature/instant/sorcery/enchantment/artifact/land/planeswalker.
- Colour-set Jaccard (`W_COLOR = 0.25`).
- CMC proximity `1/(1+|cmc_a−cmc_b|)` (`W_CMC = 0.25`); free spells treated as CMC 0.
- Shared role-tag Jaccard over `card_tags` + `interaction_facts` signals (`W_ROLE = 0.25`); gated-additive: degrades to card_tags alone when interaction_facts unavailable.
- Shared keyword Jaccard over oracle_text/type_line (`W_KEYWORD = 0.25`).
- Tie-break: `(-similarity, card_name)` — deterministic, stable sort.

**Tests:** 11 unit tests in `tests/test_speculation.py` class `TestAnalogousCards`. Covers: cantrip finds cantrips, dual-land hard filter, creature hard filter, empty pool, k > pool, similarity bounds, identical-card high similarity, stable tie-break, self-exclusion, free-spell affinity, no-analogue-above-gate. All pass.
