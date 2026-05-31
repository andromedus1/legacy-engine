---
id: fix-tuning-sideboard-winrate-reuse
kind: story
stage: done
tags: [generation, advisory, perf, cleanup]
parent: null
depends_on: []
release_binding: null
gate_origin: null
created: 2026-05-31
updated: 2026-05-31
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

## Resolution (2026-05-31)
Threaded ONE `CardWinRates` through the tune: `tune_deck` computes `compute_card_winrates` once and passes it (new optional `card_winrates=` param, default-None/additive) to `field_weighted_values` and `recommend_sideboard`, which forwards it to both its `_field_matchup_values` passes. Window-consistent (all use `eff_since/eff_until`). 3x → 1x scan per tune_deck. Guard test `test_tune_deck_computes_card_winrates_exactly_once` asserts the call count. Suite 969 green; existing callers unaffected (no-arg path still computes internally).
