---
id: idea-discovery-review-nits
created: 2026-07-11
tags: [analytics, cleanup]
---

Three MINOR notes from the deep review of the discovery engine (PR #36, APPROVE) — polish, not
defects:
1. `_bootstrap_stability` pair mask includes the matrix diagonal (self-pairs always agree) →
   slight uniform upward bias; exact fix `np.fill_diagonal(pair_mask, False)` + re-check the
   0.90 threshold still passes the Doomsday ground truth.
2. Stability excludes pairs that dissolve to noise under resampling (spec-conformant, but heavy
   noise-dissolution isn't penalized — consider a reported noise-dissolution-rate diagnostic).
3. Report vs staged record order signature cards differently in rare negative-Δ-in-top-5 cases
   (cli.py slices then filters; discovered.py filters then caps) — unify.
