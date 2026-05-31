---
id: idea-tuning-sideboard-winrate-reuse
created: 2026-05-31
tags: [generation, advisory, perf, cleanup]
---

Optimization nit surfaced by the `epic-deck-generation` Phase-8 completion review (2026-05-31): a single
`generation.tuning.tune_deck` call runs the heavy `analytics.match_results.compute_card_winrates` full-corpus
scan **3 times** — once in `field_weighted_values`, then twice inside one `recommend_sideboard` call (the
pre-solve value-aware-weighting pass + the post-solve per-matchup-plan pass, both fire when the per-card gate
clears). It is NOT inside a loop and is fast on the current corpus (the smoke test completes in <1s), so this
was deliberately NOT blocked — but it is redundant work.

Fix options (pick at implementation): (a) compute one `CardWinRates` and thread it through
`field_weighted_values` + `recommend_sideboard` (add an optional `rates=`/`card_winrates=` param so callers
can inject a precomputed aggregate); or (b) memoize `compute_card_winrates` per `(con, since, until)` on a
lightweight cache. Option (a) is cleaner (explicit, no hidden cache lifetime) and matches the project's
Ports-&-Adapters / explicit-dependency style. Touches `advisory/sideboard.recommend_sideboard` +
`_field_matchup_values` + `generation/tuning`. Low risk, additive (keep the no-arg path computing internally).

Promote via `/agile-workflow:scope` if tuning ever runs in a hot loop (e.g. tuning many decks in a batch) or
the corpus grows enough that the 3× scan becomes noticeable.
