---
id: epic-sideboard-core-and-hedge-hedge-allocator
kind: feature
stage: done
tags: [advisory, sideboard, fast-follow]
parent: epic-sideboard-core-and-hedge
depends_on: [epic-sideboard-core-and-hedge-dedicated-core, epic-sideboard-core-and-hedge-output-contract]
release_binding: null
gate_origin: null
created: 2026-06-15
updated: 2026-06-15
---

# Stage-2 hedge allocator (FAST-FOLLOW)

## Brief

Fill the slots the dedicated core left open (up to an operator cap) with **hedge** cards chosen for
robustness against field uncertainty, rather than padding the field already covered. This is the
fast-follow wave — **separable from the v1 core fix**, which already ends the padding on its own.
The hedge optimizes coverage over a *wider* field than the point estimate: reuse `positioning.py`'s
Dirichlet share draws as the ambiguity set (and/or blend the local field toward the global/online
field), with a strong **1-of diversity preference** (reuse the `U_redundancy` concavity — it falls
off fastest here). Adds the **insurance** label that the output-contract feature reserved.

Per the brief this is the NEUTRAL/judgment region: expose the dial (off / expected-coverage /
CVaR-α), default to a mild expected-coverage hedge, and **never let the hedge override a dedicated
core commit**. This feature carries the most open design judgment in the epic (how wide the
ambiguity set, expected vs CVaR, which α) — resolve it in its `/feature-design` pass against the
brief's framing; not pinned here on purpose.

Does NOT change the core or the output shape — it fills reserved slots and sets the insurance label.

## Epic context
- Parent epic: `epic-sideboard-core-and-hedge`
- Position in epic: **fast-follow**, after the v1 core wave. Consumes the dedicated core + the output
  contract's reserved insurance slots. Deferrable — the core fix is independently shippable.

## Inherited design decisions
- Hedging is primarily the operator's job; the model hedges only in flex slots, never overriding a
  core commit.
- Expose an aggressiveness dial (off / expected / CVaR-α); default mild expected-coverage. Don't bake
  in a hedge-aggressiveness constant.
- Diversity-preferring (1-ofs); reuse the concave value's redundancy term.

## Research briefs
- `docs/briefs/sideboard-core-and-hedge.md` §3 (the hedge — DRO/CVaR framing, ambiguity set, the
  judgment dials) — the load-bearing section for this feature.
- `docs/briefs/advisory-methods.md` §2 (the Dirichlet share posterior to reuse as the ambiguity set).

## Foundation references
- `src/legacy_engine/advisory/positioning.py` — Monte-Carlo Dirichlet share draws (the ambiguity set).
- `src/legacy_engine/advisory/field.py` — `FieldDistribution` + Dirichlet `counts`; local→global blend.
- Patterns: [[honest-degrade-marker]], [[objective-search-split]].

## Design + implementation (2026-06-15)
**`_hedge_fill(model, core_cards, *, budget, blend=_HEDGE_BLEND)`**: after the τ-stopped core, fill the leftover slots (budget − core) with diversity-preferring (1-of) insurance picks over a field WIDENED toward uniform (`_HEDGE_BLEND=0.4`) — so the hedge values archetypes the point estimate underweights. Inherits the core's coverage state; never re-picks or displaces a core card (`card in core_cards or card in insurance` guard); breaks when no card adds positive widened coverage. v1 = the brief's default mild EXPECTED-coverage hedge; CVaR/worst-tail is a documented future dial.

**Integration** (`recommend_sideboard`): `hedge: str = "off" | "expected"`; smart-mode (`--smart`) wires `hedge="expected"`. Runs after the core solve, captures `_core_count` first so `natural_budget_count` = the dedicated core (excludes insurance); merges insurance into `final_cards`; `insurance_cards=frozenset(_insurance)`. CLI: per-card `[insurance]` label. `hedge="off"` (default) → byte-identical.

**Files**: `src/legacy_engine/advisory/sideboard.py` (`_hedge_fill`, `_HEDGE_BLEND`, hedge param + block, output-contract core-count fix), `src/legacy_engine/cli.py` (hedge wiring + `[insurance]` label). **Tests**: `tests/test_sideboard.py::TestHedgeAllocator` (5 unit), `TestHedgeIntegrationNonVacuous` (1 — the real-catalog two-tag end-to-end with NON-EMPTY insurance).

**Review (fresh-context deep, required for the riskiest feature): Approve-with-comments, no blockers.** The reviewer empirically validated (200+ checks): the hedge never re-picks/displaces a core card, respects remaining slots, can't loop or exceed budget; `natural_budget_count` is strictly the core; gating is byte-identical; `_coverage_scale` calibration is sound. Two findings:
- **(Important — FIXED in-session)**: the original end-to-end test used a single/2-card catalog → empty insurance → vacuous wiring assertions. Added `TestHedgeIntegrationNonVacuous` (rich default catalog, dominant+small archetype) that produces real insurance and guards the recommend_sideboard↔insurance wiring (insurance non-empty, ⊆ cards, core < total, total ≤ budget).
- **(Accepted tunable — NOT changed)**: `_SMART_REDUNDANCY_FRACTION=0.5` yields an all-1-of core on real data, in mild tension with the brief's "dedicated swaps are 3-4 copies." It's the anti-4/4/4 breadth-first behavior the user explicitly wanted, is exposed via `--redundancy-strength`, and is a labeled tunable to revisit against real boards (the brief itself calls for that calibration). Verified: full suite 2242 green; sideboard suite byte-identical with the hedge off; no new ruff.
