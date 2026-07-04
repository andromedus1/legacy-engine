---
id: idea-hate-coverability-overvalues-defense-grid
created: 2026-07-03
tags: [advisory, sideboard]
---

# `_hate:` coverage applies no impact factor — Defense Grid false positive (CONFIRMED mechanism)

Field-scoped backtest: Defense Grid recommended at 4 copies; **0%** of 258 Boulder-relevant
top-finisher boards run it. Independent deep review (2026-07-03, pinned f53e6a4) confirmed the
mechanism — stronger than first filed:

1. **`_hate:` element weights are never impact-modulated** (sideboard.py ~1783: `weight =
   interactive_share * _SWING_SOFT`, full stop) — the centrality×symmetry×castability modulation
   runs only for `(archetype, tag)` opponent elements. Post-deflation-fix, real elements are
   ~0.01-0.015 while each hate element is ~0.07-0.09 — and hate weight is identical for every deck
   tag, unconditioned on whether the field actually attacks that axis.
2. **Coverage is binary set-membership** (~1882-1886): any `"_hate"`-attacking card covers every
   `_hate:<tag>` element at full weight; `_build_impact_annotations` skips `_hate` cards, so the
   self-cost never even shows in explainability output.
3. **The `symmetry: "symmetric"` flag is structurally inert for `_hate`-only cards**: the symmetry
   gate fires on `hoser.attacks ∩ my_vulnerability_tags ≠ ∅`, and `"_hate"` is never a deck
   vulnerability tag — empty by construction. Defense Grid's symmetric flag is dead data on every
   code path.
4. **The self-cost model is a binary cliff**: `_ANTI_SYNERGY_MAP` → reactive at fraction ≥0.40;
   Dimir Tempo sits just under, so the tax on its OWN instant-speed FoW/Daze/Brainstorm is priced
   at exactly zero. Domain reality: Defense Grid's protection is own-turn-scoped — right for a
   proactive combo deck, wrong for a deck that operates at instant speed on both turns; the `_hate`
   tag has no notion of protection *kind*.
5. **The removed guard**: pre-`feature-sfv-weights`, the empirical-pool filter (0% adoption) was
   the only thing blocking exactly this false-positive class; the exemption removed it on principled
   grounds with no compensating mechanical discount. Also: the Step 4c cap applies only to
   UNCOVERED hate elements — covered ones keep full weight (~5-10× the largest real element).

**Fix directions** (from the review): impact-modulate `_hate` coverage per covering card (requires a
representable self-cost — e.g. a `protects` field with scope semantics: own-turn vs both-turns);
and/or condition Step-3 hate weights on which tags the interactive field actually attacks; and/or a
graded (not cliff) reactive self-cost. Validate: Defense Grid drops out of the recommended board on
the field-scoped backtest. Relates to [[idea-card-semantics-rules-layer]] (protection-kind semantics).
