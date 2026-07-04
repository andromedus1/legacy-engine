---
id: feature-sb-board-backtest-compute
kind: story
stage: done
tags: [advisory, analytics]
parent: feature-sb-board-backtest
depends_on: []
release_binding: null
gate_origin: null
created: 2026-07-03
updated: 2026-07-03
---

# Backtest recommended boards vs top-finisher boards + CLI

## Brief

New `advisory/backtest.py`: pull top-finisher decklists of an archetype in a window, extract their
sideboards + inclusion%, run `recommend_sideboard` for the same archetype+field, and diff
(overlap / scorer-only / winners-only), gated by winner-sample confidence. New `advise backtest`
CLI leaf renders it with the honest "divergence is a signal, not proof" caveat. The empirical
anchor for the whole scoring model — measures *resemblance to what wins*, never a pass/fail verdict.

## Implementation

Covers parent feature **Units E1 + E2** — see `feature-sb-board-backtest` § Implementation Units for
`BoardBacktest`, `backtest_board`, the `_TOP_FINISHER_QUANTILE`/`_OBSERVED_THRESHOLD` constants, and
acceptance criteria. Files: new `src/legacy_engine/advisory/backtest.py` + `src/legacy_engine/cli.py`;
tests in new `tests/test_backtest.py` (hermetic file-backed tmp DuckDB) + a CLI test with tmp `--db`.

## Implementation notes

**Top-finisher definition.** For each tournament, dedupe `decks`/`standings` by
`lower(trim(player))` (mirrors `analytics.match_results`'s dup/uniq-CTE precedent exactly —
ambiguous normalized names, non-unique within a tournament, are excluded from the join rather
than guessed at). Field size per tournament = `count(*)` over its deduped `standings` rows.
Threshold = `GREATEST(1, CEIL(_TOP_FINISHER_QUANTILE * n_players))` — rounding UP so a quartile
cut on a small tournament (e.g. 4 players) still keeps ≥1 qualifying rank rather than 0. A deck
of the target `archetype` qualifies when its player's dedup'd `standings.rank` is `<=` that
threshold, joined to `tournaments.date` for the `[since, until)` window (same half-open
convention as `card_frequencies`/`regime_windows`). All of this lives in one query,
`_QUALIFYING_DECKS_SQL` in `advisory/backtest.py`.

**Observed frequency.** For the qualifying deck set, a second query pulls `deck_cards` rows
with `board='side'`, deduped to one row per (deck, card) via `SELECT DISTINCT`, joined against
the qualifying-deck keys via a `VALUES` derived table (avoids building a giant `IN` list by
hand). `observed_frequency[card] = distinct_qualifying_decks_running_card / n_winning_decks`
— i.e. presence-only (a card at any copy count in the 15 counts once), matching how
`_OBSERVED_THRESHOLD` reads as "ran this card at all in X% of top finishes," not a copy-weighted
average.

**Scorer input judgment call.** `recommend_sideboard` requires a `deck_maindeck` dict, but a
backtest has no real user decklist to compare against — there IS no "my deck" here, only "the
archetype." Resolved this by building a **modal maindeck** from `card_frequencies(con,
archetype, board="main", since, until)` (`{name: modal_count}`), the same "archetype's typical
60" role `card_frequencies` already plays for `advisory.sideboard._archetype_linchpins_and_cards`.
This is the one new judgment call not spelled out verbatim in the parent feature's Unit E1 sketch
— documenting it here rather than silently deciding. `recommend_sideboard` is called with its
default solver/collection/smart settings (no new CLI knobs for tuning the scorer call itself;
`advise sideboard` already owns those).

**Classification.** `recommended = tuple(sorted(pkg.cards.keys()))` (SideboardPackage's card
dict, names only — copy counts aren't part of the overlap/scorer-only/winners-only classification
per the parent feature's dataclass sketch). `overlap` = recommended ∩ {card: observed_frequency
>= 0.20}; `scorer_only` = recommended − overlap (a strict partition: `overlap | scorer_only ==
recommended`); `winners_only` = {card: observed_frequency >= 0.20} − recommended. All three are
sorted tuples for deterministic output/tests.

**Honest-degrade handling — two independent degrade axes, never a crash:**
1. **Winner-sample thinness**: `confidence = None` when `n_winning_decks == 0` (a stronger
   statement than `tier_for_sample(0)`'s `"speculative"` — literally nothing to compare
   against, vs. a thin-but-real signal), else `tier_for_sample(n_winning_decks)`. The CLI prints
   an explicit `// HONEST DEGRADE:` banner in both the zero-data and speculative-tier cases.
2. **Scorer failure**: `recommend_sideboard`/`card_frequencies` calls are wrapped in `try/except`
   — any exception (bad archetype string, missing field data, solver failure not already caught
   internally) degrades `recommended` to `()`, which flows naturally into the classification:
   every observed card reads as `winners_only` ("we have nothing to compare the scorer against"),
   which is itself an honest signal rather than a special-cased error path.
   Query failures on the top-finisher/observed-frequency side degrade the same way to `[]`/`{}`.

Never emits a pass/fail verdict anywhere (dataclass, CLI render, or docstrings) — only
resemblance, gated by confidence. The CLI's caveat line
(`// divergence is a signal to investigate, not proof of error (winning boards are self-selected
+ metagame-lagged)`) is printed unconditionally, even in the insufficient-data path, so it can
never be skipped by a future edit that only touches the "happy path" render branch.

**Files changed:**
- `src/legacy_engine/advisory/backtest.py` (new) — `BoardBacktest`, `backtest_board`,
  `_qualifying_top_finisher_decks`, `_observed_sideboard_frequency`.
- `src/legacy_engine/cli.py` — new `advise backtest` leaf, inserted directly after `advise
  sideboard`.
- `tests/test_backtest.py` (new) — hermetic file-backed DuckDB builder (`_build_backtest_db`,
  two 8-player tournaments, known Boulder top-finisher sideboard signal + deliberately-seeded
  non-qualifying decks with off-signal cards to prove the rank filter doesn't leak); 5 unit
  tests on `backtest_board` (classification, threshold boundary, empty-corpus, unknown-archetype,
  scorer-failure) + 2 CLI render tests (happy path + insufficient-data path), both asserting the
  caveat line verbatim. Also ran one un-mocked end-to-end CLI smoke invocation manually
  (`advise backtest` against the real `recommend_sideboard`) to confirm the real integration path
  degrades honestly (exit 0, no recommendation for a colorless test maindeck, all observed cards
  correctly fall to `winners_only`) rather than only trusting the monkeypatched unit tests.

**Test count:** 2464 passed (2457 pre-existing + 7 new: 5 unit + 2 CLI).

**Deviations from the parent feature sketch:** none structural — `BoardBacktest`'s fields,
`_TOP_FINISHER_QUANTILE`/`_OBSERVED_THRESHOLD` constants, and the CLI option set
(`--archetype --field --since --until --db`) match the spec exactly. The only addition beyond
the literal spec is `confidence: ConfidenceLevel | None` resolving to `None` (not
`tier_for_sample(0)` → `"speculative"`) at `n_winning_decks == 0`, a deliberate honest-degrade
refinement documented above.

**Escape hatch:** not used — no genuine design gap or out-of-scope bug surfaced.
