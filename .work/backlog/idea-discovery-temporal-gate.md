---
id: idea-discovery-temporal-gate
created: 2026-07-11
tags: [analytics, archetype]
---

**Era-cluster confound in subarchetype discovery** (era audit finding 2): clustering an 18-month
pool lets new-card signatures date-stamp clusters — 27/46 ranked camps were time clusters (e.g.
Dimir Reanimator [non-Troll] median 2025-08, 0.3% current; Izzet [Delver classic]=old lists vs
[Flow State]=current lists are GENERATIONS, not coexisting builds). Fixes to design:
1. `discover run --regime <label>` per-regime windows as the default recommendation;
2. a temporal-mixing Gate C: flag/fail splits whose camps' date distributions separate strongly
   (e.g. KS distance or median-date gap thresholds), with the honest-degrade label "camps may be
   list generations";
3. surface per-camp %current + median date in the discover report (cheap, immediate).
Downstream: re-run discovery per-regime and re-rank best-build (best-build-ranking.html is now a
historical lens).
