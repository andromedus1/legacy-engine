---
id: epic-sideboard-core-and-hedge-output-contract
kind: feature
stage: done
tags: [advisory, sideboard]
parent: epic-sideboard-core-and-hedge
depends_on: [epic-sideboard-core-and-hedge-dedicated-core]
release_binding: v0.2.0
gate_origin: null
created: 2026-06-15
updated: 2026-06-15
---

# Output contract: <15 return, labels, marginal-coverage curve, uncovered tail

## Brief

Rework what `recommend_sideboard` returns and how the CLI renders it, so the recommendation is
honest about how many cards the field justifies. The `SideboardPackage` may now carry fewer than 15
cards; each card is labeled **commit** (dedicated core) vs **insurance** (hedge); and the output
surfaces the **marginal-coverage curve** (budget→coverage, the 15→11→8→6 table the epic
demonstrated), the **natural dedicated count**, and the **uncovered-field tail with sizes** so the
operator spends any remaining slots deliberately. This is the honest-degrade pattern applied to
sideboard construction — show the curve, name the natural budget, let the human decide.

In the v1 (core-first) wave, the commit labels, the curve, the natural count, the uncovered tail,
and the <15 return all work from the dedicated core alone; the **insurance** label is a no-op slot
that the hedge feature fills when it lands. Touches the `SideboardPackage` shape + its text
renderer; keeps the existing per-matchup OUT/IN plan and "Considering" pool.

Does NOT decide how many cards to commit (dedicated-core feature) or compute the hedge
(hedge-allocator feature) — only the contract + presentation.

## Epic context
- Parent epic: `epic-sideboard-core-and-hedge`
- Position in epic: consumer of the dedicated core; produces the labeled, honest output. Third in
  the v1 wave. The insurance-label half is forward-compatible with the fast-follow hedge.

## Inherited design decisions
- SB may return <15; label commit vs insurance; surface the marginal-coverage curve + uncovered tail
  (honest-degrade aligned).
- Keep the existing per-matchup plan + Considering pool.

## Research briefs
- `docs/briefs/sideboard-core-and-hedge.md` §"Implementation Notes" (output contract) + §4 (surface
  the knee).
- `docs/briefs/advisory-methods.md` §3 (the existing package shape).

## Foundation references
- `src/legacy_engine/advisory/sideboard.py` — `SideboardPackage`, the renderer.
- Patterns: [[honest-degrade-marker]] (the defining shape — labeled banner + named reason +
  suppressed magnitude; here: <15 + commit/insurance + the curve), [[audit-echo-comment-lines]]
  (`// ...` provenance lines for the curve + tail).

## Design + implementation (2026-06-15)
**Additive `SideboardPackage` fields** (all None/empty defaults → byte-identical for every existing caller): `natural_budget_count: int | None`, `marginal_curve: tuple[(cards, cumulative value)]` (from the greedy trace — its flattening is the knee), `uncovered_tail: tuple[(element_id, weight)]` (top-8 field elements the package doesn't answer), `insurance_cards: frozenset[str]` (empty in v1 — hedge-allocator populates; everything else is "commit").

**Population** (`recommend_sideboard`, gated on `redundancy_strength>0 or tau>0`): natural budget = total committed copies; curve = cumulative `marginal_gain` over the greedy trace; tail = field elements with zero coverage in the final solution, by weight. Forced-budget baseline (both off) → fields stay None/empty.

**Renderer** (`cli.py` advise sideboard): a gated `// natural budget / coverage curve / uncovered field / insurance` block using the [[audit-echo-comment-lines]] `// ` pattern, printed only when `natural_budget_count is not None`. Honest-degrade aligned ([[honest-degrade-marker]]) — surfaces the knee + what's left open instead of asserting a padded 15.

**Files**: `src/legacy_engine/advisory/sideboard.py` (SideboardPackage + population), `src/legacy_engine/cli.py` (gated render block). **Tests**: `tests/test_sideboard.py::TestOutputContract` (5 — fields empty when off; natural budget == committed copies under τ; curve cumulative + 1..N indexed; redundancy also activates; tail is a tuple).

**Review (self, focused)**: purely additive dataclass fields + a gated renderer; the byte-identical guarantee is verified by the 263-test sideboard suite (incl. the CLI render tests) staying green with the contract off. Zero new ruff errors (the 16 cli.py F821s are pre-existing forward-ref hints). No blockers. The per-card commit/insurance *label* in the card list is deferred to the hedge-allocator (which introduces real insurance cards); v1 surfaces the `// insurance` line (empty until then).
