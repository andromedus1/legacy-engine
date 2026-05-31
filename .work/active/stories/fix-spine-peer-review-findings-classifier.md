---
id: fix-spine-peer-review-findings-classifier
kind: story
stage: done
tags: [ingestion, archetype, bug]
parent: fix-spine-peer-review-findings
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-30
updated: 2026-05-30
---

# Matcher contract fidelity (findings 1-4)

## Brief
Align `archetype/matcher.py` to the Badaro/rule-schema contract: variant uses its own color flag (#1);
Conflict label built from each match's final color-prefixed `_label(...)` in matcher order, no sort/dedupe
(#2); fallback weights main+side copies divided by the number of distinct entries/rows (#3); condition
semantics use `Cards[0]` for single-card types, treat empty `Cards` as non-constraining, and make
`TwoOrMoreInMainOrSideboard` double-count a card present in both zones (#4). Decisions locked in the parent.

## Implementation
Parent `fix-spine-peer-review-findings` → **Unit 1: Matcher contract fidelity**. Regression tests in
`tests/test_matcher.py` with synthetic `RuleSet`s grounded in the rule-schema brief. See parent
`## Design decisions` (fixed inputs) and `## Implementation Units` Unit 1 for exact signatures + acceptance
criteria. Trickiest part = the fallback denominator (#3) — implement and test it first.

## Implementation notes

### Changes made
- **`src/legacy_engine/archetype/matcher.py`** — four targeted fixes:
  1. **Finding #1** (`classify`, line ~112): removed `or arch.include_color_in_name` from variant
     append; each variant now uses `v.include_color_in_name` exclusively.
  2. **Finding #2** (`classify`, Conflict branch): replaced `",".join(sorted({m[0] for m in matches}))`
     with `",".join(_label(base, inc, deck_colors) for base, _bn, inc in matches)` — color-prefixed,
     ruleset order, no sort, no dedupe.
  3. **Finding #3** (`_fallback`): added `sideboard` parameter; numerator now sums copies from both
     `mainboard` and `sideboard`; denominator changed from `sum(mainboard.values())` (total copies)
     to `len(mainboard) + len(sideboard)` (distinct entry rows). Call site in `classify` updated to
     pass `sideboard`.
  4. **Finding #4** (`evaluate_condition`): rewrote to split single-card types (`In*`,
     `DoesNotContain*`) to use `cards[0]` only; `OneOrMore*` / `TwoOrMore*` keep whole-list
     semantics; `TwoOrMoreInMainOrSideboard` now sums per-zone hit counts (double-counts a card in
     both zones); empty `cards` returns `True` (non-constraining).

- **`tests/test_matcher.py`** — added 31 new regression tests across 4 classes:
  - `TestFinding1VariantOwnColorFlag` (2 tests)
  - `TestFinding2ConflictLabel` (3 tests)
  - `TestFinding3FallbackDenominator` (5 tests, via factory fixture)
  - `TestFinding4ConditionSemantics` (11 tests covering empty-Cards, Cards[0] single-card for all 6
    types, TwoOrMoreInMainOrSideboard double-count and cross-zone, OneOrMore whole-list, and
    integrated classify with empty-Cards)

### Deviations
- None from the design spec. The `TwoOrMoreInMainOrSideboard` implementation is exactly the brief
  sketch: `_present(cards, main) + _present(cards, side) >= 2`.

### Conflict analytics-key change flag (Finding #2)
Existing stored `Conflict(...)` labels differ from new form: they were raw-sorted, no color prefix
(e.g. `Conflict(Alpha,Beta)`); new form is color-prefixed in ruleset order (e.g.
`Conflict(Dimir Tempo,Izzet Delver)`). **A re-label pass over stored decks picks up new keys; no
schema migration needed since labels are derived, not authored.** Downstream analytics reading old
Conflict keys should expect the change.

### Test correction
One self-authored test (`test_variant_true_parent_false_has_prefix`) initially used the same name
("Control") for both parent and variant, causing `_parent_of` to resolve the parent first and
return `kind="archetype"`. Fixed by using a distinct variant name ("Taxblade") — the pre-existing
`_parent_of` logic is correct; the test assumption was wrong. No production behavior changed.
