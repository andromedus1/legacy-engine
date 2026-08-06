---
id: gate-patterns-multi-split-one-pass-sweep
created: 2026-08-05
updated: 2026-08-05
tags: [patterns, documentation]
---

Candidate pattern surfaced by the v0.4.0 gate-patterns pass: **one-pass multi-subject matrix
sweep**.

The bundle established a recurring shape — instead of looping a per-subject matrix build once
per split parent, build ONE `build_multi_split_adaptive` plus one `build_multi_split_matrix` per
distinct window date, serving every parent at once, while preserving the per-pair
`max(subj_ban, opp_ban)` fallback window. It is field-for-field identical to the per-subject
path and ~21x cheaper (326s -> 15s on the live corpus).

Non-test call sites (6):
- `src/legacy_engine/analytics/matchup.py`
- `src/legacy_engine/advisory/window.py`
- `src/legacy_engine/archetype/discovered.py`
- `src/legacy_engine/analytics/superarchetype/chain.py`
- `scripts/refresh_best_call_ranking.py`
- `scripts/loo_ladder_harness.py`

Clears the 3+ occurrence bar. The distinguishing discipline worth writing down is not the speed
— it is that the migration is only legitimate when paired with a **parity proof**: the retired
per-subject path reconstructed verbatim in-test and diffed field-for-field, plus a symbol-anchored
mutation proving non-vacuity. That pairing is what makes a sweep rewrite safe, and it is the part
a future implementer would otherwise skip.

Ambient/Low — the 20 documented patterns in `.agents/skills/patterns/` do not cover it, but the
shape is already described in detail in the epic bodies, so nothing is at risk today.
