---
id: feature-sfv-weights
kind: feature
stage: done
tags: [advisory]
parent: epic-scorer-flexibility-valuation
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Element-weight repair: remove draw-prob deflation; make _hate self-protection coverable

## Brief

Repair the element-weight distortions that deflate real coverage and let uncoverable needs crowd it out. (1) Remove the uniform `draw_prob(1)≈0.4` deflation from the *element weight* impact multiplier (it belongs only in the per-copy taper, not in the element's base weight) — folds idea-scorer-element-weight-drawprob. (2) Represent protective/counter-hoser cards (Veil of Summer, Defense Grid, Carpet of Flowers, …) so the dominant `_hate:` self-protection pseudo-elements become **coverable** — turning dead crowding weight into real, servable coverage. Preserve byte-identical behavior where inputs are absent (honest-degrade). Prerequisite for breadth-objective: aggregation is meaningless while the weights it sums are deflated/crowded.

## Epic context

- Parent epic: `epic-scorer-flexibility-valuation`
- Position: foundation — no deps; prerequisite for breadth-objective; parallel with attachments

## Inherited design decisions

- **Pure mechanics; NO empirical prior in scores** — value flexibility from first principles; the backtest is a divergence diagnostic + acceptance gate, never a score input.
- **Breadth mechanism = reformulate the coverage objective to true submodular marginal-gain** (a card credited by its total marginal coverage across every element it answers; inherits the 1−1/e greedy guarantee).
- **Make protective cards coverable** (`_hate:` self-protection becomes real coverage, not uncoverable crowding).


## Research briefs

- [`docs/briefs/scorer-flexibility-valuation.md`](../../docs/briefs/scorer-flexibility-valuation.md) — the design foundation (submodular breadth = marginal gain; CVaR option value under the Dirichlet field; the three distortions; pure-mechanics guardrail). Addresses root causes #2 (deflation) and #3 (_hate crowding). Folds idea-scorer-element-weight-drawprob.

## Acceptance (epic-wide oracle)

Validated via field/window-scoped `advise backtest` on the Dimir Tempo deck + local field: the recommended board's overlap with top-finisher boards improves **via first-principles flexibility value, not an empirical prior**. Residual model-vs-consensus divergence is surfaced, not scored away.

## Design (2026-07-03)

Confined to `advisory/sideboard.py` (`_build_coverage_model`) + `advisory/impact.py` (`ImpactBreakdown`) + tests, per the parent epic's touches list. Two independent distortions, fixed separately.

### Distortion 1 — draw-prob deflation on the element weight

**What was wrong:** Step 2 of `_build_coverage_model` multiplied each impact-modulated `(archetype, tag)` element weight by `impact(best_hoser, archetype, copies=1, ...).score()` — the full 4-factor product `centrality × symmetry × castability × draw_prob`. `draw_probability(1) ≈ 0.4` (the hypergeometric P(draw ≥ 1 copy in a Bo3) with `copies=1`), applied uniformly across every impact-modulated element, so it deflated the whole weight *scale* (not the ranking — it's a near-constant factor) right where the natural-budget τ stop reads absolute magnitude. It also double-counted the draw dimension: the per-copy taper (`_u_redundancy`, itself derived from `impact.draw_probability`) already owns "how many copies should I run."

**Fix:** added `ImpactBreakdown.score_without_draw_prob()` in `advisory/impact.py` — `centrality × symmetry × castability` only, no new signature, no behavior change to the existing `.score()` (still used verbatim by `_build_impact_annotations`'s per-card, actual-copy-count explainability breakdown at `cli.py:2960`, where showing the real draw probability at the recommended copy count is exactly the point — that call site was deliberately left untouched). `_build_coverage_model`'s Step 2 now calls `breakdown.score_without_draw_prob()` instead of `breakdown.score()`. `copies=1` is still passed to `impact()` (only for a possible future copy-count-sensitive `cast_requires` token; none exist today) — the resulting `draw_prob` field is simply never multiplied in. Byte-identical on `opponent_linchpins=None` (the existing gate — no candidate elements are impact-modulated at all when the gate is off).

### Distortion 2 — `_hate:` self-protection coverability

**Investigation first.** Before designing a fix I verified the epic's "no catalog card can cover it" claim empirically rather than assuming it. `_build_coverage_model` Step 4 *already* covers `_hate:<tag>` pseudo-elements for any catalog card carrying `"_hate"` in `attacks` (Veil of Summer / Defense Grid / Carpet of Flowers) — confirmed with a hand-built model where the mechanism works correctly. The real gap for the epic's acceptance-oracle deck (the maintainer's Dimir Tempo, UB) is that all three catalog hate-cards get excluded by filters BEFORE that coverage logic ever runs:
- Veil of Summer / Carpet of Flowers require `G` — genuinely uncastable in a UB deck (correct, not a bug).
- Defense Grid is colorless but gets dropped by the anti-synergy filter when `reactive=True` (it taxes the deck's own instant-speed responses too) — also mechanically correct for a genuinely reactive counter-heavy deck.
- **Newly found in this feature's investigation:** `_empirical_sideboard_pool`-gated `empirical_pool` filtering (active whenever `archetype` is passed to `recommend_sideboard`) *also* drops all three cards regardless of castability, because none of them appear at all in the real Dimir Tempo sideboard corpus (`card_frequencies(con, "Dimir Tempo", board="side")` returns 0% adoption for all three — verified against `data/legacy.duckdb`). This is a real, in-scope, additive bug: the empirical-pool filter exists to ground *opponent-facing* recommendations in what real decks run, but self-protection castability doesn't need "the field has adopted this" validation — it only needs to be castable and non-self-hosing, which the color/anti-synergy filters already decide.

**Architectural options considered:**
1. **Loosen color/anti-synergy filters for `_hate` cards specifically.** Rejected — dishonest. Veil of Summer genuinely needs green mana; Defense Grid genuinely taxes a reactive deck's own answers. Manufacturing servability that doesn't mechanically exist would violate the pure-mechanics/honest-degrade principle this whole epic is built on.
2. **Add compound tag-scoped `_hate:<tag>` attack tokens** (e.g. `attacks={"_hate:combo"}`) so hate-cards intersect against specific deck tags the way opponent-facing `(archetype, tag)` elements do (a real `attacks ∩ deck_tags` model instead of "any `_hate` marker covers everything"). Rejected for THIS feature — none of the three shipped catalog cards are semantically tag-specific (they're general "protect all my stuff" effects), catalog-data changes are out of this feature's confined scope, and adding an unused scoping mechanism with zero real consumer today is speculative complexity a later cruft gate would flag. Left as a documented, backward-compatible extension point for a future catalog-touching feature (bare `"_hate"` would keep meaning "covers every `_hate:<tag>` element"; a card additionally carrying a specific tag would narrow to just that one).
3. **(Chosen) Two-part fix: (a) exempt `_hate`-attacking catalog cards from the `empirical_pool` filter — the real, in-scope bug found above — mirroring the existing precedent that `_hate:` elements are exempt from the Step 3c maindeck-aware discount; (b) cap an `_hate:<tag>` element's weight, but ONLY when it ends up with zero covering candidate after all filters, relative to the model's own largest real `(archetype, tag)` element weight (`_HATE_UNCOVERED_WEIGHT_CAP_RATIO = 1.0`).** This directly fulfills both epic asks: coverability is the primary, real fix (2a removes a genuine over-filtering bug so a castable, non-self-hosing protective card can actually reach the coverage step; case-(b) never fires when a card successfully covers), and the cap is the honest fallback for decks where a genuinely uncastable/self-hosing catalog (the maintainer's Dimir Tempo, once Defense Grid's own anti-synergy legitimately fires, or a deck with no compatible hate card at all) would otherwise let raw field-share-derived hate weight (not itself impact-discounted per opponent, so 3-4x larger than a typical real element on a real field) dominate the ranking for a need nobody can actually serve.

**Real-world validation:** ran `advise sideboard --deck decks/dimir-tempo-current.txt --field decks/local-field-current.txt --archetype "Dimir Tempo"` against the real DB. Before this feature, Defense Grid (0% real-world Dimir Tempo sideboard adoption, confirmed via `card_frequencies`) would have been filtered by `empirical_pool` regardless of castability. After: `compute_deck_anti_synergy_signals` on the real current maindeck returns `reactive=False` (this build is not anti-synergy-flagged for Defense Grid), so with the empirical-pool exemption Defense Grid is now a live, uncapped, genuinely-covering candidate — and the greedy solver picks 4 copies of it in the recommended 15, with no `// hate-uncovered:` cap warning emitted (real coverage, not dead weight). This is exactly the "turn dead crowding weight into servable coverage" outcome the epic asked for, demonstrated on the acceptance-oracle deck, not just a synthetic unit test.

### Implementation units

- **`src/legacy_engine/advisory/impact.py`** — `ImpactBreakdown.score_without_draw_prob()` (new method, no signature changes elsewhere).
- **`src/legacy_engine/advisory/sideboard.py`** (`_build_coverage_model`):
  - Step 2: `weight *= breakdown.score_without_draw_prob()` (was `.score()`).
  - New `_HATE_UNCOVERED_WEIGHT_CAP_RATIO = 1.0` module constant.
  - New `_max_real_element_weight` snapshot (max of Step-2 element weights), taken before Step 3 creates any `_hate:` element.
  - Step 4's empirical-pool filter: added `and "_hate" not in hoser.attacks` exemption.
  - New Step 4c (after Step 4b, before Step 5's functional_group de-dup): for each `_hate:<tag>` element with zero covering candidate in `candidate_covers`, cap its weight at `_HATE_UNCOVERED_WEIGHT_CAP_RATIO × _max_real_element_weight` (only when a real reference weight exists) and emit a `// hate-uncovered: capped ...` audit line (mirrors the existing `// maindeck-aware: ...` audit-line pattern).
  - Docstrings updated (module header, `_build_coverage_model` docstring's B3/anti-hate/empirical-pool sections) to describe both changes and their rationale.

### Testing

`.venv/bin/python -m pytest -q` → **2509 passed** (2500 baseline + 4 new `TestImpactBreakdownScoreWithoutDrawProb` tests in `tests/test_impact.py` + 5 new `TestHateCoverability` tests in `tests/test_sideboard.py`, 0 skipped, 0 gamed). New tests: draw-prob exclusion (product excludes the factor; independent of its value; zero-castability still hard-gates; zero-draw-prob no longer zeroes the score); hate coverability (a covered hate element keeps full natural weight even when it exceeds a real element's weight; an uncovered one is capped to the real-coverage scale with an audit line; a model with no real elements at all leaves the natural weight uncapped rather than zeroing it; the empirical-pool exemption for `_hate` cards; a control test confirming ordinary (non-`_hate`) cards are still filtered by the empirical pool).

**Re-baseline (honest, not loosened):** `TestImpactModulatedWeighting.test_linchpin_hit_outweighs_no_linchpin_data` asserted the exact element-weight formula including a `draw_probability(1)` factor. Updated the two absolute-value assertions to drop that factor — this IS the deflation fix (the RATIO assertion two lines below was already draw-prob-independent and needed no change, since the factor was uniform on both sides of the ratio). Also strengthened `TestCoverageModel.test_veil_of_summer_covers_anti_hate_element`, which previously had a weak `if X in Y and A in B: assert ...` conditional that would silently pass even if coverage never materialized — converted to unconditional assertions (both preconditions are guaranteed given the test's own fixture: Veil of Summer's colors are a subset of the test's `deck_colors`, no anti-synergy signal is supplied) plus an explicit weight-value check, so a real regression in the hate-coverage mechanism can no longer pass silently. No test assertion was loosened; both changes make the suite strictly more precise.

### Risks / follow-ups

- **Gated/scoped:** the draw-prob removal only touches the `opponent_linchpins is not None` element-weight path (byte-identical when that gate is off, unchanged when the whole feature's inputs are absent). The `_hate` cap only fires when `hate_elements_added` is non-empty AND at least one real element exists AND the specific tag ends up with zero covering candidate — every existing hate-related test (Fix 5's interactive-share weight, the maindeck-discount exemption, the reactive-deck anti-synergy filter test) was checked against the new logic and passes unmodified.
- **Left for `feature-sfv-breadth-objective`:** this feature fixes weight magnitude and hate crowding; it does NOT change how a card's coverage across multiple elements aggregates (D1, the concavity/breadth-objective concern) — Force of Negation's `Considering`-pool `gain` is still modest post-fix (verified against the real deck) because breadth aggregation is the sibling feature's job, not this one's.
- **Documented, not implemented:** tag-scoped `_hate:<tag>` compound attack tokens (rejected option 2 above) — a real extension point if a future catalog-touching feature wants narrower protective cards, deliberately not built speculatively here.
- **Escape hatch:** not used — no design gap required re-opening drafting.

Stage advanced `drafting → review` (single-feature-sized; implemented directly in this stride, no child stories spawned, matching the sibling `feature-sfv-attachments` precedent for this epic's foundation-layer features).
