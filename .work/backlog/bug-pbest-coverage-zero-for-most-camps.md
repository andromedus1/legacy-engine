---
id: bug-pbest-coverage-zero-for-most-camps
created: 2026-08-05
updated: 2026-08-05
tags: [bug, ranking, best-call, honesty]
---

The cross-camp **P(best)** column on the Best Deck / Best Call page computes its candidacy
coverage (`s_cov`) as **exactly 0.0% for 80 of 111 camp rows**, including most of the largest
decks in the format — while those same rows display 30–69% measured coverage in their own
`coverage` column. The result is that the page's headline cross-camp column is `n/a` for the
decks a reader most wants it for, and is instead dominated by camps with almost no current
presence.

Observed 2026-08-05 on a freshly refreshed corpus (through 2026-08-05, field window since the
2026-06-29 Candelabra ban), after a full camp re-discovery:

```
camp                                          share  row cov  s_cov (gates P)  P(best)
Dimir Tempo [Flow State]                       7.8%    67.5%            12.8%     6.6%
Doomsday [The Fantasticar]                     6.5%    39.4%             0.0%      n/a
Azorius Midrange [Phelia, Exuberant Shepherd]  5.1%    69.4%             0.0%      n/a
Grixis Reanimator [Faithless Looting]          3.8%    67.5%             0.0%      n/a
Blue Artifacts [Goblin Welder]                 3.4%    58.0%             0.0%      n/a
Lands [Sphere of Resistance / Ancient Tomb]    2.8%    46.5%             0.0%      n/a
```

Twenty camps have a displayed coverage >= 30% and `s_cov` of exactly 0.0. **Exactly zero, not
small** — that is the signal that these subjects' cells are not landing in the ranking matrix at
all, rather than that they legitimately fail the 5% `_PBEST_SUPPRESS_COVERAGE` gate. It is not a
parent-level effect: `Blue Artifacts [Thoughtcast]` gets 17.6% while `Blue Artifacts [Goblin
Welder]` gets 0.0%.

Candidate site (`scripts/refresh_best_call_ranking.py`, ~line 700):

```python
used_by_subject = {**arch_used, **camp_used}  # label sets are disjoint by construction
rank_cells = {
    (subj, opp): cell
    for subj in potential
    for opp, cell in used_by_subject.get(subj, {}).items()
}
...
coverage = {d: _compute_data_coverage(rank_matrix, rank_field, d) for d in potential}
candidates = [d for d in potential if coverage[d] >= _PBEST_SUPPRESS_COVERAGE]
```

The `.get(subj, {})` silently yields no cells on a key miss, so a subject that isn't keyed the way
`potential` names it degrades to zero coverage and drops out of candidacy with no audit line —
it just renders as `n/a`, which the page's own prose explains as "failed the 5% measured-coverage
candidacy gate (its score would be pure imputation)". For these rows that explanation is false.

**Not a regression.** Verified by running the committed `HEAD` version of the script and the
in-flight `feature-multi-split-matrix-best-call-onepass` working-tree version against the same
corpus: both produce `candidates = 37 of 160` and **80 camps at `s_cov == 0.0`**, with identical
per-camp values. This is pre-existing behaviour, not something the one-pass sweep introduced.

**Why it matters beyond the missing column.** Because only 37 of 160 potential candidates enter
the shared argmax, the probability mass concentrates on whoever survives — so the column currently
reads as if fringe camps were the best decks in the format:

```
P= 23.9%  share 0.7%  n4wk  10  Blue Artifacts [Thoughtseize]
P= 12.6%  share 0.3%  n4wk   5  Ad Nauseam Tendrils [non-Preordain]
P=  6.0%  share 0.0%  n4wk   0  Dimir Tempo [Barrowgoyf]     <- zero decks in the last 4 weeks
```

A camp with **no current decks at all** holds 6% of P(best), while the format's second-biggest
deck shows `n/a`.

Wanted:
1. Find why `_compute_data_coverage` sees no cells for these subjects and fix the key/lookup.
2. Fail loudly instead of silently: if a subject in `potential` resolves to zero cells, emit a
   named audit line (`honest-degrade-marker`) rather than an unexplained `n/a` whose displayed
   reason is wrong.
3. Consider a **presence** term alongside coverage in candidacy — a camp with `recent_4wk == 0`
   arguably should not compete for "best call" at all, independent of the cell-lookup fix.
4. Assert in tests that a camp's `s_cov` is not wildly below its displayed `coverage` — the two
   numbers being this far apart is itself the bug's fingerprint.

Related: `idea-adj-field-wr-recompute-divergence` (same family — two coverage/rate numbers on one
page that are computed on different bases and disagree).
