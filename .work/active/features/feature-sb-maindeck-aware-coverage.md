---
id: feature-sb-maindeck-aware-coverage
kind: feature
stage: review
tags: [advisory]
parent: epic-sideboard-scoring-model
depends_on: [feature-sb-field-weighted-scorer]
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Maindeck-aware coverage (stop double-counting axes the deck already answers)

## Brief

Refinement (C) of `epic-sideboard-scoring-model`, on top of the scorer (Feature B). Discount the
coverage the **maindeck already provides** before scoring SB hosers, so the recommender stops
suggesting cards redundant with what the deck already runs.

<!-- Design input below preserved from the folded backlog idea. -->

## Design input (from idea-sb-maindeck-aware-coverage)

The coverage model in `advisory/sideboard.py` weights candidate hosers by `field_share × swing` per
opponent vulnerability tag, but does NOT subtract the answers the *maindeck* already supplies to the
same axis. Found in a dogfooding test-drive: the deck runs 4 Wasteland maindeck (covering the
anti-big-mana-land / ramp axis), yet the SB still recommended Ghost Quarter for "ramp/greedy-manabase"
coverage — redundant land destruction, and Ghost Quarter is a strictly worse Wasteland (ramps the
opponent, no tempo). The solver double-counts an axis the maindeck already addresses.

Fix direction: before scoring SB hosers, discount each vulnerability tag's weight by the coverage the
maindeck already provides to that tag. The recommender is already "maindeck-aware" via
`matchup_pressure` for per-card value, but the coverage-ELEMENT weighting ignores maindeck answers.
Net effect: stop recommending SB cards redundant with what the deck already runs.

---

## Architectural choice

Same extend-in-place principle as Feature B: add a maindeck-coverage **discount** to the element weights in `_build_coverage_model`, reusing the existing oracle→attacks derivation to detect which vulnerability tags the *maindeck* already answers. Gated-additive — absent maindeck-answer data ⇒ no discount ⇒ byte-identical to today.

## Implementation Units

### Unit C1: maindeck-answer coverage detector

**File**: `src/legacy_engine/advisory/sideboard.py`. **Story**: `feature-sb-maindeck-aware-coverage-discount`.

```python
_MAINDECK_DISCOUNT = 0.6   # max fraction of an element's weight a fully-maindeck-covered tag loses
_MAINDECK_SATURATION = 4   # copies of maindeck answers at which coverage of a tag saturates to 1.0

def _maindeck_answer_coverage(main_cards, get_card) -> dict[str, float]:
    """For each vulnerability tag, a saturating [0,1] coverage fraction from MAINDECK cards that
    answer it — reuse the existing oracle→attacks derivation (_derive_attacks_for_promoted-style)
    to map each maindeck card to the tags it attacks (e.g. Wasteland → {ramp, greedy-manabase}),
    weighted by copy count, saturating at _MAINDECK_SATURATION. Pure given resolved cards."""
```

### Unit C2: discount element weights + wire through recommend_sideboard

**File**: `src/legacy_engine/advisory/sideboard.py`. **Story**: same.

- `_build_coverage_model` gains `maindeck_coverage: dict[str, float] | None = None`. When present, after computing each archetype element weight, multiply by `(1 - _MAINDECK_DISCOUNT * maindeck_coverage.get(tag, 0.0))`. Anti-hate `_hate:` pseudo-elements are exempt.
- `recommend_sideboard` computes `maindeck_coverage` from `main_cards` (via C1) and passes it. `None`/empty ⇒ byte-identical.
- Add a `// maindeck-aware: discounted <tag> by <pct> (deck already answers it)` audit line when a discount fires.

**Acceptance Criteria**:
- [ ] A deck with 4 Wasteland maindeck yields a reduced `ramp`/`greedy-manabase` element weight → the recommender stops padding a redundant SB Ghost Quarter (the motivating bug).
- [ ] No maindeck answers detected ⇒ element weights byte-identical to pre-change (regression guard).
- [ ] Discount saturates (5th maindeck answer doesn't over-discount past the `_MAINDECK_DISCOUNT` cap).

## Implementation Order
Single story `…-discount` (C1 → C2). Focused, cohesive; no parallelism needed.

## Testing
- `tests/test_sideboard.py`: `_maindeck_answer_coverage` maps Wasteland→ramp/greedy-manabase with copy-count saturation; discounted element weight vs undiscounted; byte-identical guard with `maindeck_coverage=None`; Ghost-Quarter-not-padded integration test.

## Risks
- **Over-discounting a partially-covered axis** — a maindeck answer that only partly covers a tag shouldn't zero SB support. *Fallback*: `_MAINDECK_DISCOUNT=0.6` cap (never fully removes), saturating curve; both named constants, tunable.
- **Mislabeling a maindeck card's coverage** — reuses the same oracle→attacks derivation Feature A shipped, so it inherits that (reviewed) behavior; conservative by construction.
