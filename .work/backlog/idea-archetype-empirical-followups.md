---
id: idea-archetype-empirical-followups
created: 2026-06-13
tags: [advisory, generation]
---

Non-blocking follow-ups from the review of feature-archetype-empirical-recommendations (approved):

1. **(Medium) Forward `archetype` in `advisory/report.py`'s `recommend_sideboard` call (~line 325).**
   `resolved_archetype` is in scope (~203/215) but not passed, so the empirical-pool filter is a
   silent no-op in the `advise report` path (anti-synergy still fires). One-line wiring fix to
   complete the feature's stated cross-surface scope.
2. **(Medium) Chalice `low_curve` block relies on the empirical pool for realistic decks.** Force of
   Will's nominal CMC 5 lifts a Dimir Tempo deck's avg non-land CMC to ~1.86 (> the 1.5 threshold),
   so `low_curve=False` and Chalice is only blocked via the empirical-pool backstop (when archetype
   data exists). Consider excluding alternative-cost "free" pitch spells (FoW/Force of Negation/Daze)
   from the CMC average, or using a one-drop-count signal instead of avg CMC.
3. **(Low) Stale docstring** in `advisory/sideboard.py` (~line 44): says reactive threshold `> 0.55`;
   actual constant is `_REACTIVE_FRACTION_THRESHOLD = 0.40`. Cosmetic.
