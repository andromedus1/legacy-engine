---
id: epic-advisory-output-honesty-coverage-consumers
kind: feature
stage: review
tags: [advisory, analytics, correctness]
parent: epic-advisory-output-honesty
depends_on: [epic-advisory-output-honesty-positioning-coverage]
release_binding: null
gate_origin: null
created: 2026-06-06
updated: 2026-06-14
---

# Coverage Honesty Across the Remaining Positioning Consumers

## Brief

`epic-advisory-output-honesty-positioning-coverage` made the single-deck `positioning_score` honest
(auto-restrict to the covered sub-field, refuse at zero coverage), but the coverage-honesty did not
propagate to the *other* surfaces that read S. This feature closes that gap so the toolset is
internally consistent — a user must never see two different "S" for the same deck at the same
coverage.

Primary issue (Important, from review of the foundation feature): the `--candidates` **ranking path
(`rank_decks`) still computes and prints a raw full-field S** (pulled toward 0.50 by imputation),
which contradicts the single-deck `advise positioning` output that now says "S vs covered sub-field".
Note the design tension: `rank_decks` deliberately uses a *shared* sampled field across all candidates
to make P(best) honest, so per-deck restriction is NOT a drop-in — the fix is likely to
annotate/caveat (or suppress) the S column for low-coverage decks rather than restrict each deck to a
different field. The feature design pass must resolve this without breaking the shared-field MC.

Also folds in the coverage-honesty nits surfaced in the same review:
- **`PositioningResult.imputed` is misleading when `restricted=True`** — it still lists the dropped
  no-data opponents and the "imputed N no-data opponent(s)" warning still fires, but the restricted S
  imputed nothing (those were excluded). Clear/relabel `imputed` (or suppress the warning) when
  restricted.
- **`advise report` audit line prints `s_mean=nan`** when `s_computable=False` (the user-facing render
  is correct; only the diagnostic audit line is ungated).
- **`generation/tuning.py` carries NaN into the tune result's `positioning_s`** when a tuned archetype
  has zero coverage (was ~0.50 before). Fall back to `None` when `not s_computable`. Context-only
  (not a swap driver), but it leaks NaN into displayed/serialized tune output.
- **`viz/deck_dashboard.py`** reads S from `rank_decks` (un-restricted), so it inherits the same
  ranking-path inconsistency — make it consistent with whatever the ranking-path fix chooses.

## Epic context
- Parent epic: `epic-advisory-output-honesty`
- Position in epic: follow-up to `positioning-coverage` — extends its honesty to the ranking, audit,
  tuning, and viz consumers. Filed from the foundation feature's fresh-context review.

## Inherited design decisions
- The single-deck `positioning_score` restriction semantics (auto-restrict < 0.85, refuse at zero
  coverage) are fixed; this feature makes the OTHER consumers consistent with them, NOT re-litigate
  them.
- `rank_decks`' shared-field MC for honest P(best) is load-bearing — do not break it to restrict S.

## Design

### Fix 1 — `rank_decks` S column for low-coverage decks

**Constraint**: `rank_decks` samples ONE shared field `(n_draws, m)` and scores all candidates against
it. Per-deck restriction to different sub-fields would break the correlation that makes P(best) honest.
So S values in `DeckRanking` are ALWAYS full-field — we cannot change what S means here.

**Resolution**: Add a `coverage_caveated` set to `DeckRanking` (parallel to `low_coverage`) populated
with any deck whose `data_coverage < _COVERAGE_RESTRICT_THRESHOLD` (0.85). This is the exact same
threshold that `positioning_score` uses to restrict the single-deck view — giving consumers a
consistent "this deck's S is a full-field estimate dominated by imputation" signal.

Consumers (primer in `deck_dashboard.py`, report CLI, specs) then annotate: "S (full-field, imputed)"
or dim/caveat the value. No MC change; only metadata propagated.

`DeckRanking` gains `coverage_caveated: set[str]` (always computed; default `set()`). The dashboard
`_primer_summary` uses it to append a caveat note. The viz `spec_positioning` already fades
low-coverage bars via `low_coverage` — we wire `coverage_caveated` as the threshold-consistent alias
for that (callers that currently pass `min_coverage=0.0` will now get the 0.85-threshold set for
free from `coverage_caveated`, without changing the existing `low_coverage` / `min_coverage` API).

### Fix 2 — `PositioningResult.imputed` misleading when `restricted=True`

When `restricted=True`, the scoring field is the covered sub-field. The excluded archetypes were
never scored against — they were dropped entirely, not imputed. Yet the current code builds
`all_imputed = imputed_set | field.no_data` using the FULL field's no-data list, so excluded
opponents appear in `imputed` and the "imputed N no-data opponent(s)" warning fires incorrectly.

**Fix**: When `restricted=True`, restrict `all_imputed` to only opponents in the scoring field
(the covered sub-field) that had no data. Specifically, build `all_imputed` by intersecting with
`frozenset(scoring_field_archetypes)` rather than full field archetypes. The excluded ones are
already reported in `excluded_archetypes` / `restrict_warning`. When `s_computable=False`, no
imputation happened at all — clear `all_imputed` to `frozenset()`.

### Fix 3 — `advise report` audit line gated

`build_field_read_report` (report.py line ~228) unconditionally formats `positioning.s_mean`
even when `s_computable=False` (NaN). The user-facing render in `_render_positioning` already gates
correctly; only the audit line is ungated.

**Fix**: Gate the audit line on `positioning.s_computable`. When False, write
`"positioning: s not computable — no covered matchups; data_coverage=..."` instead.

### Fix 4 — `tuning.py` NaN `positioning_s` + `viz/deck_dashboard.py` S consistency

**tuning.py**: After calling `positioning_score(...)`, if `pos.s_computable is False`, `pos.s_mean`
is NaN. The field `TunedDeck.positioning_s: float | None` is typed to allow None but the code
assigns `pos.s_mean` unconditionally. **Fix**: `positioning_s = pos.s_mean if pos.s_computable else None`.

**deck_dashboard.py**: `_primer_summary` uses `ranking.s_mean.get(archetype, 0.0)` — if a deck is
in `coverage_caveated`, the prose should note "S (full-field, low coverage)" rather than presenting
it as if it were the same restricted S that `advise positioning` would show. The fix is: check
`archetype in ranking.coverage_caveated` and append a caveat phrase. This is the consumer-side
consistency that Fix 1 enables.

### Tests

- `TestCoverageConsumers` class with:
  - `test_rank_decks_low_coverage_in_coverage_caveated`: deck below 0.85 threshold → in `coverage_caveated`
  - `test_rank_decks_full_coverage_not_caveated`: deck at 1.0 → not in `coverage_caveated`
  - `test_rank_decks_shared_field_mc_unchanged`: shared S values / p_best / pairwise unaffected
  - `test_imputed_cleared_when_restricted`: restricted result's `imputed` only contains scoring-field no-data
  - `test_imputed_empty_when_not_computable`: zero-coverage result's `imputed` is empty
  - `test_audit_line_gated_when_not_computable`: audit line does not contain `s_mean=nan`
  - `test_tune_deck_no_nan_positioning_s_at_zero_coverage`: `TunedDeck.positioning_s` is None when zero coverage
  - `test_primer_summary_caveats_low_coverage_deck`: caveat phrase present in primer HTML

## Implementation notes

### Fix 1 — `rank_decks` shared-field constraint resolved via annotation, not restriction

`DeckRanking` gained `coverage_caveated: set[str]` — always populated with decks below the
`_COVERAGE_RESTRICT_THRESHOLD` (0.85) threshold, regardless of `min_coverage`. The MC loop is
unchanged (one shared field, all candidates — P(best) is still honest). The CLI now renders `S*`
instead of `S` for caveated decks in the ranking output; `_primer_summary` in `deck_dashboard.py`
labels the S value as `"S (full-field, low coverage)"`. No change to the `min_coverage` / `low_coverage`
API — `coverage_caveated` is an additive field.

### Fix 2 — `imputed` scoped to the scoring field

When `restricted=True`, `_row_winrate_inputs` is re-run on the scoring (covered sub-field) archetypes
only, so `all_imputed` contains only opponents that were actually imputed in the MC (i.e., present in
the restricted field but still no-data). Excluded opponents are already tracked in `excluded_archetypes`.
When `s_computable=False`, `all_imputed` is set to `frozenset()` — no MC ran, nothing was imputed.
The pre-existing test `test_no_data_opponent_listed_in_imputed` was updated: it now uses a
high-coverage (≥ 0.85) scenario to verify the non-restricted imputed tracking, plus a new companion
test `test_no_data_opponent_in_excluded_when_restricted` covers the restricted case explicitly.

### Fix 3 — audit line gated

Single-line guard in `build_field_read_report`: `if positioning.s_computable:` routes to the
original `s_mean=...` format, else writes `"s not computable — no covered (n≥30) matchups..."`.

### Fix 4 — tuning NaN + viz consistency

`tune_deck`: `positioning_s = pos.s_mean if pos.s_computable else None` — one-line guard.
`deck_dashboard._primer_summary`: reads `ranking.coverage_caveated` (with `getattr` fallback for
robustness) to decide label. Tests for both are in `test_generation_tuning.py` and
`test_viz_deck_dashboard.py` respectively.

### Suite result

1957 tests pass (12 new; 1945 pre-existing all green). Ruff: 0 new lint errors (2 pre-existing
unused-import warnings in `positioning.py` pre-date this feature).
