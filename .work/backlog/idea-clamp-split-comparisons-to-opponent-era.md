---
id: idea-clamp-split-comparisons-to-opponent-era
created: 2026-08-06
updated: 2026-08-06
tags: [analytics, methodology, honesty]
---

**Guard wanted: never compute a build-vs-build (or camp-vs-camp) matchup delta over a window
wider than the opponent's own detected stable era.**

Found 2026-08-06 while comparing Boros vs Mardu Energy. To get enough sample for a per-matchup
split, the comparison ran from `2025-08-01` — a window that straddles the pre-Phelia and
post-Phelia generations of the opponent label `Azorius Midrange`.

What that produced:

```
Energy vs Azorius Midrange (window since 2025-08-01)
  Boros  4-10  (28.6%)  95% CI [11.7, 54.6]
  Mardu  9-3   (75.0%)  95% CI [46.8, 91.1]   -> a 46-point "edge"
```

Two things were wrong with it at once:

1. **Era mixing.** The window spans two different decks wearing the `Azorius Midrange` label.
2. **Time concentration.** Six of Boros's fourteen matches land in a single month (2026-05,
   Boros 1-5), across four different pilots — the signature of one event cluster, not a matchup
   property. Outside that month the record is 3-5.

The engine's own era-windowed pooled cell says the opposite: **Energy beats Azorius Midrange
60.5% shrunk / 69.2% raw (n=13)**. Both builds also faced the same opponent camp
(`Azorius Midrange [Phelia]`) with roughly twelve matches each and opposite records.

That single cell carried an entire conclusion ("Mardu is better positioned in the current
meta"). Every correction — dropping it, or substituting the engine's era-windowed value —
flipped the verdict back to Boros by 3+ points.

Same failure family as `idea-consensus-blends-exclusive-build-clusters`, but blending mutually
exclusive **eras of an opponent** rather than mutually exclusive **builds of a subject**.

Two guards wanted:

- When any comparison (ad-hoc or engine-side) slices a subject into sub-builds, **clamp the
  window to `min(subject era, opponent era)`** and say so in the output rather than letting the
  caller pick a wide window to buy sample.
- Surface a **per-cell time-concentration warning** when a large share of a cell's matches fall
  in a single month or single event, since that is what an event-cluster artifact looks like and
  it is invisible in the aggregate rate.
